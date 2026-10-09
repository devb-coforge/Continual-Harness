"""Dataset integrity checks, safe task rendering, and explicit scoring boundaries."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "renters_v1"
DISPOSITIONS = {"answered", "ready", "needs_clarification", "escalate", "partial", "no_action"}
FAMILIES = {
    "support_ops": {"policy_questions": 18, "account_changes": 16, "claim_intake": 16},
    "conversation_extraction": {
        "application_filling": 18, "change_request_extraction": 16, "support_handoff": 16,
    },
}
SPLITS = {"optimization": 50, "validation": 20, "test": 30}
RESPONSE_KEYS = {"fields", "disposition", "actions", "missing_fields", "citations", "response"}
OPERATORS = {"eq", "one_of", "set_eq", "contains", "not_contains", "text_eq"}
MISSING = object()


def read_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON number: {value}")

    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(), parse_constant=reject_constant, object_pairs_hook=unique_keys)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def typed_equal(left: Any, right: Any) -> bool:
    """JSON booleans must not compare equal to numeric 0/1."""
    if type(left) is not type(right):
        if isinstance(left, (int, float)) and not isinstance(left, bool):
            return isinstance(right, (int, float)) and not isinstance(right, bool) and left == right
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(typed_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def normalized_text(value: str) -> str:
    """Formatting tolerance only; never normalize dates, amounts, or identifiers this way."""
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())


def pointer(document: Any, path: str) -> Any:
    if not isinstance(path, str) or not path.startswith("/"):
        return MISSING
    current = document
    for raw in path[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return MISSING
    return current


def evaluate_check(answer: dict[str, Any], check: dict[str, Any]) -> bool:
    actual = pointer(answer, check["path"])
    expected = check["expected"]
    operator = check["operator"]
    if actual is MISSING:
        return False
    if operator == "eq":
        return typed_equal(actual, expected)
    if operator == "text_eq":
        return isinstance(actual, str) and isinstance(expected, str) and normalized_text(actual) == normalized_text(expected)
    if operator == "one_of":
        return isinstance(expected, list) and any(typed_equal(actual, item) for item in expected)
    if operator == "set_eq":
        if not isinstance(actual, list) or not isinstance(expected, list):
            return False
        if len({canonical(v) for v in actual}) != len(actual):
            return False
        return len(actual) == len(expected) and all(
            any(typed_equal(value, other) for other in actual) for value in expected
        )
    if operator in {"contains", "not_contains"}:
        if not isinstance(actual, list):
            return False
        found = any(typed_equal(item, expected) for item in actual)
        return found if operator == "contains" else not found
    return False


def source_ids(task: dict[str, Any]) -> set[str]:
    data = task["input"]
    return {"session", "as_of", *(f"H{i:02}" for i in range(1, 17)),
            *(m["id"] for m in data["messages"]), *(r["id"] for r in data["records"])}


def matches_type(value: Any, specification: dict[str, Any]) -> bool:
    if value is None:
        return specification["nullable"]
    kind = specification["type"]
    types = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
             "array": list, "object": dict}
    if kind not in types or not isinstance(value, types[kind]):
        return False
    if kind in {"integer", "number"} and isinstance(value, bool):
        return False
    return "enum" not in specification or any(typed_equal(value, v) for v in specification["enum"])


def answer_errors(task: dict[str, Any], answer: Any) -> list[str]:
    errors = []
    if not isinstance(answer, dict) or set(answer) != RESPONSE_KEYS:
        return ["Response must be an object with exactly the six response-contract keys."]
    form = task["input"]["form"]
    if not isinstance(answer["fields"], dict) or set(answer["fields"]) != set(form):
        errors.append("fields must contain exactly the task's form fields.")
    else:
        for name, specification in form.items():
            if not matches_type(answer["fields"][name], specification):
                errors.append(f"fields.{name} violates its declared type, nullability, or enum.")
    if not isinstance(answer["disposition"], str) or answer["disposition"] not in DISPOSITIONS:
        errors.append("Invalid disposition.")
    actions = answer["actions"]
    if not isinstance(actions, list):
        errors.append("actions must be an array.")
    else:
        for action in actions:
            if not isinstance(action, dict) or set(action) != {"type", "target", "value"}:
                errors.append("Each action needs exactly type, target, value.")
            elif (not isinstance(action["type"], str)
                  or action["type"] not in task["input"]["allowed_actions"]
                  or not isinstance(action["target"], str) or not action["target"]):
                errors.append("Action type is not allowed or target is invalid.")
        if len({canonical(a) for a in actions}) != len(actions):
            errors.append("Duplicate actions are not allowed.")
    for name in ("missing_fields", "citations"):
        value = answer[name]
        if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
            errors.append(f"{name} must be an array of nonempty strings.")
        elif len(value) != len(set(value)):
            errors.append(f"{name} contains duplicates.")
    if isinstance(answer["citations"], list):
        if not answer["citations"]:
            errors.append("At least one supporting citation is required.")
        elif any(not isinstance(c, str) or c not in source_ids(task) for c in answer["citations"]):
            errors.append("Citation does not resolve to a supplied source.")
    if not isinstance(answer["response"], str) or not answer["response"].strip():
        errors.append("response must be a nonempty user-facing explanation.")
    return errors


def grade(task: dict[str, Any], oracle: dict[str, Any], answer: Any,
          judgments: Any = None) -> dict[str, Any]:
    """Never equate objective-field correctness with a fully judged case pass."""
    errors = answer_errors(task, answer)
    checks = [{"id": c["id"], "passed": evaluate_check(answer, c) if isinstance(answer, dict) else False,
               "critical": c["critical"]} for c in oracle["checks"]]
    structured = not errors and all(c["passed"] for c in checks)
    semantic_status = "pending"
    judgment_errors: list[str] = []
    if judgments is not None:
        expected_ids = {r["id"] for r in oracle["rubric"]}
        if not isinstance(judgments, list):
            judgment_errors.append("Judgments must be an array.")
        else:
            ids = []
            for entry in judgments:
                if not isinstance(entry, dict) or set(entry) != {"id", "passed", "reason", "evidence"}:
                    judgment_errors.append("Each judgment needs id, passed, reason, evidence.")
                    continue
                ids.append(entry["id"])
                if not isinstance(entry["id"], str) or type(entry["passed"]) is not bool:
                    judgment_errors.append("Invalid judgment ID or non-boolean verdict.")
                if not isinstance(entry["reason"], str) or not entry["reason"].strip():
                    judgment_errors.append("Every verdict requires a reason.")
                evidence = entry["evidence"]
                if (not isinstance(evidence, list) or not evidence
                        or any(not isinstance(e, str) or e not in source_ids(task) for e in evidence)):
                    judgment_errors.append("Every verdict requires resolvable input evidence.")
            if any(not isinstance(i, str) for i in ids) or set(i for i in ids if isinstance(i, str)) != expected_ids or len(ids) != len(expected_ids):
                judgment_errors.append("Judgments must cover every rubric exactly once.")
        semantic_status = "invalid" if judgment_errors else (
            "passed" if all(j["passed"] for j in judgments) else "failed")
    complete: bool | None = None
    if not structured or semantic_status == "failed":
        complete = False
    elif semantic_status == "passed":
        complete = True
    return {
        "task_id": task["id"], "response_valid": not errors, "response_errors": errors,
        "checks": checks, "objective_passes": sum(c["passed"] for c in checks),
        "objective_total": len(checks), "structured_correct": structured,
        "semantic_status": semantic_status, "judgment_errors": judgment_errors,
        "complete_success": complete,
    }


def validate_task(task: Any, oracle: Any, filename: str) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(f"{filename}: {message}")

    required_task = {"id", "track", "family", "split", "scenario_group", "difficulty", "input"}
    if not isinstance(task, dict) or set(task) != required_task:
        return [f"{filename}: Invalid task keys."]
    require(task["id"] == filename, "ID must match filename.")
    require(bool(re.fullmatch(r"(ops|ext)_\d{3}", task["id"])), "Invalid ID.")
    require(task["track"] in FAMILIES, "Invalid track.")
    require(task["family"] in FAMILIES.get(task["track"], {}), "Family/track mismatch.")
    require(task["split"] in SPLITS, "Invalid split.")
    require(isinstance(task["scenario_group"], str) and bool(task["scenario_group"].strip()), "Missing group.")
    require(task["difficulty"] in {"standard", "challenging", "adversarial"}, "Invalid difficulty.")
    data = task["input"]
    if not isinstance(data, dict) or set(data) != {"as_of", "instruction", "session", "records", "messages", "form", "allowed_actions"}:
        return errors + [f"{filename}: Invalid input keys."]
    try:
        require(date.fromisoformat(data["as_of"]).isoformat() == data["as_of"], "as_of must be ISO date.")
    except (TypeError, ValueError):
        require(False, "Invalid as_of date.")
    require(isinstance(data["instruction"], str) and len(data["instruction"].strip()) >= 20, "Instruction too short.")
    require(isinstance(data["session"], dict)
            and type(data["session"].get("verified")) is bool
            and isinstance(data["session"].get("role"), str)
            and bool(data["session"].get("role"))
            and "policy_id" in data["session"]
            and (data["session"]["policy_id"] is None or isinstance(data["session"]["policy_id"], str)),
            "Session needs explicit verification, role, and policy_id (null if not selected).")
    require(isinstance(data["allowed_actions"], list) and all(isinstance(a, str) and a for a in data["allowed_actions"]), "Invalid allowed_actions.")
    if not isinstance(data["messages"], list) or not isinstance(data["records"], list):
        return errors + [f"{filename}: records/messages must be arrays."]
    require(len(data["messages"]) >= (6 if task["track"] == "conversation_extraction" else 2), "Too few conversation turns.")
    all_ids = []
    for entry in data["messages"]:
        if not isinstance(entry, dict) or set(entry) != {"id", "role", "text"}:
            require(False, "Invalid message keys.")
            continue
        all_ids.append(entry["id"])
        require(isinstance(entry["id"], str) and bool(re.fullmatch(r"m\d+", entry["id"])), "Invalid message ID.")
        require(entry["role"] in {"customer", "bot", "agent", "third_party"}, "Invalid message role.")
        require(isinstance(entry["text"], str) and bool(entry["text"].strip()), "Empty message.")
    for entry in data["records"]:
        if not isinstance(entry, dict) or set(entry) != {"id", "kind", "data"}:
            require(False, "Invalid record keys.")
            continue
        all_ids.append(entry["id"])
        require(isinstance(entry["id"], str) and bool(re.fullmatch(r"r\d+", entry["id"])), "Invalid record ID.")
        require(isinstance(entry["kind"], str) and isinstance(entry["data"], dict), "Invalid record kind/data.")
    require(all(isinstance(i, str) for i in all_ids) and len(set(str(i) for i in all_ids)) == len(all_ids), "Duplicate source IDs.")
    if not isinstance(data["form"], dict) or not data["form"]:
        return errors + [f"{filename}: Missing form."]
    for name, specification in data["form"].items():
        require(bool(re.fullmatch(r"[a-z][a-z0-9_]*", name)), "Form field must use snake_case.")
        if not isinstance(specification, dict) or not {"type", "nullable", "description"} <= set(specification):
            require(False, f"Invalid form definition {name}.")
            continue
        require(specification["type"] in {"string", "integer", "number", "boolean", "array", "object"}, "Invalid field type.")
        require(type(specification["nullable"]) is bool, "nullable must be boolean.")
        require(isinstance(specification["description"], str) and bool(specification["description"].strip()), "Missing field description.")
        if "enum" in specification:
            require(isinstance(specification["enum"], list) and bool(specification["enum"]), "Invalid enum.")
    if errors:
        return errors
    if not isinstance(oracle, dict) or set(oracle) != {"task_id", "reference_answer", "checks", "rubric", "failure_modes", "rationale"}:
        return errors + [f"{filename}: Invalid oracle keys."]
    require(oracle["task_id"] == task["id"], "Oracle ID mismatch.")
    require(isinstance(oracle["rationale"], str) and len(oracle["rationale"]) >= 30, "Insufficient gold rationale.")
    require(isinstance(oracle["failure_modes"], list) and len(oracle["failure_modes"]) >= 2 and all(isinstance(f, str) and f.strip() for f in oracle["failure_modes"]), "Need two failure modes.")
    if not isinstance(oracle["checks"], list) or not isinstance(oracle["rubric"], list):
        return errors + [f"{filename}: Invalid checks/rubric."]
    require(len(oracle["rubric"]) >= 2, "Need at least two semantic criteria.")
    evidence_ids = source_ids(task)
    check_paths = set()
    for collection, key in ((oracle["checks"], "rationale"), (oracle["rubric"], "criterion")):
        ids = []
        for item in collection:
            base_keys = {"id", "evidence", "critical", key}
            if key == "rationale":
                base_keys |= {"path", "operator", "expected"}
            if not isinstance(item, dict) or set(item) != base_keys:
                require(False, "Invalid check/rubric keys.")
                continue
            ids.append(item["id"])
            require(isinstance(item["id"], str) and bool(item["id"]), "Invalid criterion ID.")
            require(type(item["critical"]) is bool, "critical must be boolean.")
            require(isinstance(item[key], str) and len(item[key]) >= 15, "Uninformative criterion/rationale.")
            evidence = item["evidence"]
            require(isinstance(evidence, list) and bool(evidence) and all(isinstance(e, str) and e in evidence_ids for e in evidence), "Missing/unresolvable gold evidence.")
            if key == "rationale":
                require(item["operator"] in OPERATORS, "Unknown check operator.")
                require(isinstance(item["path"], str) and pointer(oracle["reference_answer"], item["path"]) is not MISSING, "Check points to absent field.")
                if isinstance(item["path"], str):
                    check_paths.add(item["path"])
                if item["operator"] in {"set_eq", "one_of"}:
                    require(isinstance(item["expected"], list), "Set/choice expected must be array.")
                require(item["path"] != "/response", "Do not exact-match prose.")
        require(all(isinstance(i, str) for i in ids) and len(ids) == len(set(str(i) for i in ids)), "Repeated criterion ID.")
    for path in {"/actions", "/missing_fields", "/disposition", *(f"/fields/{k}" for k in data["form"])}:
        require(path in check_paths, f"Unscored required path: {path}")
    if not errors:
        result = grade(task, oracle, oracle["reference_answer"])
        require(result["structured_correct"], f"Reference fails objective checks: {result}")
    return errors


def load_pair(task_id: str, dataset: Path = DATASET) -> tuple[dict[str, Any], dict[str, Any]]:
    if not re.fullmatch(r"(ops|ext)_\d{3}", task_id):
        raise ValueError("Invalid task ID.")
    return read_json(dataset / "tasks" / f"{task_id}.json"), read_json(dataset / "oracles" / f"{task_id}.json")


def render(task: dict[str, Any], dataset: Path = DATASET, strategy: str | None = None) -> dict[str, str]:
    """Explicit allowlist: metadata, golds, rubrics, and split labels never reach the model."""
    if strategy is None:
        strategy = "Handle the customer's request accurately using the supplied company rules and evidence. Complete the requested document and explain the appropriate next step."
    system = "\n\n".join([
        strategy,
        (dataset / "handbook.md").read_text(),
        (dataset / "response_contract.md").read_text(),
    ])
    return {"system": system, "user": json.dumps(task["input"], indent=2, ensure_ascii=False)}


def audit(dataset: Path = DATASET, verify_manifest: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    tasks = []
    task_files = sorted((dataset / "tasks").glob("*.json"))
    oracle_files = sorted((dataset / "oracles").glob("*.json"))
    expected_ids = {f"{prefix}_{i:03}" for prefix in ("ops", "ext") for i in range(1, 51)}
    task_ids = {p.stem for p in task_files}
    oracle_ids = {p.stem for p in oracle_files}
    if task_ids != expected_ids:
        errors.append(f"Task inventory differs: missing={sorted(expected_ids-task_ids)}, extra={sorted(task_ids-expected_ids)}")
    if oracle_ids != expected_ids:
        errors.append(f"Oracle inventory differs: missing={sorted(expected_ids-oracle_ids)}, extra={sorted(oracle_ids-expected_ids)}")
    for path in task_files:
        try:
            task = read_json(path)
            oracle = read_json(dataset / "oracles" / path.name)
            case_errors = validate_task(task, oracle, path.stem)
            errors.extend(case_errors)
            if not case_errors:
                tasks.append(task)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{path.stem}: {exc}")
    counts = Counter(t["split"] for t in tasks)
    if dict(counts) != SPLITS:
        errors.append(f"Split counts differ: {dict(counts)}")
    for track, families in FAMILIES.items():
        actual = Counter(t["family"] for t in tasks if t["track"] == track)
        if dict(actual) != families:
            errors.append(f"Family counts differ for {track}: {dict(actual)}")
        actual_splits = Counter(t["split"] for t in tasks if t["track"] == track)
        if dict(actual_splits) != {"optimization": 25, "validation": 10, "test": 15}:
            errors.append(f"Track split balance differs for {track}: {dict(actual_splits)}")
        for family, total in families.items():
            expected = {"optimization": 9 if total == 18 else 8,
                        "validation": 4 if total == 18 else 3, "test": 5}
            actual_family_splits = Counter(t["split"] for t in tasks if t["family"] == family)
            if dict(actual_family_splits) != expected:
                errors.append(f"Family split balance differs for {family}: {dict(actual_family_splits)}")
    groups: dict[str, set[str]] = defaultdict(set)
    conversations: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        groups[task["scenario_group"]].add(task["split"])
        normalized = re.sub(r"\s+", " ", " ".join(m["text"] for m in task["input"]["messages"])).casefold()
        conversations[normalized].append(task["id"])
    for group, splits in groups.items():
        if len(splits) > 1:
            errors.append(f"Scenario group leaks across splits: {group}: {sorted(splits)}")
    for ids in conversations.values():
        if len(ids) > 1:
            errors.append(f"Duplicate conversation: {ids}")
    manifest_path = dataset / "manifest.json"
    if verify_manifest:
        if not manifest_path.exists():
            errors.append("Manifest is missing.")
        else:
            try:
                manifest = read_json(manifest_path)
                current = make_manifest(dataset)
                if manifest != current:
                    errors.append("Manifest metadata/checksums differ from current dataset.")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"Invalid manifest: {exc}")
    return {
        "valid": not errors, "task_count": len(tasks), "split_counts": dict(counts),
        "family_counts": dict(Counter(t["family"] for t in tasks)),
        "difficulty_counts": dict(Counter(t["difficulty"] for t in tasks)),
        "scenario_groups": len(groups), "errors": errors,
        "limits": "Offline integrity and reference checks; no empirical model performance or automatic semantic truth guarantee.",
    }


def make_manifest(dataset: Path = DATASET) -> dict[str, Any]:
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    files = [dataset / "handbook.md", dataset / "response_contract.md"]
    files += sorted((dataset / "schemas").glob("*.json"))
    files += sorted((dataset / "tasks").glob("*.json"))
    files += sorted((dataset / "oracles").glob("*.json"))
    cases = [read_json(p) for p in sorted((dataset / "tasks").glob("*.json"))]
    return {
        "dataset": "harborlight_renters_v1", "version": "1.0.0", "task_count": len(cases),
        "splits": {s: [t["id"] for t in cases if t["split"] == s] for s in SPLITS},
        "sha256": {str(p.relative_to(dataset)): digest(p) for p in files},
    }
