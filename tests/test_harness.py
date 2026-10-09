from __future__ import annotations

import asyncio
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch

from benchmarks.renters.renters_benchmark.core import DATASET, canonical, load_pair
from continual_harness.config import Config, ModelSettings
from continual_harness.demo import DEMO_STRATEGY, DemoClient, demo_config
from continual_harness.engine import Harness, initialize
from continual_harness.metrics import compare
from continual_harness.prompts import BASELINE, actor_messages, judge_messages
from continual_harness.provider import Completion, OpenRouterClient, ProviderError, parse_object
from continual_harness.store import Store


class RecordingClient(DemoClient):
    def __init__(self):
        super().__init__(DATASET)
        self.calls = []

    async def complete(self, role, settings, messages):
        self.calls.append((role, messages))
        return await super().complete(role, settings, messages)


class BrokenClient:
    def __init__(self, mode):
        self.mode = mode
        self.demo = DemoClient(DATASET)

    async def complete(self, role, settings, messages):
        if role == "actor" and self.mode == "provider":
            raise ProviderError("fixture provider outage", {"error": {"code": 503}})
        if role == "actor" and self.mode == "parse":
            return Completion({"usage": {"prompt_tokens": 9, "completion_tokens": 3, "cost": 0.01}}, "not JSON")
        if role == "judge" and self.mode == "judge":
            return Completion({}, canonical({"judgments": []}))
        return await self.demo.complete(role, settings, messages)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "experiment", create=True)
        self.config = replace(demo_config(), max_attempts=2, retry_delay_seconds=0)
        initialize(self.store, DATASET, self.config, "synthetic_offline")
        self.baseline = self.store.prompt(BASELINE)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_end_to_end_and_information_boundaries(self):
        client = RecordingClient()
        harness = Harness(DATASET, self.config, client, self.store)
        result = asyncio.run(harness.optimize(self.baseline))
        self.assertEqual(result["evidence"], "synthetic_offline")
        self.assertEqual(result["status"], "frozen")
        self.assertNotEqual(result["baseline_prompt"], result["final_prompt"])
        self.assertTrue(result["comparisons"][0]["promote"])
        self.assertEqual(result["comparisons"][0]["candidate"]["intended"], 40)
        self.assertEqual(self.store.strategy(result["final_prompt"]), DEMO_STRATEGY)
        public_optimization = {canonical(load_pair(task_id, DATASET)[0]["input"])
                               for task_id in harness.verify()["splits"]["optimization"]}
        for role, messages in client.calls:
            if role == "optimizer":
                examples = json.loads(messages[1]["content"])["optimization_examples"]
                self.assertTrue(examples)
                self.assertTrue(all(canonical(example["input"]) in public_optimization for example in examples))
                self.assertTrue(any(example["evaluation"]["complete_success"] for example in examples))
                self.assertTrue(any(not example["evaluation"]["complete_success"] for example in examples))
            elif role == "actor":
                self.assertNotIn("reference_answer", messages[1]["content"])
                self.assertNotIn('"split"', messages[1]["content"])
                self.assertNotIn('"rubric"', messages[1]["content"])
            elif role == "judge":
                self.assertNotIn(DEMO_STRATEGY, canonical(messages))
                self.assertNotIn(BASELINE, canonical(messages))
        # Nothing from the test set was evaluated during optimization.
        test_ids = set(harness.verify()["splits"]["test"])
        rows = self.store.db.execute("SELECT DISTINCT task_id FROM evaluations").fetchall()
        self.assertFalse(test_ids.intersection(row[0] for row in rows))
        report = asyncio.run(harness.final_test())
        self.assertEqual(report["candidate"]["intended"], 60)
        self.assertEqual(report["candidate"]["successes"], 60)
        self.assertNotIn("promote", report)
        self.assertEqual(self.store.get("final"), result["final_prompt"])
        with self.assertRaisesRegex(ValueError, "already reserved"):
            asyncio.run(harness.final_test())
        usage = report["usage"]
        self.assertEqual(usage["actor"]["calls"], 300)
        self.assertEqual(usage["judge"]["calls"], 300)
        self.assertEqual(usage["optimizer"]["calls"], 1)
        self.assertEqual(usage["actor"]["usage_calls"], 0)
        self.assertEqual(usage["actor"]["cost_calls"], 0)

    def test_failed_test_stays_reserved(self):
        self.store.put("baseline", self.baseline)
        self.store.put("final", self.baseline)
        self.store.put("status", "frozen")
        harness = Harness(DATASET, self.config, BrokenClient("provider"), self.store)
        report = asyncio.run(harness.final_test())
        self.assertTrue(report["candidate"]["complete_coverage"])
        self.assertEqual(report["candidate"]["quality_observations"], 0)
        self.assertEqual(report["candidate"]["model_failures"], 60)
        self.assertEqual(report["candidate"]["successes"], 0)
        with self.assertRaisesRegex(ValueError, "already reserved"):
            asyncio.run(harness.final_test())

    def test_failures_remain_distinct_and_usage_survives_bad_json(self):
        task, _ = load_pair("ops_001", DATASET)
        for mode, stage in (("provider", "actor"), ("parse", "actor"), ("judge", "judge")):
            harness = Harness(DATASET, self.config, BrokenClient(mode), self.store)
            result = asyncio.run(harness.evaluate_case(task, self.baseline, mode, 0))
            self.assertEqual(result["status"], "model_failure")
            self.assertEqual(result["failure_stage"], stage)
            self.assertIs(result["complete_success"], False)
            self.assertEqual(harness.feedback([result]), [])
        usage = self.store.usage()["actor"]
        self.assertEqual(usage["usage_calls"], 2)
        self.assertEqual(usage["input_tokens"], 18)
        self.assertEqual(usage["output_tokens"], 6)
        self.assertEqual(usage["cost_calls"], 2)
        self.assertEqual(usage["recorded_cost_usd"], 0.02)

    def test_exhausted_optimization_freezes_and_allows_test(self):
        harness = Harness(DATASET, self.config, BrokenClient("provider"), self.store)
        result = asyncio.run(harness.optimize(self.baseline))
        self.assertEqual(self.store.get("status"), "frozen")
        self.assertEqual(result["optimization"]["model_failures"], 100)
        self.assertEqual(result["final_prompt"], self.baseline)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM calls WHERE role='optimizer'").fetchone()[0], 0)

    def test_transient_provider_parse_and_judge_schema_errors_recover(self):
        for mode in ("provider", "parse", "judge"):
            broken = BrokenClient(mode)
            demo = DemoClient(DATASET)
            attempts = {"actor": 0, "judge": 0}

            class FlakyClient:
                async def complete(self, role, settings, messages):
                    attempts[role] += 1
                    if attempts[role] == 1:
                        return await broken.complete(role, settings, messages)
                    return await demo.complete(role, settings, messages)

            harness = Harness(DATASET, self.config, FlakyClient(), self.store)
            task, _ = load_pair("ops_002", DATASET)
            result = asyncio.run(harness.evaluate_case(task, self.baseline, mode, 0))
            self.assertEqual(result["status"], "evaluated")
            self.assertTrue(result["complete_success"])
            role = "judge" if mode == "judge" else "actor"
            self.assertEqual(attempts[role], 2)
            artifacts = [json.loads((self.store.directory / path).read_text())
                         for path, in self.store.db.execute(
                             "SELECT artifact FROM calls WHERE phase=? AND role=? ORDER BY rowid", (mode, role))]
            self.assertEqual([a["attempt"] for a in artifacts], [1, 2])
            self.assertEqual(artifacts[-1]["status"], "completed")

    def test_exhausted_optimizer_keeps_incumbent_and_test_runs(self):
        demo = DemoClient(DATASET)

        class BrokenOptimizer:
            async def complete(self, role, settings, messages):
                if role == "optimizer":
                    return Completion({}, '{"strategy": ""}')
                return await demo.complete(role, settings, messages)

        harness = Harness(DATASET, self.config, BrokenOptimizer(), self.store)
        result = asyncio.run(harness.optimize(self.baseline))
        self.assertEqual(result["final_prompt"], self.baseline)
        self.assertEqual(result["proposal_failures"][0]["failure_stage"], "optimizer")
        self.assertEqual(result["usage"]["optimizer"]["calls"], 2)
        report = asyncio.run(harness.final_test())
        self.assertTrue(report["candidate"]["complete_coverage"])

    def test_feedback_rejects_validation_task(self):
        harness = Harness(DATASET, self.config, DemoClient(DATASET), self.store)
        task = harness.tasks("validation")[0]
        result = asyncio.run(harness.evaluate_case(task, self.baseline, "fixture", 0))
        with self.assertRaisesRegex(ValueError, "Only optimization"):
            harness.feedback([result])

    def test_dataset_drift_and_unfrozen_test_are_blocked(self):
        harness = Harness(DATASET, self.config, DemoClient(DATASET), self.store)
        with self.assertRaisesRegex(ValueError, "Freeze"):
            asyncio.run(harness.final_test())
        self.store.put("dataset_digest", "different")
        with self.assertRaisesRegex(ValueError, "Dataset changed"):
            harness.verify()

    def test_existing_experiment_is_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            Store(self.store.directory, create=True)


