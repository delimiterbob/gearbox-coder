import time
from pathlib import Path

from openai import OpenAI

GEARBOX_ROOT = Path(__file__).parent.parent


class CoderClient:
    def __init__(self, endpoint: str, model_name: str, temperature: float, max_tokens: int):
        self.client = OpenAI(base_url=endpoint, api_key="local")
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def ask(
        self,
        task: str,
        file_excerpts: dict[str, str],
        constraints: list[str] | None = None,
        build_output: str | None = None,
        target_spec: str = "",
    ) -> tuple[str, int, int, int]:
        system = _load_migration_system()
        if target_spec:
            system = system + "\n\n" + target_spec

        file_block = "\n\n".join(
            f"### {path}\n```\n{content}\n```" for path, content in file_excerpts.items()
        )
        constraint_block = ""
        if constraints:
            constraint_block = "\n\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints)
        build_block = ""
        if build_output:
            build_block = f"\n\nBuild/test output:\n```\n{build_output[-3000:]}\n```"

        user_message = (
            f"Task:\n{task}\n\n"
            f"Relevant files:\n{file_block}"
            f"{build_block}"
            f"{constraint_block}"
        )

        t0 = time.time()
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        latency_ms = int((time.time() - t0) * 1000)
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0

        output = response.choices[0].message.content or ""
        return output.strip(), latency_ms, prompt_tokens, completion_tokens


def _load_migration_system() -> str:
    return (GEARBOX_ROOT / "prompts" / "migration-system.md").read_text(encoding="utf-8")
