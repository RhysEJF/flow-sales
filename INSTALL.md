# Installing FlowSales

FlowSales is a Claude Code plugin. It needs Claude Code 2.1 or newer and Python 3.10 or newer on the path as `python3`. No Python packages are installed; everything is standard library. The whole install is done by whoever runs your CRM or sales operations, in about twenty minutes. Reps install nothing.

## Before anything: check the machine

Paste this block into a terminal. Three lines come back, each saying ok or what to do.

```bash
claude --version >/dev/null 2>&1 && echo "Claude Code: ok" || echo "Claude Code: not found. Install it first: https://docs.claude.com/en/docs/claude-code/quickstart"
python3 -c 'import sys; v=sys.version_info; print("Python: ok" if v>=(3,10) else "Python: %d.%d found, need 3.10 or newer: https://www.python.org/downloads/" % v[:2])' 2>/dev/null || echo "Python: not found. Install 3.10 or newer: https://www.python.org/downloads/"
git ls-remote -q https://github.com/RhysEJF/flow-sales.git HEAD >/dev/null 2>&1 && echo "GitHub access: ok" || echo "GitHub access: no. The repo is private: ask Rhys to add your GitHub account, then sign in in this terminal (gh auth login) and paste again"
```

The third line is the one that usually needs a person: the repository is private, so your GitHub account has to be added to it before the marketplace command below can fetch it. Once all three say ok, nothing else is needed.

## Option 1: marketplace (the normal route)

Inside Claude Code:

```
/plugin marketplace add RhysEJF/flow-sales
/plugin install flow-sales@flow-sales
```

Each line answers in a second or two. Type `/flow-sales:` afterwards and the commands appear in the list; that is the sign it worked. If the first line fails with an access error, the GitHub check above is the fix.

## Option 2: local checkout (for working on the plugin)

```bash
git clone https://github.com/RhysEJF/flow-sales.git ~/flow-sales
claude --plugin-dir ~/flow-sales
```

The `--plugin-dir` flag loads the plugin for that session only. Repeat it each time, or install from the marketplace.

## Option 3: tell Claude Code to install it

Open Claude Code and say: "Install FlowSales from https://github.com/RhysEJF/flow-sales". Claude reads this file and follows Option 1 or 2.

## After installing

1. Make an empty folder for FlowSales to keep its data in and start Claude Code there: `mkdir -p ~/flowsales-demo && cd ~/flowsales-demo && claude`. FlowSales stores everything under `.flow-sales/` in that directory.
2. Run `/flow-sales:setup --demo` (a few seconds, asks nothing) and then `/flow-sales:audit` (prints the volume and cost on one line and starts, then about six to eight minutes with a progress line per deal, ending with `Report is ready at <path>`). Run the session on Opus; the scoring runs in Sonnet sub-agents on its own.
3. For your own data, make a second folder and run `/flow-sales:setup`. It asks who will see the report and whether the reps have been told before it connects anything. For HubSpot, follow [docs/hubspot.md](docs/hubspot.md) to create a private app with read scopes. For Granola, follow [docs/granola.md](docs/granola.md). For Gong, Fireflies or Fathom, export the transcripts to a folder. For Salesforce or any other CRM, see [docs/other-crms.md](docs/other-crms.md).
4. `/flow-sales:status` at any time says whether everything is working and what the next audit would judge and cost, without spending anything.

## Verifying without Claude Code

```bash
python3 ~/flow-sales/scripts/fs.py --home /tmp/fs-check init
python3 ~/flow-sales/scripts/fs.py --home /tmp/fs-check import demo
python3 ~/flow-sales/scripts/fs.py --home /tmp/fs-check status
```

If the last command prints deal and interaction counts, the toolkit works. Inside Claude Code, `/flow-sales:setup` should appear in the slash-command list.

## Uninstalling

`/plugin uninstall flow-sales@flow-sales` removes the plugin. Delete any `.flow-sales/` folders you created to remove the data.
