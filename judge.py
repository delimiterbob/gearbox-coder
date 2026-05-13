"""
Gearbox LLM-as-judge: scores a completed task run using Claude.

Usage:
    python judge.py --run-dir runs/2026-05-13-123456-qwen3-4b+phi4/compile_fix_001
    python judge.py --run-dir runs/2026-05-13-123456-qwen3-4b+phi4  # score all tasks in run
"""
import argparse
import json
from pathlib import Path

import anthropic

GEARBOX_ROOT = Path(__file__).parent
TASKS_PATH   = GEARBOX_ROOT / "tasks" / "benchmark_tasks.yaml"

# Claude model used for judging (matches MTS pattern: Opus for judging)
JUDGE_MODEL = "claude-opus-4-7"

JUDGE_SYSTEM = """\
You are an impartial benchmark evaluator for a local multi-model coding agent system called Gearbox.
You receive evidence from a single benchmark task run and score it on five criteria.
Respond with ONLY a JSON object — no prose before or after it.
"""

JUDGE_RUBRIC = """\
Score this Gearbox benchmark task run on the following criteria:

1. task_success (0 or 1): Did the final verification command pass? (1 = yes, 0 = no)
2. tool_call_reliability (0-10): Were controller tool calls valid, well-formed, and sensible?
   10 = all valid and appropriate
   7  = mostly valid, minor misfires
   4  = frequent invalid or misguided calls
   0  = mostly invalid or hallucinated
3. patch_quality (0-10): Was the patch minimal, correct, and clean?
   10 = minimal, correct, no regressions
   7  = correct but slightly verbose or imprecise
   4  = overly broad or risky changes
   0  = patch not applied or incorrect
4. iteration_efficiency (0-10): How efficiently did the controller reach a solution?
   10 = solved in 1-3 steps
   7  = 4-6 steps
   4  = 7-9 steps
   0  = hit max steps without finishing
5. evidence_completeness (0-10): Was the evidence ledger complete and informative?
   10 = all steps recorded with actor, action, latency, tokens
   5  = partially recorded
   0  = missing or corrupt

Respond with ONLY this JSON object:
{
  "task_success":          <0 or 1>,
  "tool_call_reliability": <0-10>,
  "patch_quality":         <0-10>,
  "iteration_efficiency":  <0-10>,
  "evidence_completeness": <0-10>,
  "weighted_score":        <computed: success*35 + reliability*2 + quality*2 + efficiency + completeness>,
  "grade":                 "A|B|C|D|F",
  "summary":               "One sentence summary of how the agent performed."
}
"""


def judge_task(task_dir: Path) -> dict:
    score_path = task_dir / "score.json"
    evidence_path = task_dir / "evidence.jsonl"

    if not score_path.exists():
        return {"error": f"No score.json in {task_dir}"}

    score_data = json.loads(score_path.read_text(encoding="utf-8"))

    evidence_lines = []
    if evidence_path.exists():
        evidence_lines = evidence_path.read_text(encoding="utf-8").strip().splitlines()[:50]
    evidence_sample = "\n".join(evidence_lines)

    user_content = (
        f"Task ID: {score_data.get('task_id', task_dir.name)}\n\n"
        f"Harness result:\n{json.dumps(score_data, indent=2)}\n\n"
        f"Evidence ledger (first 50 lines):\n{evidence_sample}\n\n"
        + JUDGE_RUBRIC
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=512,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text.strip()
    try:
        judgment = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            judgment = json.loads(raw[start:end+1])
        else:
            return {"error": "Judge returned non-JSON response.", "raw": raw}

    # Merge judgment into score.json
    merged = {**score_data, "judgment": judgment}
    score_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def main():
    parser = argparse.ArgumentParser(description="Gearbox LLM-as-judge scorer.")
    parser.add_argument("--run-dir", required=True,
                        help="Path to a task result dir or a run dir containing multiple tasks.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Directory not found: {run_dir}")
        return

    # If run_dir contains task subdirectories, score all of them
    task_dirs = [d for d in run_dir.iterdir() if d.is_dir() and (d / "score.json").exists()]
    if not task_dirs:
        # Treat run_dir itself as a task dir
        task_dirs = [run_dir]

    results = []
    for task_dir in sorted(task_dirs):
        print(f"  Judging {task_dir.name}...", end=" ", flush=True)
        result = judge_task(task_dir)
        judgment = result.get("judgment", {})
        grade = judgment.get("grade", "?")
        score = judgment.get("weighted_score", "?")
        print(f"Grade: {grade}  Score: {score}")
        results.append(result)

    print(f"\n  Judged {len(results)} tasks. Updated score.json files in {run_dir}")


if __name__ == "__main__":
    main()
