from __future__ import annotations

import asyncio
import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from benchmarks.renters.renters_benchmark.core import DATASET, canonical, load_pair, read_json
from continual_harness.config import Config, ModelSettings
from continual_harness.demo import DEMO_STRATEGY, DemoClient, demo_config
from continual_harness.engine import Harness, initialize
from continual_harness.memory import CaseMemory, TOOLS, VARIANT, memory_messages
from continual_harness.prompts import BASELINE
from continual_harness.provider import Completion, OpenRouterClient, ProviderError, request_body
from continual_harness.store import Store


def tool_reply(name, arguments, call_id="test-call"):
    message = {"role": "assistant", "content": None, "tool_calls": [
        {"id": call_id, "type": "function", "function": {
            "name": name, "arguments": arguments}}]}
    return Completion({"choices": [{"message": message, "finish_reason": "tool_calls"}]}, None, message)


class MemoryTests(unittest.TestCase):
    def test_public_boundary_and_full_document_fidelity_for_all_cases(self):
        for path in sorted((DATASET / "tasks").glob("*.json")):
            task = read_json(path)
            memory = CaseMemory(task, DATASET)
            messages = memory_messages(task, DATASET, BASELINE)
            public = json.loads(messages[1]["content"])
            self.assertNotIn("records", public)
            self.assertEqual(public["messages"], task["input"]["messages"])
            self.assertNotIn("Base coverage includes", messages[0]["content"])
            for forbidden in ("reference_answer", '"rubric"', '"split"', "scenario_group"):
                self.assertNotIn(forbidden, canonical(messages))
                self.assertNotIn(forbidden, canonical(memory.documents))
            self.assertEqual(len(memory.documents), 16 + len(task["input"]["records"]))
            for record in task["input"]["records"]:
                result = memory.execute("read_memory", {"document_id": record["id"]})
                self.assertEqual(result["data"], record["data"])
                self.assertEqual(result["kind"], record["kind"])

    def test_distractors_search_limits_and_read_isolation(self):
        task, _ = load_pair("ops_001", DATASET)
        memory = CaseMemory(task, DATASET)
        results = memory.execute("search_memory", {"query": "apartment excluded", "limit": 5})
        self.assertIn("r2", [r["document_id"] for r in results["results"]])
        self.assertEqual(memory.read_ids, set())
        result = memory.execute("read_memory", {"document_id": "r2"})
        self.assertEqual(result["data"]["authority"], "advertisement")
        result["data"]["text"] = "mutated"
        self.assertIn("excluded", memory.documents["r2"]["data"]["text"])
        other, _ = load_pair("ops_002", DATASET)
        second = CaseMemory(other, DATASET)
        self.assertEqual(second.read_ids, set())
        self.assertNotEqual(second.documents["r1"]["data"], memory.documents["r1"]["data"])
        self.assertEqual(memory.execute("search_memory", {"query": "zzzznomatch"})["results"], [])
        self.assertEqual(len(memory.execute("search_memory", {"query": ""})["results"]), 5)
        for name, arguments, error in [
            ("read_memory", {"document_id": "../../oracles/ops_001.json"}, "unknown_document"),
            ("read_memory", {"document_id": []}, "invalid_arguments"),
            ("search_memory", {"query": "policy", "limit": True}, "invalid_arguments"),
            ("search_memory", {"query": "x", "limit": 6}, "invalid_arguments"),
            ("search_memory", {"query": "x", "path": "oracles"}, "invalid_arguments"),
            ("write_memory", {}, "unknown_tool")]:
            self.assertEqual(memory.execute(name, arguments)["error"], error)


class ActorMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "run", create=True)
        self.config = replace(demo_config(), actor_memory=True, max_attempts=2, retry_delay_seconds=0)
        initialize(self.store, DATASET, self.config, "synthetic_offline")
        self.prompt = self.store.prompt(DEMO_STRATEGY)
        self.task, self.oracle = load_pair("ops_001", DATASET)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_end_to_end_variant_and_blinded_feedback(self):
        demo = DemoClient(DATASET)
        calls = []

        class Recording:
            async def complete(self, role, settings, messages, **kwargs):
                calls.append((role, json.loads(canonical(messages))))
                return await demo.complete(role, settings, messages, **kwargs)

        harness = Harness(DATASET, self.config, Recording(), self.store)
        result = asyncio.run(harness.optimize(self.store.prompt(BASELINE)))
        self.assertEqual(result["variant"], VARIANT)
        self.assertTrue(result["comparisons"][0]["promote"])
        self.assertGreater(result["usage"]["actor"]["calls"], 100)
        for role, messages in calls:
            data = json.loads(messages[1]["content"])
            if role == "actor":
                self.assertNotIn("records", data)
                self.assertNotIn("reference_answer", canonical(messages))
                self.assertNotIn('"split"', canonical(messages))
            elif role == "judge":
                self.assertIn("tool_trace", data)
                self.assertNotIn(DEMO_STRATEGY, canonical(messages))
                self.assertNotIn(BASELINE, canonical(messages))
            elif role == "optimizer":
                for example in data["optimization_examples"]:
                    self.assertTrue(example["tool_trace"])
                    task_id = demo.by_input[canonical(example["input"])]
                    self.assertEqual(load_pair(task_id, DATASET)[0]["split"], "optimization")
        report = asyncio.run(harness.final_test())
        self.assertEqual(report["variant"], VARIANT)
        self.assertEqual(report["candidate"]["successes"], 60)
        self.assertEqual(report["candidate"]["model_failures"], 0)
        self.assertTrue(list((self.store.directory / "tools").glob("*.json")))

    def test_unread_citations_fail_even_with_correct_gold_answer(self):
        demo = DemoClient(DATASET)
        oracle = self.oracle

        class Guess:
            async def complete(self, role, settings, messages, **kwargs):
                if role == "actor":
                    return Completion({}, canonical(oracle["reference_answer"]))
                return await demo.complete(role, settings, messages)

        result = asyncio.run(Harness(DATASET, self.config, Guess(), self.store).evaluate_case(
            self.task, self.prompt, "guess", 0))
        self.assertEqual(result["status"], "evaluated")
        self.assertFalse(result["complete_success"])
        self.assertFalse(result["response_valid"])
        self.assertIn("reading memory", result["response_errors"][-1])
        self.assertEqual(result["retrieved_sources"], [])

    def test_retry_preserves_history_and_records_usage_without_reexecuting_tools(self):
        demo = DemoClient(DATASET)
        attempts = 0

        class Flaky:
            async def complete(self, role, settings, messages, **kwargs):
                nonlocal attempts
                if role == "actor":
                    attempts += 1
                    if attempts == 2:
                        raise ProviderError("transient", {"usage": {
                            "prompt_tokens": 7, "completion_tokens": 2, "cost": 0.01}})
                return await demo.complete(role, settings, messages, **kwargs)

        result = asyncio.run(Harness(DATASET, self.config, Flaky(), self.store).evaluate_case(
            self.task, self.prompt, "retry", 0))
        self.assertTrue(result["complete_success"])
        self.assertEqual(sum(t["tool_call"]["function"]["name"] == "search_memory"
                             for t in result["tool_trace"]), 1)
        artifacts = [read_json(self.store.directory / row[0]) for row in self.store.db.execute(
            "SELECT artifact FROM calls WHERE role='actor' ORDER BY rowid")]
        self.assertEqual(artifacts[1]["request"], artifacts[2]["request"])
        usage = self.store.usage()["actor"]
        self.assertEqual(usage["retry_attempts"], 1)
        self.assertEqual(usage["recorded_cost_usd"], 0.01)
        self.assertEqual(usage["calls"], attempts)

    def test_invalid_tools_arguments_and_budget_reach_final_turn(self):
        config = replace(self.config, max_tool_calls=3)
        initialize(self.store, DATASET, config, "synthetic_offline")
        sequence = [("not_a_tool", "{}"), ("read_memory", "[]"),
                    ("read_memory", '{"document_id":"missing"}')]
        actor_turns = []
        demo = DemoClient(DATASET)
        oracle = self.oracle

        class InvalidTools:
            async def complete(self, role, settings, messages, **kwargs):
                if role == "judge":
                    return await demo.complete(role, settings, messages)
                actor_turns.append(kwargs["tool_choice"])
                if kwargs["tool_choice"] == "none":
                    self_answer = json.loads(canonical(oracle["reference_answer"]))
                    self_answer["citations"] = ["m1"]
                    return Completion({}, canonical(self_answer))
                name, arguments = sequence[len(actor_turns) - 1]
                return tool_reply(name, arguments)

        result = asyncio.run(Harness(DATASET, config, InvalidTools(), self.store).evaluate_case(
            self.task, self.prompt, "invalid", 0))
        self.assertEqual(actor_turns, ["auto", "auto", "auto", "none"])
        self.assertEqual([t["result"]["error"] for t in result["tool_trace"]],
                         ["unknown_tool", "invalid_arguments", "unknown_document"])

    def test_batch_budget_caps_reads_and_final_refusal_is_model_failure(self):
        config = replace(self.config, max_tool_calls=1)
        initialize(self.store, DATASET, config, "synthetic_offline")

        class Endless:
            async def complete(self, role, settings, messages, **kwargs):
                reply = tool_reply("read_memory", '{"document_id":"H01"}')
                if kwargs["tool_choice"] == "auto":
                    reply.message["tool_calls"].append({"id": "second", "type": "function", "function": {
                        "name": "read_memory", "arguments": '{"document_id":"H04"}'}})
                return reply

        result = asyncio.run(Harness(DATASET, config, Endless(), self.store).evaluate_case(
            self.task, self.prompt, "budget", 0))
        self.assertEqual(result["status"], "model_failure")
        self.assertEqual(result["retrieved_sources"], ["H01"])
        self.assertEqual(result["tool_trace"][1]["result"]["error"], "tool_budget_exhausted")
        self.assertFalse(result["complete_success"])
        self.assertEqual(self.store.usage()["actor"]["calls"], 3)
        trace = read_json(next((self.store.directory / "tools").glob("*.json")))
        self.assertEqual(len(trace["trace"]), 2)

    def test_config_drift_and_old_configs(self):
        with self.assertRaisesRegex(ValueError, "Configuration changed"):
            Harness(DATASET, replace(self.config, actor_memory=False), DemoClient(DATASET), self.store).verify()
        old = demo_config().to_dict()
        old.pop("actor_memory")
        old.pop("max_tool_calls")
        self.assertFalse(Config.from_dict(old).actor_memory)
        for kwargs in ({"actor_memory": "true"}, {"max_tool_calls": 0}, {"max_tool_calls": True}):
            with self.assertRaises(ValueError):
                replace(self.config, **kwargs)
        self.store.put("memory_tools_digest", "changed")
        with self.assertRaisesRegex(ValueError, "tool definitions changed"):
            Harness(DATASET, self.config, DemoClient(DATASET), self.store).verify()


