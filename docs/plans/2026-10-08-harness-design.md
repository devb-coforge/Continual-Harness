# Continual prompt harness

Recovered from the opening discussion of the previous chat; implemented at the user's request.

The actor solves fixed renters cases. The evaluator combines the existing executable checks with a blinded, criterion-level judge. The optimizer sees only optimization cases, their failures and representative successes, and proposes one revised strategy with a rationale. Company rules, output contract, model settings and dataset remain fixed. Paired validation decides promotion; the optimizer never receives validation or test feedback.

Use a Python CLI and typed dataclass boundaries, a standard-library async OpenRouter adapter, SQLite metadata and JSON call artifacts. This avoids adding a framework to the existing standard-library benchmark. Live requests use JSON-object output with local validation and explicit provider routing. API failures, malformed actor responses, and invalid judgments remain separate from observed task failures. There are no automatic paid retries.

For each iteration, evaluate the incumbent on optimization tasks; give the optimizer a bounded deterministic sample of failures and successes. Evaluate incumbent and candidate on identical validation task/repetition pairs, alternating arm order. Promote only with full actor/judge coverage, positive success gain exceeding the configured margin, and regressions at or below the configured cap. This is a transparent selection rule, not a statistical significance claim. Record all comparisons, including rejected candidates. Freeze the selected strategy at the end. An explicit, one-shot test command compares the original baseline and frozen final strategy; reserving test access before calls prevents retry-based test selection.

The offline demo deliberately uses reference answers and scripted judgments to test orchestration. Its artifacts are labeled synthetic and cannot establish model performance. Live artifacts preserve exact messages, raw provider replies, request settings, generation IDs, and separate actor/judge/optimizer usage coverage. Stored artifacts include private grading material and must be kept private from actors.

Deliverables:

1. [x] Configuration, prompt templates, and typed provider boundary.
2. [x] Immutable prompt versions, SQLite records, and raw call artifacts.
3. [x] Actor execution, blinded judging, failure accounting, and summaries.
4. [x] Optimization feedback, paired comparisons, and promotion gate.
5. [x] Frozen final prompt and one-shot held-out test command.
6. [x] CLI, synthetic offline demo, documentation, and focused tests.

Verification: full existing dataset audit/tests plus offline orchestration, leakage boundaries, promotion/regression/incomplete gates, usage coverage, provider errors and final-test reservation. Live inference and judge calibration are separate unperformed checks.

Validation record: 42 unittest tests pass, the frozen 100-case dataset audit passes, and the CLI synthetic demo completes optimization, validation, promotion, freezing and held-out reporting. Offline demo artifacts are stored under `artifacts/demo-001`; they are private, ignored run artifacts. No live OpenRouter calls were performed. The mocked provider's thread-shutdown test requires execution outside this sandbox.
