import json
import time
from pathlib import Path


class EvidenceLedger:
    def __init__(self, path: Path, run_id: str, task_id: str):
        self.path = path
        self.run_id = run_id
        self.task_id = task_id
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(path, "a", encoding="utf-8")

    def record(self, step: int, actor: str, action: str, **kwargs) -> None:
        entry = {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "step": step,
            "actor": actor,
            "action": action,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **kwargs,
        }
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
