"""`fs.py import hubspot-cache --dir <folder>`: build the store from HubSpot objects saved verbatim by the connector route.

The HubSpot MCP server (mcp.hubspot.com; each person signs in as themselves, no token on disk) returns CRM objects
in the shape of the REST API v3: ``{"id", "properties": {...}}`` with an optional ``associations`` map. The setup,
audit and daily-sync skills save every tool response unchanged into ``.flow-sales/cache/hubspot-mcp/`` as
``<kind>-<n>.json`` (deals, contacts, companies, calls, emails, meetings, notes, owners, pipelines,
associations-<from>-<to>). This adapter reads that folder, keeps the deals inside the configured window, and runs
the same normalisation as ``pull hubspot`` (``assemble_and_save``), so the store is identical whichever route
filled it.

Tolerant on purpose: a file may hold a bare list, ``{"results": [...]}``, a single object, an MCP ``content``
envelope with JSON inside its text, or several JSON values back to back; the kind comes from the file name, else
from the object's properties. Unverified against the live connector as of 2026-09-09: the shapes are the
documented v3 shapes, and the first live sign-in confirms them (docs/hubspot.md, "Connector route").
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterator, Optional

from ..config import Config
from ..store import Store
from .hubspot import (ENGAGEMENT_TYPES, _Context, _ms, assemble_and_save, register_pipelines, window_bounds)

KINDS = ("deals", "contacts", "companies", "calls", "emails", "meetings", "notes", "owners", "pipelines")
SINGULAR = {"deal": "deals", "contact": "contacts", "company": "companies", "call": "calls", "email": "emails",
            "meeting": "meetings", "note": "notes", "owner": "owners", "pipeline": "pipelines", "association": "associations",
            "associations": "associations"}
SNIFF = [  # property present -> kind
    ("dealstage", "deals"), ("dealname", "deals"), ("hs_call_body", "calls"), ("hs_call_title", "calls"),
    ("hs_email_subject", "emails"), ("hs_email_text", "emails"), ("hs_meeting_title", "meetings"),
    ("hs_meeting_body", "meetings"), ("hs_note_body", "notes"), ("firstname", "contacts"), ("lastname", "contacts"),
    ("domain", "companies"),
]
DEFAULT_DIR = "cache/hubspot-mcp"


# ---------------------------------------------------------------------------
# reading files
# ---------------------------------------------------------------------------
def json_values(text: str) -> Iterator[Any]:
    """Every JSON value in a text, in order (a tool reply may wrap JSON in prose or return several values)."""
    dec = json.JSONDecoder()
    i = 0
    n = len(text)
    while i < n:
        m = re.search(r"[\[{]", text[i:])
        if not m:
            return
        start = i + m.start()
        try:
            value, end = dec.raw_decode(text, start)
        except ValueError:
            i = start + 1
            continue
        yield value
        i = end


def records(value: Any) -> list[Any]:
    """Flatten a tool reply into the objects inside it."""
    out: list[Any] = []
    if isinstance(value, list):
        for v in value:
            out.extend(records(v))
        return out
    if not isinstance(value, dict):
        return out
    if "content" in value and isinstance(value["content"], list):   # MCP envelope
        for part in value["content"]:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                for inner in json_values(part["text"]):
                    out.extend(records(inner))
            elif isinstance(part, dict) and part.get("type") == "json":
                out.extend(records(part.get("data") or part.get("json")))
        return out
    for key in ("results", "objects", "data", "items", "deals", "contacts", "companies", "calls", "emails", "meetings",
                "notes", "owners", "pipelines"):
        if isinstance(value.get(key), list):
            out.extend(records(value[key]))
            return out
    if "text" in value and isinstance(value["text"], str) and len(value) <= 3:   # {"type": "text", "text": "..."}
        for inner in json_values(value["text"]):
            out.extend(records(inner))
        return out
    return [value]


def kind_from_name(name: str) -> Optional[str]:
    stem = Path(name).stem.lower()
    head = re.split(r"[-_. ]", stem, maxsplit=1)[0]
    if head in KINDS:
        return head
    return SINGULAR.get(head)


def kind_from_object(obj: dict) -> Optional[str]:
    if not isinstance(obj, dict):
        return None
    if "stages" in obj and "label" in obj:
        return "pipelines"
    if "email" in obj and ("firstName" in obj or "userId" in obj) and "properties" not in obj:
        return "owners"
    if "from" in obj and "to" in obj:
        return "associations"
    props = obj.get("properties") if isinstance(obj.get("properties"), dict) else {}
    for prop, kind in SNIFF:
        if prop in props:
            return kind
    if "email" in props:
        return "contacts"
    return None


def embedded_associations(obj: dict) -> dict[str, list[dict]]:
    """The v3 ``associations`` map on an object, normalised to the v4 batch entry shape."""
    out: dict[str, list[dict]] = {}
    raw = obj.get("associations")
    if not isinstance(raw, dict):
        return out
    for to_type, body in raw.items():
        entries = body.get("results") if isinstance(body, dict) else body
        if not isinstance(entries, list):
            continue
        norm = []
        for e in entries:
            if isinstance(e, dict):
                tid = e.get("toObjectId") or e.get("id")
                types = e.get("associationTypes")
                if not types:
                    types = [{"typeId": e.get("typeId"), "label": e.get("type")}] if (e.get("typeId") or e.get("type")) else []
                if tid is not None:
                    norm.append({"toObjectId": str(tid), "associationTypes": types})
            elif e is not None:
                norm.append({"toObjectId": str(e), "associationTypes": []})
        if norm:
            out[str(to_type).lower()] = norm
    return out


def load_dir(folder: Path) -> dict:
    """Everything in the folder, deduplicated by object id, plus associations from files and from objects."""
    objects: dict[str, dict[str, dict]] = {k: {} for k in KINDS if k not in ("owners", "pipelines")}
    owners: dict[str, dict] = {}
    pipelines: dict[str, dict] = {}
    assoc: dict[tuple[str, str], dict[str, list[dict]]] = {}
    stage_labels: dict[str, str] = {}
    read: list[str] = []
    unknown = 0

    def add_assoc(from_type: str, to_type: str, from_id: str, entries: list[dict]) -> None:
        table = assoc.setdefault((from_type, to_type), {})
        seen = {str(e.get("toObjectId")) for e in table.get(from_id, [])}
        for e in entries:
            if str(e.get("toObjectId")) not in seen:
                table.setdefault(from_id, []).append(e)
                seen.add(str(e.get("toObjectId")))

    for path in sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in (".json", ".txt", ".md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        read.append(str(path))
        named = kind_from_name(path.name)
        m = re.match(r"associations?[-_](\w+)[-_](\w+)", path.stem.lower())
        assoc_pair = (m.group(1), m.group(2)) if m else None
        dm = re.match(r"(calls|emails|meetings|notes|contacts|companies)[-_]deal[-_]([A-Za-z0-9]+)", path.stem.lower())
        for_deal = dm.group(2) if dm else None   # every object in this file belongs to that deal
        for value in json_values(text):
            for obj in records(value):
                if not isinstance(obj, dict):
                    continue
                kind = named if named and named != "associations" else kind_from_object(obj)
                if kind == "associations" or (assoc_pair and "from" in obj and "to" in obj):
                    if not assoc_pair:
                        unknown += 1
                        continue
                    from_id = str((obj.get("from") or {}).get("id"))
                    tos = [{"toObjectId": str(t.get("toObjectId")), "associationTypes": t.get("associationTypes") or []}
                           for t in obj.get("to") or [] if isinstance(t, dict) and t.get("toObjectId") is not None]
                    add_assoc(assoc_pair[0], assoc_pair[1], from_id, tos)
                    continue
                if kind == "owners":
                    if obj.get("id") is not None:
                        owners[str(obj["id"])] = obj
                    continue
                if kind == "pipelines":
                    if obj.get("id") is not None:
                        pipelines[str(obj["id"])] = obj
                    continue
                if kind in objects and obj.get("id") is not None:
                    oid = str(obj["id"])
                    if oid in objects[kind]:   # merge properties from a later, richer fetch
                        merged = dict(objects[kind][oid])
                        merged_props = dict(merged.get("properties") or {})
                        merged_props.update(obj.get("properties") or {})
                        merged.update(obj)
                        merged["properties"] = merged_props
                        obj = merged
                    objects[kind][oid] = obj
                    for to_type, entries in embedded_associations(obj).items():
                        add_assoc(kind, to_type, oid, entries)
                    if for_deal:
                        add_assoc("deals", kind, for_deal, [{"toObjectId": oid, "associationTypes": []}])
                    continue
                if isinstance(obj.get("options"), list) and str(obj.get("name")) == "dealstage":
                    for opt in obj["options"]:   # get_properties(dealstage): stage ids with their labels
                        if isinstance(opt, dict) and opt.get("value") is not None:
                            stage_labels[str(opt["value"])] = str(opt.get("label") or opt["value"])
                    continue
                unknown += 1
    return {"objects": objects, "owners": list(owners.values()), "pipelines": list(pipelines.values()),
            "assoc": assoc, "stageLabels": stage_labels, "read": read, "unknown": unknown}


# ---------------------------------------------------------------------------
# the import
# ---------------------------------------------------------------------------
def _in_window(value: Optional[str], start_ms: Optional[int], end_ms: Optional[int]) -> bool:
    ms = _ms(value) if value else None
    if ms is None:
        return start_ms is None and end_ms is None
    return (start_ms is None or ms >= start_ms) and (end_ms is None or ms <= end_ms)


def deals_in_window(deals: dict[str, dict], cfg: Config, configured_pipelines: list[str]) -> list[str]:
    """Closed deals by close date, open deals by create date, the same rule as the REST search."""
    start_ms, end_ms = window_bounds(cfg)
    keep: list[str] = []
    for did, raw in deals.items():
        p = raw.get("properties") or {}
        if configured_pipelines and str(p.get("pipeline")) not in configured_pipelines:
            continue
        closed = str(p.get("hs_is_closed") or "").lower() == "true" or str(p.get("dealstage") or "") in ("closedwon", "closedlost")
        if _in_window(p.get("closedate") if closed else p.get("createdate"), start_ms, end_ms):
            keep.append(did)
    return keep


def synth_pipelines(deals: dict[str, dict], stage_labels: Optional[dict[str, str]] = None) -> list[dict]:
    """When the pipelines were not saved, the dealstage property options (if saved) or the stage ids stand in for labels."""
    stage_labels = stage_labels or {}
    by_pipe: dict[str, dict] = {}
    for raw in deals.values():
        p = raw.get("properties") or {}
        pid = str(p.get("pipeline") or "default")
        pl = by_pipe.setdefault(pid, {"id": pid, "label": pid, "stages": []})
        sid = p.get("dealstage")
        if sid and not any(s["id"] == str(sid) for s in pl["stages"]):
            pl["stages"].append({"id": str(sid), "label": stage_labels.get(str(sid), str(sid))})
    return list(by_pipe.values())


def synth_owners(deals: dict[str, dict], engagements: dict[str, dict[str, dict]]) -> list[dict]:
    ids: set[str] = set()
    for raw in deals.values():
        oid = (raw.get("properties") or {}).get("hubspot_owner_id")
        if oid:
            ids.add(str(oid))
    for kind in engagements.values():
        for raw in kind.values():
            oid = (raw.get("properties") or {}).get("hubspot_owner_id")
            if oid:
                ids.add(str(oid))
    return [{"id": oid, "email": None, "firstName": None, "lastName": f"Owner {oid}", "archived": False} for oid in sorted(ids)]


def build(store: Store, cfg: Config, folder: Path, log=None) -> dict:
    log = log or (lambda msg: None)
    started = time.time()
    loaded = load_dir(folder)
    objects = loaded["objects"]
    warnings: list[str] = []
    if not objects["deals"]:
        raise ValueError(f"no HubSpot deals found in {folder}; save the search_crm_objects reply for deals as deals-1.json there first")
    hs_cfg = cfg.get("sources.hubspot") or {}
    ctx = _Context(cfg)
    pipelines = loaded["pipelines"] or synth_pipelines(objects["deals"], loaded["stageLabels"])
    if not loaded["pipelines"] and not loaded["stageLabels"]:
        warnings.append("pipelines were not saved, so stage labels are stage ids; save the get_properties reply for dealstage as properties-dealstage.json for real labels")
    configured_pipelines, unmapped = register_pipelines(ctx, cfg, hs_cfg, pipelines, warnings, log)
    deal_ids = deals_in_window(objects["deals"], cfg, configured_pipelines)
    log(f"deals: {len(deal_ids)} in window of {len(objects['deals'])} saved")
    deals_raw = {did: objects["deals"][did] for did in deal_ids}

    def table(from_type: str, to_type: str) -> dict[str, list[dict]]:
        return loaded["assoc"].get((from_type, to_type), {})

    assoc = {to: {did: table("deals", to).get(did, []) for did in deal_ids} for to in ("contacts", "companies", *ENGAGEMENT_TYPES)}
    # engagements that were saved but not associated to a deal by any file: leave them out (unlinked is the linker's job)
    eng_contacts = {kind: {oid: [str(e.get("toObjectId")) for e in table(kind, "contacts").get(oid, [])] for oid in objects[kind]}
                    for kind in ENGAGEMENT_TYPES}
    contact_company: dict[str, Optional[str]] = {}
    for cid in objects["contacts"]:
        tos = table("contacts", "companies").get(cid, [])
        primary = None
        for a in tos:
            types = a.get("associationTypes") or []
            if any(str(t.get("typeId")) == "1" for t in types if isinstance(t, dict)):
                primary = str(a.get("toObjectId"))
                break
        if primary is None and tos:
            primary = str(tos[0].get("toObjectId"))
        contact_company[cid] = primary
    owners = loaded["owners"] or synth_owners(deals_raw, {k: objects[k] for k in ENGAGEMENT_TYPES})
    if not loaded["owners"]:
        warnings.append("owners were not saved, so reps have ids but no names or emails; save the search_owners reply as owners-1.json")
    missing_assoc = [did for did in deal_ids if not any(assoc[t].get(did) for t in ENGAGEMENT_TYPES)]
    if missing_assoc and len(missing_assoc) == len(deal_ids):
        warnings.append("no deal-to-engagement associations were saved, so no interactions are attached; fetch deals with associations "
                        "(calls, emails, meetings, notes) or save the association replies as associations-deals-<type>.json")
    built = assemble_and_save(store, cfg, ctx, deal_ids=deal_ids, deals_raw=deals_raw, assoc=assoc, objects=objects,
                              eng_contacts=eng_contacts, contact_company=contact_company, owners=owners,
                              warnings=warnings, log=log)
    counts = built["counts"]
    return {
        "ok": True, "source": "hubspot-cache", "folder": str(folder), "route": "connector",
        "window": {"from": cfg.window[0], "to": cfg.window[1]},
        "saved": {k: len(v) for k, v in objects.items()},
        "counts": {"deals": len(built["deals"]), "contacts": len(built["contacts"]), "companies": len(built["companies"]),
                   "reps": len(built["reps"]), "interactions": counts, "links": len(built["links"])},
        "unmappedStages": unmapped, "filesRead": len(loaded["read"]), "unknownObjects": loaded["unknown"],
        "warnings": warnings, "validation": built["validation"], "wrote": built["wrote"],
        "read": loaded["read"], "durationMs": int((time.time() - started) * 1000),
    }


def _text(s: dict) -> str:
    c = s["counts"]
    lines = [f"Imported HubSpot connector cache {s['folder']} for window {s['window']['from']} to {s['window']['to']}",
             f"  deals: {c['deals']}   contacts: {c['contacts']}   companies: {c['companies']}   reps: {c['reps']}",
             "  interactions: " + ", ".join(f"{k} {v}" for k, v in c["interactions"].items()) + f"   links: {c['links']}",
             f"  files read: {s['filesRead']}, objects saved: " + ", ".join(f"{k} {v}" for k, v in s["saved"].items() if v)]
    if s.get("unmappedStages"):
        lines.append("  stages without a phase mapping (run doctor, then config set stagePhases.<id> <phase>):")
        for u in s["unmappedStages"]:
            lines.append(f"    {u['stageId']} ({u['label']}) in pipeline {u['pipelineId']}: suggested {u['suggestedPhase']}")
    for w in s.get("warnings") or []:
        lines.append(f"  warning: {w}")
    return "\n".join(lines)


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    folder = Path(getattr(args, "dir", None) or (store.home / DEFAULT_DIR)).expanduser()
    if not folder.is_dir():
        msg = f"no connector cache at {folder}; the setup or daily-sync skill saves HubSpot tool replies there first"
        if ctx.get("json"):
            print(json.dumps({"ok": False, "error": msg}))
        else:
            print(msg, file=sys.stderr)
        return 1
    cfg = store.config
    try:
        summary = build(store, cfg, folder, log=lambda m: print(f"  {m}", file=sys.stderr))
    except ValueError as exc:
        if ctx.get("json"):
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            print(f"error: {exc}", file=sys.stderr)
        ctx["summary"] = {"read": [str(folder)], "wrote": [], "notes": str(exc)}
        return 1
    cfg.set("sources.hubspot.route", "connector")
    store.save_config()
    ctx["summary"] = {"read": summary["read"], "wrote": summary["wrote"],
                      "notes": f"{summary['counts']['deals']} deals, {sum(summary['counts']['interactions'].values())} interactions from {summary['filesRead']} files"}
    if ctx.get("json"):
        print(json.dumps({k: v for k, v in summary.items() if k != "read"}, ensure_ascii=False, indent=2))
    else:
        print(_text(summary))
    return 0
