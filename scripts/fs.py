#!/usr/bin/env python3
"""FlowSales command line. Standard library only, Python 3.10+.

Usage: python3 scripts/fs.py <command> [options] [--home DIR] [--json]
See docs/CONTRACTS.md section 10 for the command table.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from flowsales.store import Store, resolve_home  # noqa: E402
from flowsales.util import now_iso  # noqa: E402

PLUGIN_ROOT = SCRIPTS_DIR.parent

# command -> (module, function). Modules are loaded lazily so a missing module only breaks its own command.
COMMANDS: dict[str, tuple[str, str]] = {
    "init": ("flowsales.core_cmds", "cmd_init"),
    "config": ("flowsales.core_cmds", "cmd_config"),
    "status": ("flowsales.core_cmds", "cmd_status"),
    "log": ("flowsales.core_cmds", "cmd_log"),
    "doctor": ("flowsales.doctor", "run"),
    "pull": ("flowsales.crm.pull", "run"),
    "import": ("flowsales.crm.import_cmd", "run"),
    "link": ("flowsales.link.linker", "run"),
    "plan-assessment": ("flowsales.assess.planner", "run"),
    "validate-assessment": ("flowsales.assess.validate", "run"),
    "rollup": ("flowsales.analytics.rollup", "run"),
    "impact": ("flowsales.analytics.impact", "run"),
    "report": ("flowsales.report.build_report", "run"),
    "briefing-data": ("flowsales.analytics.packs", "briefing"),
    "retro-data": ("flowsales.analytics.packs", "retro"),
    "eval-golden": ("flowsales.evals.golden", "run"),
    "team": ("flowsales.team", "run"),
}


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--home", help="store directory (default $FLOW_SALES_HOME or ./.flow-sales)")
    common.add_argument("--json", action="store_true", help="machine-readable output")
    # Subcommands accept the same flags after their name. SUPPRESS keeps the subparser from
    # overwriting a value that was already parsed before the subcommand name.
    common_sub = argparse.ArgumentParser(add_help=False)
    common_sub.add_argument("--home", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common_sub.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p = argparse.ArgumentParser(prog="fs", description="FlowSales local toolkit", parents=[common])
    _sub = p.add_subparsers(dest="command", required=True)

    class _Sub:  # every subcommand also accepts --home and --json after its name
        def add_parser(self, name: str, **kw):
            return _sub.add_parser(name, parents=[common_sub], **kw)

    sub = _Sub()

    sub.add_parser("init", help="create the store and a default config")

    c = sub.add_parser("config", help="get or set config values")
    c.add_argument("action", choices=["get", "set", "show"])
    c.add_argument("key", nargs="?")
    c.add_argument("value", nargs="?", help="JSON value for set (strings may be bare)")

    sub.add_parser("status", help="counts of everything in the store")

    lg = sub.add_parser("log", help="append a note to runs.jsonl")
    # dest must not be "command": that is the subparser slot, and a collision sends main() looking for a subcommand named after the note
    lg.add_argument("--command", dest="log_command", required=True, help="the skill or step being logged, e.g. daily-sync")
    lg.add_argument("--note", default="")

    d = sub.add_parser("doctor", help="check python, tokens, sources")
    d.add_argument("--source", choices=["all", "hubspot", "granola", "transcripts", "csv"], default="all")

    pl = sub.add_parser("pull", help="pull from a live source")
    pl.add_argument("source", choices=["hubspot"])
    pl.add_argument("--since", help="only objects modified since this ISO date")
    pl.add_argument("--limit-deals", type=int, default=None, help="cap the number of deals (testing)")
    pl.add_argument("--owner", default=None, help="only deals owned by this HubSpot user: an email, or 'me' for config me.email (a rep's own pipeline)")

    im = sub.add_parser("import", help="import from a file-based source")
    im.add_argument("source", choices=["demo", "csv", "granola", "transcripts", "hubspot-cache"])
    im.add_argument("--seed", type=int, default=7)
    im.add_argument("--deals", help="csv: deals file")
    im.add_argument("--interactions", help="csv: interactions file")
    im.add_argument("--cache", help="granola: path to the local cache file")
    im.add_argument("--export-dir", help="granola: directory of exported meeting JSON files")
    im.add_argument("--folder", help="transcripts: folder of transcript files")
    im.add_argument("--dir", help="hubspot-cache: folder of HubSpot connector responses saved verbatim (default .flow-sales/cache/hubspot-mcp)")

    ln = sub.add_parser("link", help="link interactions to deals")
    ln.add_argument("action", nargs="?", choices=["run", "confirm", "reject", "pending"], default="run")
    ln.add_argument("interaction_id", nargs="?")
    ln.add_argument("deal_id", nargs="?")
    ln.add_argument("--dry-run", action="store_true")

    pa = sub.add_parser("plan-assessment", help="write judge batches and print the volume estimate")
    pa.add_argument("--force", action="store_true", help="re-plan every deal even if unchanged")
    pa.add_argument("--sample", type=int, default=None, help="only plan N deals (random, seeded)")
    pa.add_argument("--deal", action="append", help="only these deal ids")
    pa.add_argument("--estimate-only", action="store_true", help="print the volume and cost estimate without writing or clearing any batch files")

    va = sub.add_parser("validate-assessment", help="validate and quote-verify a judge output file")
    va.add_argument("file")

    sub.add_parser("rollup", help="compute analytics from assessments")

    ip = sub.add_parser("impact", help="quarter attribution")
    ip.add_argument("--quarter", required=True, help="YYYY-Qn")

    rp = sub.add_parser("report", help="build the HTML report")
    rp.add_argument("--open", action="store_true")
    rp.add_argument("--out", help="output path override")

    bd = sub.add_parser("briefing-data", help="JSON pack for the standup skill")
    bd.add_argument("--rep", required=True)
    bd.add_argument("--date", default=None)

    rd = sub.add_parser("retro-data", help="JSON pack for the retro skill")
    rd.add_argument("--rep", required=True)
    rd.add_argument("--week", default=None, help="ISO week YYYY-Www (default: current, or last week on a Monday or Tuesday)")

    eg = sub.add_parser("eval-golden", help="golden-set evaluation of the judge (evals/golden)")
    eg.add_argument("action", choices=["build", "compare"])
    eg.add_argument("--parts", type=int, default=None, help="build: number of batch files to split the snippets across (default 4)")
    eg.add_argument("--model", default=None, help="compare: judge model name to record (default: from the assessments)")
    eg.add_argument("--note", default=None, help="compare: free-text note for runs.jsonl")
    eg.add_argument("--strict", action="store_true", help="compare: exit 1 when a target is missed")

    tm = sub.add_parser("team", help="a folder the team syncs, holding one judged assessment per deal, so a deal is judged once")
    tm.add_argument("action", nargs="?", choices=["status", "init", "join", "sync", "leave", "candidates"], default="status")
    tm.add_argument("path", nargs="?", help="init/join: the folder (inside Drive, OneDrive, Dropbox or any folder the team syncs)")
    tm.add_argument("--pull-only", action="store_true", help="sync: copy in only")
    tm.add_argument("--push-only", action="store_true", help="sync: copy out only")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    home = resolve_home(args.home)
    store = Store(home)
    started = time.time()
    module_name, func_name = COMMANDS[args.command]
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        msg = {"ok": False, "error": f"command '{args.command}' is not available yet ({exc})"}
        print(json.dumps(msg) if args.json else msg["error"], file=sys.stderr)
        return 1
    func = getattr(module, func_name)
    ctx = {"store": store, "home": home, "plugin_root": PLUGIN_ROOT, "json": args.json, "started": started, "now": now_iso()}
    try:
        code = func(ctx, args)
    except KeyboardInterrupt:
        return 130
    except SystemExit as exc:  # let modules exit with a code
        return int(exc.code or 0)
    except Exception as exc:  # noqa: BLE001 - surface everything, log it, exit 2
        store.log_run(args.command, vars(args), False, started, notes=f"{type(exc).__name__}: {exc}")
        if args.json:
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        else:
            print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return int(code or 0)


if __name__ == "__main__":
    sys.exit(main())
