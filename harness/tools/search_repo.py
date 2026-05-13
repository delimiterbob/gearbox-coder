import subprocess
from pathlib import Path


def search_repo(query: str, path: str | None, workspace_root: Path) -> dict:
    search_dir = workspace_root
    if path:
        search_dir = workspace_root / path

    cmd = ["rg", "--line-number", "--with-filename", "--no-heading", query, str(search_dir)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        lines = result.stdout.strip().splitlines()
        matches = []
        for line in lines[:100]:  # cap at 100 results
            matches.append(line)
        return {"matches": matches, "count": len(matches), "truncated": len(lines) > 100}
    except FileNotFoundError:
        # rg not found; fall back to Python glob+search
        return _python_search(query, search_dir, workspace_root)
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out.", "matches": [], "count": 0}


def _python_search(query: str, search_dir: Path, workspace_root: Path) -> dict:
    matches = []
    try:
        for fpath in search_dir.rglob("*"):
            if not fpath.is_file():
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), 1):
                    if query.lower() in line.lower():
                        rel = fpath.relative_to(workspace_root)
                        matches.append(f"{rel}:{i}:{line.rstrip()}")
                        if len(matches) >= 100:
                            return {"matches": matches, "count": len(matches), "truncated": True}
            except (OSError, PermissionError):
                pass
    except OSError:
        pass
    return {"matches": matches, "count": len(matches), "truncated": False}
