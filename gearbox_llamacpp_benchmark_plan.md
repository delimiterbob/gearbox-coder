# Gearbox: Local Tool-Aware Coding Agent Benchmark Plan for llama.cpp

**Date:** 2026-05-13  
**Project Name:** Gearbox  
**Purpose:** Evaluate whether a capable-but-not-native-tool-calling coding model such as **Phi-4 14B GGUF** can be made effective for local agentic coding work by pairing it with a smaller **tool-aware controller model** and a deterministic harness. The name **Gearbox** reflects the core thesis: tool intelligence and coding intelligence are separate gears that can be combined through a harness.

---

## 1. Executive Summary

**Gearbox** is a local-agent experiment that separates responsibilities across three layers: a tool-aware controller, a smart coding specialist, and a deterministic harness. The point is not that one model must be good at everything; the point is to test whether the right combination of gears produces a reliable agentic coding workflow on a desktop.

The recommended starting architecture is:

```text
Harness = the real agent
Tool-aware controller model = chooses actions and requests tools
Phi-4 14B = bounded coding specialist
Compiler/tests/parity checks = judge
```

The first pairing to benchmark should be:

```text
Qwen3-4B-Instruct-2507 controller + Phi-4 14B coder
```

Why this pairing:

- **Phi-4 14B** appears strong enough to be useful as a focused coding worker.
- **Qwen3-4B-Instruct-2507** is small enough for local experimentation and is explicitly positioned for tool-calling / agentic use.
- **llama.cpp / llama-server** supports OpenAI-style chat completions and function/tool calling through Jinja chat templates.
- The harness can keep tool execution deterministic, auditable, and safe.

The goal is not to prove that Phi-4 is a native agent. The goal is to prove the **Gearbox** thesis: a model can contribute useful coding work inside an agentic system where tool use, state, execution, and verification are owned by the harness/controller layer.

---

## 2. Core Hypothesis

### Hypothesis

A non-tool-native but capable coding model can perform useful agentic coding work when:

1. A tool-aware controller selects actions.
2. The harness executes tools and owns state.
3. Phi-4 receives focused coding tasks rather than full agent responsibilities.
4. Deterministic checks validate each proposed patch.

### What This Benchmark Should Prove

The benchmark should answer:

1. Does the controller reliably choose the right tool/action?
2. Does the controller produce parseable tool requests?
3. Does Phi-4 produce useful patches when given focused context?
4. Does the combined system outperform Phi-4 acting alone as both controller and coder?
5. How much additional complexity is introduced?
6. Which controller model gives the best quality/speed/stability tradeoff on a desktop?

---

## 3. Recommended Model Combinations

### Primary Recommendation

| Rank | Controller Model | Coder Model | Why |
|---:|---|---|---|
| 1 | `Qwen3-4B-Instruct-2507` | `Phi-4 14B GGUF` | Best default experiment: small, tool-capable controller plus strong coding worker. |

### Alternatives to Benchmark

| Rank | Controller Model | Coder Model | Best Use |
|---:|---|---|---|
| 2 | `Phi-4-mini-instruct` | `Phi-4 14B GGUF` | Same-family Microsoft experiment with explicit function-calling format. |
| 3 | `Command R7B` | `Phi-4 14B GGUF` | Strong practical router / tool-use model, but heavier than Qwen3-4B. |
| 4 | `Functionary-small-v3.2` | `Phi-4 14B GGUF` | Dedicated function-calling controller; likely good at structured tool decisions. |
| 5 | `Hermes 2 Pro / Hermes 3 8B` | `Phi-4 14B GGUF` | Good function-calling / JSON behavior; test for over-creativity. |
| 6 | `Mistral NeMo 12B Instruct` | `Phi-4 14B GGUF` | Stronger but probably too heavy for comfortable simultaneous local desktop use. |

### Baselines

Benchmark these baselines to make the result meaningful:

| Baseline | Purpose |
|---|---|
| Phi-4 alone, no tools | Measures raw coding ability only. |
| Phi-4 alone with forced JSON/tool schema | Measures whether prompting alone is enough. |
| Controller alone as coder | Measures whether the controller is good enough without Phi-4. |
| Qwen3-4B + Phi-4 | Recommended two-model architecture. |

---

## 4. Target Architecture

