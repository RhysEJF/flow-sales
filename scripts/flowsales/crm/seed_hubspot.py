#!/usr/bin/env python3
"""Seed a HubSpot developer test account with the local demo dataset (canonical records in data/).

    python3 scripts/flowsales/crm/seed_hubspot.py --home DIR [--dry-run] [--wipe] [--json] [--rate 4]

This is the one script in FlowSales that writes to HubSpot. It is meant for a developer test account
(docs/hubspot.md section 2) and needs the write scopes listed there. Idempotent: every created object is
recorded in cache/hubspot/seed_map.json (local id -> HubSpot id) and skipped on the next run; --wipe archives
everything the map knows about and clears it.

Order: companies, contacts (associated to their company), deals (created in their first stage, associated to
contacts and company, then PATCHed through stageHistory in order), then calls, emails, meetings and notes with
back-dated hs_timestamp and inline associations to the deal and its contacts.

Association type ids (HubSpot-defined, research doc section 2.4): contact->company primary 1, deal->contact 3,
deal->company primary 5, call->deal 206, email->deal 210, meeting->deal 212, note->deal 214, call->contact 194,
email->contact 198, meeting->contact 200, note->contact 202.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

if __package__ in (None, ""):  # executed as a script: make `flowsales` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from flowsales.config import Config, resolve_hubspot_token  # noqa: E402
from flowsales.crm.hubspot import (  # noqa: E402
    ASSOCIATION_TYPE_IDS, DEFAULT_BASE_URL, HubSpotClient, HubSpotError, ScopeError, parse_iso, to_iso,
)
from flowsales.store import Store, resolve_home  # noqa: E402

SEED_MAP = "cache/hubspot/seed_map.json"
TEXT_LIMIT = 65000  # hs_note_body caps at 65,536 characters; keep other text fields under the same bound

ENGAGEMENT_OBJECT = {"call": "calls", "email": "emails", "meeting": "meetings", "note": "notes", "transcript": "calls"}
TO_DEAL = {"calls": 206, "emails": 210, "meetings": 212, "notes": 214}
TO_CONTACT = {"calls": 194, "emails": 198, "meetings": 200, "notes": 202}
DEAL_TO_CONTACT = ASSOCIATION_TYPE_IDS[("deals", "contacts")]           # 3
DEAL_TO_COMPANY_PRIMARY = ASSOCIATION_TYPE_IDS[("deals", "companies", "primary")]   # 5
CONTACT_TO_COMPANY_PRIMARY = ASSOCIATION_TYPE_IDS[("contacts", "companies", "primary")]  # 1

WRITE_SCOPES = [
    "crm.objects.companies.write", "crm.objects.contacts.write", "crm.objects.deals.write", "sales-email-read",
]


def _assoc(to_id: str, type_id: int) -> dict:
    return {"to": {"id": str(to_id)}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": int(type_id)}]}


def _local(id_: str, prefix: str) -> str:
    """Strip a canonical prefix (c:, co:, rep:, hs:, demo:) for display."""
    return id_.split(":", 1)[1] if ":" in id_ else id_


def _clip(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return text if len(text) <= TEXT_LIMIT else text[:TEXT_LIMIT - 20] + "\n[truncated]"


def _epoch_iso(value: Optional[str]) -> Optional[str]:
    d = parse_iso(value)
    return to_iso(d) if d else None


class Seeder:
    def __init__(self, store: Store, client: Optional[HubSpotClient], dry_run: bool, log=print):
        self.store = store
        self.client = client
        self.dry_run = dry_run
        self.log = log
        self.map: dict = store.read_json(SEED_MAP, None) or {"version": 1, "hubId": None, "objects": {}, "stages": {}}
        self.owner_for_rep: dict[str, Optional[str]] = {}
        self.default_owner: Optional[str] = None
        self.stage_map: dict[str, Optional[str]] = {}
        self.pipeline_id: Optional[str] = None
        self.first_stage: Optional[str] = None
        self.disposition_connected: Optional[str] = None
        self.created = {"companies": 0, "contacts": 0, "deals": 0, "calls": 0, "emails": 0, "meetings": 0, "notes": 0}
        self.skipped = 0
        self.stage_patches = 0
        self.errors: list[str] = []
        self.plan: list[str] = []

    # ---------- map ----------
    def hs_id(self, local_id: str) -> Optional[str]:
        entry = self.map["objects"].get(local_id)
        return entry.get("hubspotId") if entry else None

    def remember(self, local_id: str, object_type: str, hubspot_id: str) -> None:
        self.map["objects"][local_id] = {"type": object_type, "hubspotId": str(hubspot_id), "at": to_iso(_dt.datetime.now(_dt.timezone.utc))}
        self.save_map()

    def save_map(self) -> None:
        if not self.dry_run:
            self.store.write_json(SEED_MAP, self.map)

    # ---------- account discovery ----------
    def discover(self, cfg: Config, reps: list[dict]) -> None:
        if self.client is None:
            self.log("no token: dry run without account lookups (owners and stages shown as local values)")
            self.default_owner = None
            return
        info = self.client.token_info() or {}
        self.map["hubId"] = info.get("hubId")
        owners = self.client.owners()
        by_email = {str(o.get("email") or "").lower(): str(o.get("id")) for o in owners if o.get("email")}
        by_name = {f"{o.get('firstName', '')} {o.get('lastName', '')}".strip().lower(): str(o.get("id")) for o in owners}
        me = self.client.owner_by_user_id(info.get("userId")) if info.get("userId") is not None else None
        self.default_owner = str(me.get("id")) if me else (str(owners[0].get("id")) if owners else None)
        for rep in reps:
            rid = rep.get("id")
            email = str(rep.get("email") or "").lower()
            name = str(rep.get("name") or "").strip().lower()
            self.owner_for_rep[rid] = by_email.get(email) or by_name.get(name) or self.default_owner
        matched = sum(1 for r in reps if self.owner_for_rep.get(r.get("id")) not in (None, self.default_owner))
        self.log(f"account {self.map['hubId']}: {len(owners)} owners, {matched}/{len(reps)} local reps matched, "
                 f"others assigned to owner {self.default_owner}")

        pipelines = self.client.pipelines("deals")
        pipeline = next((p for p in pipelines if str(p.get("id")) == "default"), pipelines[0] if pipelines else None)
        if not pipeline:
            raise HubSpotError("the account has no deal pipeline")
        self.pipeline_id = str(pipeline.get("id"))
        stages = sorted(pipeline.get("stages") or [], key=lambda s: s.get("displayOrder", 0))
        self.first_stage = str(stages[0].get("id")) if stages else None
        by_id = {str(s.get("id")): str(s.get("id")) for s in stages}
        by_label = {str(s.get("label") or "").lower(): str(s.get("id")) for s in stages}
        by_phase: dict[str, str] = {}
        for s in stages:
            phase = cfg.phase_for_stage(str(s.get("id")), s.get("label"))
            by_phase.setdefault(phase, str(s.get("id")))
        self._stage_lookup = (by_id, by_label, by_phase)
        self.log(f"pipeline {self.pipeline_id}: {len(stages)} stages")

        try:
            disp = self.client.get("/calling/v1/dispositions") or []
            for d in disp if isinstance(disp, list) else []:
                if str(d.get("label", "")).lower() == "connected":
                    self.disposition_connected = d.get("id")
        except HubSpotError:
            self.disposition_connected = None

    def stage_for(self, entry: dict) -> Optional[str]:
        """Map a local stage history entry to a stage id in the target pipeline."""
        if self.client is None:
            return entry.get("stage")
        by_id, by_label, by_phase = self._stage_lookup
        sid = str(entry.get("stage") or "")
        if sid in by_id:
            return sid
        label = str(entry.get("label") or "").lower()
        if label in by_label:
            return by_label[label]
        phase = entry.get("phase")
        return by_phase.get(phase) if phase else None

    def owner_for(self, rep_id: Optional[str]) -> Optional[str]:
        if rep_id and rep_id in self.owner_for_rep:
            return self.owner_for_rep[rep_id]
        return self.default_owner

    # ---------- create helpers ----------
    def create(self, local_id: str, object_type: str, properties: dict, associations: Optional[list[dict]] = None,
               label: str = "") -> Optional[str]:
        existing = self.hs_id(local_id)
        if existing:
            self.skipped += 1
            return existing
        props = {k: v for k, v in properties.items() if v not in (None, "")}
        if self.dry_run:
            self.plan.append(f"create {object_type} {label or local_id} ({len(props)} properties, {len(associations or [])} associations)")
            return f"dry-{object_type}-{local_id}"
        try:
            res = self.client.create(object_type, props, associations)  # type: ignore[union-attr]
        except HubSpotError as exc:
            self.errors.append(f"{object_type} {local_id}: {exc}")
            self.log(f"  failed {object_type} {label or local_id}: {exc}")
            return None
        hid = str(res.get("id"))
        self.remember(local_id, object_type, hid)
        self.created[object_type] += 1
        return hid

    # ---------- phases ----------
    def seed_companies(self, companies: list[dict]) -> None:
        self.log(f"companies: {len(companies)}")
        for co in companies:
            self.create(co["id"], "companies", {"name": co.get("name"), "domain": co.get("domain")}, label=co.get("name") or co["id"])

    def seed_contacts(self, contacts: list[dict]) -> None:
        self.log(f"contacts: {len(contacts)}")
        for c in contacts:
            name = (c.get("name") or "").strip()
            first, _, last = name.partition(" ")
            assoc = []
            if c.get("companyId") and self.hs_id(c["companyId"]):
                assoc.append(_assoc(self.hs_id(c["companyId"]), CONTACT_TO_COMPANY_PRIMARY))
            self.create(c["id"], "contacts", {"email": c.get("email"), "firstname": first or None, "lastname": last or None,
                                              "jobtitle": c.get("title")}, assoc, label=c.get("email") or c["id"])

    def seed_deals(self, deals: list[dict]) -> None:
        self.log(f"deals: {len(deals)}")
        for d in deals:
            history = list(d.get("stageHistory") or [])
            if not history and d.get("stage"):
                history = [{"stage": d.get("stage"), "label": d.get("stageLabel"), "phase": d.get("phase"), "at": d.get("createdAt")}]
            target_stages = [s for s in (self.stage_for(h) for h in history) if s]
            first = target_stages[0] if target_stages else self.first_stage
            assoc = [_assoc(self.hs_id(c), DEAL_TO_CONTACT) for c in d.get("contactIds") or [] if self.hs_id(c)]
            if d.get("companyId") and self.hs_id(d["companyId"]):
                assoc.append(_assoc(self.hs_id(d["companyId"]), DEAL_TO_COMPANY_PRIMARY))
            props = {"dealname": d.get("name"), "amount": d.get("amount"), "pipeline": self.pipeline_id or d.get("pipeline"),
                     "dealstage": first, "hubspot_owner_id": self.owner_for(d.get("ownerId"))}
            if d.get("currency"):
                props["deal_currency_code"] = d["currency"]
            hid = self.create(d["id"], "deals", props, assoc, label=d.get("name") or d["id"])
            if not hid:
                continue
            done: list[str] = list(self.map["stages"].get(d["id"], [])) or ([first] if first else [])
            remaining = target_stages[len(done):] if target_stages[:len(done)] == done else target_stages[1:]
            for i, sid in enumerate(remaining):
                props = {"dealstage": sid}
                is_last = i == len(remaining) - 1
                if is_last and d.get("outcome") in ("won", "lost") and d.get("closedAt"):
                    props["closedate"] = _epoch_iso(d["closedAt"])
                if self.dry_run:
                    self.plan.append(f"patch deal {d.get('name')} dealstage -> {sid}")
                    continue
                try:
                    self.client.update("deals", hid, props)  # type: ignore[union-attr]
                    self.stage_patches += 1
                    done.append(sid)
                    self.map["stages"][d["id"]] = done
                    self.save_map()
                except HubSpotError as exc:
                    self.errors.append(f"deal {d['id']} stage {sid}: {exc}")
                    self.log(f"  failed stage patch {d.get('name')} -> {sid}: {exc}")
                    break

    def seed_interactions(self, deals: list[dict], contacts_by_id: dict[str, dict]) -> None:
        total = 0
        for d in deals:
            deal_hs = self.hs_id(d["id"])
            if not deal_hs:
                continue
            items = sorted(self.store.load_interactions(d["id"]), key=lambda i: i.get("at") or "")
            total += len(items)
            contact_emails = {str((contacts_by_id.get(c) or {}).get("email") or "").lower(): c for c in d.get("contactIds") or []}
            for it in items:
                object_type = ENGAGEMENT_OBJECT.get(it.get("type") or "note", "notes")
                assoc = [_assoc(deal_hs, TO_DEAL[object_type])]
                linked: set[str] = set()
                for p in it.get("participants") or []:
                    cid = contact_emails.get(str(p.get("email") or "").lower())
                    if cid and cid not in linked and self.hs_id(cid):
                        linked.add(cid)
                        assoc.append(_assoc(self.hs_id(cid), TO_CONTACT[object_type]))
                if not linked:
                    for cid in d.get("contactIds") or []:
                        if self.hs_id(cid):
                            assoc.append(_assoc(self.hs_id(cid), TO_CONTACT[object_type]))
                props = self.engagement_properties(object_type, it, d, contacts_by_id)
                self.create(it["id"], object_type, props, assoc, label=f"{it.get('type')} {it.get('title') or it['id']}")
        self.log(f"interactions: {total}")

    def engagement_properties(self, object_type: str, it: dict, deal: dict, contacts_by_id: dict[str, dict]) -> dict:
        at = _epoch_iso(it.get("at")) or _epoch_iso(deal.get("createdAt"))
        owner = self.owner_for(it.get("repId") or deal.get("ownerId"))
        body = it.get("body") or ""
        if it.get("type") == "transcript" and not body and it.get("transcript"):
            body = "\n".join(f"{s.get('speaker', 'Unknown')}: {s.get('text', '')}" for s in it["transcript"])
        props: dict[str, Any] = {"hs_timestamp": at, "hubspot_owner_id": owner}
        if object_type == "calls":
            direction = {"inbound": "INBOUND", "outbound": "OUTBOUND"}.get(it.get("direction") or "", "OUTBOUND")
            props.update({"hs_call_title": it.get("title") or "Call", "hs_call_body": _clip(body),
                          "hs_call_direction": direction, "hs_call_status": "COMPLETED",
                          "hs_call_duration": str(int((it.get("durationSec") or 0) * 1000)) if it.get("durationSec") else None,
                          "hs_call_recording_url": it.get("recordingUrl"), "hs_call_disposition": self.disposition_connected})
        elif object_type == "emails":
            outbound = (it.get("direction") or "outbound") != "inbound"
            props.update({"hs_email_direction": "EMAIL" if outbound else "INCOMING_EMAIL", "hs_email_subject": it.get("title") or "(no subject)",
                          "hs_email_text": _clip(body), "hs_email_status": "SENT",
                          "hs_email_headers": self.email_headers(it, outbound)})
        elif object_type == "meetings":
            start = at
            end = None
            if start and it.get("durationSec"):
                d = parse_iso(start)
                end = to_iso(d + _dt.timedelta(seconds=int(it["durationSec"]))) if d else None
            props.update({"hs_meeting_title": it.get("title") or "Meeting", "hs_meeting_body": _clip(body),
                          "hs_internal_meeting_notes": _clip(it.get("notes")), "hs_meeting_start_time": start,
                          "hs_meeting_end_time": end, "hs_meeting_outcome": "COMPLETED"})
        else:
            text = body if body else (it.get("title") or "")
            if it.get("title") and it["title"] not in text:
                text = f"{it['title']}\n\n{text}"
            props["hs_note_body"] = _clip(text) or "(empty)"
        return props

    @staticmethod
    def email_headers(it: dict, outbound: bool) -> Optional[str]:
        reps = [p for p in it.get("participants") or [] if p.get("role") == "rep" and p.get("email")]
        buyers = [p for p in it.get("participants") or [] if p.get("role") != "rep" and p.get("email")]
        senders, receivers = (reps, buyers) if outbound else (buyers, reps)
        if not senders or not receivers:
            return None

        def person(p: dict) -> dict:
            name = (p.get("name") or "").strip()
            first, _, last = name.partition(" ")
            return {"email": p["email"], "firstName": first or None, "lastName": last or None}

        return json.dumps({"from": person(senders[0]), "to": [person(p) for p in receivers],
                           "cc": [person(p) for p in senders[1:]], "bcc": []})

    # ---------- wipe ----------
    def wipe(self) -> dict:
        by_type: dict[str, list[str]] = {}
        for local_id, entry in self.map["objects"].items():
            by_type.setdefault(entry["type"], []).append(entry["hubspotId"])
        order = ["calls", "emails", "meetings", "notes", "deals", "contacts", "companies"]
        archived = {t: 0 for t in order}
        for t in order:
            ids = by_type.get(t) or []
            if not ids:
                continue
            self.log(f"archiving {len(ids)} {t}")
            if self.dry_run:
                self.plan.append(f"archive {len(ids)} {t}")
                archived[t] = len(ids)
                continue
            try:
                self.client.batch_archive(t, ids)  # type: ignore[union-attr]
                archived[t] = len(ids)
            except HubSpotError as exc:
                self.errors.append(f"archive {t}: {exc}")
                self.log(f"  failed archiving {t}: {exc}")
                continue
        if not self.dry_run and not self.errors:
            self.map = {"version": 1, "hubId": self.map.get("hubId"), "objects": {}, "stages": {}}
            self.save_map()
        return archived


def seed(store: Store, cfg: Config, client: Optional[HubSpotClient], dry_run: bool = False, wipe: bool = False,
         log=print) -> dict:
    seeder = Seeder(store, client, dry_run, log=log)
    started = time.time()
    if wipe:
        archived = seeder.wipe()
        return {"ok": not seeder.errors, "mode": "wipe", "dryRun": dry_run, "archived": archived, "errors": seeder.errors,
                "plan": seeder.plan, "requests": client.request_count if client else 0,
                "durationMs": int((time.time() - started) * 1000)}
    deals = store.load_deals()
    contacts = store.load_contacts()
    companies = store.load_companies()
    reps = store.load_reps()
    if not deals:
        raise SystemExit(f"no deals in {store.data_dir}; run `fs.py import demo` first")
    seeder.discover(cfg, reps)
    seeder.seed_companies(companies)
    seeder.seed_contacts(contacts)
    seeder.seed_deals(deals)
    seeder.seed_interactions(deals, {c["id"]: c for c in contacts})
    return {"ok": not seeder.errors, "mode": "seed", "dryRun": dry_run, "hubId": seeder.map.get("hubId"),
            "created": seeder.created, "stagePatches": seeder.stage_patches, "skippedExisting": seeder.skipped,
            "mapped": len(seeder.map["objects"]), "errors": seeder.errors, "plan": seeder.plan,
            "requests": client.request_count if client else 0, "durationMs": int((time.time() - started) * 1000)}


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    if not store.exists():
        print(f"No FlowSales store at {store.home}. Run: fs.py init, then fs.py import demo", file=sys.stderr)
        return 1
    cfg = store.config
    dry_run = bool(getattr(args, "dry_run", False))
    wipe = bool(getattr(args, "wipe", False))
    token = resolve_hubspot_token(cfg, store.home)
    client: Optional[HubSpotClient] = ctx.get("hubspot_client")
    if client is None and token:
        hs_cfg = cfg.get("sources.hubspot") or {}
        client = HubSpotClient(token, base_url=hs_cfg.get("baseUrl") or DEFAULT_BASE_URL,
                               rate_per_sec=float(getattr(args, "rate", None) or hs_cfg.get("requestsPerSecond") or 4.0))
    if client is None and not dry_run:
        print("No HubSpot token found (HUBSPOT_ACCESS_TOKEN, CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN or secrets.json). "
              "Use --dry-run to preview without an account.", file=sys.stderr)
        return 1
    log = (lambda msg: print(msg, file=sys.stderr)) if ctx.get("json") else print
    try:
        result = seed(store, cfg, client, dry_run=dry_run, wipe=wipe, log=log)
    except ScopeError as exc:
        print(f"missing scopes: {', '.join(exc.required_scopes)}. Seeding needs: {', '.join(WRITE_SCOPES)}", file=sys.stderr)
        store.log_run("seed hubspot", {"dryRun": dry_run, "wipe": wipe}, False, ctx["started"], notes=str(exc))
        return 2
    except HubSpotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        store.log_run("seed hubspot", {"dryRun": dry_run, "wipe": wipe}, False, ctx["started"], notes=str(exc))
        return 2
    store.log_run("seed hubspot", {"dryRun": dry_run, "wipe": wipe}, result["ok"], ctx["started"],
                  wrote=[] if dry_run else [SEED_MAP, "hubspot:writes"], notes=f"{result['requests']} requests")
    if ctx.get("json"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if dry_run:
            print("\n".join(result["plan"]) if result["plan"] else "nothing to do")
        print(json.dumps({k: v for k, v in result.items() if k != "plan"}, ensure_ascii=False))
    return 0 if result["ok"] else 2


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Seed a HubSpot developer test account with the local demo dataset")
    p.add_argument("--home", help="store directory (default $FLOW_SALES_HOME or ./.flow-sales)")
    p.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    p.add_argument("--wipe", action="store_true", help="archive everything the seed map knows about")
    p.add_argument("--json", action="store_true")
    p.add_argument("--rate", type=float, default=None, help="requests per second (default 4)")
    args = p.parse_args(argv)
    home = resolve_home(args.home)
    store = Store(home)
    ctx = {"store": store, "home": home, "json": args.json, "started": time.time()}
    return run(ctx, args)


if __name__ == "__main__":
    sys.exit(main())
