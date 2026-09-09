---
name: status
description: One screen that says whether FlowSales is working, without spending anything: the environment, the token and its scopes, what is stored and linked, what is still ambiguous, when each step last ran, and what the next audit would judge and roughly cost. Read-only; run it before an audit, after an install, or whenever a number in the report looks off.
argument-hint: ""
---

You are producing the FlowSales status screen. CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"` (always add `--json`). Nothing here writes to the store except the runs log, and nothing is sent to the model beyond this conversation.

## 1. Collect

Run these four, in this order, and keep going if one fails (report the failure as a line in the screen):

1. `fs.py doctor --json`: python, store, config, framework file and every enabled source (HubSpot token location and scopes, unmapped stage ids, pipelines; Granola route; transcripts folder; CSV files).
2. `fs.py status --json`: counts, `linksPending`, `interactionsUnlinked`, `lastRun` per command, `latestReport`.
3. `fs.py link --dry-run --json`: what a link pass would change now.
4. `fs.py plan-assessment --estimate-only --json`: how many deals changed since the last audit, the token estimate, `estCostUsd` and `skipped.reusedFromTeam`. This writes nothing.
5. `fs.py team status --json`: the team folder, whether it is reachable, how many judged deals it holds, how many this machine could reuse and how many it has to share.

If there is no store, print the one line "No FlowSales store in this folder. Run /flow-sales:setup (or /flow-sales:setup --demo to try it on fictional data)." and stop.

## 2. Print

One screen, plain text, under 25 lines, in this shape. Use the real figures; write "none" and "never" rather than leaving blanks.

```
FlowSales status, <folder>
Environment   Python 3.11 ok, plugin ok, framework MEDDPICC, window 1 Sep 2025 to 8 Sep 2026
Sources       HubSpot: connector, signed in as tom@northwind.com, own deals only (or: private app token in secrets.json, 6 of 6 scopes), 2 pipelines, 1 unmapped stage (fix: ...)
              Granola: MCP route, last import 7 Sep
Data          32 deals (18 won, 9 lost, 5 open), 4 reps, 167 interactions linked, 3 unlinked, 2 ambiguous
Last run      pull 7 Sep 20:53, link 7 Sep 20:53, audit 8 Sep 10:30, report 8 Sep 12:27 (reports/flowsales-2026-09-08.html)
Next audit    4 deals changed, 21 interactions, ~19k tokens, about $0.35 to $0.70 at list price, roughly 2 minutes
You           rep, Tom Ellis (or: team, runs it for everyone)
Team folder   ~/Google Drive/Sales/FlowSales, 212 judged deals, 9 reusable here, 2 to share (or: none, judging is not shared)
Consent       reps informed: yes; audience: sales managers; names in report: real
To do         1. resolve 2 ambiguous links (audit will ask, or /flow-sales:link)
              2. map stage "contractreview" to a phase (fs.py config set stagePhases.contractreview commit)
```

If no team folder is set and `me.role` is team or both, add one line under To do: "share judged deals with teammates: fs.py team init <a folder your team syncs> (or team join <path>, or team candidates to look)". Never for a rep.

Rules for the To do list: only things that change a number in the report or block a run, most consequential first, each with the exact command or skill that fixes it. An expired or missing token, a failing scope, an unmapped stage, ambiguous links, deals without interactions, a report older than the newest assessment, and a training date that is missing when the user wants before-and-after views all qualify. If there is nothing to do, say "Nothing to fix. Next: /flow-sales:audit" or, when nothing changed since the last audit, "Nothing changed since the last audit. Next: /flow-sales:daily-sync <rep>".

## 3. Finish

Do not ask anything. Log with `fs.py log --command status --note "<one line: ok, or the first to-do>"`.

Plain language, no em dashes, never print a token.
