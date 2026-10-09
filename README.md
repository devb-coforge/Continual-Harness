# Continual-Harness

A Python CLI that optimizes an actor's strategy prompt using a fixed **100-task renters insurance benchmark**, an OpenRouter judge and optimizer, paired validation, and a frozen held-out comparison. The fictional company, Harborlight Renters, has one supplied handbook; no outside insurance knowledge is needed.

## Prompt optimization

The [architecture](docs/architecture.md) implements the discussed loop: execute → evaluate → diagnose/propose → compare → promote/reject → freeze → test. The handbook, task inputs and scoring stay fixed; only the strategy changes.

Run from this repository checkout. The packages use the standard library; dataset files remain in the checkout. An editable install can expose the `continual-harness` console command; the examples below need no installation. For a non-editable package install, supply the checkout's dataset directory with `--dataset`.

Exercise the full flow without API calls:

```bash
source .venv/bin/activate
python -m continual_harness demo --output artifacts/demo-001
python -m continual_harness report artifacts/demo-001
```

The demo uses private reference answers and scripted judgments. Its scores are **synthetic orchestration evidence**, not model performance.

For live use, copy `harness.example.toml` to a config file and choose each role's model and provider slug. Set `OPENROUTER_API_KEY` in your shell environment; the CLI does not read or modify `.env` files. Each configured provider must support the selected model, temperature and JSON-object output. Explicit routing disables fallbacks.

```bash
python -m continual_harness optimize --config harness.toml --output artifacts/run-001
python -m continual_harness report artifacts/run-001
python -m continual_harness test artifacts/run-001
```

`optimize` makes paid calls to all optimization cases and paired validation cases for each iteration, with the configured repetitions. It saves SQLite metadata, exact call artifacts, prompt lineage, paired results and `final_strategy.txt`. An optional `--strategy-file` supplies your competent baseline; a reasonable default strategy is included. Output directories must be new. Progress and failed calls are persisted as they finish; there is no resume command. Calls retry provider failures, malformed JSON, and invalid judge/optimizer contracts up to `max_attempts` (default 4), with exponential backoff and jitter starting at `retry_delay_seconds` (default 1). Every attempt is saved and included in usage/cost totals. Valid task-quality failures are not retried.

Exhausted actor/judge failures are terminal `model_failure` cases with `complete_success: false`. They count in success rates and paired improvements/regressions; reports separately show graded observations, model failures, and failure stages. Complete coverage means every intended case has a graded verdict or terminal model failure. Only graded optimization examples reach the optimizer. An exhausted optimizer failure retains the incumbent and is recorded in `optimization_report.json`. Promotion requires complete coverage, positive gain above `min_gain`, and regressions at or below `max_regressions` (default zero). Reports preserve role-specific input/output tokens, recorded costs and missing-usage coverage. Calibrate the semantic judge manually before treating its verdicts as reliable evidence. The separate `test` command reserves one held-out baseline/final comparison on the frozen experiment and never changes the selected prompt. Failed/interrupted tests remain reserved.

## Benchmark bundle

The 100-task benchmark, answer keys, offline tools, tests, and dataset documentation are isolated in [benchmarks/renters/](benchmarks/renters/README.md). The split remains 50 optimization / 20 validation / 30 test, with equal support/operations and conversation/document tracks.

```bash
source .venv/bin/activate
python -m benchmarks.renters validate
python -m unittest discover -s tests -q
```

See the [task catalog](benchmarks/renters/datasets/renters_v1/CATALOG.md), [dataset card](benchmarks/renters/datasets/renters_v1/DATASET_CARD.md), and [evaluation protocol](benchmarks/renters/datasets/renters_v1/EVALUATION.md).

Offline checks and the synthetic demo do not establish live model improvement. No real insurance transaction is performed. Task difficulty labels are author estimates, not measured model performance.
