---
name: daily-sync
description: A rep's daily sync: pull the latest calls and emails on their own deals (seconds, never the whole portal), reuse what the team has already judged, score anything new, ask the rep where each live deal stands before showing the evidence, then write a two-minute briefing with the next framework move per deal and one thing to practise today.
disable-model-invocation: true
argument-hint: "[rep name or email] [--no-refresh]"
---

You are running a FlowSales stand-up for one rep. Load the `flow-sales:coaching-voice` skill before writing anything rep-facing. CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"` (add `--json` to parse). Plugin root: `${CLAUDE_PLUGIN_ROOT}`.

## 1. Who

Run `fs.py status --json`; if there is no store, point to `/flow-sales:setup` and stop. Read `.flow-sales/data/reps.json`. If `$ARGUMENTS` names a rep (name or email, case-insensitive), use them; otherwise use `me.repId` from the status payload when it is set (the rep set themselves up); otherwise ask which rep with AskUserQuestion (up to four per question, more questions if needed).

## 2. Refresh (gate, skipped with --no-refresh)

Ask whether to pull the latest activity first, and say it takes seconds: this machine pulls only this rep's deals since the last pull, never the whole portal.

- HubSpot, connector route (`sources.hubspot.route` is `connector`): with the HubSpot connector tools, `search_crm_objects` on `deals` owned by this rep (`hubspot_owner_id` equals their owner id, from `.flow-sales/cache/hubspot-mcp/user-1.json` or `search_owners` by their email) and modified since the last successful pull or import in `lastRun`; then, for each of those deals, the engagements since that time (`calls`, `emails`, `meetings`, `notes` with the `associations.deal` filter, body properties as in the setup skill). Save every reply verbatim into `.flow-sales/cache/hubspot-mcp/` as `deals-<n>.json` and `<type>-deal-<dealId>-<n>.json`, then run `fs.py import hubspot-cache --json`. If the connector tools are not available, say how to sign in (`/mcp` in Claude Code; Connectors in the desktop app) and offer to continue without refreshing.
- HubSpot, private-app route: `fs.py pull hubspot --since <yesterday> --owner me` when `me.email` is set, else without `--owner`.
- Granola, connector route: export the last 7 days as described in the setup skill and run `fs.py import granola --export-dir .flow-sales/cache/granola`.

Then `fs.py link --json` and, if anything is pending for this rep's deals, resolve it the way the audit skill's link step does. If a team folder is set (`team.folder` in the status payload), run `fs.py team sync --pull-only --json` so deals a teammate already judged are not judged again. Then `fs.py plan-assessment --json`: it reports what it reused from the team folder; if it planned batches, judge them exactly as the audit skill does (parallel `flow-sales:deal-assessor` agents, one per batch, up to config `judge.parallel`), then `fs.py rollup --json`, then `fs.py team sync --push-only --json` when a team folder is set. Keep this quiet: one line of progress, for example `Pulled 14 deals, 6 new interactions. Reused 12 judged deals from the team folder, judged 2.`

## 3. Pack

Run `fs.py briefing-data --rep <rep id> --date <today>` and read the JSON (it is small: deals, states, gaps, next questions, last interactions, trend). If it reports no active deals, say so and offer the retro instead.

## 4. Self-assessment (gate, the conscious-competence step)

Before showing any evidence, ask the rep about their top active deals (up to four deals, one question each, multi-select): "On <deal> (<company>), which of these do you believe you have established?" with options: Economic Buyer identified and engaged; Champion tested (has power and sells for you when you are not there); Metrics quantified in the buyer's words; Decision process and paper process mapped with dates. Record the answers. Compare with the pack's element levels (E, CH, M, DP and PP): note each place where the rep's belief and the evidence differ.

## 5. Write the briefing

Follow the briefing template in the coaching-voice skill. Per deal: one line on standing, the next move as a question in the rep's voice (use the pack's `nextQuestion` for the lowest applicable element, adapted to the named people), the why (quote or silence), and the self-assessment gap where one exists. One thing to practise today: the rep's weakest element from the pack, with one example phrasing for one of today's deals. Watch list from the pack (silent deals, pending links, unscored interactions). Under 350 words.

## 6. Deliver (gate)

Show the briefing. Ask: keep as is, edit (take the rep's changes), or discard. Save the kept version to `.flow-sales/briefings/<repIdSafe>/<YYYY-MM-DD>.md` (repIdSafe replaces `:` with `_`). Offer to copy it to the clipboard (`pbcopy` on macOS) so the rep can paste it wherever they keep their day. Log with `fs.py log --command daily-sync --note "<rep> <date>"`.

Never send anything anywhere. Never show one rep another rep's briefing. No em dashes.
