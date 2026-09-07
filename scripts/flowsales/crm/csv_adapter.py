"""`fs.py import csv --deals <file> --interactions <file>`: the two-file CSV port for any CRM.

Column contract and export tips are in docs/other-crms.md; sample files in docs/examples/.
Ids become `csv:<id>`, reps `rep:<email>`, contacts `c:<email>`, companies `co:<domain>`.
Interactions without a deal_id go to _unlinked for the linker. Standard library only.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

from ..config import Config
from ..schema.validate import DIRECTIONS, INTERACTION_TYPES, validate_records
from ..store import Store
from ..util import email_domain, parse_iso, to_iso
from .transcripts_folder import parse_person, parse_speaker_lines

DEAL_COLUMNS = ["id", "name", "amount", "currency", "pipeline", "stage", "stage_label", "outcome", "created_at", "closed_at",
                "owner_email", "owner_name", "contact_emails", "contact_names", "company_name", "company_domain"]
DEAL_OPTIONAL = ["stage_history"]
INTERACTION_COLUMNS = ["id", "deal_id", "type", "direction", "at", "duration_sec", "title", "body", "participants", "rep_email"]
CLOSED_STAGE_LABELS = {"won": ("closedwon", "Closed Won"), "lost": ("closedlost", "Closed Lost")}


def _split(value: Optional[str]) -> list[str]:
    return [v.strip() for v in (value or "").split(";") if v.strip()]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "unknown"


def _prefixed(raw: str, prefix: str = "csv:") -> str:
    raw = raw.strip()
    return raw if re.match(r"^(hs|csv|demo|granola|tx):", raw) else f"{prefix}{raw}"


def _read_rows(path: Path, required: list[str], label: str, errors: list[str]) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in required if c not in headers]
        if missing:
            errors.append(f"{label}: missing column(s) {', '.join(missing)}; found {', '.join(headers) or 'nothing'}")
            return []
        rows = []
        for n, row in enumerate(reader, start=2):
            clean = {(k or "").strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            clean["_line"] = n
            rows.append(clean)
        return rows


def _iso(value: Optional[str], field: str, label: str, errors: list[str], required: bool = False) -> Optional[str]:
    if not value:
        if required:
            errors.append(f"{label}: {field} is required")
        return None
    parsed = parse_iso(value.replace(" ", "T", 1) if re.match(r"^\d{4}-\d{2}-\d{2} \d", value) else value)
    if parsed is None:
        errors.append(f"{label}: {field} is not an ISO 8601 date: {value!r}")
        return None
    return to_iso(parsed)


def _stage_history(row: dict, cfg: Config, created: Optional[str], closed: Optional[str], stage: str, label: str, phase: str, outcome: str,
                   row_label: str, errors: list[str]) -> list[dict]:
    raw = row.get("stage_history")
    if raw:
        history = []
        for item in _split(raw):
            if "@" not in item:
                errors.append(f"{row_label}: stage_history entries look like stage@ISO, got {item!r}")
                continue
            sid, at = item.rsplit("@", 1)
            at_iso = _iso(at, "stage_history", row_label, errors, required=True)
            if at_iso:
                history.append({"stage": sid.strip(), "label": sid.strip(), "phase": cfg.phase_for_stage(sid.strip()), "at": at_iso})
        history.sort(key=lambda h: h["at"])
        if history:
            return history
    if closed and outcome in CLOSED_STAGE_LABELS and created:
        return [{"stage": "created", "label": "Created", "phase": "discovery", "at": created},
                {"stage": stage, "label": label, "phase": phase, "at": closed}]
    return [{"stage": stage, "label": label, "phase": phase, "at": created}] if created else []


def load_deals(path: Path, cfg: Config, errors: list[str]) -> tuple[list[dict], dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Deal rows -> (deals, reps by id, contacts by id, companies by id)."""
    rows = _read_rows(path, ["id", "name"], f"deals file {path.name}", errors)
    deals: list[dict] = []
    reps: dict[str, dict] = {}
    contacts: dict[str, dict] = {}
    companies: dict[str, dict] = {}
    for row in rows:
        label = f"{path.name} line {row['_line']}"
        if not row.get("id"):
            errors.append(f"{label}: id is empty")
            continue
        deal_id = _prefixed(row["id"])
        amount = None
        if row.get("amount"):
            try:
                amount = float(re.sub(r"[^\d.\-]", "", row["amount"]))
            except ValueError:
                errors.append(f"{label}: amount is not a number: {row['amount']!r}")
        created = _iso(row.get("created_at"), "created_at", label, errors, required=True)
        closed = _iso(row.get("closed_at"), "closed_at", label, errors)
        stage = row.get("stage") or ""
        stage_label = row.get("stage_label") or stage
        outcome = (row.get("outcome") or "").lower()
        phase = cfg.phase_for_stage(stage or None, stage_label or None) if (stage or stage_label) else "evaluation"
        if outcome not in ("won", "lost", "open"):
            outcome = "won" if phase == "won" else "lost" if phase == "lost" else "open"
        if outcome in CLOSED_STAGE_LABELS and phase not in ("won", "lost"):
            phase = outcome
            if not stage:
                stage, stage_label = CLOSED_STAGE_LABELS[outcome]
        owner_email = (row.get("owner_email") or "").lower()
        owner_id = f"rep:{owner_email}" if owner_email else None
        if owner_id:
            reps.setdefault(owner_id, {"id": owner_id, "name": row.get("owner_name") or owner_email.split("@")[0], "email": owner_email, "source": "csv"})
        domain = (row.get("company_domain") or "").lower() or None
        company_name = row.get("company_name") or (domain or "")
        company_id = f"co:{domain or _slug(company_name)}" if (domain or company_name) else None
        if company_id:
            companies.setdefault(company_id, {"id": company_id, "name": company_name or domain, "domain": domain or ""})
        emails = [e.lower() for e in _split(row.get("contact_emails"))]
        names = _split(row.get("contact_names"))
        contact_ids = []
        for i, email in enumerate(emails):
            cid = f"c:{email}"
            contact_ids.append(cid)
            contacts.setdefault(cid, {"id": cid, "name": names[i] if i < len(names) else email.split("@")[0], "email": email, "title": None,
                                      "companyId": company_id, "buyingRole": None})
        deals.append({
            "id": deal_id, "source": "csv", "name": row["name"], "amount": amount, "currency": (row.get("currency") or "").upper() or None,
            "pipeline": row.get("pipeline") or "default", "stage": stage, "stageLabel": stage_label, "phase": phase,
            "stageHistory": _stage_history(row, cfg, created, closed, stage, stage_label, phase, outcome, label, errors),
            "outcome": outcome, "createdAt": created, "closedAt": closed, "ownerId": owner_id, "contactIds": contact_ids,
            "companyId": company_id, "companyDomain": domain, "meta": {"csv": {"file": path.name, "line": row["_line"], "rawId": row["id"]}},
        })
    return deals, reps, contacts, companies


