# Actor memory tools

Set these top-level keys in the harness TOML configuration to enable the
`renters_memory_v1` benchmark variant:

```toml
actor_memory = true
max_tool_calls = 12
```

The default remains `actor_memory = false`, which uses the existing full-context
actor. Memory mode needs an actor model/backend supporting native tool calls;
the final response must still satisfy the same six-key JSON contract. Judge and
optimizer requests remain ordinary JSON completions. The protocol follows
[OpenRouter client tools](https://openrouter.ai/docs/guides/features/tool-calling).
Each subsequent inference includes tool definitions, the assistant tool-call
message and corresponding tool results. Provider reasoning metadata on those
assistant messages is retained for replay. JSON-object mode is requested on the
final-only turn; earlier final answers are parsed strictly in the harness.

## What the actor sees

Initially the actor sees its strategy, response contract, current conversation,
session/verification, as_of, requested form, instruction and allowed actions.
The full handbook and all task records are removed from the initial prompt.
They become a fresh read-only memory for that case, with documents H01-H16 and
the case's original record IDs such as r1. No task metadata, split labels,
private oracles, evaluation feedback or other cases are added to memory.

| Tool | Arguments | Result |
| --- | --- | --- |
| `search_memory` | `query`, optional `limit` (1-5, default 5) | Source IDs, kinds, titles, original provenance and excerpts of at most 400 characters |
| `read_memory` | `document_id` | Complete handbook section or case record, preserving source ID and data |

Search is deterministic lexical token overlap with source-ID tie breaking;
underscores are treated as word separators. It does not boost sources using
authority labels, answer keys or rubric relevance. An empty query returns the
first five documents, and a query with no matches returns an empty result.
Full documents can be read directly when their IDs are known. Search excerpts
do not authorize citations; citations to memory sources require a successful
full-document read. Conversation/session/as_of citations remain available.

Memory keeps the existing difficult evidence intact: misleading marketing
pages, drafts, historical incidents, withdrawn facts and conflicting records.
For example, ops_001's r2 marketing page excludes off-premises belongings while
H04's actual base rule includes eligible belongings temporarily away from home.
The actor needs to compare source authority and applicability. No new false
facts or per-case answer summaries are injected. The same 100 cases, split
assignments, structured checks and semantic criteria are reused; scores from
the two context modes must be labeled separately. Empirical difficulty remains
unmeasured until a live evaluation.

## Limits, grading and artifacts

Every requested tool execution, including an invalid tool or arguments, uses
one slot in `max_tool_calls`. Invalid requests return structured errors so the
actor can recover. When a batch exceeds the remaining budget, excess calls
return `tool_budget_exhausted` without executing. Once the budget is exhausted,
one final inference turn disables tools. Each inference can retry according to
`max_attempts`; successful tool results are retained rather than reexecuted on
retry. With a budget of B there are at most B+1 inference turns, each with at
most `max_attempts` attempts. Failure to produce the final JSON follows the
existing terminal actor `model_failure` behavior.

The judge sees original evidence plus the tool trace, without the actor's
strategy, prompt version or optimization history. It checks both correctness
and whether the actor retrieved support for its claims. The executable check
also rejects citations to unread handbook/record documents. A read or search
success alone never establishes task success. Optimization feedback includes
traces only for graded optimization cases; validation and test feedback stay
out of the optimizer.

Each model attempt lives in `calls/` and includes the exact messages, tool
definitions, turn/attempt numbers and raw reply. Successful tool results are
also saved immediately in `tools/`, keyed by phase/prompt/task/repetition, so
they survive a later inference failure. Saved evaluations include
`tool_trace` and `retrieved_sources`. Usage totals count every inference,
including tool-selection turns and retries; tools themselves run locally.
Reports label the variant. Configuration, dataset checksums, variant identity
and tool definitions are checked before optimization or frozen testing.

Memory resets for every case, repetition and prompt arm. It offers no writes,
cross-case retrieval or transaction execution. Experiment artifacts contain
private evaluation evidence and are not exposed as a memory source.

## Offline demo

```bash
source .venv/bin/activate
python -m continual_harness demo --actor-memory --output artifacts/memory-demo-001
python -m continual_harness report artifacts/memory-demo-001
```

The demo scripts search/read calls and uses private golds deliberately. It
verifies orchestration, trace persistence, citation access and promotion/test
boundaries. Its scores do not establish real retrieval quality, semantic judge
accuracy, provider compatibility or model improvement. Offline tests mock the
native OpenRouter protocol; no paid live inference is part of these checks.
