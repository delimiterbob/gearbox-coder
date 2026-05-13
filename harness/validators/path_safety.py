from pathlib import Path


def is_safe_path(requested: str, workspace_root: Path) -> bool:
    try:
        resolved = (workspace_root / requested).resolve()
        return resolved.is_relative_to(workspace_root.resolve())
    except (ValueError, OSError):
        return False
