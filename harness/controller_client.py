import json
import time
from typing import Any

from openai import OpenAI

from harness.validators.json_contract import extract_json

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_repo",
            "description": "Search source/ or output/ text using ripgrep.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text or regex to search for."},
                    "path":  {"type": "string", "description": "Subdirectory to restrict search (e.g. 'source')."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the workspace (source/ or output/).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":       {"type": "string", "description": "File path relative to workspace root."},
                    "start_line": {"type": "integer"},
                    "end_line":   {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a single file to output/. Path must start with 'output/'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Destination path starting with 'output/'."},
                    "content": {"type": "string", "description": "Complete file content."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_coder",
            "description": (
                "Ask the Phi-4 coding specialist to produce migration output or a fix patch. "
                "For migration: coder returns a '// FILE: path' bundle; harness writes all files automatically. "
                "For fixes: coder returns a unified diff; use apply_patch afterwards."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task":         {"type": "string", "description": "Precise description of what to produce."},
                    "files":        {"type": "array",  "items": {"type": "string"}, "description": "Files to send as context."},
                    "constraints":  {"type": "array",  "items": {"type": "string"}},
                    "build_output": {"type": "string", "description": "Build/test error output to help the coder fix issues."},
                },
                "required": ["task", "files"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "Apply a unified diff patch to the workspace. Use after ask_coder returns a fix patch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patch": {"type": "string", "description": "Unified diff string."},
                },
                "required": ["patch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run an allowlisted build or verification command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run (must be in allowlist)."},
                    "cwd":     {"type": "string", "description": "Optional subdirectory relative to workspace root."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_evidence",
            "description": "Record a key observation or decision in the evidence ledger.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event":   {"type": "string"},
                    "details": {"type": "object"},
                },
                "required": ["event", "details"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Signal task completion. Only call after a passing build/verify command.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


class ControllerClient:
    def __init__(self, endpoint: str, model_name: str, temperature: float, max_tokens: int):
        self.client = OpenAI(base_url=endpoint, api_key="local")
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def ask(self, messages: list[dict]) -> tuple[dict | None, int, int, int]:
        t0 = time.time()
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        latency_ms = int((time.time() - t0) * 1000)
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        choice = response.choices[0]

        if choice.message.tool_calls:
            tc = choice.message.tool_calls[0]
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            action = {
                "thought_summary": choice.message.content or "",
                "action": tc.function.name,
                "arguments": args,
                "success_criteria": "",
                "_native_tool_call": True,
                "_tool_call_id": tc.id,
            }
            return action, latency_ms, prompt_tokens, completion_tokens

        content = choice.message.content or ""
        parsed = extract_json(content)
        if parsed:
            parsed["_native_tool_call"] = False
            return parsed, latency_ms, prompt_tokens, completion_tokens

        return None, latency_ms, prompt_tokens, completion_tokens

    def build_tool_result_message(self, action: dict, result: Any) -> list[dict]:
        result_text = json.dumps(result) if not isinstance(result, str) else result
        if action.get("_native_tool_call"):
            return [
                {"role": "assistant", "content": None, "tool_calls": [{
                    "id": action["_tool_call_id"],
                    "type": "function",
                    "function": {
                        "name": action["action"],
                        "arguments": json.dumps(action.get("arguments", {})),
                    },
                }]},
                {"role": "tool", "tool_call_id": action["_tool_call_id"], "content": result_text},
            ]
        return [
            {"role": "assistant", "content": json.dumps({
                k: v for k, v in action.items() if not k.startswith("_")
            })},
            {"role": "user", "content": f"Tool result:\n{result_text}"},
        ]
