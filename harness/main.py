"""
Gearbox harness entry point.

Usage:
    python -m harness.main --phase smoke
    python -m harness.main --phase breadth --combo qwen3-4b+phi4
    python -m harness.main --phase full --target BZ
    python -m harness.main --phase smoke --baseline phi4-alone
    python -m harness.main --tasks VB6_T1-Calculator_BZ,Delphi_T1-Calculator_WF
"""
import argparse
import json
import shutil
import time
from pathlib import Path

import yaml

from harness.agent_loop import run_task, setup_workspace
from harness.controller_client import ControllerClient
from harness.coder_client import CoderClient
from harness.evidence import EvidenceLedger

GEARBOX_ROOT = Path(__file__).parent.parent
CONFIG_PATH  = GEARBOX_ROOT / "config" / "models.yaml"
TASKS_PATH   = GEARBOX_ROOT / "tasks" / "benchmark_tasks.yaml"
REPOS_ROOT   = GEARBOX_ROOT / "repos"
PROMPTS_ROOT = GEARBOX_ROOT / "prompts"


def main():
    parser = argparse.ArgumentParser(description="Gearbox multi-model migration benchmark harness.")
    parser.add_argument("--phase", choices=["smoke", "breadth", "full"], default="smoke")
    parser.add_argument("--target", choices=["BZ", "WF", "NG", "all"], default="all",
                        help="Restrict to a specific migration target.")
    parser.add_argument("--lang", default="",
                        help="Restrict to a specific source language (e.g. VB6).")
    parser.add_argument("--tasks", default="",
                        help="Comma-separated task IDs to run (overrides --phase).")
    parser.add_argument("--combo", default="qwen3-4b+phi4",
                        help="Controller+coder combo label for run directory naming.")
    parser.add_argument("--baseline", default="",
                        choices=["", "phi4-alone", "controller-alone"],
                        help="Run a baseline mode instead of the two-model system.")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip tasks that already have a score.json.")
    args = parser.parse_args()

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    task_spec = yaml.safe_load(TASKS_PATH.read_text(encoding="utf-8"))

    # Expand task matrix
    all_tasks = _expand_tasks(task_spec, config)

    # Filter
    if args.tasks:
        task_ids = {t.strip() for t in args.tasks.split(",")}
        tasks = [t for t in all_tasks if t["id"] in task_ids]
    else:
        tasks = _filter_phase(all_tasks, task_spec, args.phase)
        if args.target != "all":
            tasks = [t for t in tasks if t["target"] == args.target]
        if args.lang:
            tasks = [t for t in tasks if t["lang"] == args.lang]

    if not tasks:
        print("No tasks matched. Check --phase, --target, or --lang.")
        return

    run_id = f"{time.strftime('%Y-%m-%d-%H%M%S')}-{args.combo}"
    run_dir = GEARBOX_ROOT / config["runtime"]["evidence_root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  GEARBOX BENCHMARK")
    print(f"  Combo:  {args.combo}")
    print(f"  Phase:  {args.phase}")
    print(f"  Tasks:  {len(tasks)}")
    print(f"  Run ID: {run_id}")
    print(f"{'='*60}\n")

    controller, coder = _build_clients(args, config)

    results = []
    for task in tasks:
        task_id = task["id"]
        result_dir = run_dir / task_id
        score_path = result_dir / "score.json"

        if args.skip_existing and score_path.exists():
            print(f"  [SKIP] {task_id}")
            continue

        repo_path = REPOS_ROOT / task["lang"] / task["test"]
        if not repo_path.exists():
            print(f"  [MISS] {task_id}: repo not found at {repo_path}. Run setup_repos.ps1.")
            results.append({"task_id": task_id, "success": False, "reason": "repo_missing"})
            continue

        print(f"  [{task_id}] Starting...")
        workspace = result_dir / "workspace"
        setup_workspace(task, repo_path, workspace)

        ledger = EvidenceLedger(result_dir / "evidence.jsonl", run_id, task_id)

        t0 = time.time()
        try:
            outcome = run_task(task, workspace, controller, coder, ledger, config)
        except Exception as exc:
            outcome = {"success": False, "steps": 0, "reason": str(exc)}
        elapsed = round(time.time() - t0, 1)

        outcome["task_id"] = task_id
        outcome["wall_clock_s"] = elapsed
        outcome["run_id"] = run_id

        ledger.close()
        result_dir.mkdir(parents=True, exist_ok=True)
        score_path.write_text(json.dumps(outcome, indent=2), encoding="utf-8")

        status = "PASS" if outcome.get("success") else "FAIL"
        print(f"  [{task_id}] {status}  steps={outcome.get('steps','?')}  {elapsed}s")
        results.append(outcome)

    summary = {
        "run_id": run_id,
        "combo": args.combo,
        "phase": args.phase,
        "total": len(results),
        "passed": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "task_results": results,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  RESULTS: {summary['passed']}/{summary['total']} passed")
    print(f"  Evidence: {run_dir}")
    print(f"{'='*60}\n")


def _expand_tasks(task_spec: dict, config: dict) -> list[dict]:
    """Expand sources × targets into individual task dicts."""
    targets = task_spec["targets"]
    sources = task_spec["sources"]
    tasks = []

    system_spec = (PROMPTS_ROOT / "migration-system.md").read_text(encoding="utf-8")

    for src in sources:
        lang = src["lang"]
        for test in src["tests"]:
            for target_code, tgt in targets.items():
                prompt_file = GEARBOX_ROOT / tgt["prompt_file"]
                target_spec = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
                task_id = f"{lang}_{test}_{target_code}"
                tasks.append({
                    "id":             task_id,
                    "lang":           lang,
                    "test":           test,
                    "target":         target_code,
                    "target_name":    tgt["name"],
                    "target_spec":    target_spec,
                    "system_spec":    system_spec,
                    "verify_command": tgt["verify_command"],
                    "verify_cwd":     tgt.get("verify_cwd"),
                    "success":        tgt["success"],
                })
    return tasks


def _filter_phase(all_tasks: list[dict], task_spec: dict, phase: str) -> list[dict]:
    if phase == "smoke":
        smoke_ids = {
            f"{t['lang']}_{t['test']}_{t['target']}"
            for t in task_spec["phases"]["smoke"]["tasks"]
        }
        return [t for t in all_tasks if t["id"] in smoke_ids]
    if phase == "breadth":
        return [t for t in all_tasks if t["target"] in ("BZ", "WF")]
    return all_tasks  # full


def _build_clients(args, config: dict) -> tuple[ControllerClient, CoderClient]:
    ctrl_cfg = config["models"]["controller"]
    coder_cfg = config["models"]["coder"]

    if args.baseline == "phi4-alone":
        controller = ControllerClient(
            coder_cfg["endpoint"], coder_cfg["name"],
            coder_cfg["temperature"], coder_cfg["max_tokens"],
        )
        coder = CoderClient(
            coder_cfg["endpoint"], coder_cfg["name"],
            coder_cfg["temperature"], coder_cfg["max_tokens"],
        )
    elif args.baseline == "controller-alone":
        controller = ControllerClient(
            ctrl_cfg["endpoint"], ctrl_cfg["name"],
            ctrl_cfg["temperature"], ctrl_cfg["max_tokens"],
        )
        coder = CoderClient(
            ctrl_cfg["endpoint"], ctrl_cfg["name"],
            ctrl_cfg["temperature"], ctrl_cfg["max_tokens"],
        )
    else:
        controller = ControllerClient(
            ctrl_cfg["endpoint"], ctrl_cfg["name"],
            ctrl_cfg["temperature"], ctrl_cfg["max_tokens"],
        )
        coder = CoderClient(
            coder_cfg["endpoint"], coder_cfg["name"],
            coder_cfg["temperature"], coder_cfg["max_tokens"],
        )
    return controller, coder


if __name__ == "__main__":
    main()
