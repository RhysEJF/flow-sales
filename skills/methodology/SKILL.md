---
name: methodology
description: "MEDDPICC and MEDDIC scoring rules for FlowSales judges and coaches: the 0-3 evidence ladder, quote requirement, per-phase applicability, behaviour tags and how to read the framework JSON. Load when judging an interaction, explaining a score, or coaching a rep on an element."
user-invocable: false
---

# Methodology: how FlowSales scores MEDDPICC and MEDDIC

The framework file the batch names in `frameworkFile` (`frameworks/meddpicc.json` or `frameworks/meddic.json`) is the rubric. Every element carries `anchors` (operational criteria for levels 0 to 3), `evidenceSignals`, `exampleQuotes`, `nextQuestionAt1`, `behaviourTags`, `stageExpectations` and `applicableFrom`; top-level `scoring` holds the quote rule, decay, commit gate and qualify-out thresholds. Never score from memory of MEDDPICC; score from the anchors.

## Judging one interaction, end to end

1. Read the batch manifest (`work/batches/<n>.json`). Note `dealId`, `framework`, `frameworkFile`, `rubricHash`, `priorState` and `outputFile`. Load the framework file it names.
2. For each interaction, decide the applicable elements from `phaseAtTime` and each element's `applicableFrom`. Phase order is discovery, evaluation, proposal, commit. An element is applicable when the interaction's phase is at or after its `applicableFrom`. DP and PP are therefore not applicable on discovery interactions. CO on a discovery interaction is applicable only when either side raised alternatives, including the status quo. Every non-applicable element goes in `notApplicableReason` with a short reason.
3. Score each applicable element with the ladder: 0 nothing in the text addresses it; 1 the rep asserted or inferred it, or the buyer was too vague to act on; 2 a buyer-side speaker said it specifically, single source; 3 confirmed by a second buyer-side person, a buyer artefact or a demonstrated buyer action, and connected to the decision. Match the text against the element's `anchors`, not a general impression of the call.
4. Above level 1, attach one verbatim `quote` copied exactly from `body`, with `speaker` set to `buyer` or `rep`. Never paraphrase; the validator fuzzy-matches at 0.85 and caps unverified quotes at 1. At levels 0 and 1, `quote` and `speaker` are null.
5. Set `behaviour` to 1 and add `behaviourTags` only when the rep visibly applied the framework for that element in this interaction (asked one of its questions, tested the champion, asked for Economic Buyer access, mapped criteria or process). A buyer volunteering perfect evidence while the rep says nothing is high evidence and zero behaviour. Tags come only from the element's `behaviourTags` plus the three `generalBehaviourTags`.
6. Write one sentence for `whyNotHigher` (what the next anchor requires that the text lacks) and one `nextQuestion` (`nextQuestionAt1` when the level is 1, otherwise the single question that reaches the next anchor). Set `confidence` to high, medium or low. Fill `hygiene` and a one-sentence `summary` with no scores in the prose.
7. Output JSON exactly as CONTRACTS section 8. Include `batchFile` and `batchId` copied from the manifest so the validator can find the interactions. Write it to `outputFile`.
8. Run `python3 <plugin root>/scripts/fs.py validate-assessment <outputFile>`. It rewrites the file in place with `verified` flags and prints `{ "ok": ..., "errors": [], "warnings": [], "capped": n }`. Fix every error (missing elements, out-of-range values, tags outside the vocabulary) and re-run until `ok` is true. A non-zero `capped` count means a quote did not verify: copy the exact words from the body and re-run.

## The six honesty rules

1. Silence is 0. If nobody addressed the element, the score is 0, even for a deal you believe is healthy.
2. No inference from titles. A CFO on the invite list is not the Economic Buyer, and a VP who is enthusiastic is not a Champion, until the text shows the authority or the action.
3. The buyer's words outrank the rep's. A rep assertion, ROI model or note is worth at most 1. Level 2 needs a buyer-side speaker; level 3 needs a second buyer-side source or a buyer action.
4. Later reversals win. When a buyer contradicts earlier evidence inside the interaction, score the latest statement and say so in `whyNotHigher`.
5. No penalty for elements outside the phase. Absent Paper Process on a discovery call is not applicable, not a zero. Gaps are flagged against `stageExpectations` at the deal level, never as per-interaction punishment.
6. Never score what is not in the text. Prior state, CRM fields and your own knowledge of the company do not count. If a quote cannot be copied verbatim, the level is 1.

