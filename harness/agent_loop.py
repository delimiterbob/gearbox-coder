"""
Main agentic loop: controller drives migration, coder produces file bundles,
harness executes tools and writes output files.
"""
import json
import shutil
import time
from pathlib import Path
from typing import Any

from harness.controller_client import ControllerClient
from harness.coder_client import CoderClient
from harness.evidence import EvidenceLedger
from harness.validators.json_contract import validate_action
from harness.validators.path_safety import is_safe_path
from harness.tools.search_repo import search_repo
from harness.tools.read_file import read_file
from harness.tools.write_file import write_file, extract_file_bundle, write_file_bundle
from harness.tools.apply_patch import apply_patch
from harness.tools.run_command import run_command


def run_task(
    task: dict,
    workspace_root: Path,
    controller: ControllerClient,
    coder: CoderClient,
    ledger: EvidenceLedger,
    config: dict,
) -> dict:
    allow_commands: list[str] = config["runtime"]["allow_commands"]
    max_steps: int = config["runtime"]["max_steps_per_task"]

    # Build initial controller state message
    system_prompt = _load_controller_system()
    initial_user = _build_initial_message(task, workspace_root)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_user},
    ]

    last_action_key: str = ""
    repeat_count: int = 0

    for step in range(max_steps):
        action, latency_ms, prompt_tok, completion_tok = controller.ask(messages)

        if action is None:
            ledger.record(
                step=step, actor="controller", action="parse_failure",
                output_valid=False, latency_ms=latency_ms,
                tokens_prompt=prompt_tok, tokens_completion=completion_tok,
            )
            messages.append({"role": "user", "content":
                "Your response could not be parsed as valid JSON. "
                "Emit exactly one JSON object matching the required schema."})
            continue

        action_name = action.get("action", "")
        valid, error = validate_action(action)

        ledger.record(
            step=step, actor="controller", action=action_name,
            output_valid=valid, latency_ms=latency_ms,
            tokens_prompt=prompt_tok, tokens_completion=completion_tok,
            thought_summary=action.get("thought_summary", ""),
        )

        if not valid:
            for msg in controller.build_tool_result_message(action, {"error": error}):
                messages.append(msg)
            continue

        # Detect repeat loops
        action_key = f"{action_name}:{json.dumps(action.get('arguments', {}), sort_keys=True)}"
        if action_key == last_action_key:
            repeat_count += 1
        else:
            repeat_count = 0
        last_action_key = action_key

        if repeat_count >= 2:
            feedback = {"error": "You have repeated the same action twice with no progress. Change strategy."}
            for msg in controller.build_tool_result_message(action, feedback):
                messages.append(msg)
            continue

        if action_name == "finish":
            ledger.record(step=step, actor="harness", action="finish", success=True)
            return {"success": True, "steps": step + 1}

        result = _dispatch(
            action_name, action.get("arguments", {}),
            workspace_root, coder, allow_commands, ledger, step, task,
        )

        for msg in controller.build_tool_result_message(action, result):
            messages.append(msg)

    return {"success": False, "steps": max_steps, "reason": "max_steps_exceeded"}


def setup_workspace(task: dict, repo_root: Path, workspace_root: Path) -> None:
    """Create workspace with source/ (repo copy) and empty output/ directory."""
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True)

    # source/ = copy of repo files
    source_dir = workspace_root / "source"
    shutil.copytree(repo_root, source_dir)

    # output/ = empty, agent writes here
    (workspace_root / "output").mkdir()

    # Write PLAN.md
    plan = _build_plan_md(task)
    (workspace_root / "PLAN.md").write_text(plan, encoding="utf-8")


