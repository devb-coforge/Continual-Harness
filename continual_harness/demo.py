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
        self.by_memory_input = {canonical({key: value for key, value in read_json(path)["input"].items()
                                           if key != "records"}): path.stem
                                for path in (dataset / "tasks").glob("*.json")}

    async def complete(self, role: str, settings: ModelSettings,
                       messages: list[dict], *, tools: list[dict] | None = None,
                       tool_choice: str = "auto") -> Completion:
        data = json.loads(messages[1]["content"])
        if role == "optimizer":
            answer = {"strategy": DEMO_STRATEGY, "rationale": "Scripted fixture to verify promotion only."}
        else:
            index = self.by_memory_input if role == "actor" and tools is not None else self.by_input
            task_id = index[canonical(data if role == "actor" else data["task_input"])]
            _, oracle = load_pair(task_id, self.dataset)
            if role == "actor":
                if tools is not None and tool_choice != "none":
                    tool_results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
                    read_ids = {r["document_id"] for r in tool_results if "document_id" in r and "error" not in r}
                    needed = [c for c in oracle["reference_answer"]["citations"]
                              if c.startswith(("H", "r")) and c not in read_ids]
                    if not tool_results:
                        functions = [{"name": "search_memory", "arguments": canonical({"query": "policy"})}]
                    else:
                        functions = [{"name": "read_memory", "arguments": canonical({"document_id": c})}
                                     for c in needed]
                    if functions:
                        message = {"role": "assistant", "content": None, "tool_calls": [
                            {"id": f"fixture_{len(tool_results)}_{i}", "type": "function", "function": function}
                            for i, function in enumerate(functions)]}
                        return Completion({"choices": [{"message": message, "finish_reason": "tool_calls"}]}, None, message)
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