class MetricsTests(unittest.TestCase):
    @staticmethod
    def rows(verdicts, status="evaluated"):
        return [{"task_id": str(i), "repetition": 0, "family": "fixture",
                 "complete_success": verdict, "status": status} for i, verdict in enumerate(verdicts)]

    def test_gate_gain_regressions_incomplete_and_matching_cohort(self):
        result = compare(self.rows([False, True]), self.rows([True, True]))
        self.assertTrue(result["promote"])
        self.assertEqual(result["gain"], 0.5)
        self.assertFalse(compare(self.rows([False, True]), self.rows([True, True]), min_gain=0.5)["promote"])
        result = compare(self.rows([False, False, True]), self.rows([True, True, False]))
        self.assertEqual(result["reason"], "regression_limit")
        self.assertEqual(len(result["improvements"]), 2)
        self.assertEqual(len(result["regressions"]), 1)
        self.assertTrue(compare(self.rows([False, False, True]), self.rows([True, True, False]), max_regressions=1)["promote"])
        result = compare(self.rows([False, True]), self.rows([True, True], "judge_invalid"))
        self.assertEqual(result["reason"], "incomplete_evaluation")
        with self.assertRaises(ValueError):
            compare(self.rows([True]), self.rows([True, False]))
        with self.assertRaises(ValueError):
            compare(self.rows([True]) * 2, self.rows([True]) * 2)

    def test_model_failures_count_in_paired_gains_and_regressions(self):
        failures = self.rows([False], "model_failure")
        result = compare(failures, self.rows([True]))
        self.assertTrue(result["promote"])
        self.assertEqual(len(result["improvements"]), 1)
        self.assertEqual(result["incumbent"]["quality_observations"], 0)
        result = compare(self.rows([True]), failures)
        self.assertEqual(result["reason"], "regression_limit")
        self.assertEqual(len(result["regressions"]), 1)


