# Shared authoring contract v1

Read handbook.md before authoring. All dates, USD amounts, names, emails (.example), addresses, and accounts are synthetic. No external facts may be required. We author original cases, not rewrites of public examples.

## Files and allocation

Each case has tasks/{id}.json (public task plus evaluation-only metadata) and oracles/{id}.json (private). IDs ops_001..ops_050 and ext_001..ext_050. Each author delivers 25 optimization, 10 validation, 15 test. Families operations 18 policy_questions /16 account_changes /16 claim_intake; extraction 18 application_filling /16 change_request_extraction /16 support_handoff. Use IDs 001..025 optimization, 026..035 validation, 036..050 test; interleave families inside each split. Aim 9/8/8 per family in optimization, 4/3/3 validation, 5/5/5 test. Related templates/variants must share scenario_group and split. Distinct scenario mechanisms may share general skills across splits. Do NOT create 100 renamings of six templates. Include routine success, warranted clarification, correct inaction, and partial completion; difficulty standard/challenging/adversarial.

## Public task format

{
  "id": "ops_001", "track": "support_ops", "family": "policy_questions",
  "split": "optimization", "scenario_group": "owned_belongings_off_premises", "difficulty": "challenging",
  "input": {
    "as_of": "2026-10-08",
    "instruction": "Specific request and scope of output; do not reveal desired answers or trap names.",
    "session": {"verified": true, "role": "named_insured", "policy_id": "P-100"},
    "records": [{"id":"r1", "kind":"policy", "data": {"policy_id":"P-100"}}],
    "messages": [{"id":"m1", "role":"customer", "text":"Natural customer text."}],
    "form": {"field_name": {"type":"string", "nullable":false, "description":"Meaning, not answer", "enum":["a","b"]}},
    "allowed_actions": ["action_type"]
  }
}

Track is support_ops or conversation_extraction. input fields all required. messages need >=2 for ops, >=6 for extraction; realistic dialogues, not repetitive filler. Message roles customer, bot, agent, third_party. Record IDs r1 etc, message IDs m1 etc unique. Session can include additional task context but never hidden answers. Form declares every output fields key, JSON types string/integer/number/boolean/array/object with nullable and description. Optional enum. Task records may be empty; establish all relevant current state for operations. Include starts_on/ends_on for event-date questions and record authority where needed. Form fields must use canonical simple snake_case names and carry explicit normalization/uncertainty instructions in descriptions where needed. Dates ISO. Optional unknown null vs explicit no false/[] must be distinguishable.

## Common response format

{
  "fields": {"field_name":"a"},
  "disposition": "answered",
  "actions": [{"type":"action_type", "target":"r1", "value":{}}],
  "missing_fields": [],
  "citations": ["m1","r1","H04"],
  "response": "Concise grounded user-facing explanation; proposals are not executed actions."
}

fields must contain exactly task.form keys, no extras. actions may be []; each has exactly type,target,value; allowed_actions [] means no actions. missing_fields string array, citations source-ID array using H01..H16, m#, r#, session, as_of. All references resolve to supplied sources. Cite evidence supporting material facts, but don't insist on one exact citation ordering or textual explanation. Semantic rubrics assess support. No hidden reasoning transcript required.

## Private oracle format

{
  "task_id":"ops_001",
  "reference_answer": { ... valid common response ... },
  "checks": [
    {"id":"C1", "path":"/fields/field_name", "operator":"eq", "expected":"a", "critical":true,
      "evidence":["m1","H04"], "rationale":"Why the field has this answer."},
    {"id":"C2", "path":"/actions", "operator":"set_eq", "expected":[], "critical":true,
      "evidence":["m1","H16"], "rationale":"No transaction was requested."},
    {"id":"C3", "path":"/disposition", "operator":"one_of", "expected":["answered"], "critical":true,
      "evidence":["m1","H16"], "rationale":"Informational task."},
    {"id":"C4", "path":"/missing_fields", "operator":"set_eq", "expected":[], "critical":true,
      "evidence":["m1"], "rationale":"Enough information is supplied."}
  ],
  "rubric":[
    {"id":"R1","criterion":"Specific binary semantic criterion about reply factual accuracy, not generic helpfulness.","evidence":["m1","H04"],"critical":true},
    {"id":"R2","criterion":"Second case-specific criterion including a meaningful negative requirement.","evidence":["m1","H16"],"critical":true}
  ],
  "failure_modes":["specific failure this task distinguishes","another failure"],
  "rationale":"Reasoned gold explanation including ambiguity resolution and source precedence."
}

Allowed checks eq (typed deep equality), one_of (accepted alternatives), set_eq (unordered array equality with no duplicates), contains (array element), not_contains (array element), text_eq (Unicode NFKC, case-fold, punctuation and whitespace tolerance for copied address/name text only; preserve tokens). Do not use text_eq for dates, amounts, emails, or identifiers. Do not compare free-form prose for exact equality. Every form field must have at least one direct check at /fields/FIELD, plus checks on /actions, /missing_fields, /disposition. Use set_eq for unordered lists; eq for objects only with clearly specified public structure. Use flexible one_of only where substantively equivalent. Each oracle needs >=2 specific rubrics, >=2 failure modes, and meaningful evidence/rationale. Every reference answer must pass every objective check and semantic rubric. No guessed gold values. Human-friendly reference_answer.response should be natural, not criterion IDs. Avoid unsupported procedural requirements.

## Quality requirements

Use substantive scenario diversity: corrections, dates, actor roles, cause ambiguity, policy timing, contradictory record authority, partial requests, unknown vs none, conditional/withdrawn intent, proof limits, pending evidence, and evidence-backed handoffs. Some tasks must succeed directly so blanket deferral/clarification fails. Cases should require integrating distributed facts, not spotting a keyword. All relevant rules are in the unchanged handbook; no task should require real-world insurance law. Reference keys and metadata are never rendered to the tested model. The same policy/output contract is supplied to every prompt variant. No model pilot, artificial performance claims, or paid API calls.