```text
┌─────────────────────────────────────────────────────────┐
│ Harness                                                  │
│                                                         │
│ - owns repo workspace                                    │
│ - exposes safe tools                                     │
│ - validates tool calls                                   │
│ - applies patches                                        │
│ - runs build/test/lint                                   │
│ - records evidence                                       │
│ - controls retry loop                                    │
└───────────────┬─────────────────────────┬───────────────┘
                │                         │
                ▼                         ▼
┌───────────────────────────┐   ┌──────────────────────────┐
│ Tool-Aware Controller      │   │ Phi-4 Coder               │
│ Qwen3-4B / Phi-4-mini etc. │   │ Phi-4 14B GGUF            │
│                            │   │                           │
│ - choose next action       │   │ - produce focused patches │
│ - request tools            │   │ - fix compiler errors     │
│ - summarize observations   │   │ - explain implementation  │
│ - decide when to ask coder │   │ - return diff only        │
└───────────────────────────┘   └──────────────────────────┘
```

The controller should never directly edit files. It should request actions from the harness.

Phi-4 should never receive the full tool catalog. It should receive focused coding prompts and return a patch.

---

## 5. llama.cpp Deployment Strategy

### Option A: Two llama-server Instances

This is the simplest architecture for early experiments.

```powershell
# Controller server
.\llama-server.exe `
  -m C:\models\qwen3-4b-instruct-2507-q4_k_m.gguf `
  --host 127.0.0.1 `
  --port 8001 `
  -c 8192 `
  --jinja `
  --chat-template chatml `
  -ngl 999

# Phi-4 coder server
.\llama-server.exe `
  -m C:\models\phi-4-q4_k_m.gguf `
  --host 127.0.0.1 `
  --port 8002 `
  -c 8192 `
  --jinja `
  --chat-template phi4 `
  -ngl 999
```

If VRAM pressure is too high, use one of these approaches:

1. Run the controller mostly on CPU and Phi-4 on GPU.
2. Run the models sequentially instead of simultaneously.
3. Reduce context size to `4096`.
4. Use smaller quantizations.
5. Reduce `-ngl` until the model fits.

### Option B: Sequential Model Loading

Use a single server endpoint but swap models between controller and coder phases.

This reduces memory pressure but adds latency and implementation complexity.

Use this only if two simultaneous servers do not fit comfortably.

### Option C: llama.cpp Router Server / Multi-Model Mode

llama.cpp has router/multi-model-related server options, but for the first benchmark, avoid depending on this. Two explicit ports are easier to reason about and easier to debug.

---

## 6. Tooling Boundary

### Recommended Tools Exposed by the Harness

Keep the initial tool surface small.

```json
[
  {
    "name": "search_repo",
    "description": "Search repository text using ripgrep.",
    "parameters": {
      "query": "string",
      "path": "string"
    }
  },
  {
    "name": "read_file",
    "description": "Read a file from the repository.",
    "parameters": {
      "path": "string",
      "start_line": "integer",
      "end_line": "integer"
    }
  },
  {
    "name": "ask_coder",
    "description": "Ask Phi-4 to produce a focused code patch.",
    "parameters": {
      "task": "string",
      "files": "array",
      "constraints": "array"
    }
  },
  {
    "name": "apply_patch",
    "description": "Apply a unified diff to the working tree.",
    "parameters": {
      "patch": "string"
    }
  },
  {
    "name": "run_command",
    "description": "Run an allowlisted build/test command.",
    "parameters": {
      "command": "string"
    }
  },
  {
    "name": "record_evidence",
    "description": "Record benchmark evidence, observations, and artifacts.",
    "parameters": {
      "event": "string",
      "details": "object"
    }
  }
]
```

### Safety Rules

- Do not expose unrestricted shell execution.
- Use an allowlist for commands such as:
  - `dotnet build`
  - `dotnet test`
  - `pytest`
  - `npm test`
  - `npm run lint`
  - `cargo test`
- Run inside a disposable repo copy.
- Reject tool calls that attempt to access paths outside the workspace.
- Never let a model directly write files without harness validation.
- Capture every patch, command, result, and retry in an evidence ledger.

---

## 7. Controller Contract

The controller should output one action at a time.

```json
{
  "thought_summary": "Brief rationale. No hidden chain-of-thought required.",
  "action": "search_repo | read_file | ask_coder | apply_patch | run_command | record_evidence | finish",
  "arguments": {},
  "success_criteria": "What this action should accomplish."
}
```

### Hard Validation Rules

The harness should reject outputs when:

- The response is not valid JSON.
- The action is not in the allowlist.
- Required arguments are missing.
- The controller requests an unsafe command.
- A file path escapes the workspace.
- The same failed action repeats more than N times.

### Controller System Prompt Sketch

