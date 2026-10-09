# Project history

Shared handoff log for agents working on this project. Append a short dated entry after each meaningful change or experiment: what changed, outcome, why accepted/rejected, and evidence. Keep previous entries intact. Commit this file with the related changes; local run artifacts are gitignored.

## 2026-10-09 — Muse Spark benchmark and retries

- **Setup:** `meta/muse-spark-1.3-contributor` for actor, judge, and optimizer; Meta routing; two iterations and two repetitions.
- **Why:** The first run stopped with 21 actor transport failures and six invalid judge responses. Only 73/100 evaluations were valid (69 passed), so optimization/testing could not proceed.
- **Fresh run:** Optimization scored 94/100, then 93/100. All 480 task/arm/repetition evaluations completed; 43 failed call attempts recovered through retries; zero exhausted model failures. Recorded cost: $0.576261 (usage/cost available for 998/1,005 attempts).
- **Candidate 1 rejected:** Validation 34/40 versus incumbent 37/40; gain −7.5 percentage points, four regressions and one improvement. Failed both the positive-gain and zero-regression requirements.
- **Candidate 2 rejected:** Validation 35/40 versus incumbent 38/40; gain −7.5 percentage points, three regressions and no improvements. Failed both requirements.
- **Final decision:** Retained the original baseline. Held-out baseline and final each passed 60/60 (30 tasks × two repetitions). They use the same strategy, so this demonstrates no prompt improvement. Scores include same-model judge verdicts.
- **Local evidence:** Completed run `artifacts/muse-spark-20261009-002/` contains `RESULTS.md`, `results.json`, optimization/test reports, SQLite records, and exact calls. Failed first run: `artifacts/muse-spark-20261009-001/`.
