# Gearbox

**Local multi-model coding agent benchmark.**

Gearbox tests the thesis that *tool intelligence and coding intelligence are separate gears that can be combined through a deterministic harness*. A small tool-aware controller model drives an agentic loop; a stronger coding specialist produces the actual output. Neither model needs to be good at both.

The benchmark task is code migration — the same matrix used by the [Model Testing Suite](../Model%20Testing%20Suite): 13 legacy source languages, T1 and T2 test projects, migrated to three modern .NET/Angular targets. Verification is `dotnet build` or `npm run build`.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ Harness (Python)                                          │
│  - owns workspace (source/ + output/)                     │
│  - exposes safe tools                                     │
│  - validates every action                                 │
│  - writes output files from coder bundles                 │
│  - runs build commands                                    │
│  - records JSONL evidence                                 │
└──────────────┬───────────────────────────┬───────────────┘
               │                           │
               ▼                           ▼
┌─────────────────────────┐   ┌────────────────────────────┐
│ Controller              │   │ Coder (Phi-4 14B)           │
│ Qwen3-4B-Instruct       │   │                            │
│                         │   │ - reads source files        │
│ - chooses next action   │   │ - produces // FILE: bundles │
│ - requests tools        │   │ - produces fix patches      │
│ - never writes files    │   │ - no tool access            │
└─────────────────────────┘   └────────────────────────────┘
```

The controller runs on **port 8001**. The coder runs on **port 8002**. Both are served by `llama-server` from `I:\llama-cpp`.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| `llama-server.exe` | Located at `I:\llama-cpp\llama-server.exe` |
| GGUF models | Downloaded to `I:\gguf-models\` by `scripts\download_models.ps1` |
| Python 3.11+ | `pip install -r requirements.txt` |
| .NET 10 SDK | For `dotnet build` verification of BZ and WF targets |
| Node.js + npm | For `npm run build` verification of NG targets |
| ripgrep (`rg`) | Optional but recommended; `search_repo` falls back to Python if absent |
| Model Testing Suite | Located at `C:\Users\Admin\Desktop\Model Testing Suite` — read-only source of benchmark repos |

---

## Setup (one-time)

### 1. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 2. Copy source repos from MTS

```powershell
.\scripts\setup_repos.ps1
```

This copies T1-Calculator and T2-LoginDialog from each MTS source language into `repos/`. The MTS directory is never modified.

### 3. Download models

```powershell
.\scripts\download_models.ps1
```

Downloads via `curl` with resume support:
- **Controller:** `Qwen3-4B-Q4_K_M.gguf` (~2.5 GB) → `I:\gguf-models\`
- **Coder:** `phi-4-Q4_K_M.gguf` (~8.4 GB) → `I:\gguf-models\`

Use `-SkipController` or `-SkipCoder` if one is already present.

---

## Running a benchmark

### Start both servers

```powershell
.\scripts\start_servers.ps1
```

Starts `llama-server` on ports 8001 (controller) and 8002 (coder). GPU layers are auto-tuned for the RTX 5060 (8 GB VRAM). Use `-ControllerOnly` or `-CoderOnly` for single-server runs.

> **Resource note:** Do not start servers while other llama.cpp benchmarks (e.g., MTS) are running. Both share the same VRAM.

### Run a phase

```powershell
# Smoke: 5 tasks — T1 from 5 languages, BZ target
python -m harness.main --phase smoke --combo qwen3-4b+phi4

# Breadth: all T1+T2, BZ and WF targets
python -m harness.main --phase breadth --combo qwen3-4b+phi4

# Full: entire matrix (all languages × all tests × all targets)
python -m harness.main --phase full --combo qwen3-4b+phi4

# Restrict by target or language
python -m harness.main --phase breadth --target BZ --lang VB6

# Run specific tasks by ID
python -m harness.main --tasks VB6_T1-Calculator_BZ,Delphi_T1-Calculator_WF

# Skip tasks that already have a score.json
python -m harness.main --phase smoke --combo qwen3-4b+phi4 --skip-existing
```

### Stop servers

```powershell
.\scripts\stop_servers.ps1
```

### Judge results with LLM-as-judge

```powershell
# Score all tasks in a run
python judge.py --run-dir runs/2026-05-13-120000-qwen3-4b+phi4

