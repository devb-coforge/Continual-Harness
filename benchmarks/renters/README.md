# Harborlight renters benchmark

This folder owns the **100-task renters insurance benchmark**: synthetic customer chats and records, private answer keys, the fixed company handbook, offline grading/validation tools, tests, and creation/review documentation. The repository's [outer loop](../../README.md) lives in `continual_harness/`.

```text
benchmarks/renters/
├── datasets/renters_v1/     # 100 inputs, 100 private oracles, schemas, manifest, reviews
├── renters_benchmark/      # Canonical offline CLI and scoring implementation
├── tests/                  # Dataset and scoring verification
└── docs/plans/             # Benchmark creation checklist
```

| Family | Optimization | Validation | Test | Total |
| --- | ---: | ---: | ---: | ---: |
| Policy questions | 9 | 4 | 5 | 18 |
| Account changes | 8 | 3 | 5 | 16 |
| Claim intake | 8 | 3 | 5 | 16 |
| Application filling | 9 | 4 | 5 | 18 |
| Change-request extraction | 8 | 3 | 5 | 16 |
| Support handoff | 8 | 3 | 5 | 16 |
| Total | 50 | 20 | 30 | 100 |

Start with the [task catalog](datasets/renters_v1/CATALOG.md), [dataset card](datasets/renters_v1/DATASET_CARD.md), [handbook](datasets/renters_v1/handbook.md), [evaluation protocol](datasets/renters_v1/EVALUATION.md), and [review record](datasets/renters_v1/reviews/quality_review.md). [Source provenance](datasets/renters_v1/SOURCES.md) records public resources used for terminology and evaluation design. All tasks and procedures are fictional.

## Commands

Run from the repository root with Python 3.11+. The benchmark uses the standard library and makes no API calls. Activate the repository's environment before Python commands:

```bash
source .venv/bin/activate
python -m benchmarks.renters validate
python -m unittest discover -s benchmarks/renters/tests -q
```

Render actor context, optionally substituting the strategy under investigation:

```bash
python -m benchmarks.renters render ops_001
python -m benchmarks.renters render ext_001 --strategy-file my_strategy.txt
```

The renderer supplies only the public input, handbook, response contract, and strategy. It excludes split/scenario/difficulty metadata, reference answers, checks, and rubrics. Use it instead of passing raw task files to the actor.

Score a saved actor response:

```bash
python -m benchmarks.renters score ext_001 response.json
python -m benchmarks.renters score ext_001 response.json --judgments judgments.json
```

Each submitted judgment needs a rubric `id`, boolean `passed`, nonempty `reason`, and resolvable source-ID `evidence`. Missing or invalid judgments cannot establish full success. A correct structured answer without semantic judgments has `complete_success: null`. The offline CLI validates judgments; the outer loop owns calling the judge. See the [protocol](datasets/renters_v1/EVALUATION.md) for the evidence limits.

Export a new local SQLite index:

```bash
python -m benchmarks.renters export-sqlite /tmp/harborlight-renters.sqlite3
```

The export refuses to overwrite existing files and includes private answer keys. Separate tables do not provide an actor access-control boundary. JSON files are canonical; SQLite is an optional dataset index, not an account transaction engine.

## Outer-loop integration

The harness imports `benchmarks.renters.renters_benchmark.core`. `DATASET` points to `benchmarks/renters/datasets/renters_v1`. The repository test loader includes these benchmark tests in `python -m unittest discover -s tests -q` alongside the outer-loop tests.

For checkout-based or editable use, defaults locate the bundled data. A non-editable installation must supply the checkout dataset explicitly to commands that accept `--dataset`; the package discovery includes the benchmark namespace, but dataset assets are not promised as wheel contents.

```bash
python -m continual_harness optimize --dataset /path/to/checkout/benchmarks/renters/datasets/renters_v1 --config harness.toml --output artifacts/run-001
```

Dataset creation and checks do not demonstrate model improvement. The 30-case test set remains small, and shared general handbook skills intentionally recur in different scenarios. Keep private oracles and test feedback out of the optimizer until the frozen comparison.
