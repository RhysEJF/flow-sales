# Installing FlowSales

FlowSales is a Claude Code plugin. It needs Claude Code 2.1 or newer and Python 3.10 or newer on the path as `python3`. No Python packages are installed; everything is standard library.

## Option 1: marketplace (recommended)

Inside Claude Code:

```
/plugin marketplace add RhysEJF/flow-sales
/plugin install flow-sales@flow-sales
```

The repository is private for now, so your git credentials (the GitHub CLI, SSH keys or a credential helper) must have access to it.

## Option 2: local checkout

```bash
git clone https://github.com/RhysEJF/flow-sales.git ~/flow-sales
claude --plugin-dir ~/flow-sales
```

The `--plugin-dir` flag loads the plugin for that session only. Repeat it each time, or install from the marketplace.

## Option 3: tell Claude Code to install it

Open Claude Code and say: "Install FlowSales from https://github.com/RhysEJF/flow-sales". Claude reads this file and follows Option 1 or 2.

## After installing

1. `cd` into the directory where you want FlowSales to keep its data (a fresh folder is fine) and start Claude Code there. FlowSales stores everything under `.flow-sales/` in that directory.
2. Run `/flow-sales:setup --demo` to see the whole loop on the demo dataset, or `/flow-sales:setup` to connect your own data.
3. For HubSpot, follow [docs/hubspot.md](docs/hubspot.md) to create a private app with read scopes. For Granola, follow [docs/granola.md](docs/granola.md).

## Verifying

```bash
python3 ~/flow-sales/scripts/fs.py --home /tmp/fs-check init
python3 ~/flow-sales/scripts/fs.py --home /tmp/fs-check import demo
python3 ~/flow-sales/scripts/fs.py --home /tmp/fs-check status
```

If the last command prints deal and interaction counts, the toolkit works. Inside Claude Code, `/flow-sales:setup` should appear in the slash-command list.

## Uninstalling

`/plugin uninstall flow-sales@flow-sales` removes the plugin. Delete any `.flow-sales/` folders you created to remove the data.