## From scores to coaching

A coach reads the assessment, not the transcript, and turns one element into one recommendation:

- Cite the deal and the quote. "On the Vantage deal, the buyer said: 'Anything over eighty thousand goes to Marta.'"
- Say what it means in plain words. "That names the Economic Buyer, but nobody has met her, so the deal is exposed if she has other priorities."
- Show what good looks like: the element's level 3 `exampleQuote` is the picture, `nextQuestionAt1` (or the assessment's `nextQuestion`) is the move. "Next call, ask: how does a decision of this size get made here, and who signs the actual contract? Then ask your contact for twenty minutes with Marta."
- Pick one focus: one element, one question, one next interaction. Praise the behaviour tags the rep earned before naming the gap.

Scores are proposals the rep confirms, edits or rejects with a reason; they are coaching telemetry, never a performance input.

## The eight elements

| Code | Element | One-line definition | Behaviour tags |
|---|---|---|---|
| M | Metrics | The buyer's own number with baseline, target and date | asked-metrics, quantified-impact |
| E | Economic Buyer | The one person who can release the budget and overrule the rest | identified-eb, asked-eb-access, engaged-eb |
| DC | Decision Criteria | What vendors are judged against, in the buyer's words, weighted and shaped | mapped-decision-criteria, shaped-decision-criteria |
| DP | Decision Process | Steps, owners and dates from today to a decision (from evaluation) | mapped-decision-process, agreed-mutual-plan |
| PP | Paper Process | Legal, security, procurement and signature between yes and contract (from evaluation) | asked-paper-process |
| I | Pain | The problem, owned and costed, with a consequence of doing nothing | identified-pain, implicated-pain |
| CH | Champion | Influence, sells for you when you are absent, personal stake; tested by action | tested-champion, developed-champion |
| CO | Competition | Named vendors, build, other priorities and the status quo, each assessed | named-competition, tested-status-quo, positioned-differentiation |

General tags for any element: secured-next-step, multi-threaded, summarised-and-confirmed. MEDDIC uses the first seven rows without PP and CO, with I read as Identify Pain.

## Behaviour tags: when each one applies

A tag records what the rep did, not what the buyer said. Attach every tag whose test is met in the interaction; two tags on one element are normal when the rep did both things. Where two tags in one element look alike, the second is the step beyond the first.

| Tag | The rep... |
|---|---|
| asked-metrics | asked what number would change, what it is today, or who reports it |
| quantified-impact | asked what the problem or the improvement is worth in money, time or volume (beyond naming the metric) |
| identified-eb | asked who approves or signs spend of this size, or who holds the budget, whatever the answer |
| asked-eb-access | asked to meet, be introduced to, or present to that person |
| engaged-eb | spoke with the Economic Buyer directly in this interaction, or asked them a question |
| mapped-decision-criteria | asked what the buyer will judge vendors on, how criteria are weighted, or what the scorecard looks like |
| shaped-decision-criteria | proposed a criterion or a weighting, and the buyer took it into their list |
| mapped-decision-process | asked about the steps, the people or the dates between now and a decision |
| agreed-mutual-plan | proposed or confirmed a dated sequence of steps that both sides accepted |
| asked-paper-process | asked about legal, security, procurement, contract or signature steps, owners or durations |
| identified-pain | asked what the problem is, how it shows up, or who feels it |
| implicated-pain | asked what happens if nothing changes, what it costs, or who is accountable for it |
| tested-champion | asked the contact to do something that shows influence: an introduction, an internal meeting, a document shared, a scenario without the rep in the room |
| developed-champion | armed the contact to sell internally: gave them the business case, coached the pitch, offered material for the steering group |
| named-competition | asked which alternatives are being considered, including build or the incumbent |
| tested-status-quo | asked what happens if the buyer does nothing, or whether doing nothing is an option |
| positioned-differentiation | contrasted the offer with a named alternative on a criterion the buyer cares about |
| secured-next-step | a dated next step both sides agreed before the interaction ended |
| multi-threaded | a second buyer-side person took part in the interaction, or the rep asked for another named person to be brought in |
| summarised-and-confirmed | restated what the buyer said and the buyer confirmed or corrected it |

Attach an element's tags to that element. Attach a general tag to the element it served (multi-threaded usually to E or CH, secured-next-step to DP, summarised-and-confirmed to whatever was summarised).
