"""`fs.py doctor`: environment, store, config, framework and source checks. Never prints a token."""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from .config import Config, resolve_hubspot_token
from .store import Store

REQUIRED_HUBSPOT_SCOPES = [
    "crm.objects.deals.read",
    "crm.objects.contacts.read",
    "crm.objects.companies.read",
    "crm.objects.owners.read",
    "crm.schemas.deals.read",
    "sales-email-read",
]
GRANOLA_DEFAULT_CACHE = "~/Library/Application Support/Granola/cache-v3.json"


def _check(checks: list[dict], name: str, ok: bool, detail: str, fix: Optional[str] = None) -> dict:
    entry = {"check": name, "ok": bool(ok), "detail": detail, "fix": None if ok else fix}
    checks.append(entry)
    return entry


def token_location(cfg: Config, home: Path) -> Optional[str]:
    """Which of the three places holds the token (never the token itself)."""
    env_name = cfg.get("sources.hubspot.tokenEnv") or "HUBSPOT_ACCESS_TOKEN"
    for name in (env_name, "HUBSPOT_ACCESS_TOKEN", "CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN"):
        if os.environ.get(name):
            return f"environment variable {name}"
    secrets = home / "secrets.json"
    if secrets.exists():
        try:
            with secrets.open("r", encoding="utf-8") as fh:
                if (json.load(fh) or {}).get("hubspot_token"):
                    return f"{secrets} (key hubspot_token)"
        except (OSError, ValueError):
            return None
    return None


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    source = getattr(args, "source", "all") or "all"
    checks: list[dict] = []
    extra: dict[str, Any] = {}

    # python
    v = sys.version_info
    _check(checks, "python", v >= (3, 10), f"python {v.major}.{v.minor}.{v.micro}",
           "install Python 3.10 or newer and make sure `python3` points at it")

    # store
    _check(checks, "store", store.exists(), f"store at {store.home}" if store.exists() else f"no store at {store.home}",
           "run: fs.py init")

    # config
    cfg: Optional[Config] = None
    try:
        cfg = Config.load(store.config_path)
        w_from, w_to = cfg.window
        _check(checks, "config", True, f"framework {cfg.framework}, window {w_from} to {w_to}"
               + ("" if store.exists() else " (defaults; no config file yet)"))
    except (OSError, ValueError) as exc:
        _check(checks, "config", False, f"config.json does not parse: {exc}",
               f"fix the JSON in {store.config_path} or move it aside and run init again")

    # framework file
    plugin_root = Path(ctx.get("plugin_root") or Path(__file__).resolve().parents[2])
    if cfg is not None:
        fw = plugin_root / "frameworks" / f"{cfg.framework}.json"
        _check(checks, "framework", fw.exists(), str(fw) if fw.exists() else f"missing {fw}",
               "set `framework` to meddpicc or meddic (fs.py config set framework meddpicc) or restore the plugin's frameworks folder")

    if cfg is not None:
        sources = cfg.get("sources") or {}
        want = lambda name: source == name or (source == "all" and (sources.get(name) or {}).get("enabled"))  # noqa: E731
        if want("hubspot"):
            extra["hubspot"] = _hubspot_checks(checks, cfg, store, ctx)
        if want("granola"):
            _granola_checks(checks, cfg)
        if want("transcripts"):
            _transcripts_checks(checks, cfg)
        if want("csv"):
            _csv_checks(checks, cfg)

    all_ok = all(c["ok"] for c in checks)
    payload = {"ok": all_ok, "checks": checks, **extra}
    if store.exists():
        store.log_run("doctor", {"source": source}, all_ok, ctx["started"],
                      notes=", ".join(f"{c['check']}={'ok' if c['ok'] else 'FAIL'}" for c in checks))
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_table(checks, extra))
    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# hubspot
