import subprocess
import time
from pathlib import Path

from harness.validators.path_safety import is_safe_path


def run_command(
    command: str,
    workspace_root: Path,
    allowlist: list[str],
    cwd: str | None = None,
) -> dict:
    if not _is_allowed(command, allowlist):
        return {
            "success": False,
            "exit_code": -1,
            "error": f"Command '{command}' is not in the allowlist: {allowlist}",
        }

    run_dir = workspace_root
    if cwd:
        if not is_safe_path(cwd, workspace_root):
            return {"success": False, "exit_code": -1, "error": f"cwd '{cwd}' escapes workspace."}
        run_dir = workspace_root / cwd
        if not run_dir.exists():
            return {"success": False, "exit_code": -1, "error": f"cwd '{cwd}' does not exist."}

    t0 = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(run_dir),
            capture_output=True,
            text=True,
            timeout=180,
        )
        elapsed = round(time.time() - t0, 2)
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-6000:] if result.stdout else "",
            "stderr": result.stderr[-3000:] if result.stderr else "",
            "duration_s": elapsed,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "exit_code": -1, "error": "Command timed out after 180s."}
    except OSError as exc:
        return {"success": False, "exit_code": -1, "error": str(exc)}


def _is_allowed(command: str, allowlist: list[str]) -> bool:
    cmd = command.strip()
    return any(cmd == allowed or cmd.startswith(allowed + " ") for allowed in allowlist)
