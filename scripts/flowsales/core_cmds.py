"""init, config, status, log commands."""
from __future__ import annotations

import json
import time
from typing import Any

from .store import Store


def _out(ctx: dict, payload: dict, text: str) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text)


def cmd_init(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    created = not store.exists()
    store.ensure()
    store.config.save()
    gitignore = store.home / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")
    store.log_run("init", {}, True, ctx["started"], wrote=[str(store.config_path)])
    _out(ctx, {"ok": True, "home": str(store.home), "created": created},
         f"{'Created' if created else 'Found'} FlowSales store at {store.home}")
    return 0


def _parse_value(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw


def cmd_config(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    if args.action == "show":
        _out(ctx, {"ok": True, "config": store.config.data}, json.dumps(store.config.data, indent=2, ensure_ascii=False))
        return 0
    if not args.key:
        print("config get|set needs a key", file=__import__("sys").stderr)
        return 1
    if args.action == "get":
        val = store.config.get(args.key)
        _out(ctx, {"ok": True, "key": args.key, "value": val}, json.dumps(val, ensure_ascii=False))
        return 0
    store.ensure()
    store.config.set(args.key, _parse_value(args.value))
    store.config.save()
    store.log_run("config set", {"key": args.key}, True, ctx["started"], wrote=[str(store.config_path)])
    _out(ctx, {"ok": True, "key": args.key, "value": store.config.get(args.key)}, f"{args.key} = {json.dumps(store.config.get(args.key))}")
    return 0


def cmd_status(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    if not store.exists():
        _out(ctx, {"ok": False, "error": "no store; run init"}, "No FlowSales store here. Run: fs.py init")
        return 1
    deals = store.load_deals()
    linked = 0
    unlinked = len(store.load_unlinked())
    by_type: dict[str, int] = {}
    for deal_id, it in store.iter_all_interactions():
        if deal_id:
            linked += 1
        by_type[it.get("type", "?")] = by_type.get(it.get("type", "?"), 0) + 1
    assessments = sum(1 for _ in store.iter_assessments())
    links = store.load_links().get("links", [])
    pending = sum(1 for l in links if l.get("status") == "pending")
    analytics = sorted(p.name for p in store.analytics_dir.glob("*.json")) if store.analytics_dir.exists() else []
    reports = sorted(p.name for p in store.reports_dir.glob("*.html")) if store.reports_dir.exists() else []
    payload = {
        "ok": True,
        "home": str(store.home),
        "framework": store.config.framework,
        "window": store.config.get("window"),
        "sources": {k: v.get("enabled", False) for k, v in (store.config.get("sources") or {}).items()},
        "deals": len(deals),
        "dealsByOutcome": _count(deals, "outcome"),
        "reps": len(store.load_reps()),
        "contacts": len(store.load_contacts()),
        "interactionsLinked": linked,
        "interactionsUnlinked": unlinked,
        "interactionsByType": by_type,
        "links": len(links),
        "linksPending": pending,
        "assessments": assessments,
        "analytics": analytics,
        "reports": reports,
    }
    text = "\n".join(f"{k}: {json.dumps(v) if not isinstance(v, str) else v}" for k, v in payload.items() if k != "ok")
    _out(ctx, payload, text)
    return 0


def _count(items: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        out[str(it.get(key))] = out.get(str(it.get(key)), 0) + 1
    return out


def cmd_log(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    store.ensure()
    store.log_run(getattr(args, "log_command", None) or "log", {}, True, ctx["started"], notes=args.note)
    _out(ctx, {"ok": True}, "logged")
    return 0