# Score a single task
python judge.py --run-dir runs/2026-05-13-120000-qwen3-4b+phi4/VB6_T1-Calculator_BZ
```

Uses **Claude Opus** to score each task on 5 criteria (see [Scoring](#scoring)). Requires `ANTHROPIC_API_KEY` in the environment. Merges scores back into each task's `score.json`.

### Aggregate results

```powershell
python aggregate.py
```

Produces `runs/results.csv`, `runs/results.jsonl`, and `runs/by_combo.json` with per-combo pass rates and average scores.

---

## Baselines

Run the same tasks in single-model mode to measure the two-model system against alternatives:

```powershell
# Phi-4 acts as both controller and coder
python -m harness.main --phase smoke --baseline phi4-alone

# Controller model acts as both controller and coder
python -m harness.main --phase smoke --baseline controller-alone
```

---

## Task matrix

### Sources (13 languages, T1+T2)

| Language | T1 | T2 |
|---|:---:|:---:|
| CSharp-WinForms | ✓ | ✓ |
| VB.NET | ✓ | ✓ |
| VB6 | ✓ | ✓ |
| Delphi | ✓ | ✓ |
| PowerBuilder | ✓ | ✓ |
| Legacy-Java | ✓ | ✓ |
| Silverlight | ✓ | ✓ |
| FoxPro | ✓ | ✓ |
| Clarion | ✓ | ✓ |
| ASP-Classic | — | ✓ |
| ASP-WebForms | — | ✓ |
| Informix-4GL | — | ✓ |
| COBOL | ✓ | — |

### Targets

| Code | Name | Verification |
|---|---|---|
| `BZ` | C# Blazor Server .NET 10 | `dotnet build output` |
| `WF` | C# WinForms .NET 10 | `dotnet build output` |
| `NG` | C# .NET 10 + Angular | `npm run build` (in `output/ClientApp`) |

### Phases

| Phase | Tasks | Filter |
|---|---|---|
| `smoke` | 5 | T1 from 5 representative languages, BZ only |
| `breadth` | ~22 | All available T1+T2, BZ and WF only |
| `full` | ~66 | All available T1+T2, all three targets |

Task IDs follow the pattern `{lang}_{test}_{target}` (e.g., `VB6_T1-Calculator_BZ`).

---

## Scoring

### Harness metrics (automatic)

| Metric | Description |
|---|---|
| `success` | Did the verification command exit with code 0? |
| `steps` | Number of controller actions taken |
| `wall_clock_s` | Total seconds for the task |

### Judge criteria (LLM-as-judge via Claude Opus)

| Criterion | Weight | Description |
|---|---|---|
| `task_success` | 35 pts | Final build passed (0 or 1) |
| `tool_call_reliability` | 0–10 | Controller actions valid and well-chosen |
| `patch_quality` | 0–10 | Migration output minimal, correct, no regressions |
| `iteration_efficiency` | 0–10 | Solved in few steps |
| `evidence_completeness` | 0–10 | Full JSONL trace captured |

**Weighted score:** `success×35 + reliability×2 + quality×2 + efficiency + completeness`

**Grades:** A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F < 60

### Scorecard weights (combo comparison)

```yaml
task_success_rate:   0.35
tool_call_reliability: 0.20
patch_quality:       0.20
speed:               0.10
resource_fit:        0.10
evidence_quality:    0.05
```

---

## Agent workflow

For each task, the harness:

1. Copies the source repo into `workspace/{run_id}/{task_id}/source/`
2. Creates an empty `workspace/{run_id}/{task_id}/output/`
3. Writes a `PLAN.md` with task description, target spec, and success criteria
4. Runs the controller loop (up to 12 steps)

The controller follows this pattern:

```
read PLAN.md → read source files → record_evidence (root understanding)
→ ask_coder (full migration) → harness writes // FILE: bundle to output/
→ run_command (dotnet build output) → if fail: ask_coder (fix) → apply_patch
→ run_command again → finish (when build passes)
```

---

## Evidence ledger

Every step is recorded as a JSONL entry in `runs/{run_id}/{task_id}/evidence.jsonl`:

```json
{"run_id": "2026-05-13-...", "task_id": "VB6_T1-Calculator_BZ", "step": 0, "actor": "controller", "action": "read_file", "output_valid": true, "latency_ms": 312, "tokens_prompt": 980, "tokens_completion": 88}
{"run_id": "2026-05-13-...", "task_id": "VB6_T1-Calculator_BZ", "step": 2, "actor": "phi4", "action": "produce_migration", "latency_ms": 18400, "tokens_prompt": 4200, "tokens_completion": 2100, "files_written": 7}
{"run_id": "2026-05-13-...", "task_id": "VB6_T1-Calculator_BZ", "step": 3, "actor": "harness", "action": "run_command", "command": "dotnet build output", "exit_code": 0, "success": true}
```

---

## Run output structure

```
runs/
  {run_id}/
    summary.json              ← pass/fail counts for the run
    {task_id}/
      evidence.jsonl          ← per-step event log
      score.json              ← harness result + judge scores (after judge.py)
      workspace/
        PLAN.md
        source/               ← copy of legacy source files
        output/               ← agent-generated migration