class ProviderTests(unittest.TestCase):
    def test_strict_json_and_config_validation(self):
        for content in ('{"x": NaN}', '{"x": 1e309}', '{"x": 1, "x": 2}', '[]', '```json\n{}\n```'):
            with self.assertRaises(ValueError):
                parse_object(content)
        for kwargs in ({"temperature": float("nan")}, {"max_tokens": True}, {"provider": ""}):
            values = {"model": "fixture/model", "provider": "fixture", **kwargs}
            with self.assertRaises(ValueError):
                ModelSettings(**values)
        with self.assertRaises(ValueError):
            Config.from_dict({**demo_config().to_dict(), "repetitions": 0})
        for value in (0, True):
            with self.assertRaises(ValueError):
                replace(demo_config(), max_attempts=value)
        for value in (-1, float("nan"), True):
            with self.assertRaises(ValueError):
                replace(demo_config(), retry_delay_seconds=value)
        self.assertEqual(Config.load(Path("harness.example.toml")).repetitions, 2)

    def test_request_routing_usage_and_errors_without_network(self):
        settings = ModelSettings("fixture/model", "fixture-provider")
        messages = [{"role": "user", "content": "Return JSON"}]
        raw = {"id": "generation-fixture", "model": settings.model,
               "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
               "usage": {"prompt_tokens": 10, "completion_tokens": 4, "cost": 0.02}}
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "secret-fixture"}):
            client = OpenRouterClient()
        with patch("urllib.request.urlopen", return_value=io.BytesIO(canonical(raw).encode())) as opened:
            completion = asyncio.run(client.complete("actor", settings, messages))
            self.assertEqual(completion.raw["usage"]["cost"], 0.02)
            request = opened.call_args.args[0]
            body = json.loads(request.data)
            self.assertEqual(body["provider"]["only"], ["fixture-provider"])
            self.assertFalse(body["provider"]["allow_fallbacks"])
            self.assertTrue(body["provider"]["require_parameters"])
            self.assertNotIn("secret-fixture", canonical(body))
        for envelope in ({"error": {"message": "fixture"}},
                         {**raw, "choices": []},
                         {**raw, "choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}):
            with patch("urllib.request.urlopen", return_value=io.BytesIO(canonical(envelope).encode())):
                with self.assertRaises(ProviderError):
                    asyncio.run(client.complete("actor", settings, messages))
        failure = urllib.error.HTTPError("https://example.invalid", 429, "limit", {}, io.BytesIO(b"rate limited"))
        with patch("urllib.request.urlopen", side_effect=failure):
            with self.assertRaisesRegex(ProviderError, "HTTP 429"):
                asyncio.run(client.complete("actor", settings, messages))


if __name__ == "__main__":
    unittest.main()
