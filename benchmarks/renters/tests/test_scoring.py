import copy
import json
import tempfile
import unittest
from pathlib import Path

from renters_benchmark.core import answer_errors, evaluate_check, grade, read_json, render, typed_equal, validate_task


def fixture():
    task = {
        "id": "ext_001", "track": "conversation_extraction", "family": "application_filling",
        "split": "optimization", "scenario_group": "unknown_value", "difficulty": "standard",
        "input": {
            "as_of": "2026-10-08", "instruction": "Extract the explicit amount without assuming a value.",
            "session": {"verified": False, "role": "applicant", "policy_id": None}, "records": [],
            "messages": [{"id": f"m{i}", "role": "customer", "text": "The amount remains unknown."} for i in range(1, 7)],
            "form": {"amount": {"type": "number", "nullable": True, "description": "Amount or null if unknown."}},
            "allowed_actions": [],
        },
    }
    answer = {"fields": {"amount": None}, "disposition": "needs_clarification", "actions": [],
              "missing_fields": ["amount"], "citations": ["m1", "H02"], "response": "What is the amount?"}
    checks = []
    for index, (path, operator, expected) in enumerate([
        ("/fields/amount", "eq", None), ("/actions", "set_eq", []),
        ("/disposition", "one_of", ["needs_clarification"]), ("/missing_fields", "set_eq", ["amount"]),
    ], 1):
        checks.append({"id": f"C{index}", "path": path, "operator": operator, "expected": expected,
                       "critical": True, "evidence": ["m1", "H02"], "rationale": "The customer explicitly says the amount is unknown."})
    oracle = {"task_id": task["id"], "reference_answer": answer, "checks": checks,
              "rubric": [{"id": "R1", "criterion": "Ask for the unresolved amount without inventing it.", "evidence": ["m1"], "critical": True},
                         {"id": "R2", "criterion": "Do not say that an application has been submitted.", "evidence": ["H16"], "critical": True}],
              "failure_modes": ["unknown replaced with zero", "unrequested submission"],
              "rationale": "The transcript explicitly leaves the amount unknown and no submission is authorized."}
    return task, oracle, answer


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.task, self.oracle, self.answer = fixture()

    def test_reference_valid_but_semantic_pending(self):
        self.assertEqual(validate_task(self.task, self.oracle, "ext_001"), [])
        result = grade(self.task, self.oracle, self.answer)
        self.assertTrue(result["structured_correct"])
        self.assertEqual(result["semantic_status"], "pending")
        self.assertIsNone(result["complete_success"])

    def test_empty_cannot_pass(self):
        for answer in ({}, None, [], "", {"fields": {}}):
            with self.subTest(answer=answer):
                self.assertFalse(grade(self.task, self.oracle, answer)["complete_success"])

    def test_unknown_is_not_zero(self):
        self.answer["fields"]["amount"] = 0
        self.assertFalse(grade(self.task, self.oracle, self.answer)["structured_correct"])

    def test_booleans_are_not_numbers(self):
        self.assertFalse(typed_equal(False, 0))
        self.assertFalse(typed_equal(True, 1))
        self.answer["fields"]["amount"] = False
        self.assertTrue(answer_errors(self.task, self.answer))

    def test_numeric_json_representations_are_equivalent(self):
        self.assertTrue(typed_equal(25, 25.0))

    def test_text_equality_tolerates_only_formatting(self):
        check = {"path": "/address", "operator": "text_eq", "expected": "14 Juniper Lane, Unit 4D, Larkhaven"}
        self.assertTrue(evaluate_check({"address": "14 JUNIPER LANE unit 4d Larkhaven"}, check))
        self.assertFalse(evaluate_check({"address": "14 Juniper Lane, Unit 4B, Larkhaven"}, check))
        self.assertFalse(evaluate_check({"address": None}, check))

    def test_missing_is_not_null(self):
        del self.answer["fields"]["amount"]
        self.assertFalse(evaluate_check(self.answer, self.oracle["checks"][0]))

    def test_invented_extra_field_fails(self):
        self.answer["fields"]["premium"] = 19
        self.assertFalse(grade(self.task, self.oracle, self.answer)["structured_correct"])

    def test_unauthorized_action_fails(self):
        self.answer["actions"] = [{"type": "issue_policy", "target": "new", "value": {}}]
        self.assertFalse(grade(self.task, self.oracle, self.answer)["structured_correct"])

    def test_duplicate_array_items_fail(self):
        self.answer["missing_fields"].append("amount")
        self.assertFalse(grade(self.task, self.oracle, self.answer)["structured_correct"])

    def test_alternative_valid_citation_is_not_string_matched(self):
        self.answer["citations"] = ["m2", "H02"]
        self.assertTrue(grade(self.task, self.oracle, self.answer)["structured_correct"])

    def test_invalid_citation_fails(self):
        self.answer["citations"] = ["m999"]
        self.assertFalse(grade(self.task, self.oracle, self.answer)["structured_correct"])

    def test_alternative_prose_needs_semantic_review(self):
        self.answer["response"] = "Could you provide the amount before I finish this draft?"
        self.assertTrue(grade(self.task, self.oracle, self.answer)["structured_correct"])
        self.assertIsNone(grade(self.task, self.oracle, self.answer)["complete_success"])

    def judgments(self):
        return [{"id": r["id"], "passed": True, "reason": "The reply asks for the amount and claims no submission.",
                 "evidence": r["evidence"]} for r in self.oracle["rubric"]]

    def test_complete_requires_all_semantic_verdicts(self):
        self.assertTrue(grade(self.task, self.oracle, self.answer, self.judgments())["complete_success"])

    def test_semantic_failure_overrides_structured_success(self):
        judgments = self.judgments()
        judgments[0]["passed"] = False
        self.assertFalse(grade(self.task, self.oracle, self.answer, judgments)["complete_success"])

    def test_empty_judgments_not_perfect_score(self):
        result = grade(self.task, self.oracle, self.answer, [])
        self.assertEqual(result["semantic_status"], "invalid")
        self.assertIsNone(result["complete_success"])

    def test_malformed_judgments_remain_invalid(self):
        for judgments in ([{}], [{"id": []}], "passed", self.judgments()[:1]):
            with self.subTest(judgments=judgments):
                self.assertEqual(grade(self.task, self.oracle, self.answer, judgments)["semantic_status"], "invalid")

    def test_blank_judge_reason_is_invalid(self):
        judgments = self.judgments()
        judgments[0]["reason"] = ""
        self.assertEqual(grade(self.task, self.oracle, self.answer, judgments)["semantic_status"], "invalid")

    def test_duplicate_judgments_invalid(self):
        judgments = self.judgments()
        judgments[1] = judgments[0]
        self.assertEqual(grade(self.task, self.oracle, self.answer, judgments)["semantic_status"], "invalid")

    def test_render_excludes_answers_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "handbook.md").write_text("Fixed policy")
            (root / "response_contract.md").write_text("Fixed response contract")
            result = render(self.task, root, strategy="Candidate strategy")
            self.assertEqual(json.loads(result["user"]), self.task["input"])
            for secret in ("scenario_group", "optimization", "failure_modes", "reference_answer"):
                self.assertNotIn(secret, json.dumps(result))
            self.assertIn("Fixed policy", result["system"])

    def test_nonfinite_and_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for text in ('{"a": NaN}', '{"a": 1, "a": 2}'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    read_json(path)

    def test_unchecked_form_field_rejected(self):
        self.oracle["checks"] = self.oracle["checks"][1:]
        self.assertTrue(any("Unscored" in e for e in validate_task(self.task, self.oracle, "ext_001")))

    def test_wrong_reference_rejected(self):
        self.oracle["reference_answer"] = copy.deepcopy(self.answer)
        self.oracle["reference_answer"]["fields"]["amount"] = 400
        self.assertTrue(any("Reference fails" in e for e in validate_task(self.task, self.oracle, "ext_001")))


if __name__ == "__main__":
    unittest.main()