```

---

## Model configuration

Edit `config/models.yaml` to change endpoints, temperatures, or model files:

```yaml
models:
  controller:
    name: qwen3-4b-instruct
    endpoint: http://127.0.0.1:8001/v1
    temperature: 0.1
    max_tokens: 2048
    gguf_filename: Qwen3-4B-Q4_K_M.gguf

  coder:
    name: phi-4
    endpoint: http://127.0.0.1:8002/v1
    temperature: 0.1
    max_tokens: 4096
    gguf_filename: phi-4-Q4_K_M.gguf
```

Alternative controller pairings for Phase 5 benchmarking (Phi-4-mini, Qwen3-8B) are also defined in `config/models.yaml`.

---

## Project structure

```
GearBox/
├── config/
│   ├── models.yaml           ← model endpoints, GGUF filenames, HuggingFace URLs
│   ├── tools.yaml            ← tool schema definitions
│   └── scoring.yaml          ← scorecard weights and criteria
├── harness/
│   ├── main.py               ← CLI entry point; phase runner
│   ├── agent_loop.py         ← controller loop, workspace setup, tool dispatch
│   ├── controller_client.py  ← OpenAI-compatible client for Qwen3-4B
│   ├── coder_client.py       ← OpenAI-compatible client for Phi-4
│   ├── evidence.py           ← JSONL ledger writer
│   ├── tools/
│   │   ├── search_repo.py    ← ripgrep wrapper with Python fallback
│   │   ├── read_file.py      ← line-range file reader
│   │   ├── write_file.py     ← output/ writer + // FILE: bundle extractor
│   │   ├── apply_patch.py    ← unified diff applicator
│   │   └── run_command.py    ← allowlisted command runner with optional cwd
│   └── validators/
│       ├── json_contract.py  ← action schema validation + JSON extraction
│       ├── patch_contract.py ← unified diff format check
│       └── path_safety.py    ← workspace escape prevention
├── prompts/
│   ├── controller_system.md  ← controller persona and rules
│   ├── coder_system.md       ← coder output format rules
│   ├── migration-system.md   ← shared migration rules (from MTS)
│   ├── migrate-to-blazor.md  ← BZ target spec (from MTS)
│   ├── migrate-to-winforms.md← WF target spec (from MTS)
│   └── migrate-to-angular.md ← NG target spec (from MTS)
├── tasks/
│   └── benchmark_tasks.yaml  ← target definitions, source matrix, phase filters
├── scripts/
│   ├── setup_repos.ps1       ← copy T1+T2 sources from MTS into repos/
│   ├── download_models.ps1   ← download controller + coder GGUFs
│   ├── start_servers.ps1     ← start llama-server on ports 8001 + 8002
│   └── stop_servers.ps1      ← stop both instances
├── judge.py                  ← LLM-as-judge scorer (Claude Opus)
├── aggregate.py              ← CSV/JSON rollup across all runs
├── requirements.txt
└── gearbox_llamacpp_benchmark_plan.md  ← original design spec
```

> **`repos/` is not committed.** Run `.\scripts\setup_repos.ps1` to populate it from MTS.
> **`runs/` and `workspaces/` are not committed.** These are generated at runtime.

---

## Acceptance criteria

The two-model architecture is worth continuing if (from the design spec):

- Controller produces valid actions ≥ 90% of the time
- Controller selects useful tools ≥ 80% of the time
- End-to-end task success improves over Phi-4 alone by ≥ 20 percentage points
- Median task completes in fewer than 6 controller steps
- Unsafe tool request rate is near zero

Strong success threshold: end-to-end task success > 70% on the smoke benchmark.
