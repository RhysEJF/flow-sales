"""`fs.py import <source>`: dispatch to a file-based adapter, enable the source in config, log the run.

Each adapter module exposes ``run(ctx, args) -> int`` and may leave ``ctx["summary"]`` as
``{"read": [...], "wrote": [...], "notes": "..."}`` for the runs log. Adapters validate their own
records with ``flowsales.schema.validate.validate_records`` before writing anything.
"""
from __future__ import annotations

import importlib
import json
import sys
from typing import Any

from ..store import Store

ADAPTERS = {
    "demo": "flowsales.crm.demo",
    "csv": "flowsales.crm.csv_adapter",
    "granola": "flowsales.crm.granola",
    "transcripts": "flowsales.crm.transcripts_folder",
    "hubspot-cache": "flowsales.crm.hubspot_cache",
}
ENABLES = {"hubspot-cache": "hubspot"}   # which source flag an adapter switches on


def _fail(ctx: dict, message: str) -> int:
    if ctx.get("json"):
        print(json.dumps({"ok": False, "error": message}))
    else:
        print(message, file=sys.stderr)
    return 1


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    source = getattr(args, "source", None)
    module_name = ADAPTERS.get(source or "")
    if not module_name:
        return _fail(ctx, f"unknown import source {source!r}; expected one of {', '.join(ADAPTERS)}")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return _fail(ctx, f"{source} adapter not available yet")
        raise
    command = f"import {source}"
    logged_args = {k: v for k, v in vars(args).items() if k not in ("command", "home", "json") and v is not None}
    store.ensure()
    code = int(module.run(ctx, args) or 0)
    summary = ctx.get("summary") or {}
    if code == 0:
        store.config.set(f"sources.{ENABLES.get(source, source)}.enabled", True)
        store.save_config()
    store.log_run(command, logged_args, code == 0, ctx["started"], read=summary.get("read") or [],
                  wrote=summary.get("wrote") or [], notes=summary.get("notes") or ("" if code == 0 else f"exit {code}"))
    return code
