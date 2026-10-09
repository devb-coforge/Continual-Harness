"""Synthetic orchestration fixture. Deliberately uses private golds; never a model score."""
from __future__ import annotations

import json
from pathlib import Path

from benchmarks.renters.renters_benchmark.core import canonical, load_pair, read_json
from .config import Config, ModelSettings
from .provider import Completion

DEMO_STRATEGY = "SYNTHETIC_DEMO_CORRECT: reconcile corrections and verify every prerequisite."


def demo_config() -> Config:
    role = ModelSettings("synthetic/fixture")
    return Config(role, role, role, iterations=1, repetitions=2)


class DemoClient:
    def __init__(self, dataset: Path):
        self.dataset = dataset
        self.by_input = {canonical(read_json(path)["input"]): path.stem
                         for path in (dataset / "tasks").glob("*.json")}

    async def complete(self, role: str, settings: ModelSettings,
                       messages: list[dict[str, str]]) -> Completion:
        data = json.loads(messages[1]["content"])
        if role == "optimizer":
            answer = {"strategy": DEMO_STRATEGY, "rationale": "Scripted fixture to verify promotion only."}
        else:
            task_id = self.by_input[canonical(data if role == "actor" else data["task_input"])]
            _, oracle = load_pair(task_id, self.dataset)
            if role == "actor":
                answer = json.loads(canonical(oracle["reference_answer"]))
                if DEMO_STRATEGY not in messages[0]["content"] and int(task_id[-3:]) % 3 == 1:
                    # An observed response-contract failure, not an infrastructure failure.
                    answer["disposition"] = "invalid_fixture_disposition"
            else:
                answer = {"judgments": [
                    {"id": criterion["id"], "passed": True,
                     "reason": "Scripted synthetic verdict; not semantic model evidence.",
                     "evidence": criterion["evidence"]}
                    for criterion in oracle["rubric"]]}
        content = canonical(answer)
        return Completion({"id": "synthetic", "model": settings.model, "provider": "offline",
                           "choices": [{"message": {"content": content}, "finish_reason": "stop"}]}, content)
