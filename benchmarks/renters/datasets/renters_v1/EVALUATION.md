# Evaluation and experiment protocol

## Input boundary

Render via `python -m benchmarks.renters render ID`. It emits a `system` string (strategy + fixed handbook + fixed response contract) and a `user` string containing only the task input. Pass these messages to the chosen actor model using a future runner. Never include oracle, difficulty, scenario-group or split metadata. The renderer works without access to the oracles directory.

Optimization may use the 50 optimization task outputs and feedback; selection may use the 20 validation outcomes. The 30 test inputs, answers and feedback are withheld from the optimizer. Freeze the final prompt before the paired baseline/final test evaluation. Reviewing test artifacts during dataset construction does not authorize sending them to a future optimizer.

## Objective evaluation

`score` checks the exact response contract, declared field types/nullability/enums, action vocabulary, unique collections, resolvable citations, and every task-specific declarative check. Operators:

| Operator | Meaning |
| --- | --- |
| `eq` | Typed deep equality; false is not 0 and true is not 1; JSON numeric 25 and 25.0 are equivalent. |
| `one_of` | One of an explicitly listed set of substantively acceptable values. |
| `set_eq` | Unordered array equality with no duplicates and no extra entries. |
| `contains` / `not_contains` | Presence/absence of a typed array element. |
| `text_eq` | Copied name/address tokens with Unicode normalization, case-folding, punctuation and whitespace tolerance. No synonym, abbreviation, identifier or numeric-value normalization. |

Every form field, actions, disposition, and missing_fields is checked. Exact full-sentence response matching is forbidden. A resolvable citation does not by itself prove support; semantic judging must inspect the cited content. Objective pass fraction is a diagnostic metric; complete-case success is separate.

## Semantic judging

Give a judge the fixed handbook, public task, actor answer, and private rubric. Ask for a binary verdict per criterion with source evidence and a concise reason. Hide the actor's prompt/version, optimization history and expected improvement direction. Reference answers illustrate an acceptable answer but are not canonical prose. Prefer rubric-based judgments to stylistic ranking; if using pairwise judging later, counterbalance answer order.

Example judgment file shape (IDs must match that case's actual rubric):

```json
[
  {"id": "R1", "passed": true, "reason": "The reply preserves the uncertainty stated in m3.", "evidence": ["m3", "H02"]},
  {"id": "R2", "passed": false, "reason": "The reply claims execution although only a proposal exists.", "evidence": ["H16"]}
]
```

Missing/duplicate criteria, non-boolean verdicts, blank rationales, and unresolvable evidence are invalid judge results. Invalid/missing judgments never count as successful cases. The CLI checks their shape/completeness, not whether the judge reason is substantively correct. Calibrate any future judge with manually checked good/bad answers and inspect disagreements before relying on scores.

## Metrics and failure accounting

`structured_correct` requires all objective checks and response validation. `semantic_status` is pending/passed/failed/invalid. `complete_success` is false on an observed objective or semantic failure, true only when both are successful, otherwise null. All delivered criteria are required; `critical` records their diagnostic severity, not an exemption from complete-case success.

Separate API/provider failures, response parsing failures, tool/runtime failures (if later added), and invalid judgments from valid task-quality observations. Report intended cases, completed responses, valid judgments, and exclusions. Never silently discard failed generations or report an incomplete cohort as a full benchmark score.

Report family-level and overall raw counts, paired improvements/regressions, and run-to-run variation. Keep costs for actor, optimizer, and judge separate, with input/output tokens and missing-usage coverage. No dynamic task generation or changes to test golds during optimization.

## Integrity and reproducibility

`validate` compares all current files against manifest checksums and verifies exact inventory, family/split totals, group separation, duplicate conversations, evidence IDs, coverage of required checks and all reference answers. Content review addresses ambiguities these structural checks cannot detect.

`build-manifest` is an explicit authoring operation and refuses to freeze an invalid dataset. After any content repair, rerun content review for affected cases, validation, negative controls and the test suite before rebuilding the manifest. The exported SQLite database contains the same public inputs and private oracles in distinct tables; keep the entire database private from the actor.
