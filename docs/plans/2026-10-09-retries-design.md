# Bounded retries and terminal model failures

The live Muse Spark run stopped on missing evaluation coverage after transport failures and invalid judge JSON. The requested behavior is to retry those failures and score an exhausted call as a model failure so optimization and held-out testing can finish.

The engine allows four attempts by default. It retries provider errors, invalid JSON, and invalid judge/optimizer contracts, with exponential backoff and jitter outside the concurrency semaphore. Valid task-quality failures are final, avoiding selection of a better answer through retries. Every attempted request and response remains in the call artifacts, and usage includes all attempts with available provider usage.

An exhausted actor or judge call yields a terminal model failure and a false success verdict. It counts in the intended denominator and paired gains/regressions. Reports distinguish resolved coverage from graded quality evidence and expose failure stage/reason. Only valid graded optimization examples reach the optimizer. An exhausted optimizer call keeps the incumbent and records a proposal failure; freezing and held-out testing remain available.

A new experiment preserves the failed first run. It uses the same model in every role, two iterations, two repetitions, pinned Meta routing, and a 180-second request timeout. Offline tests cover transient recovery, exhausted failures, invalid contracts, paired failure scoring, usage persistence, and optimizer exhaustion.
