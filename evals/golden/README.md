# Golden set for the FlowSales judge

`snippets.json` holds 40 short, fictional B2B interactions (calls, emails and rep notes from invented UK and EU deals) with hand-labelled expected scores. It is the fixed reference the judge is measured against before any rubric, prompt or model change ships.

## What is in a snippet

| Field | Meaning |
|---|---|
| `id`, `type`, `phase` | Stable id (`g01` to `g40`), `call` / `email` / `note`, and the phase the judge should treat as `phaseAtTime` |
| `kind` | `standard`, `rep-assertion` (rep states everything, buyer says nothing: expected level 1 across the board), `reversal` (the buyer contradicts themselves; the later statement wins), `pitch-monologue` (rep talks, no framework behaviour, `pitchBeforePain` true) |
| `speakerRoles` | Speaker labels as they appear in `body`, mapped to `rep` or `buyer` |
| `body` | The text the judge sees; quotes must be copied verbatim from here |
| `expected` | Per applicable element: `evidence` (0 to 3) and, above 1, the exact `quote` and `speaker` that justify it |
| `notApplicable` | Elements the judge should not score on this snippet, with the reason (DP and PP before evaluation; CO on a discovery call where nobody raised alternatives) |
| `expectedBehaviourTags` | Tags the rep earned in this snippet, from the vocabulary in `docs/CONTRACTS.md` section 8.1 |
| `reversal` | Present on reversal snippets: the element, the earlier quote that must lose, and the rule |

Counts: 25 standard, 6 rep-assertion, 4 reversal, 5 pitch-monologue. Every element is labelled at every level (0, 1, 2, 3) at least twice; DP, PP and CO level 0 come only from evaluation-or-later snippets, because on discovery calls they are not applicable rather than zero.

## Targets

| Metric | Target | How it is computed |
|---|---|---|
| Exact agreement | 0.80 | Share of (snippet, applicable element) pairs where the judge's `evidence` equals `expected.evidence` |
| Within one level | 0.95 | Share of pairs where the absolute difference is at most 1 |
| Behaviour tag agreement | 0.90 | Per snippet, Jaccard overlap of the judge's union of `behaviourTags` with `expectedBehaviourTags` (empty versus empty counts as 1.0), averaged over snippets |

Secondary checks reported alongside: applicability mismatches (an element scored that should be `notApplicable`, or the reverse), quote failures (a level above 1 whose quote is not verbatim), rep-assertion snippets scored above 1 anywhere, reversal snippets where the earlier quote was used, and pitch-monologue snippets with any behaviour tag.

## Running a comparison

1. Build a batch from the golden set: one interaction per snippet, `interactionId` = snippet `id`, `body` = `body`, `phaseAtTime` = `phase`, `participants` from `speakerRoles`, all under a single deal id such as `demo:golden`. Point `frameworkFile` at `frameworks/meddpicc.json`. Write it as `work/batches/golden.json` in a scratch store.
2. Run the judge on that batch (the `judge` agent with `skills/methodology/SKILL.md` loaded), producing `assessments/demo_golden.json` in the CONTRACTS section 8 shape.
3. Validate the output: `python3 <plugin root>/scripts/fs.py validate-assessment <assessment file>`. Unverified quotes are capped at 1 before comparison, exactly as they would be in production.
4. Compare, one snippet at a time: for each snippet, look up the judge's interaction by `id`, then for each element in `expected` compare `evidence`, and for each element in `notApplicable` confirm it is absent from `applicable`. Collect the judge's tags across all elements of that interaction and compare with `expectedBehaviourTags`. Compute the three metrics above and the secondary checks, and print a per-element confusion table (expected level by judged level) so systematic drift (for example, inflating rep assertions to 2) is visible.
5. Record the run in `runs.jsonl` next to this README with the rubric hash, model, date and the three metrics. A change to `frameworks/*.json`, the judge prompt or the model is accepted only if no target regresses.

The steps are implemented by `fs.py eval-golden`:

```bash
python3 scripts/fs.py --home /tmp/fs-golden/.flow-sales eval-golden build          # writes 4 batch files and prints them
# launch one deal-assessor agent per batch file (the audit skill's judge step, or the manual prompt in docs/HANDOFF.md)
python3 scripts/fs.py --home /tmp/fs-golden/.flow-sales eval-golden compare --model claude-sonnet-5
```

`compare` validates the assessments first, prints the three metrics against the targets, the secondary checks and a per-element confusion table, appends the run to `runs.jsonl` here and writes the per-snippet detail to `results/`.

## Editing the set

Keep snippets fictional, 60 to 200 words, with speaker labels that match `speakerRoles`. Any level above 1 needs a quote that is a verbatim substring of `body`. When adding a snippet, keep every element at every level covered at least twice, and re-run the checks: quote verbatim, word count, coverage, tags in vocabulary, no em dashes.
