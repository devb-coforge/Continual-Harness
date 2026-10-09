# Renters support benchmark implementation checklist

Build the agreed 100 fixed tasks for a Python/OpenRouter CLI harness. Benchmark creation excludes a model pilot and outer-loop implementation; the user supplies the outer loop separately in `continual_harness/`.

1. [x] Publish a fictional insurer handbook, response contract, and source provenance.
2. [x] Author 50 support/operations tasks: 18 policy questions, 16 account changes, 16 claim intake.
3. [x] Author 50 conversation/document tasks: 18 applications, 16 change requests, 16 support handoffs.
4. [x] Separate model-visible inputs and private answer keys, with 50 optimization / 20 validation / 30 test cases; balance both tracks 25/10/15.
5. [x] Supply specific reference answers, objective checks, semantic rubrics, evidence IDs, and documented failure modes for every case.
6. [x] Validate schema, evidence, oracle consistency, family/split counts, missing/extra artifacts, and duplicate/related-scenario leakage.
7. [x] Independently review all tasks, repair findings, and record the limits of this review.
8. [x] Document dataset use and run offline checks, including evaluator negative controls. No live model performance claim.

The immutable policy and task inputs define truth. The outer loop optimizes only the strategy prompt. The benchmark measures decisions, proposed actions, document fields, and explanations; it does not execute insurance transactions. SQLite is a local dataset/index convenience, not evidence of real execution.

## Bundle integration

Dataset, offline implementation, tests, and this creation plan are isolated under `benchmarks/renters/`. The public `renters_benchmark` imports and CLI forward to this implementation, and the former `datasets/renters_v1` path remains a compatibility symlink for saved experiments. The dataset-relative manifest remains byte-for-byte unchanged by the move.

The outer-loop source, its test file, configuration example and architecture/design docs retain their original hashes. Repository package discovery includes the benchmark namespace and repository test discovery includes the relocated benchmark suite. See the [bundle README](../../README.md) for commands and the [verification record](../../datasets/renters_v1/reviews/verification.json) for the final checks.