# ---------------------------------------------------------------------------
def _hubspot_checks(checks: list[dict], cfg: Config, store: Store, ctx: dict) -> dict:
    from .crm.hubspot import DEFAULT_BASE_URL, HubSpotClient, HubSpotError, ScopeError  # lazy: keeps doctor cheap

    info: dict[str, Any] = {"tokenSource": None, "hubId": None, "userId": None, "scopes": [], "missingScopes": [],
                            "pipelines": [], "unmappedStages": [], "unknownPipelines": []}
    hs_cfg = cfg.get("sources.hubspot") or {}
    base_url = hs_cfg.get("baseUrl") or DEFAULT_BASE_URL
    location = token_location(cfg, store.home)
    token = resolve_hubspot_token(cfg, store.home)
    info["tokenSource"] = location
    env_name = cfg.get("sources.hubspot.tokenEnv") or "HUBSPOT_ACCESS_TOKEN"
    _check(checks, "hubspot token", bool(token), f"found in {location}" if token else "not found",
           f"set ${env_name}, or the plugin option CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN, or write "
           f"{store.home / 'secrets.json'} as {{\"hubspot_token\": \"...\"}} with chmod 600 (docs/hubspot.md)")
    if not token:
        return info

    secrets = store.home / "secrets.json"
    if location and str(secrets) in location:
        try:
            mode = stat.S_IMODE(secrets.stat().st_mode)
            _check(checks, "hubspot secrets.json permissions", mode & 0o077 == 0, f"mode {oct(mode)}",
                   f"chmod 600 {secrets}")
        except OSError:
            pass

    factory: Callable[..., HubSpotClient] = ctx.get("hubspot_client_factory") or (
        lambda tok, url: HubSpotClient(tok, base_url=url, rate_per_sec=float(hs_cfg.get("requestsPerSecond") or 4.0)))
    client = factory(token, base_url)

    # token info
    try:
        ti = client.token_info() or {}
    except HubSpotError as exc:
        _check(checks, "hubspot token info", False, f"{exc}",
               "the token was rejected: check it was pasted in full and has not been rotated; EU portals use "
               f"baseUrl https://api-eu1.hubapi.com (config sources.hubspot.baseUrl); current baseUrl {base_url}")
        return info
    scopes = sorted(str(s) for s in (ti.get("scopes") or []))
    info.update({"hubId": ti.get("hubId"), "userId": ti.get("userId"), "appId": ti.get("appId"), "scopes": scopes})
    _check(checks, "hubspot token info", True, f"hubId {ti.get('hubId')}, userId {ti.get('userId')}, {len(scopes)} scopes ({base_url})")

    # scopes
    missing = [s for s in REQUIRED_HUBSPOT_SCOPES if s not in scopes]
    info["missingScopes"] = missing
    _check(checks, "hubspot scopes", not missing,
           "all required read scopes present" if not missing else "missing: " + ", ".join(missing),
           "add the missing scopes to the private app (Settings > Integrations > Legacy apps > Private), "
           "rotate the token, store the new token, then run doctor again (docs/hubspot.md)")

    # tiny deals search
    try:
        page = client.post("/crm/v3/objects/deals/search", {"filterGroups": [], "properties": ["dealname"], "limit": 1}) or {}
        _check(checks, "hubspot deals search", True, f"ok, {page.get('total', '?')} deals visible")
    except ScopeError as exc:
        _check(checks, "hubspot deals search", False, f"missing scopes: {', '.join(exc.required_scopes)}",
               "add the listed scopes to the private app and rotate the token")
        info["missingScopes"] = sorted(set(missing) | set(exc.required_scopes))
    except HubSpotError as exc:
        _check(checks, "hubspot deals search", False, str(exc), "check network access to HubSpot and the token")

    # pipelines and stage mapping
    try:
        pipelines = client.pipelines("deals")
    except ScopeError as exc:
        _check(checks, "hubspot pipelines", False, f"missing scopes: {', '.join(exc.required_scopes)}",
               "add the listed scopes to the private app and rotate the token")
        return info
    except HubSpotError as exc:
        _check(checks, "hubspot pipelines", False, str(exc), "check network access to HubSpot and the token")
        return info
    mapping = cfg.get("stagePhases") or {}
    configured = [str(p) for p in (hs_cfg.get("pipelines") or []) if p]
    known_ids = {str(p.get("id")) for p in pipelines}
    info["unknownPipelines"] = [p for p in configured if p not in known_ids]
    unmapped: list[dict] = []
    for pl in pipelines:
        pid = str(pl.get("id"))
        stages = []
        for st in sorted(pl.get("stages") or [], key=lambda s: s.get("displayOrder", 0)):
            sid = str(st.get("id"))
            label = st.get("label") or sid
            mapped = sid in mapping
            phase = mapping.get(sid) if mapped else cfg.phase_for_stage(sid, label)
            stages.append({"id": sid, "label": label, "phase": phase, "mapped": mapped,
                           "isClosed": (st.get("metadata") or {}).get("isClosed")})
            if not mapped and (not configured or pid in configured):
                unmapped.append({"pipelineId": pid, "pipelineLabel": pl.get("label") or pid, "stageId": sid,
                                 "label": label, "suggestedPhase": phase})
        info["pipelines"].append({"id": pid, "label": pl.get("label") or pid, "stages": stages})
    info["unmappedStages"] = unmapped
    _check(checks, "hubspot pipelines", True,
           ", ".join(f"{p['label']} ({p['id']}, {len(p['stages'])} stages)" for p in info["pipelines"]) or "none")
    if info["unknownPipelines"]:
        _check(checks, "hubspot configured pipelines", False,
               "not in this portal: " + ", ".join(info["unknownPipelines"]),
               "set sources.hubspot.pipelines to ids from the pipelines check (fs.py config set sources.hubspot.pipelines '[\"default\"]')")
    if unmapped:
        detail = "; ".join(f"{u['stageId']} ({u['label']}) suggested {u['suggestedPhase']}" for u in unmapped)
        _check(checks, "hubspot stage phases", False, f"{len(unmapped)} stage ids without a phase mapping: {detail}",
               "map each stage: fs.py config set stagePhases.<stageId> \"<discovery|evaluation|proposal|commit|won|lost>\"")
    else:
        _check(checks, "hubspot stage phases", True, "every stage id in the configured pipelines has a phase")
    return info