class ToolProviderTests(unittest.TestCase):
    def test_native_protocol_null_content_history_and_malformed_calls(self):
        settings = ModelSettings("fixture/model")
        messages = [{"role": "user", "content": "Use memory"}]
        reply = tool_reply("search_memory", '{"query":"theft"}')
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "secret-fixture"}):
            client = OpenRouterClient()
        with patch("urllib.request.urlopen", return_value=io.BytesIO(canonical(reply.raw).encode())) as opened:
            result = asyncio.run(client.complete("actor", settings, messages, tools=TOOLS))
        self.assertIsNone(result.content)
        self.assertEqual(result.message["tool_calls"], reply.message["tool_calls"])
        body = json.loads(opened.call_args.args[0].data)
        self.assertEqual(body["tools"], TOOLS)
        self.assertNotIn("response_format", body)
        history = messages + [reply.message, {"role": "tool", "tool_call_id": "test-call", "content": "{}"}]
        final = request_body(settings, history, tools=TOOLS, tool_choice="none")
        self.assertEqual(final["messages"], history)
        self.assertEqual(final["response_format"], {"type": "json_object"})
        self.assertNotIn("tools", request_body(settings, messages))
        for message in (None, {"content": None, "tool_calls": []},
                        {"content": None, "tool_calls": [{"id": "x", "type": "function", "function": {}}]},
                        {"content": None, "tool_calls": reply.message["tool_calls"] * 2}):
            raw = {"choices": [{"message": message, "finish_reason": "tool_calls"}]}
            with patch("urllib.request.urlopen", return_value=io.BytesIO(canonical(raw).encode())):
                with self.assertRaises(ProviderError):
                    asyncio.run(client.complete("actor", settings, messages, tools=TOOLS))
        with patch("urllib.request.urlopen", return_value=io.BytesIO(canonical(reply.raw).encode())):
            with self.assertRaises(ProviderError):
                asyncio.run(client.complete("actor", settings, messages, tools=TOOLS, tool_choice="none"))


if __name__ == "__main__":
    unittest.main()
