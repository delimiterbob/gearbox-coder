"""
Gearbox aggregate: roll up all run results into summary CSV and JSON.

Usage:
    python aggregate.py
    python aggregate.py --runs-dir runs
"""
import argparse
import csv
import json
from pathlib import Path

GEARBOX_ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description="Aggregate Gearbox benchmark results.")
    parser.add_argument("--runs-dir", default="runs",
                        help="Directory containing run subdirectories.")
    args = parser.parse_args()

    runs_dir = GEARBOX_ROOT / args.runs_dir
    if not runs_dir.exists():
        print(f"No runs directory at {runs_dir}")
        return

    rows = []
    by_combo: dict[str, list[dict]] = {}

    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        combo = _extract_combo(run_id)

        for task_dir in sorted(run_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            score_path = task_dir / "score.json"
            if not score_path.exists():
                continue

            data = json.loads(score_path.read_text(encoding="utf-8"))
            judgment = data.get("judgment", {})

            row = {
                "run_id":                run_id,
                "combo":                 combo,
                "task_id":               data.get("task_id", task_dir.name),
                "success":               int(data.get("success", False)),
                "steps":                 data.get("steps", ""),
                "wall_clock_s":          data.get("wall_clock_s", ""),
                "task_success":          judgment.get("task_success", ""),
                "tool_call_reliability": judgment.get("tool_call_reliability", ""),
                "patch_quality":         judgment.get("patch_quality", ""),
                "iteration_efficiency":  judgment.get("iteration_efficiency", ""),
                "evidence_completeness": judgment.get("evidence_completeness", ""),
                "weighted_score":        judgment.get("weighted_score", ""),
                "grade":                 judgment.get("grade", ""),
                "summary":               judgment.get("summary", ""),
            }
            rows.append(row)
            by_combo.setdefault(combo, []).append(row)

    if not rows:
        print("No scored tasks found.")
        return

    # Write CSV
    csv_path = runs_dir / "results.csv"
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {csv_path}")

    # Write JSONL
    jsonl_path = runs_dir / "results.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"  Wrote {jsonl_path}")

    # Per-combo summary
    combo_summary = {}
    for combo, combo_rows in by_combo.items():
        n = len(combo_rows)
        passed = sum(r["success"] for r in combo_rows)
        scores = [r["weighted_score"] for r in combo_rows if isinstance(r["weighted_score"], (int, float))]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        steps = [r["steps"] for r in combo_rows if isinstance(r.get("steps"), (int, float))]
        avg_steps = round(sum(steps) / len(steps), 1) if steps else None
        combo_summary[combo] = {
            "total": n,
            "passed": passed,
            "failed": n - passed,
            "pass_rate": round(passed / n, 3) if n else 0,
            "avg_weighted_score": avg_score,
            "avg_steps": avg_steps,
        }

    summary_path = runs_dir / "by_combo.json"
    summary_path.write_text(json.dumps(combo_summary, indent=2), encoding="utf-8")
    print(f"  Wrote {summary_path}")

    # Print scorecard table
    print(f"\n  {'Combo':<30} {'Pass':>5} {'Total':>6} {'Pass%':>6} {'AvgScore':>9} {'AvgSteps':>9}")
    print(f"  {'-'*30} {'-'*5} {'-'*6} {'-'*6} {'-'*9} {'-'*9}")
    for combo, s in sorted(combo_summary.items()):
        pct = f"{s['pass_rate']*100:.0f}%"
        avg = str(s['avg_weighted_score']) if s['avg_weighted_score'] is not None else "-"
        steps = str(s['avg_steps']) if s['avg_steps'] is not None else "-"
        print(f"  {combo:<30} {s['passed']:>5} {s['total']:>6} {pct:>6} {avg:>9} {steps:>9}")
    print()


def _extract_combo(run_id: str) -> str:
    # run_id format: 2026-05-13-123456-combo-name
    parts = run_id.split("-", 4)
    return parts[4] if len(parts) > 4 else run_id


if __name__ == "__main__":
    main()
