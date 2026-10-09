# Harborlight Renters v1 — dataset card

## Purpose and scope

One hundred original synthetic tasks for a CLI prompt-optimization experiment: 50 support/operations cases and 50 website-chat/document extraction cases. All necessary company rules appear in handbook.md. Models are asked for structured fields, a disposition, proposed actions, unresolved prerequisites, source citations, and a customer-facing reply.

The benchmark evaluates proposed decisions and document contents. It does not execute account mutations, bind coverage, adjudicate claims, or draft landlord leases. Fixed transcripts replace a stochastic user simulator. The suite was authored directly without a model pilot, as requested.

## Contents

- `tasks/{id}.json`: actor inputs plus evaluation metadata. Use the renderer to strip metadata.
- `CATALOG.md`: all 100 task links, families, splits and scenario mechanisms for reviewers.
- `oracles/{id}.json`: private reference answers, objective checks, semantic criteria, evidence and failure modes.
- `handbook.md` and `response_contract.md`: shared, fixed actor context.
- `schemas/`: JSON Schema documents for tasks, answers, private oracles and supplied judgments. The Python validator additionally checks cross-field/cross-file invariants.
- `manifest.json`: frozen split IDs and SHA-256 hashes of every task, oracle, schema, and shared actor document.
- `reviews/`: agent content-review records and a machine-generated verification record covering integrity, negative controls and relocation compatibility.
- `SOURCES.md`: primary-source inspiration and the boundary between public information and fictional rules.

| Family | Optimization | Validation | Test | Total |
| --- | ---: | ---: | ---: | ---: |
| Policy questions | 9 | 4 | 5 | 18 |
| Account changes | 8 | 3 | 5 | 16 |
| Claim intake | 8 | 3 | 5 | 16 |
| Application filling | 9 | 4 | 5 | 18 |
| Change-request extraction | 8 | 3 | 5 | 16 |
| Support handoff | 8 | 3 | 5 | 16 |
| Total | 50 | 20 | 30 | 100 |

## Intended experiment

Use optimization cases for failure analysis and candidate strategy creation, validation cases for selection, and the 30 test cases only for the final frozen comparison. Keep actor model/provider/settings, task inputs, handbook, schemas, turn budget, and evaluator fixed. Task-family skills intentionally recur across splits; close scenario variants must not cross splits. Scenario groups are manually assigned and reviewed, not an automatic proof of independence.

A test task contributes 1/30 (about 3.33 percentage points) to the overall test success rate. Report raw numerator/denominator and paired corrected/regressed cases. Repeated attempts on one case are not additional independent cases. Compare against a competent initial prompt and report prompt length, latency, and separate input/output tokens alongside quality.

## Labels and evaluation

Objective fields encode facts and decisions rather than exact free-form prose. Unknown null differs from explicitly absent/declined false or an empty list. Exact identifiers/dates/amounts stay exact; selected copied text has limited, documented formatting tolerance. Unordered collections use set equality and reject extra items. Each task's public form defines field meaning and any closed vocabulary; public instructions define action payloads.

Semantic rubrics cover supported explanation, uncertainty, source use, and false completion claims. A fully correct case requires a valid response, all objective checks, and all semantic criteria. There is no default perfect score for missing judge results. See EVALUATION.md for judge handling and scoring limits.

## Construction and evidence limits

Task authors and content reviewers were separate AI-agent roles. All people, organizations, accounts, properties, policies and conversations are synthetic; emails use reserved example/test domains. No customer data or copied insurer forms are included. Public insurance resources supplied topic/terminology inspiration, not legal rules or answer keys.

Offline validation can establish artifact integrity, answer/check consistency and rejection of known mutations. Content review adds a separate reading of the source evidence and rules. Neither is human adjudication, measured inter-annotator agreement, proof of headroom for a specific model, or evidence that prompt optimization succeeds. A future experiment may find a ceiling, regressions, or no improvement. No model performance or cost results are fabricated here.

The fictional handbook is intentionally compact. Results do not imply readiness to operate a real insurer or interpret real contracts. Closed vocabularies and synthetic conversations limit external validity; public holdouts cannot remain secret once distributed. The runner must keep test inputs and private answer keys out of optimizer context until final evaluation.