```text
You are a local coding-agent controller.

You do not edit files directly.
You do not invent tool results.
You must choose exactly one action per response.
You must emit valid JSON matching the required schema.
Use tools to inspect the repository before asking the coder to modify code.
Ask the coder only after you have enough relevant context.
Prefer small, reversible patches.
After applying a patch, run the relevant deterministic check.
Finish only when the task is complete and evidence has been recorded.
```

---

## 8. Phi-4 Coder Contract

Phi-4 should receive focused context and return only a patch.

### Phi-4 Prompt Sketch

```text
You are a coding specialist.

Task:
{task}

Relevant files:
{file excerpts}

Build/test error or requested behavior:
{evidence}

Constraints:
- Preserve existing behavior unless explicitly asked otherwise.
- Make the smallest reasonable change.
- Do not introduce new dependencies unless required.
- Return a unified diff only.
- Do not include prose outside the diff.
```

### Phi-4 Output Validation

The harness should reject the patch if:

- It is not a valid unified diff.
- It touches files outside the allowed set.
- It deletes unrelated code.
- It includes prose outside the diff.
- It fails to apply cleanly.

---

## 9. Benchmark Design

### Benchmark Phases

| Phase | Goal | Expected Output |
|---|---|---|
| 0. Environment smoke test | Confirm models load and endpoints respond. | Endpoint health report. |
| 1. Tool-call smoke test | Confirm controller emits valid tool requests. | Tool validity score. |
| 2. Repo navigation test | Confirm controller finds relevant files. | Search/read accuracy. |
| 3. Focused coding patch test | Confirm Phi-4 can generate usable diffs. | Patch apply + test result. |
| 4. End-to-end agent loop | Confirm controller + Phi-4 can solve tasks. | Pass/fail + iteration count. |
| 5. Stress / regression | Run multiple tasks across repo types. | Comparative scorecard. |

---

## 10. Benchmark Task Suite

Use 10-20 tasks. Keep them small enough to execute repeatedly.

### Recommended Task Types

| Task Type | Example |
|---|---|
| Compiler fix | Introduce a small compile error and ask the system to fix it. |
| Unit test repair | Add a failing unit test, then ask the agent to make it pass. |
| API behavior change | Change expected behavior in one method with test coverage. |
| Refactor without behavior change | Rename/extract logic while preserving tests. |
| Config-driven behavior | Add a setting and update behavior based on config. |
| Bug localization | Provide a failing test and no file hints. |
| Multi-file change | Require a model/type/controller/view update. |
| Modernization micro-task | Replace deprecated API usage. |
| Documentation-driven task | Update code to match a short requirement. |
| Parity task | Preserve old behavior while moving logic to a new shape. |

### Starter Task Set

```yaml
tasks:
  - id: compile_fix_001
    type: compiler_fix
    repo: sample-dotnet
    instruction: "Fix the build without changing public behavior."
    command: "dotnet build"
    success: "Build passes."

  - id: unit_fix_001
    type: unit_test_repair
    repo: sample-dotnet
    instruction: "Make the failing test pass with the smallest reasonable code change."
    command: "dotnet test"
    success: "All tests pass."

  - id: behavior_001
    type: behavior_change
    repo: sample-python
    instruction: "Update the discount calculation to match the new requirement."
    command: "pytest"
    success: "All tests pass."

  - id: refactor_001
    type: safe_refactor
    repo: sample-typescript
    instruction: "Extract validation logic into a helper without changing behavior."
    command: "npm test"
    success: "All tests pass."

  - id: modernization_001
    type: modernization_microtask
    repo: sample-dotnet
    instruction: "Replace obsolete API usage while preserving behavior."
    command: "dotnet test"
    success: "All tests pass."
```

---

## 11. Metrics

### Controller Metrics

| Metric | Description |
|---|---|
| Valid JSON rate | Percentage of controller responses that parse correctly. |
| Valid action rate | Percentage of responses using an allowed action. |
| Tool selection accuracy | Whether the selected action was reasonable for the state. |
| Unsafe request rate | Attempts to run unsafe commands or access invalid paths. |
| Repeated-action loop rate | Whether the controller gets stuck repeating ineffective actions. |
| Context efficiency | Number of file reads/searches before asking coder. |

### Coder Metrics

| Metric | Description |
|---|---|
| Patch validity rate | Whether Phi-4 returns a valid unified diff. |
| Patch apply rate | Whether the diff applies cleanly. |
| Test pass rate | Whether deterministic checks pass after patch. |
| Minimality score | How small/relevant the patch is. |
| Regression rate | Whether unrelated tests fail. |
| Human review score | Subjective review of clarity, maintainability, and risk. |

### End-to-End Metrics

