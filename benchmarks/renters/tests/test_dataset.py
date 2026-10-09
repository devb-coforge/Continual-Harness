"""Whole-suite integrity, response-isolation, and meaningful negative controls."""

import copy
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from renters_benchmark.core import DATASET, ROOT, audit, grade, load_pair, read_json, render


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ids = [f"{prefix}_{i:03}" for prefix in ("ops", "ext") for i in range(1, 51)]

    def test_full_suite_and_frozen_manifest(self):
        result = audit()
        self.assertTrue(result["valid"], "\n".join(result["errors"]))
        self.assertEqual(result["task_count"], 100)

    def test_all_reference_answers_are_objectively_valid_but_not_auto_judged(self):
        for task_id in self.ids:
            with self.subTest(task_id=task_id):
                task, oracle = load_pair(task_id)
                result = grade(task, oracle, oracle["reference_answer"])
                self.assertTrue(result["structured_correct"])
                self.assertIsNone(result["complete_success"])

    def test_all_cases_reject_empty_outputs_and_hallucinated_fields(self):
        for task_id in self.ids:
            task, oracle = load_pair(task_id)
            for mode in ("empty", "extra_field", "unsupported_action", "bad_citation"):
                with self.subTest(task_id=task_id, mode=mode):
                    answer = copy.deepcopy(oracle["reference_answer"])
                    if mode == "empty":
                        answer = {}
                    elif mode == "extra_field":
                        answer["fields"]["invented_premium"] = 17.99
                    elif mode == "unsupported_action":
                        answer["actions"].append({"type": "unauthorized_payment", "target": "new", "value": 999})
                    else:
                        answer["citations"] = ["nonexistent_source"]
                    self.assertFalse(grade(task, oracle, answer)["complete_success"])

    def test_every_required_field_is_actually_enforced(self):
        for task_id in self.ids:
            task, oracle = load_pair(task_id)
            for field in task["input"]["form"]:
                with self.subTest(task_id=task_id, field=field):
                    answer = copy.deepcopy(oracle["reference_answer"])
                    del answer["fields"][field]
                    self.assertFalse(grade(task, oracle, answer)["structured_correct"])

    def test_semantically_wrong_typed_values_fail(self):
        mutated = 0
        for task_id in self.ids:
            task, oracle = load_pair(task_id)
            for field, value in oracle["reference_answer"]["fields"].items():
                with self.subTest(task_id=task_id, field=field):
                    if value is None:
                        specification = task["input"]["form"][field]
                        wrong = {"integer": 0, "number": 0, "boolean": False,
                                 "string": "invented", "array": [], "object": {}}[specification["type"]]
                    elif type(value) is bool:
                        wrong = not value
                    elif isinstance(value, (int, float)):
                        wrong = value + 701
                    elif isinstance(value, str):
                        wrong = value + " unsupported"
                    elif isinstance(value, list):
                        wrong = value + ["invented"]
                    else:
                        wrong = {**value, "invented": True}
                    answer = copy.deepcopy(oracle["reference_answer"])
                    answer["fields"][field] = wrong
                    self.assertFalse(grade(task, oracle, answer)["structured_correct"])
                    mutated += 1
        self.assertGreater(mutated, 100)

    def test_blanket_deferral_is_not_a_winning_strategy(self):
        eligible = 0
        for task_id in self.ids:
            task, oracle = load_pair(task_id)
            check = next(c for c in oracle["checks"] if c["path"] == "/disposition")
            allowed = check["expected"] if check["operator"] == "one_of" else [check["expected"]]
            if "needs_clarification" in allowed:
                continue
            answer = copy.deepcopy(oracle["reference_answer"])
            answer["disposition"] = "needs_clarification"
            self.assertFalse(grade(task, oracle, answer)["structured_correct"])
            eligible += 1
        self.assertGreaterEqual(eligible, 50)

    def test_all_rendered_tasks_exclude_metadata_and_oracles(self):
        for task_id in self.ids:
            with self.subTest(task_id=task_id):
                task, _ = load_pair(task_id)
                messages = render(task)
                user = json.loads(messages["user"])
                self.assertEqual(user, task["input"])
                self.assertNotIn("scenario_group", user)
                self.assertNotIn("split", user)
                self.assertNotIn("reference_answer", user)
                self.assertNotIn("rubric", user)

    def test_schemas_are_parseable_and_declare_the_version(self):
        for name in ("task", "response", "oracle", "judgments"):
            schema = read_json(DATASET / "schemas" / f"{name}.schema.json")
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIn(schema["type"], {"object", "array"})

    def test_sqlite_export_integrity_balance_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dataset.sqlite3"
            command = [sys.executable, "-m", "renters_benchmark", "export-sqlite", str(output)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with sqlite3.connect(output) as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(connection.execute("SELECT count(*) FROM tasks").fetchone()[0], 100)
                self.assertEqual(connection.execute("SELECT count(*) FROM oracles").fetchone()[0], 100)
                self.assertEqual(dict(connection.execute("SELECT split, count(*) FROM tasks GROUP BY split")),
                                 {"optimization": 50, "validation": 20, "test": 30})
                task = read_json(DATASET / "tasks" / "ext_001.json")
                stored = connection.execute("SELECT input_json FROM tasks WHERE id = ?", ("ext_001",)).fetchone()[0]
                self.assertEqual(json.loads(stored), task["input"])
            prior_bytes = output.read_bytes()
            again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(output.read_bytes(), prior_bytes)


if __name__ == "__main__":
    unittest.main()
