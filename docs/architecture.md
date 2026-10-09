# Continual Harness

```mermaid
flowchart LR
    P[Incumbent strategy] --> A[Actor: optimization tasks]
    A --> E[Executable checks + blinded judge]
    E --> O[Optimizer: failures + successes]
    O --> C[Candidate strategy]
    P --> V[Paired validation]
    C --> V
    V --> G[Coverage, gain and regression gate]
    G --> P
    G --> F[Freeze selected strategy]
    F --> T[One-shot baseline / final test]
    A --> S[(SQLite + call artifacts)]
    E --> S
    O --> S
    V --> S
    T --> S
```

`continual_harness/config.py` owns immutable role/inference settings. `provider.py` implements the async provider boundary: nonstreaming JSON-object completions and bounded network timeout. OpenRouter handles backend routing when no `provider` preferences are sent. It uses `asyncio.to_thread` around standard-library HTTP; concurrency is limited by a semaphore. Cancelling the Python coroutine does not guarantee cancellation of an already running HTTP request. The engine retries provider failures, invalid JSON, and invalid judge/optimizer contracts up to `max_attempts`, with exponential backoff and jitter outside the semaphore. Every attempt and its usage are saved. Valid negative judgments and actor task-quality failures are not retried.

`prompts.py` controls information boundaries. The actor sees only the existing public renderer output. The judge sees the fixed rules, public input, answer and rubric, without strategy/version or optimization history. The optimizer receives a deterministic family-diverse sample of valid optimization failures and successes, with reference answers and evaluation feedback. It never receives validation or test cases. API failures and invalid judgments are not optimization lessons. Strategy changes cannot edit benchmark files; every evaluation checks the frozen manifest.

With `actor_memory = true`, `memory.py` replaces the actor's initial full context
with current chat/session/form plus two tools. Handbook sections and case
records are reachable through deterministic, read-only search/read memory.
The engine replays native tool messages in a bounded loop, persists tool results
and inference usage, and restricts memory citations to documents read. The judge
receives the trace alongside original sources; optimization examples include
traces only for the optimization split. Configuration and tool-definition drift
are checked alongside the dataset. See [actor memory](actor-memory.md).

`engine.py` orchestrates execution, evaluation, proposal, paired validation, selection and freezing. `metrics.py` keeps intended cohorts, actor completions, valid judgments and full-case successes distinct. Reported success rates use all intended cases as denominator, including infrastructure failures; they should be interpreted alongside coverage. Exhausted actor/judge calls have status `model_failure`, an explicit failure stage/reason, and `complete_success: false`. They are resolved cases for coverage and count in paired improvements/regressions. Quality observations count only graded cases. Exhausted optimizer calls retain the incumbent and record a proposal failure, allowing freezing/testing to proceed. If no graded optimization failures are available to learn from, the incumbent freezes without a proposal. Missing evidence never becomes a pass.

The promotion rule requires full coverage in both arms, a strict gain above `min_gain` (fraction, not percent), and no more than `max_regressions` task/repetition regressions. A gain with zero allowed regressions is the default. Repetitions and paired outcomes are retained; this rule does not establish statistical significance. Repeated validation selection can still overfit the selection set. Only the final held-out comparison measures transfer.

`store.py` records content-addressed prompt versions and lineage, evaluations, proposals, comparisons, metadata and exact call artifacts. Artifacts retain raw replies, timestamps, requests, model/provider settings and generation usage. Authorization headers are never stored. The database and JSON files contain private benchmark evidence; the directory is not an actor-facing data source. Usage reports input/output tokens and recorded USD cost separately per role, with coverage counts. Absent provider usage stays absent; no fabricated or estimated totals. The synthetic demo records no usage/cost.

`test` checks the unchanged dataset and frozen experiment, then atomically reserves held-out access before any model call. It reports baseline versus frozen final and never promotes a strategy. Interrupted tests remain reserved: inspect their saved partial artifacts rather than retrying for a better test outcome. New experiments do not magically restore scientific independence once a human has inspected the held-out set. There is currently no resume command or cross-experiment access-control service.

## Evidence limits

The demo deliberately obtains answers from private reference files and returns scripted judgments. It validates orchestration only. The harness proposes decisions/documents; its optional memory tools retrieve evidence and do not execute insurance transactions. Live model quality, provider eligibility and substantive judge correctness need live runs and manual calibration. Actor/judge/optimizer model selection is explicit in configuration; no paid calls run during setup or offline tests.

The OpenRouter request follows the official [chat completion API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request) and [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection). JSON output is still validated locally. No model or price recommendations are baked in.
