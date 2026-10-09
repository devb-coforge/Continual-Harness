# Independent review of operations optimization cases

Reviewer: ops_holdouts agent, independently of the ops_optimization author. Review date: 2026-10-08. Scope: all 25 public task/private oracle pairs `ops_001` through `ops_025`, against handbook H01–H16 and the shared authoring contract. The reviewer read the supplied records, complete conversations, public forms/action instructions, reference answers, objective checks, semantic criteria, and gold explanations. This is an offline content and contract review, not a measured model evaluation.

## Repaired findings

The author approved these narrow public-task repairs; the answers and handbook did not change. Each affected pair passed `validate_task` after repair.

1. **ops_010 — unpublished normalization token.** The oracle required `sudden_internal_supply_escape`, but the public field only said to normalize the cause. Added an explicit cause vocabulary and meanings, including alternative water mechanisms and unknown. A model no longer has to guess a private spelling.
2. **ops_019 — unpublished ownership category.** The oracle required `unnamed_roommate` without publishing the available categories. Added the ownership category enum and definitions. This preserves the ownership reasoning while making serialization fair.
3. **ops_004 — undeclared missing-prerequisite label.** The oracle used `property_ownership`, but the form was named `owned_by_named_insured`. Added the canonical missing-fields label and defined the ownership question, including possible joint ownership. The repair specifies serialization, not whether ownership is resolved in this case.
4. **ops_017 — authority versus verification label.** Published `authorized_requester` as the missing-prerequisite code and explained that policy-specific authority differs from identity verification. The verified landlord still lacks account authority; this avoids rewarding or penalizing arbitrary missing-field spellings.

## Case-by-case checks

| Case | Main reasoning checked | Result |
|---|---|---|
| ops_001 | Named-insured camera, temporary travel, eligible event interval, explanation-only scope | Supported by H04/H08; no unsolicited intake or payment. |
| ops_002 | Independently confirmed mailing-only change versus explicitly conditional cancellation | Mailing proposal supported; insured premises preserved; conditional cancellation is not an active missing-data workflow. |
| ops_003 | Complete smoke intake despite pending receipt and unknown value | H12 prerequisites supplied; uncertainty retained; no invented claim ID. |
| ops_004 | Shared projector use/payment does not prove ownership | Null ownership and targeted clarification supported; missing-prerequisite label repaired. |
| ops_005 | Corrected November 15 future move and separate mailing intent | Latest date and full destination approved; today’s address preserved; no simultaneous coverage inferred. |
| ops_006 | Reported loss below deductible does not prevent intake | Intake supported under H04/H12; declined payout calculation remains null. |
| ops_007 | Base per-occurrence jewelry sublimit within total property limit | $1,500 applies to the combined unscheduled occurrence; no per-item multiplication or unsolicited payout. |
| ops_008 | Confirmed immediate policy cancellation preserving existing claim | H10 conditions satisfied; supplied claim reference retained; unknown refund stays null. |
| ops_009 | Customer explicitly confirms same bicycle theft and supplies receipt | Existing claim evidence update supported; historical purchase price is not a settlement. |
| ops_010 | Specific plumber finding defeats blanket “all water excluded” assertion | Included sudden internal pipe cause supported; canonical public vocabulary repaired. |
| ops_011 | Quote request complete although issuance consent absent | Ready quote workflow supported; current deductible preserved and premium not invented. |
| ops_012 | Draft requested with location/contact missing, receipt optional | Exactly two material submission prerequisites; no inferred travel location or account contact. |
| ops_013 | Issued ACV versus archived replacement-cost advertisement | H01 authority resolves conflict; no need to invent depreciation or open an unwanted quote. |
| ops_014 | Interested-party notice recipient is not a named insured | Exact recipient authorization supplied; no unwanted one-time proof delivery or recipient opt-in demand. |
| ops_015 | Claimed earlier login does not verify present session | Customer facts usable for draft only; private r2 email/name/status not disclosed; no password collected. |
| ops_016 | Covered uninhabitable displacement, additional hotel expense, ordinary rent | Receipt classifications follow H07; review eligibility not approval. |
| ops_017 | Verified landlord identity does not authorize tenant account disclosure/change | Authority gate supported; missing code clarified; no private r1 facts disclosed. |
| ops_018 | Bot submission/callback promise contradicted by authoritative draft | Recorded draft and no claim ID retained; conditional permission becomes actionable because draft status is established. |
| ops_019 | Sole unnamed-roommate ownership despite shared rent | Explicit ownership/status resolves exclusion without a guess; public category vocabulary repaired. |
| ops_020 | Latest move withdrawal versus earlier bot promise and unsent draft | Correct inaction; no invented reverse/delete transaction. |
| ops_021 | Wear-and-tear scope excluded but complete authorized intake permissible | Cause preserved, scope separated from claim adjudication, intake supported. |
| ops_022 | Theft before inception despite active status today | Dates resolve interval without backdating or changing the reported event. |
| ops_023 | Future cancellation with recorded approved-but-unpaid refund | Scheduling preserves today’s active status; exact approved amount/status supported; no disbursement promise. |
| ops_024 | Unverified staging allegation accompanies complete intake | Suspicion retained as allegation; intake plus staff review; no invented guilt, hazard, or deadline. |
| ops_025 | Landlord’s building components versus insured-owned contents | Sofa and cabinets classified separately; no invented liability allegation or payment route. |

## Cross-case and scoring checks

- Reviewed all explicit action shapes against the exact action gold. Draft-reference operations preserve supplied draft values; fields-as-payload operations publish that shape. No free-form narrative is graded by exact equality. The two unpublished canonical field spellings identified above were repaired.
- Every reference answer has the declared form fields, action/missing-field/disposition checks, resolvable evidence, and case-specific semantic constraints. The repair did not loosen facts, authority, consent, or policy rules.
- Sources distinguish reported incidents from issued policy and authoritative workflow status. None of these cases requires external insurance law, a real insurer’s contract, fabricated premiums, or a model-generated private rule.
- Compared the 25 optimization mechanisms against the authored 25 operations holdouts. Shared general skills (date applicability, consent, ownership, source authority, and intake readiness) intentionally transfer. The holdouts add scheduled-item endorsement scope, equal-authority conflict, a confirmed foreign destination, unknown-date intake expressly permitted by H12, actual injury review, an immediate active hazard, contradictory ownership assertions, uncertain duplicate identity, policy-specific representative authority, and revised-quote acceptance. These are not renamed copies of the optimization records or dialogue.
- Date applicability appears both before inception (`ops_022`) and before an already-effective cancellation (`ops_036`); withdrawal appears in different operational workflows (`ops_020`, `ops_047`). These are disclosed shared skills, not independent evidence that the learned rule is wholly unseen. Evaluation should describe held-out scenarios, not claim unseen-policy or unseen-skill generalization.

After the four public-contract repairs, no unresolved task/gold contradiction was identified in this reviewed allocation. The review establishes internal consistency and explicit grading contracts; it does not establish task difficulty, prompt improvement, judge reliability, or live provider performance.