def _dispatch(
    action: str,
    args: dict,
    workspace_root: Path,
    coder: CoderClient,
    allow_commands: list[str],
    ledger: EvidenceLedger,
    step: int,
    task: dict,
) -> Any:
    if action == "search_repo":
        result = search_repo(args["query"], args.get("path"), workspace_root)
        ledger.record(step=step, actor="harness", action="search_repo",
                      match_count=result.get("count", 0))
        return result

    if action == "read_file":
        result = read_file(
            args["path"], workspace_root,
            args.get("start_line"), args.get("end_line"),
        )
        ledger.record(step=step, actor="harness", action="read_file",
                      path=args["path"], found="error" not in result)
        return result

    if action == "write_file":
        result = write_file(args["path"], args["content"], workspace_root)
        ledger.record(step=step, actor="harness", action="write_file",
                      path=args["path"], success=result.get("success", False))
        return result

    if action == "ask_coder":
        files_requested: list[str] = args.get("files", [])
        file_excerpts: dict[str, str] = {}
        for fpath in files_requested:
            fr = read_file(fpath, workspace_root)
            if "error" not in fr:
                file_excerpts[fpath] = fr["content"]

        patch, latency_ms, prompt_tok, completion_tok = coder.ask(
            task=args["task"],
            file_excerpts=file_excerpts,
            constraints=args.get("constraints"),
            build_output=args.get("build_output"),
            target_spec=task.get("target_spec", ""),
        )

        # Auto-detect and write file bundles from coder response
        bundle = extract_file_bundle(patch)
        files_written: list[str] = []
        if bundle:
            files_written = write_file_bundle(bundle, workspace_root)
            ledger.record(
                step=step, actor="phi4", action="produce_migration",
                latency_ms=latency_ms, tokens_prompt=prompt_tok,
                tokens_completion=completion_tok, files_written=len(files_written),
            )
            return {"files_written": files_written, "mode": "migrate"}

        # No bundle markers — treat as patch
        ledger.record(
            step=step, actor="phi4", action="produce_patch",
            latency_ms=latency_ms, tokens_prompt=prompt_tok,
            tokens_completion=completion_tok, patch_length=len(patch),
        )
        return {"patch": patch, "mode": "fix"}

    if action == "apply_patch":
        result = apply_patch(args["patch"], workspace_root)
        ledger.record(step=step, actor="harness", action="apply_patch",
                      patch_applied=result.get("success", False))
        return result

    if action == "run_command":
        result = run_command(
            args["command"], workspace_root, allow_commands,
            cwd=args.get("cwd"),
        )
        ledger.record(step=step, actor="harness", action="run_command",
                      command=args["command"], exit_code=result.get("exit_code"),
                      success=result.get("success", False))
        return result

    if action == "record_evidence":
        ledger.record(step=step, actor="controller", action="record_evidence",
                      event=args.get("event"), details=args.get("details", {}))
        return {"recorded": True}

    return {"error": f"Unknown action: {action}"}


def _build_initial_message(task: dict, workspace_root: Path) -> str:
    source_dir = workspace_root / "source"
    files = sorted(source_dir.rglob("*"))
    file_list = "\n".join(
        f"  source/{f.relative_to(source_dir)}" for f in files if f.is_file()
    )
    return (
        f"Read PLAN.md for the full task description.\n\n"
        f"Source files available in source/:\n{file_list}\n\n"
        f"Write all migrated output files to output/.\n"
        f"When the build passes, call finish."
    )


def _build_plan_md(task: dict) -> str:
    target_name = task.get("target_name", task.get("target", ""))
    target_spec = task.get("target_spec", "")
    system_spec = task.get("system_spec", "")
    return (
        f"# Migration Task\n\n"
        f"**Source language:** {task['lang']}\n"
        f"**Test:** {task['test']}\n"
        f"**Target:** {target_name}\n\n"
        f"## Task\n\n"
        f"Read every file in `source/` to understand the legacy code. "
        f"Migrate it to a complete {target_name} project written to `output/`. "
        f"When the output project builds successfully, call finish.\n\n"
        f"## Verification command\n\n"
        f"```\n{task['verify_command']}\n```\n\n"
        f"## Success criteria\n\n"
        f"{task['success']}\n\n"
        f"## Migration rules\n\n"
        f"{system_spec}\n\n"
        f"## Target stack specification\n\n"
        f"{target_spec}\n"
    )


def _load_controller_system() -> str:
    from pathlib import Path as P
    prompt_path = P(__file__).parent.parent / "prompts" / "controller_system.md"
    return prompt_path.read_text(encoding="utf-8")
