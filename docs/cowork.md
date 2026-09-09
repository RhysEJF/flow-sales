# Cowork: the 15-minute compatibility check

FlowSales is built and tested in Claude Code. Cowork (the Claude desktop app's agent) installs the same plugin format: a git repository as a marketplace, skills, connectors, subagents and slash commands. Three things have only been verified in Claude Code and need one run in Cowork before FlowSales claims support. This is the checklist; note what you see next to each line.

Install: Customize, Plugins, add the marketplace `RhysEJF/flow-sales` (the repo is private, so the GitHub account must have access), install `flow-sales`. Then open Cowork in an empty folder.

| # | Try | What should happen | Risk it tests |
|---|---|---|---|
| 1 | Type `/flow-sales:` | The commands appear: setup, audit, daily-sync, retro, impact, status, link | Slash commands from plugin skills exist in Cowork |
| 2 | `/flow-sales:setup --demo` | "Store created at ...", 32 deals loaded, no questions asked | **Python.** Every command shells out to `python3 scripts/fs.py` under the plugin root. If this line fails, nothing else will work and the fix is a Cowork-side one (bundled Python, or a different runtime) |
| 3 | `/flow-sales:status` | The one-screen status, "Next: /flow-sales:audit" | The read-only path, `${CLAUDE_PLUGIN_ROOT}` resolution |
| 4 | `/flow-sales:audit`, answer "sample 10 deals" | The link line, the plan and the cost line, one question, then "Judged 1 of 10 ..." lines | **Subagents in parallel.** Audit launches the deal-assessor agent five at a time. Cowork supports subagents; the parallel launch is the thing to watch. If they run one at a time it still finishes, only slower |
| 5 | Open the report when offered | The report opens in the browser | File opening from the sandbox |
| 6 | `/flow-sales:daily-sync Tom Ellis` | The refresh question, the self-assessment questions, a briefing under 350 words | Gates (AskUserQuestion) in Cowork's own question UI |
| 7 | Customize, Connectors: HubSpot | The HubSpot connector from the plugin's `.mcp.json` is listed and can be signed in to | **The no-token route.** Sign in, then `/flow-sales:setup` on real data and watch step 6 of the setup skill save replies into `.flow-sales/cache/hubspot-mcp/` and `fs.py import hubspot-cache` read them. This is the first live observation of the connector's reply shape; if the import warns or fails, keep the saved files and send them over |
| 8 | Export, "Impact slide, names hidden (PDF)" | The print dialog with rep names replaced | Printing from Cowork's browser |

If 2 passes, everything else is a matter of wording. If 2 fails, say so and we decide between a bundled runtime and a Cowork-specific route before any Cowork promise is made.