def load_interactions(path: Path, deals_by_id: dict[str, dict], reps: dict[str, dict], internal: set[str], errors: list[str]) -> list[dict]:
    rows = _read_rows(path, ["id", "type", "at"], f"interactions file {path.name}", errors)
    out: list[dict] = []
    for row in rows:
        label = f"{path.name} line {row['_line']}"
        if not row.get("id"):
            errors.append(f"{label}: id is empty")
            continue
        itype = (row.get("type") or "").lower()
        if itype not in INTERACTION_TYPES:
            errors.append(f"{label}: type must be one of {', '.join(INTERACTION_TYPES)}, got {itype!r}")
            continue
        direction = (row.get("direction") or "").lower()
        if direction not in DIRECTIONS:
            direction = "internal" if itype == "note" else "unknown"
        at = _iso(row.get("at"), "at", label, errors, required=True)
        duration = None
        if row.get("duration_sec"):
            try:
                duration = int(float(row["duration_sec"]))
            except ValueError:
                errors.append(f"{label}: duration_sec is not a number: {row['duration_sec']!r}")
        deal_id = _prefixed(row["deal_id"]) if row.get("deal_id") else None
        rep_email = (row.get("rep_email") or "").lower()
        participants = []
        for raw in _split(row.get("participants")):
            person = parse_person(raw)
            if not person:
                continue
            domain = email_domain(person.get("email"))
            role = "rep" if (person.get("email") and (person["email"] == rep_email or (domain and domain in internal))) else ("buyer" if person.get("email") else "unknown")
            participants.append({"name": person.get("name") or "", "email": person.get("email"), "role": role})
        rep_id = f"rep:{rep_email}" if rep_email else None
        if not rep_id:
            internal_p = next((p for p in participants if p["role"] == "rep" and p.get("email")), None)
            rep_id = f"rep:{internal_p['email']}" if internal_p else (deals_by_id.get(deal_id or "", {}).get("ownerId"))
        if rep_id and rep_id not in reps:
            reps[rep_id] = {"id": rep_id, "name": rep_id.split(":", 1)[1].split("@")[0], "email": rep_id.split(":", 1)[1], "source": "csv"}
        body = (row.get("body") or "").replace("\r\n", "\n")
        segments = parse_speaker_lines(body) if itype in ("call", "meeting", "transcript") else []
        if segments and len(segments) < 2:
            segments = []
        out.append({
            "id": _prefixed(row["id"]), "source": "csv", "type": itype, "dealId": deal_id, "direction": direction, "at": at,
            "durationSec": duration, "title": row.get("title") or "", "body": body, "transcript": segments, "notes": None, "summary": None,
            "participants": participants, "repId": rep_id, "recordingUrl": None,
            "meta": {"csv": {"file": path.name, "line": row["_line"], "rawId": row["id"], "rawDealId": row.get("deal_id") or None}},
        })
    return out


