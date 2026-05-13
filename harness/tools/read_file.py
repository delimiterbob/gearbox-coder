from pathlib import Path
from harness.validators.path_safety import is_safe_path


def read_file(
    path: str,
    workspace_root: Path,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict:
    if not is_safe_path(path, workspace_root):
        return {"error": f"Path '{path}' is outside the workspace."}

    fpath = workspace_root / path
    if not fpath.exists():
        return {"error": f"File not found: {path}"}
    if not fpath.is_file():
        return {"error": f"Not a file: {path}"}

    try:
        lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return {"error": str(exc)}

    total = len(lines)
    lo = (start_line - 1) if start_line else 0
    hi = end_line if end_line else total
    lo = max(0, lo)
    hi = min(total, hi)

    selected = lines[lo:hi]
    numbered = [f"{lo + i + 1}: {line}" for i, line in enumerate(selected)]
    return {
        "path": path,
        "total_lines": total,
        "start_line": lo + 1,
        "end_line": lo + len(selected),
        "content": "\n".join(numbered),
    }
