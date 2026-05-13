from pathlib import Path

from harness.validators.path_safety import is_safe_path


def write_file(path: str, content: str, workspace_root: Path) -> dict:
    if not path.startswith("output/") and not path.startswith("output\\"):
        return {"success": False, "error": "write_file may only write inside output/."}

    if not is_safe_path(path, workspace_root):
        return {"success": False, "error": f"Path '{path}' escapes the workspace."}

    fpath = workspace_root / path
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_text(content, encoding="utf-8")
    return {"success": True, "path": path, "bytes": len(content.encode("utf-8"))}


def extract_file_bundle(text: str) -> dict[str, str]:
    """Parse coder output that uses '// FILE: path' markers into {path: content} dict."""
    files: dict[str, str] = {}
    current_path: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("// FILE:"):
            if current_path is not None:
                files[current_path] = "\n".join(current_lines).strip()
            current_path = stripped[len("// FILE:"):].strip()
            current_lines = []
        else:
            if current_path is not None:
                current_lines.append(line)

    if current_path is not None:
        files[current_path] = "\n".join(current_lines).strip()

    return files


def write_file_bundle(bundle: dict[str, str], workspace_root: Path) -> list[str]:
    """Write a parsed file bundle to disk. Returns list of paths written."""
    written = []
    for path, content in bundle.items():
        result = write_file(path, content, workspace_root)
        if result.get("success"):
            written.append(path)
    return written