| Metric | Description |
|---|---|
| Task success rate | Percentage of tasks completed. |
| Iterations to success | Number of controller/coder loops required. |
| Wall-clock time | End-to-end time per task. |
| Token usage | Prompt/completion tokens for each model. |
| Memory footprint | VRAM/RAM observed during run. |
| Evidence completeness | Whether patches, logs, and decisions were captured. |

---

## 12. Benchmark Scorecard

Use a weighted score to compare combinations.

```yaml
weights:
  task_success_rate: 0.35
  tool_call_reliability: 0.20
  patch_quality: 0.20
  speed: 0.10
  resource_fit: 0.10
  evidence_quality: 0.05
```

### Example Scorecard

| Combo | Success | Tool Reliability | Patch Quality | Speed | Resource Fit | Evidence | Weighted Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| Phi-4 alone | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Phi-4 forced JSON | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Qwen3-4B + Phi-4 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Phi-4-mini + Phi-4 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Command R7B + Phi-4 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Functionary + Phi-4 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Hermes + Phi-4 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 13. Minimal Harness Flow

```text
for task in benchmark_tasks:
    reset_repo_to_clean_state()
    start_evidence_ledger(task)

    controller_state = {
        task,
        repo_summary,
        allowed_tools,
        previous_actions: []
    }

    for step in range(max_steps):
        action = ask_controller(controller_state)
        validate_action(action)

        if action.name == "search_repo":
            result = search_repo(action.arguments)

        if action.name == "read_file":
            result = read_file(action.arguments)

        if action.name == "ask_coder":
            patch = ask_phi4_coder(action.arguments)
            result = validate_patch(patch)

        if action.name == "apply_patch":
            result = apply_patch(action.arguments.patch)

        if action.name == "run_command":
            result = run_allowlisted_command(action.arguments.command)

        if action.name == "finish":
            break

        append_result_to_controller_state(result)
        record_evidence(action, result)

    run_final_validation()
    score_task()
```

---

## 14. Suggested Folder Structure

```text
phi4-agent-benchmark/
  README.md
  config/
    models.yaml
    tools.yaml
    scoring.yaml
  harness/
    main.py
    controller_client.py
    coder_client.py
    tools/
      search_repo.py
      read_file.py
      apply_patch.py
      run_command.py
    validators/
      json_contract.py
      patch_contract.py
      path_safety.py
  tasks/
    benchmark_tasks.yaml
  repos/
    sample-dotnet/
    sample-python/
    sample-typescript/
  runs/
    2026-05-13-qwen3-phi4/
      evidence.jsonl
      scorecard.json
      patches/
      logs/
```

---

## 15. Model Configuration File

```yaml
models:
  controller:
    name: qwen3-4b-instruct-2507
    endpoint: http://127.0.0.1:8001/v1
    temperature: 0.1
    top_p: 0.8
    max_tokens: 2048

  coder:
    name: phi-4-14b
    endpoint: http://127.0.0.1:8002/v1
    temperature: 0.1
    top_p: 0.8
    max_tokens: 4096

runtime:
  max_steps_per_task: 12
  workspace_root: ./workspaces
  evidence_root: ./runs
  allow_shell_commands:
    - dotnet build
    - dotnet test
    - pytest
    - npm test
    - npm run lint
    - cargo test
```

---

## 16. OpenAI-Compatible Controller Request Shape

Use the OpenAI-compatible `/v1/chat/completions` endpoint exposed by `llama-server`.

```json
{
  "model": "controller",
  "temperature": 0.1,
  "messages": [
    {
      "role": "system",
      "content": "You are a local coding-agent controller. Emit exactly one valid JSON action."
    },
    {
      "role": "user",
      "content": "Task state and tool results go here."
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_repo",
        "description": "Search repository text using ripgrep.",
        "parameters": {
          "type": "object",
          "properties": {
            "query": { "type": "string" },
            "path": { "type": "string" }
          },
          "required": ["query"]
        }
      }
    }
  ]
}
```

For early benchmarking, consider using both approaches:

1. Native tool-calling via `tools`.
2. Plain strict JSON contract without the `tools` parameter.

This helps isolate whether failures come from the model, the chat template, the tools API, or the controller prompt.

---

## 17. Evidence Ledger

Every step should produce JSONL evidence.

```json
{
  "run_id": "2026-05-13-qwen3-phi4",
  "task_id": "unit_fix_001",
  "step": 4,
  "actor": "controller",
  "action": "ask_coder",
  "input_summary": "Failing test points to discount calculation.",
  "output_valid": true,
  "latency_ms": 1820,
  "tokens_prompt": 1280,
  "tokens_completion": 244
}
```

