from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from renters_benchmark.core import audit, canonical, grade, load_pair, make_manifest, read_json
from .config import Config
from .metrics import compare, summary
from .prompts import actor_messages, judge_messages, optimizer_messages
from .provider import Client, ProviderError, parse_object, request_body
from .store import Store


class Harness:
    def __init__(self, dataset: Path, config: Config, client: Client, store: Store):
        self.dataset, self.config, self.client, self.store = dataset, config, client, store
        self.semaphore = asyncio.Semaphore(config.concurrency)

    def verify(self) -> dict[str, Any]:
        report = audit(self.dataset)
        if not report["valid"]:
            raise ValueError(f"Dataset integrity failed: {report['errors']}")
        manifest = make_manifest(self.dataset)
        digest = hashlib.sha256(canonical(manifest).encode()).hexdigest()
        if digest != self.store.get("dataset_digest"):
            raise ValueError("Dataset changed since experiment initialization")
        return manifest

    def tasks(self, split: str) -> list[dict[str, Any]]:
        manifest = self.verify()
        return [read_json(self.dataset / "tasks" / f"{task_id}.json")
                for task_id in manifest["splits"][split]]

    async def call(self, role: str, messages: list[dict[str, str]], phase: str,
                   prompt_id: str, task_id: str | None = None,
                   repetition: int | None = None) -> tuple[Any, str | None]:
        settings = getattr(self.config, role)
        artifact: dict[str, Any] = {
            "request": request_body(settings, messages), "status": "started",
            "started_at": datetime.now(timezone.utc).isoformat(), "raw": None}
        try:
            async with self.semaphore:
                reply = await self.client.complete(role, settings, messages)
            artifact["raw"] = reply.raw
            artifact["content"] = reply.content
            result = parse_object(reply.content)
            artifact["status"] = "completed"
            return result, None
        except ProviderError as exc:
            artifact.update(status="provider_error", error=str(exc), raw=exc.raw)
            return None, "provider_error"
        except (ValueError, TypeError) as exc:
            artifact.update(status="parse_error", error=str(exc))
            return None, "parse_error"
        finally:
            artifact["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.store.call(role, phase, prompt_id, task_id, repetition, artifact)

    async def evaluate_case(self, task: dict[str, Any], prompt_id: str, phase: str,
                            repetition: int) -> dict[str, Any]:
        _, oracle = load_pair(task["id"], self.dataset)
        answer, error = await self.call("actor", actor_messages(task, self.dataset, self.store.strategy(prompt_id)),
                                        phase, prompt_id, task["id"], repetition)
        result: dict[str, Any] = {"task_id": task["id"], "family": task["family"],
                                  "track": task["track"], "repetition": repetition,
                                  "answer": answer, "complete_success": None}
        if error:
            result["status"] = "actor_" + error
        else:
            judgments, judge_error = await self.call("judge", judge_messages(task, oracle, answer, self.dataset),
                                                      phase, prompt_id, task["id"], repetition)
            entries = judgments.get("judgments") if isinstance(judgments, dict) and set(judgments) == {"judgments"} else {}
            score = grade(task, oracle, answer, entries)
            result.update(score, judgments=judgments)
            if judge_error or score["semantic_status"] == "invalid":
                result["status"] = "judge_" + (judge_error or "invalid")
            else:
                result["status"] = "evaluated"
        self.store.evaluation(phase, prompt_id, result)
        return result

    async def evaluate(self, prompt_id: str, split: str, phase: str) -> list[dict[str, Any]]:
        return list(await asyncio.gather(*[
            self.evaluate_case(task, prompt_id, phase, repetition)
            for repetition in range(self.config.repetitions) for task in self.tasks(split)]))

    async def paired(self, incumbent: str, candidate: str, split: str,
                     phase: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        tasks = self.tasks(split)

        async def pair(task: dict[str, Any], repetition: int, position: int) -> tuple[dict[str, Any], dict[str, Any]]:
            # Alternate order so the final arm does not always run later.
            arms = [(incumbent, "incumbent"), (candidate, "candidate")]
            if (position + repetition) % 2:
                arms.reverse()
            records = {}
            for prompt_id, arm in arms:
                records[arm] = await self.evaluate_case(task, prompt_id, phase + "/" + arm, repetition)
            return records["incumbent"], records["candidate"]

        pairs = await asyncio.gather(*[pair(task, repetition, position)
                                       for repetition in range(self.config.repetitions)
                                       for position, task in enumerate(tasks)])
        return [p[0] for p in pairs], [p[1] for p in pairs]

    def feedback(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Only valid task-quality observations may motivate a prompt change.
        usable = [r for r in results if r["status"] == "evaluated"]
        failures = [r for r in usable if r["complete_success"] is False]
        successes = [r for r in usable if r["complete_success"] is True]

        def sample(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
            # Round-robin families, with one observation per task.
            by_family: dict[str, list[dict[str, Any]]] = {}
            seen = set()
            for record in sorted(records, key=lambda r: (r["task_id"], r["repetition"])):
                if record["task_id"] in seen:
                    continue
                seen.add(record["task_id"])
                by_family.setdefault(record["family"], []).append(record)
            selected = []
            while len(selected) < limit and any(by_family.values()):
                for family in sorted(by_family):
                    if by_family[family] and len(selected) < limit:
                        selected.append(by_family[family].pop(0))
            return selected

        selected = sample(failures, self.config.feedback_failures) + sample(successes, self.config.feedback_successes)
        examples = []
        for result in selected:
            task, oracle = load_pair(result["task_id"], self.dataset)
            if task["split"] != "optimization":
                raise ValueError("Only optimization feedback may reach the optimizer")
            examples.append({"input": task["input"], "answer": result["answer"],
                             "reference_answer": oracle["reference_answer"],
                             "checks": oracle["checks"], "rubric": oracle["rubric"],
                             "evaluation": {key: result[key] for key in (
                                 "checks", "response_errors", "judgments", "complete_success")}})
        return examples

    async def optimize(self, baseline: str) -> dict[str, Any]:
        self.verify()
        self.store.put("status", "optimizing")
        self.store.put("baseline", baseline)
        incumbent = baseline
        comparisons = []
        for iteration in range(1, self.config.iterations + 1):
            phase = f"iteration-{iteration}"
            records = await self.evaluate(incumbent, "optimization", phase + "/optimization")
            if not summary(records)["complete_coverage"]:
                self.store.put("status", "failed")
                raise ValueError("Optimization evaluation incomplete; inspect saved call artifacts")
            if not any(r["complete_success"] is False for r in records):
                break
            proposal, error = await self.call("optimizer", optimizer_messages(
                self.store.strategy(incumbent), self.feedback(records), self.config.max_strategy_chars),
                phase + "/proposal", incumbent)
            if error or not isinstance(proposal, dict) or set(proposal) != {"strategy", "rationale"}:
                self.store.put("status", "failed")
                raise ValueError("Optimizer did not return a valid strategy proposal")
            strategy, rationale = proposal["strategy"], proposal["rationale"]
            if (not isinstance(strategy, str) or not strategy.strip() or len(strategy) > self.config.max_strategy_chars
                    or not isinstance(rationale, str) or not rationale.strip()):
                self.store.put("status", "failed")
                raise ValueError("Optimizer proposal violates strategy/rationale constraints")
            candidate = self.store.prompt(strategy, incumbent, rationale)
            if candidate == incumbent:
                break
            left, right = await self.paired(incumbent, candidate, "validation", phase + "/validation")
            comparison = compare(left, right, self.config.min_gain, self.config.max_regressions)
            comparison.update(incumbent_prompt=incumbent, candidate_prompt=candidate)
            self.store.comparison(phase, comparison)
            comparisons.append(comparison)
            if comparison["promote"]:
                incumbent = candidate
        self.store.put("final", incumbent)
        self.store.put("status", "frozen")
        self.store.put("frozen_at", datetime.now(timezone.utc).isoformat())
        (self.store.directory / "final_strategy.txt").write_text(self.store.strategy(incumbent) + "\n")
        report = {"evidence": self.store.get("evidence"), "status": "frozen",
                  "baseline_prompt": baseline, "final_prompt": incumbent,
                  "comparisons": comparisons, "usage": self.store.usage()}
        (self.store.directory / "optimization_report.json").write_text(canonical(report) + "\n")
        return report

    async def final_test(self) -> dict[str, Any]:
        if self.store.get("status") != "frozen":
            raise ValueError("Freeze a completed optimization experiment before testing")
        self.verify()
        self.store.reserve_test()
        left, right = await self.paired(self.store.get("baseline"), self.store.get("final"), "test", "test")
        result = compare(left, right, self.config.min_gain, self.config.max_regressions)
        # Test evidence is reported, never used for promotion.
        result.pop("promote")
        result["reason"] = "held_out_report_only"
        result.update(evidence=self.store.get("evidence"), usage=self.store.usage())
        self.store.comparison("test", result)
        (self.store.directory / "test_report.json").write_text(canonical(result) + "\n")
        return result


def initialize(store: Store, dataset: Path, config: Config, evidence: str) -> None:
    report = audit(dataset)
    if not report["valid"]:
        raise ValueError(f"Invalid dataset: {report['errors']}")
    store.put("dataset", str(dataset.resolve()))
    store.put("dataset_digest", hashlib.sha256(canonical(make_manifest(dataset)).encode()).hexdigest())
    store.put("config", config.to_dict())
    store.put("evidence", evidence)
    store.put("status", "initialized")
