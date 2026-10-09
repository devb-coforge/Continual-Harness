# Independent quality review — Harborlight Renters v1

Review scope: all 100 task inputs and private answer keys, the common handbook, split grouping, and outcome coverage. This is a content and offline-verifier audit, not evidence that a model improves on these tasks. No live model evaluation or pilot is part of this review.

A 2026-10-09 hardness pass rewrote all 100 public inputs and private oracles while keeping IDs, families, splits, and scenario groups. The 2026-10-08 case ledgers below still describe the preserved gold mechanisms; they do not enumerate every later distractor. Re-run offline `validate` after that pass; they are not a substitute for a fresh independent content review of the hardened transcripts.

## Review method

For each case, read the customer conversation and supplied records against the handbook, then verify the expected fields, action proposals, missing prerequisites, disposition, and semantic rubric. Check that the supplied evidence supports the expected answer and that the public form explains any required normalization. Inspect scenario mechanisms across splits rather than treating different names or IDs as independent scenarios.

The task authors and reviewer are separate agents sharing the same published contract. This provides an additional review pass, not independent human annotation or a measured inter-annotator agreement rate.

## Research informing this review

- The [official τ-bench task audit](https://taubench.com/blog/tau3-task-fixes.html) describes wrong expected actions, ambiguous instructions, impossible constraints, and omitted fallback behavior. This review therefore checks golds against the supplied rules and asks whether valid clarification or partial outcomes would be rejected.
- [Anthropic's agent evaluation guide](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) distinguishes conversational claims from environment outcomes and recommends examining transcripts to identify invalid graders. Here, outputs are explicitly proposals; successful benchmark grading must not be described as executed insurance transactions.
- [Elangovan, He, and Verspoor's leakage study](https://arxiv.org/abs/2102.01818) motivates checking train/test overlap beyond exact text. Shared skills are intentional; close scenario variants belong in one split.
- The [NAIC's policy explanation](https://content.naic.org/article/consumer-insight-understanding-your-homeowners-or-renters-policy) informed realistic distinctions between declarations, endorsements, insured addresses, limits, and property inventories. The benchmark's contract and all eligibility procedures remain fictional and self-contained.

## Handbook findings

| Finding | Requested resolution | Status |
| --- | --- | --- |
| H11's phrase “recipient consent” did not identify whose consent is required for third-party delivery. | Specify the verified authorized customer's approval of the particular recipient and destination. | Fixed by root and verified in the handbook. |
| H08 explicitly defined policy intervals but left endorsement boundary inclusivity implicit. | Apply the same inclusive-start, exclusive-end convention to issued endorsements. | Fixed by root and verified in the handbook. |
| H09 called foreign destinations out of scope without stating a supported country. | Establish the fictional service area or supply it in relevant tasks. | Fixed by root and verified in the handbook. |

## Case review ledger

All 100 public task/private oracle pairs are present. Separate author/reviewer roles inspected their evidence, rules, output contracts and reference answers. The detailed records are:

| Allocation | Cases | Record |
| --- | ---: | --- |
| Operations optimization, reviewed by the holdout author | 25 | [Operations optimization review](ops_optimization_independent_review.md) |
| Operations validation/test, reviewed by the extraction author | 25 | [Operations holdout review](ops_holdouts_independent_review.md) |
| Conversation extraction, reviewed by an operations author and final documentation reviewer | 50 | [Extraction review](extraction_independent_review.md) |

Concrete repairs included four unpublished category/prerequisite tokens in operations inputs, the reference reply for ops_029 omitting the amounts required by its rubric, and explicit dual-policy read authority for ext_043. The application review also introduced formatting tolerance for copied addresses, corrected a prospective occupancy date, and replaced a close unknown-address variant with application-record binding in ext_039.

Related cross-track scenarios were grouped into the same split, preserving 50 optimization / 20 validation / 30 test and family balance:

| Related cases | Common split | Mechanism |
| --- | --- | --- |
| ops_029 / ext_028 | Validation | Equally authoritative deductible conflict |
| ops_026 / ext_034 | Validation | Scheduled jewelry scope does not extend to other items |
| ops_036 / ext_041 | Test | Historical incident before effective cancellation |
| ops_038 / ext_044 | Test | Immediate active hazard with intake/handoff |

There are 96 scenario groups for the 100 tasks. Broad handbook skills recur intentionally across different scenarios; grouping and review do not establish unseen-policy generalization or statistically independent samples.

## Verification and folder isolation

The [verification record](verification.json) records the frozen dataset audit, whole-suite negative controls, 32 benchmark tests and 42 repository tests. All 100 reference answers pass their objective checks; semantic results remain pending in the absence of actual judgments. Empty outputs, invented fields, unauthorized actions, invalid citations and mutated required values are rejected.

The benchmark is isolated under `benchmarks/renters/`. Existing imports and CLI entry points forward to the bundled implementation; the old dataset path is a compatibility symlink. Relocation preserves the dataset-relative manifest and every task/oracle checksum. The outer-loop source, its test/configuration files and its architecture/design documents retain their pre-move hashes.

## Evidence limits

An offline reference-answer pass establishes that the authored answers are accepted by the local grader. It does not independently prove that the answers are correct, that natural-language rubrics are calibrated, that tasks have headroom for a selected model, or that prompt optimization improves held-out performance. Those are separate claims requiring subsequent measurements.