```json
{
  "run_id": "2026-05-13-qwen3-phi4",
  "task_id": "unit_fix_001",
  "step": 5,
  "actor": "phi4",
  "action": "produce_patch",
  "patch_path": "runs/2026-05-13-qwen3-phi4/patches/unit_fix_001_step5.diff",
  "patch_applied": true
}
```

```json
{
  "run_id": "2026-05-13-qwen3-phi4",
  "task_id": "unit_fix_001",
  "step": 6,
  "actor": "harness",
  "action": "run_command",
  "command": "dotnet test",
  "exit_code": 0,
  "success": true
}
```

---

## 18. Acceptance Criteria

### Minimum Viable Success

The architecture is worth continuing if:

- The controller produces valid actions at least 90% of the time.
- The controller selects useful tools at least 80% of the time.
- Phi-4 patches apply cleanly at least 70% of the time.
- End-to-end task success improves over Phi-4 alone by at least 20 percentage points.
- The harness can capture a complete evidence ledger for every task.

### Strong Success

The architecture is promising if:

- End-to-end success exceeds 70% on the starter benchmark.
- Median task completes in fewer than 6 controller steps.
- Unsafe tool request rate is near zero.
- Patch quality is acceptable under human review.
- The two-model setup runs acceptably on the target desktop.

---

## 19. Recommended Execution Order

### Step 1: Build the Harness Skeleton

Implement:

- OpenAI-compatible client wrapper
- Controller prompt
- Phi-4 coder prompt
- JSON validator
- Patch validator
- Repo workspace reset
- Evidence ledger

Do not build a large framework yet.

### Step 2: Run Controller Tool-Call Smoke Tests

Use fake tools first.

Tasks:

1. Ask the controller to search for a file.
2. Ask the controller to read a file.
3. Ask the controller to decide whether to run tests.
4. Ask the controller to finish when the task is already complete.

Pass condition:

- Valid, parseable actions.
- No hallucinated tool names.
- No unsafe commands.

### Step 3: Run Phi-4 Patch Smoke Tests

Give Phi-4 tiny focused tasks:

1. Fix one-line Python bug.
2. Fix one-line C# compile error.
3. Modify one function with clear test failure.

Pass condition:

- Unified diff only.
- Patch applies.
- Test/build passes.

### Step 4: Combine Controller + Phi-4

Run the first 5 benchmark tasks.

Compare:

1. Phi-4 alone.
2. Qwen3-4B alone.
3. Qwen3-4B + Phi-4.

### Step 5: Add Alternative Controllers

Run the same tasks against:

1. Phi-4-mini-instruct + Phi-4.
2. Command R7B + Phi-4.
3. Functionary-small-v3.2 + Phi-4.
4. Hermes 2 Pro / Hermes 3 + Phi-4.

### Step 6: Decide

Select the controller based on:

1. Highest end-to-end success.
2. Lowest invalid tool-call rate.
3. Best desktop resource fit.
4. Best evidence trace.
5. Lowest prompt/template fragility.

---

## 20. Expected Outcome

The likely winner is:

```text
Qwen3-4B-Instruct-2507 controller + Phi-4 14B coder
```

The likely runner-up is:

```text
Phi-4-mini-instruct controller + Phi-4 14B coder
```

The likely practical conclusion is:

> Phi-4 should not be treated as the native agent controller. It should be treated as a strong local coding worker inside a deterministic harness. The controller model should be small, tool-aware, and replaceable.

---

## 21. Reference Notes

- llama.cpp `llama-server` supports OpenAI-compatible chat completions and tool/function calling through Jinja chat templates.
- llama.cpp’s function-calling docs list native formats for several tool-capable families and generic fallback support for other templates.
- Qwen3-4B-Instruct-2507 is documented as suitable for local use through llama.cpp-compatible applications and is explicitly positioned for agentic/tool-calling use.
- Phi-4-mini-instruct documents a tool-enabled function-calling format using `<|tool|>` and `<|/tool|>` blocks in the system prompt.
- llama.cpp’s built-in server tools are useful for experimentation, but the safer architecture is to keep production tool execution in the external harness.

References:

1. llama.cpp function-calling documentation: https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md
2. llama.cpp server README: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
3. Qwen3-4B-Instruct-2507 model card: https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
4. Qwen function-calling guide: https://qwen.readthedocs.io/en/latest/framework/function_call.html
5. Phi-4-mini-instruct model card: https://huggingface.co/microsoft/Phi-4-mini-instruct
