from __future__ import annotations

from collections import Counter
from typing import Any


def summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    intended = len(results)
    complete = sum(r["complete_success"] is not None for r in results)
    successes = sum(r["complete_success"] is True for r in results)
    return {"intended": intended, "actor_completed": sum(r.get("answer") is not None for r in results),
            "valid_judgments": sum(r.get("semantic_status") in {"passed", "failed"} for r in results),
            "quality_observations": complete, "successes": successes,
            "complete_coverage": all(r["status"] == "evaluated" for r in results),
            "success_rate": successes / intended if intended else None,
            "statuses": dict(Counter(r["status"] for r in results)),
            "by_family": {family: {"intended": sum(r["family"] == family for r in results),
                                   "successes": sum(r["family"] == family and r["complete_success"] is True for r in results)}
                          for family in sorted({r["family"] for r in results})}}


def compare(incumbent: list[dict[str, Any]], candidate: list[dict[str, Any]],
            min_gain: float = 0.0, max_regressions: int = 0) -> dict[str, Any]:
    def index(results: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
        indexed = {(r["task_id"], r["repetition"]): r for r in results}
        if len(indexed) != len(results):
            raise ValueError("Duplicate task/repetition pair")
        return indexed

    left, right = index(incumbent), index(candidate)
    if not left or left.keys() != right.keys():
        raise ValueError("Comparison requires identical nonempty task/repetition cohorts")
    improved, regressed = [], []
    for key in sorted(left):
        if left[key]["status"] != "evaluated" or right[key]["status"] != "evaluated":
            continue
        a, b = left[key]["complete_success"], right[key]["complete_success"]
        if a is False and b is True:
            improved.append({"task_id": key[0], "repetition": key[1]})
        elif a is True and b is False:
            regressed.append({"task_id": key[0], "repetition": key[1]})
    a, b = summary(incumbent), summary(candidate)
    coverage = a["complete_coverage"] and b["complete_coverage"]
    gain = b["success_rate"] - a["success_rate"]
    promote = coverage and gain > min_gain and len(regressed) <= max_regressions
    return {"incumbent": a, "candidate": b, "improvements": improved, "regressions": regressed,
            "gain": gain, "promote": promote,
            "reason": "promoted" if promote else (
                "incomplete_evaluation" if not coverage else
                "regression_limit" if len(regressed) > max_regressions else "insufficient_gain"),
            "per_repetition": [{"repetition": repetition,
                                "incumbent_successes": sum(r["repetition"] == repetition and r["complete_success"] is True for r in incumbent),
                                "candidate_successes": sum(r["repetition"] == repetition and r["complete_success"] is True for r in candidate)}
                               for repetition in sorted({key[1] for key in left})]}
