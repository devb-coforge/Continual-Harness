# Actor memory variant

Implement the approved required-retrieval option as `renters_memory_v1`, selected
with `actor_memory = true`. Existing configuration defaults to the original
full-context benchmark. The dataset, splits, reference answers and rubric stay
unchanged; the variant changes how public evidence reaches the actor.

Each case gets a fresh read-only memory built exclusively from its public
records and the fixed handbook sections H01-H16. The actor initially sees the
current conversation, session, form, allowed actions, strategy and response
contract. Records and handbook rules are available only through tools.
Search returns bounded excerpts with source IDs and original provenance;
read returns complete documents. Existing misleading advertisements, drafts,
old records and unrelated incidents remain in the corpus. Retrieval ranking
uses lexical overlap, never source authority or private answer relevance.

Checklist:

1. [x] Add deterministic task-scoped search/read tools and a variant renderer.
2. [x] Support native OpenRouter tool messages and a bounded actor loop, preserving
   existing plain completion clients and judge/optimizer behavior.
3. [x] Persist each inference attempt and tool result; count every inference in
   usage. Retry failed inference turns without replaying successful tool calls.
4. [x] Grade only citations to documents actually read plus initially visible
   sources. The blinded judge receives original evidence and the retrieval
   trace; optimizer feedback contains optimization cases and their traces only.
5. [x] Save/freeze the variant and tool budget in experiment configuration, include
   variant identity in reports, and reject configuration drift.
6. [x] Extend the synthetic demo and add offline tests for protocol, boundaries,
   errors, limits, drift, citation availability and end-to-end orchestration.
7. [x] Document configuration and evidence limits; validate the original dataset
   and run the repository suite plus both synthetic demo modes.

Default budget: 12 tool calls per case, followed by a final-answer turn with
tools disabled. Unknown documents, tools or bad arguments produce structured
tool errors the actor can correct within that budget. No memory writes,
cross-case retrieval, filesystem paths, account actions or external search.
Memory is reset for every case/repetition/prompt arm and is not learned from
evaluation feedback. Offline checks cannot establish empirical difficulty or
live model/provider compatibility.

Validation: all 54 repository tests passed; the original 100-task dataset audit
remained valid with the 50/20/30 split. Both CLI demos completed optimization,
promotion, freezing and held-out reporting. The memory demo saved 540 actor
inferences versus 180 for the full-context demo, including final tests. Both
scripted final candidates passed all 60 test repetitions. Artifacts were written
under `/tmp/actor-memory-check.ur6Ffc`; the memory report CLI also succeeded.
The suite still emits its pre-existing SQLite ResourceWarning. No live API
calls were made.
