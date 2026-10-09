# Independent review: support/operations holdouts

Reviewed by the extraction author, independently of the operations holdout author, on 2026-10-08. Scope: all 25 public tasks and private oracles `ops_026` through `ops_050`. Read the full handbook, task instructions, sessions, records, conversations, form contracts, reference answers, deterministic checks, semantic rubrics, and gold rationales.

The review checked policy applicability and dates; verified versus claimed authority; current versus requested state; intake completeness versus coverage/settlement decisions; exact publicly declared action payloads and categorical tokens; null versus explicit false; field-level source support; targeted missing fields; and whether the reference reply satisfies its own semantic rubric. This was an offline content review, not a model run or a calibrated measurement of task difficulty.

## Findings and repairs

- `ops_029`: The structured gold was correct, but semantic criterion R1 expressly asks the reply to identify the $500 versus $1,000 deductible conflict. The reference reply described a conflict without naming the amounts. Updated only that reference reply to identify r1/$500 and r2/$1,000. No input, scoring rule, action, or expected value changed. Notified the author and root before the edit.
- No other substantive gold contradiction, unsupported prerequisite, undisclosed action payload, or private-account authority error was found in these 25 cases.
- Cross-track related cases were communicated to the root. The root placed the scheduled-jewelry pair (`ops_026`, current `ext_034`), equal-authority deductible pair (`ops_029`, current `ext_028`), and historical canceled-policy pair (`ops_036`, current `ext_041`) within common splits. Final corpus-wide split review is separate from this 25-case review.

## Checked cases

| Case | Content checked and outcome |
|---|---|
| ops_026 | Issued necklace schedule applies to its item only; ring retains base jewelry sublimit. Event lies in policy/endorsement intervals. No payout values or intake invented. Pass. |
| ops_027 | Confirmed US mailing update is independent of a Canadian insured move requiring review. Two public action payloads match these separate outcomes, with no cancellation. Pass. |
| ops_028 | Separate theft dates, serials, and explicit customer confirmation establish a new incident rather than a duplicate. Intake prerequisites and empty review list are supported. Pass. |
| ops_029 | Equally authoritative same-term records do not resolve a deductible by customer preference. Both deductible and illustration remain null; deductible is materially needed for the requested calculation. Reference prose repaired as described above. |
| ops_030 | Exact quote, future date, and additional premium are explicitly accepted. Current issued deductible remains distinct, and scheduled action is only proposed. No redundant consent requirement. Pass. |
| ops_031 | Known discovery date does not fill explicitly unknown event date. H12 permits complete intake with the public unknown_event_date flag and no date in missing_fields. Pass. |
| ops_032 | Supplied active backup endorsement and maintenance findings establish included sewer backup, with $5,000 limit rather than payment. Neighbor assertion carries no issued authority. Pass. |
| ops_033 | Verified customer approves a specific proof recipient and email while declining quote/change. Issued $100,000 cannot be altered to landlord-requested $300,000; separate recipient opt-in is not invented. Pass. |
| ops_034 | Guest injury allegation warrants liability review but does not block otherwise complete intake or establish fault. Public action incorporates review without an extra escalation transaction. Pass. |
| ops_035 | Documented additional hotel expense does not establish unknown uninhabitability. Null is preserved, eligibility remains unresolved, and only the habitability prerequisite is missing. Pass. |
| ops_036 | Historical theft falls before exclusive policy end despite current canceled status. Requested inaction on reinstatement is preserved; scope is not settlement approval. Pass. |
| ops_037 | Ambiguous numeric date cannot be resolved by US address. General cancellation intent is true, confirmed date remains null, and scheduling is withheld. Pass. |
| ops_038 | Active smoke/fire calls for immediate departure and local emergency services before routine intake discussion. Supplied complete intake remains permissible; photos/serials are not prerequisites. Both ready and escalate dispositions are accepted. Pass. |
| ops_039 | Customer expressly supplies no theft evidence and possible misplacement; requested relabeling is not a factual correction. Base disappearance exclusion is explained without a formal claim denial. Pass. |
| ops_040 | Explicitly multiunit destination lacks an assigned unit. Future date/building are retained without borrowing current Unit 4 or scheduling an incomplete move. Pass. |
| ops_041 | Verified requester's intake authority does not adjudicate disputed ownership. Both assertions remain in incident record; H13 supports complete intake with ownership_conflict rather than denial for absent receipt. Pass. |
| ops_042 | Backup endorsement is temporally active on the publicly specified report date but does not cover documented gradual leakage. Applicability is kept separate from active status. Pass. |
| ops_043 | Effective cancellation and requested gap-free restoration require reinstatement referral; explicit consent cannot authorize erasing the record or backdating through the bot. Requested date is preserved without missing facts. Pass. |
| ops_044 | Shared cause/property plus conflicting date and express customer uncertainty establish only a possible duplicate. Neither new intake nor old-record update is proposed; incident_identity is publicly named. Pass. |
| ops_045 | Customer upload contains usable earthquake facts plus instruction-like text. Actual base exclusion and absence of issued override control; no submission or payment is implied. Pass. |
| ops_046 | Confirmed disabling of identified autopay is a billing-only proposal. Current insurance stays active; full card data, a refund, and balance changes are not required or invented. Pass. |
| ops_047 | Latest withdrawal overrides complete earlier intake consent. Event itself is not retracted, and explicitly empty claim ledger supports zero existing claims without deletion. Pass. |
| ops_048 | Supplied eligible ordinary-contents value is capped before the deductible: min(22000,15000)-500=14500. No jewelry limit, undocumented hotel expense, or settlement approval is added. Pass. |
| ops_049 | Prior $18 quote consent does not carry onto explicitly superseding $31 quote. Current acceptance is missing; publicly specified request_quote_acceptance action is authorized and no issued change is implied. Pass. |
| ops_050 | Session explicitly verifies and authorizes the representative for this policy. Supplied report establishes named-insured property ownership, complete intake, and exact contact; caller is not added as an insured. Pass. |

## Verification

After the reference-only repair, all 25 reviewed pairs passed `renters_benchmark.core.validate_task`. This includes schema/type/source-reference integrity and each reference answer satisfying every deterministic check. Semantic reference consistency was assessed by the content review above, not by fabricated automated judge verdicts. No external model, paid API, dev server, or live insurance transaction was used.