def _emit(ctx: dict, payload: dict, text: str, err: bool = False) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text, file=sys.stderr if err else sys.stdout)


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    cfg = store.config
    deals_arg = getattr(args, "deals", None) or cfg.get("sources.csv.dealsFile")
    inter_arg = getattr(args, "interactions", None) or cfg.get("sources.csv.interactionsFile")
    if not deals_arg and not inter_arg:
        _emit(ctx, {"ok": False, "error": "no files"}, "import csv needs --deals <file> and/or --interactions <file> (see docs/other-crms.md)", err=True)
        return 1
    paths = {}
    for name, arg in (("deals", deals_arg), ("interactions", inter_arg)):
        if arg:
            p = Path(arg).expanduser().resolve()
            if not p.is_file():
                _emit(ctx, {"ok": False, "error": f"{name} file not found: {p}"}, f"{name} file not found: {p}", err=True)
                return 1
            paths[name] = p

    errors: list[str] = []
    warnings: list[str] = []
    existing_deals = {d["id"]: d for d in store.load_deals()}
    deals: list[dict] = []
    reps: dict[str, dict] = {r["id"]: r for r in store.load_reps()}
    contacts: dict[str, dict] = {}
    companies: dict[str, dict] = {}
    if "deals" in paths:
        deals, new_reps, contacts, companies = load_deals(paths["deals"], cfg, errors)
        reps.update(new_reps)
    deals_by_id = dict(existing_deals)
    deals_by_id.update({d["id"]: d for d in deals})
    internal = cfg.internal_domains(list(reps.values()))
    interactions: list[dict] = []
    if "interactions" in paths:
        interactions = load_interactions(paths["interactions"], deals_by_id, reps, internal, errors)
    if errors:
        for line in errors[:30]:
            print(f"  {line}", file=sys.stderr)
        _emit(ctx, {"ok": False, "errors": errors}, f"{len(errors)} problem(s) in the CSV files; nothing written", err=True)
        return 1
    errors = validate_records("deal", deals) + validate_records("rep", list(reps.values())) + validate_records("contact", list(contacts.values())) \
        + validate_records("company", list(companies.values())) + validate_records("interaction", interactions)
    if errors:
        for line in errors[:30]:
            print(f"  {line}", file=sys.stderr)
        _emit(ctx, {"ok": False, "errors": errors}, f"{len(errors)} contract violation(s); nothing written", err=True)
        return 1

    linked: dict[str, list[dict]] = {}
    unlinked: list[dict] = []
    for it in interactions:
        if it["dealId"] and it["dealId"] not in deals_by_id:
            warnings.append(f"{it['id']}: deal {it['dealId']} is not in the deals file or the store; left unlinked")
            it["meta"]["csv"]["unknownDealId"] = it["dealId"]
            it["dealId"] = None
        (linked.setdefault(it["dealId"], []) if it["dealId"] else unlinked).append(it)

    store.ensure()
    wrote: list[str] = []
    if deals:
        store.save_deals(Store.upsert(store.load_deals(), deals))
        store.save_contacts(Store.upsert(store.load_contacts(), list(contacts.values())))
        store.save_companies(Store.upsert(store.load_companies(), list(companies.values())))
        wrote += [str(store.data_dir / n) for n in ("deals.json", "contacts.json", "companies.json")]
    store.save_reps(Store.upsert(store.load_reps(), list(reps.values())))
    wrote.append(str(store.data_dir / "reps.json"))
    new_ids = {it["id"] for it in interactions}
    links = store.load_links()
    links["links"] = [l for l in links.get("links", []) if l.get("interactionId") not in new_ids]
    for deal_id, items in linked.items():
        store.save_interactions(deal_id, Store.upsert(store.load_interactions(deal_id), items))
        wrote.append(str(store.interactions_path(deal_id)))
        for it in items:
            links["links"].append({"interactionId": it["id"], "dealId": deal_id, "method": "crm-association", "confidence": 1.0, "status": "auto",
                                   "evidence": {"matchedEmails": [], "domain": None, "matchedHubspotMeeting": None, "titleHit": None},
                                   "candidates": [{"dealId": deal_id, "confidence": 1.0}], "at": ctx.get("now"), "by": "linker"})
    if interactions:
        keep = [u for u in store.load_unlinked() if u.get("id") not in new_ids]
        store.save_unlinked(keep + unlinked)
        wrote.append(str(store.interactions_dir / "_unlinked.json"))
    store.save_links(links)
    wrote.append(str(store.data_dir / "links.json"))
    if "deals" in paths:
        cfg.set("sources.csv.dealsFile", str(paths["deals"]))
    if "interactions" in paths:
        cfg.set("sources.csv.interactionsFile", str(paths["interactions"]))
    store.save_config()

    by_type: dict[str, int] = {}
    for it in interactions:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1
    by_outcome = {o: sum(1 for d in deals if d["outcome"] == o) for o in ("won", "lost", "open")}
    summary = {"ok": True, "files": {k: str(v) for k, v in paths.items()},
               "counts": {"deals": len(deals), "dealsByOutcome": by_outcome, "reps": len(reps), "contacts": len(contacts), "companies": len(companies),
                          "interactions": len(interactions), "interactionsByType": by_type, "linked": sum(len(v) for v in linked.values()),
                          "unlinked": len(unlinked), "withTranscript": sum(1 for it in interactions if it["transcript"])},
               "warnings": warnings}
    ctx["summary"] = {"read": [str(p) for p in paths.values()], "wrote": wrote,
                      "notes": f"{len(deals)} deals, {len(interactions)} interactions ({len(unlinked)} unlinked)"}
    text = [f"Imported CSV: {', '.join(f'{k} {v.name}' for k, v in paths.items())}",
            f"  deals: {len(deals)} (won {by_outcome['won']}, lost {by_outcome['lost']}, open {by_outcome['open']})   reps: {len(reps)}   contacts: {len(contacts)}   companies: {len(companies)}",
            f"  interactions: {len(interactions)} (" + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items())) + f"), linked {summary['counts']['linked']}, unlinked {len(unlinked)}, with transcript {summary['counts']['withTranscript']}"]
    text += [f"  warning: {w}" for w in warnings]
    if unlinked:
        text.append("  next: fs.py link to attach the unlinked interactions to deals")
    _emit(ctx, summary, "\n".join(text))
    return 0
