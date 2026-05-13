import json
from typing import Any

ALLOWED_ACTIONS = {
    "search_repo",
    "read_file",
    "write_file",
    "ask_coder",
    "apply_patch",
    "run_command",
    "record_evidence",
    "finish",
}

REQUIRED_ARGS: dict[str, list[str]] = {
    "search_repo":    ["query"],
    "read_file":      ["path"],
    "write_file":     ["path", "content"],
    "ask_coder":      ["task", "files"],
    "apply_patch":    ["patch"],
    "run_command":    ["command"],
    "record_evidence": ["event", "details"],
    "finish":         [],
}


def validate_action(raw: Any) -> tuple[bool, str]:
    if not isinstance(raw, dict):
        return False, "Response is not a JSON object."

    action = raw.get("action")
    if not action:
        return False, "Missing 'action' field."
    if action not in ALLOWED_ACTIONS:
        return False, f"Unknown action '{action}'. Allowed: {sorted(ALLOWED_ACTIONS)}"

    args = raw.get("arguments", {})
    if not isinstance(args, dict):
        return False, "'arguments' must be a JSON object."

    for required in REQUIRED_ARGS.get(action, []):
        if required not in args:
            return False, f"Action '{action}' requires argument '{required}'."

    return True, ""


def extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None