# ---------------------------------------------------------------------------
# file based sources
# ---------------------------------------------------------------------------
def _granola_checks(checks: list[dict], cfg: Config) -> None:
    g = cfg.get("sources.granola") or {}
    cache_path = Path(g.get("cachePath") or GRANOLA_DEFAULT_CACHE).expanduser()
    export_dir = Path(g["exportDir"]).expanduser() if g.get("exportDir") else None
    if cache_path.exists():
        _check(checks, "granola", True, f"local cache {cache_path} ({cache_path.stat().st_size // 1024} KB)")
    elif export_dir and export_dir.is_dir():
        n = len(list(export_dir.glob("*.json")))
        _check(checks, "granola", n > 0, f"export folder {export_dir} ({n} JSON files)",
               "export meetings into the folder first (docs/granola.md)")
    else:
        _check(checks, "granola", False,
               f"no cache at {cache_path}" + (f" and no export folder at {export_dir}" if export_dir else ""),
               "set sources.granola.cachePath to the Granola cache file, or export meetings and set sources.granola.exportDir (docs/granola.md)")


def _transcripts_checks(checks: list[dict], cfg: Config) -> None:
    folder = cfg.get("sources.transcripts.folder")
    p = Path(folder).expanduser() if folder else None
    if p and p.is_dir():
        n = sum(1 for f in p.rglob("*") if f.suffix.lower() in (".md", ".txt", ".vtt", ".json", ".srt"))
        _check(checks, "transcripts", n > 0, f"{p} ({n} transcript files)", "add .md/.txt/.vtt/.json transcript files to the folder")
    else:
        _check(checks, "transcripts", False, f"folder not found: {folder}", "fs.py config set sources.transcripts.folder \"/path/to/folder\"")


def _csv_checks(checks: list[dict], cfg: Config) -> None:
    for key, label in (("dealsFile", "csv deals file"), ("interactionsFile", "csv interactions file")):
        f = cfg.get(f"sources.csv.{key}")
        p = Path(f).expanduser() if f else None
        ok = bool(p and p.is_file())
        _check(checks, label, ok, str(p) if ok else f"not found: {f}", f"fs.py config set sources.csv.{key} \"/path/to/file.csv\" (docs/other-crms.md)")


def _table(checks: list[dict], extra: dict) -> str:
    width = max((len(c["check"]) for c in checks), default=10)
    lines = []
    for c in checks:
        mark = "ok  " if c["ok"] else "FAIL"
        lines.append(f"[{mark}] {c['check']:<{width}}  {c['detail']}")
        if not c["ok"] and c.get("fix"):
            lines.append(f"       fix: {c['fix']}")
    hs = extra.get("hubspot")
    if hs and hs.get("pipelines"):
        lines.append("")
        lines.append("HubSpot pipelines and stages:")
        for p in hs["pipelines"]:
            lines.append(f"  {p['label']} (id {p['id']})")
            for s in p["stages"]:
                flag = "" if s["mapped"] else "  (unmapped, suggested)"
                lines.append(f"    {s['id']:<28} {s['label']:<32} phase {s['phase']}{flag}")
    ok = all(c["ok"] for c in checks)
    lines.append("")
    lines.append("All checks passed." if ok else f"{sum(1 for c in checks if not c['ok'])} check(s) need attention.")
    return "\n".join(lines)
