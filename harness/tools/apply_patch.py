import subprocess
import tempfile
from pathlib import Path

from harness.validators.patch_contract import validate_patch


def apply_patch(patch: str, workspace_root: Path) -> dict:
    valid, error = validate_patch(patch)
    if not valid:
        return {"success": False, "error": error}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".diff", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(patch)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["patch", "-p1", "--input", tmp_path],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        # Try git apply as fallback
        git_result = subprocess.run(
            ["git", "apply", "--whitespace=fix", tmp_path],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if git_result.returncode == 0:
            return {"success": True, "output": git_result.stdout}
        return {
            "success": False,
            "error": result.stderr or result.stdout or git_result.stderr,
        }
    except FileNotFoundError:
        return {"success": False, "error": "'patch' command not found. Install GNU patch."}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "patch command timed out."}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
