"""`fs.py pull hubspot`: resolve the token, run the HubSpot walk, print a summary, log the run."""
from __future__ import annotations

import json
import sys
from typing import Any

from ..config import resolve_hubspot_token
from ..store import Store
from .hubspot import DEFAULT_BASE_URL, HubSpotClient, HubSpotError, ScopeError, pull

TOKEN_HELP = """No HubSpot token found. It can live in one of three places (checked in this order):
  1. the environment variable named by config sources.hubspot.tokenEnv (default HUBSPOT_ACCESS_TOKEN)
  2. the plugin user config, exposed as the environment variable CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN
  3. {secrets} with {{"hubspot_token": "pat-..."}} and permissions 600
See docs/hubspot.md for creating a private app with the read scopes."""


def _emit(ctx: dict, payload: dict, text: str, err: bool = False) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text, file=sys.stderr if err else sys.stdout)


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    source = getattr(args, "source", "hubspot")
    if source != "hubspot":
        _emit(ctx, {"ok": False, "error": f"unknown pull source {source!r}"}, f"unknown pull source: {source}", err=True)
        return 1
    if not store.exists():
        _emit(ctx, {"ok": False, "error": "no store; run init"}, f"No FlowSales store at {store.home}. Run: fs.py init", err=True)
        return 1
    cfg = store.config
    hs_cfg = cfg.get("sources.hubspot") or {}
    token = resolve_hubspot_token(cfg, store.home)
    if not token:
        text = TOKEN_HELP.format(secrets=store.home / "secrets.json")
        store.log_run("pull hubspot", _args(args), False, ctx["started"], notes="no token")
        _emit(ctx, {"ok": False, "error": "no HubSpot token", "help": text}, text, err=True)
        return 1
    if not hs_cfg.get("enabled", False):
        print("note: sources.hubspot.enabled is false in config; pulling anyway", file=sys.stderr)

    client = HubSpotClient(token, base_url=hs_cfg.get("baseUrl") or DEFAULT_BASE_URL,
                           rate_per_sec=float(hs_cfg.get("requestsPerSecond") or 4.0))

    def progress(msg: str) -> None:
        print(f"  {msg}", file=sys.stderr)

    since = getattr(args, "since", None)
    limit = getattr(args, "limit_deals", None)
    try:
        summary = pull(store, cfg, since=since, limit_deals=limit, client=client, log=progress)
    except ValueError as exc:  # bad --since
        store.log_run("pull hubspot", _args(args), False, ctx["started"], notes=str(exc))
        _emit(ctx, {"ok": False, "error": str(exc)}, f"error: {exc}", err=True)
        return 1
    except ScopeError as exc:
        notes = f"MISSING_SCOPES: {', '.join(exc.required_scopes)} ({client.request_count} requests)"
        store.log_run("pull hubspot", _args(args), False, ctx["started"], notes=notes)
        text = (f"HubSpot refused the request: the token is missing scopes: {', '.join(exc.required_scopes) or 'unlisted'}\n"
                f"Add them to the private app, rotate the token, and run doctor again. See docs/hubspot.md.")
        _emit(ctx, {"ok": False, "error": "missing scopes", "requiredScopes": exc.required_scopes,
                    "requests": client.request_count}, text, err=True)
        return 2
    except HubSpotError as exc:
        store.log_run("pull hubspot", _args(args), False, ctx["started"],
                      notes=f"{type(exc).__name__}: {exc} ({client.request_count} requests)")
        _emit(ctx, {"ok": False, "error": str(exc), "status": exc.status, "category": exc.category,
                    "correlationId": exc.correlation_id, "requests": client.request_count}, f"error: {exc}", err=True)
        return 2

    store.log_run("pull hubspot", _args(args), True, ctx["started"],
                  read=[f"hubspot:{client.base_url}"], wrote=summary.get("wrote", []),
                  notes=f"{summary['requests']} requests, {summary['counts']['deals']} deals, "
                        f"{sum(summary['counts']['interactions'].values())} interactions")
    _emit(ctx, summary, _text(summary))
    return 0


def _args(args: Any) -> dict:
    return {"source": getattr(args, "source", None), "since": getattr(args, "since", None),
            "limitDeals": getattr(args, "limit_deals", None)}


def _text(s: dict) -> str:
    c = s["counts"]
    lines = [
        f"Pulled HubSpot ({s['baseUrl']}) for window {s['window']['from']} to {s['window']['to']}"
        + (f" (modified since {s['since']})" if s.get("since") else ""),
        f"  deals: {c['deals']}   contacts: {c['contacts']}   companies: {c['companies']}   reps: {c['reps']}",
        "  interactions: " + ", ".join(f"{k} {v}" for k, v in c["interactions"].items()) + f"   links: {c['links']}",
        f"  cache: {s['cache']['dealsFromCache']} deals and {s['cache']['objectsFromCache']} objects reused, "
        f"{s['cache']['objectsFetched']} objects fetched",
        f"  requests: {s['requests']} ({s['retries']} retries) in {s['durationMs'] / 1000:.1f}s",
    ]
    if s.get("unmappedStages"):
        lines.append("  stages without a phase mapping (run doctor, then config set stagePhases.<id> <phase>):")
        for u in s["unmappedStages"]:
            lines.append(f"    {u['stageId']} ({u['label']}) in pipeline {u['pipelineId']}: suggested {u['suggestedPhase']}")
    for w in s.get("warnings") or []:
        lines.append(f"  warning: {w}")
    v = s.get("validation")
    if v:
        bad = [k for k, r in v.items() if isinstance(r, dict) and r.get("ok") is False]
        if bad:
            lines.append(f"  validation problems in: {', '.join(bad)} (see --json output)")
    return "\n".join(lines)
