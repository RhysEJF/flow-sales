"""link: attach interactions to deals (CONTRACTS section 6).

Candidates come from data/interactions/_unlinked.json; records already inside a deal file
are never re-linked. Rules run per deal in priority order (crm-association, time-match,
email-match, domain-match, title-match) and the best rule becomes that deal's candidate.
A single top candidate at or above linking.autoAcceptConfidence is accepted ("auto");
a tie at the top or a lower score leaves the interaction in _unlinked with its candidates
and a "pending" link. Rejected pairs are never proposed again; a rejection without a deal
suppresses the interaction entirely. Internal emails never count as buyer matches.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from typing import Any, Optional

from ..config import Config
from ..store import Store
from ..util import email_domain, normalize_text, now_iso, parse_iso

METHOD_CRM = "crm-association"
METHOD_TIME = "time-match"
METHOD_EMAIL = "email-match"
METHOD_DOMAIN = "domain-match"
METHOD_TITLE = "title-match"
METHOD_MANUAL = "manual"
CONFIDENCE = {METHOD_CRM: 1.0, METHOD_TIME: 0.95, METHOD_EMAIL: 0.9, METHOD_DOMAIN: 0.7, METHOD_TITLE: 0.5, METHOD_MANUAL: 1.0}
TIME_MATCH_WINDOW = _dt.timedelta(minutes=15)
TIME_MATCH_TYPES = ("meeting", "call", "transcript")
MIN_TITLE_NAME = 3
ACCEPTED_STATUSES = ("auto", "confirmed")


def _out(ctx: dict, payload: dict, text: str) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text)


def empty_evidence() -> dict:
    return {"matchedEmails": [], "domain": None, "matchedHubspotMeeting": None, "titleHit": None}


def decide(candidates: list[dict], threshold: float) -> str:
    """auto when the top candidate clears the threshold and nothing ties with it; pending otherwise."""
    if not candidates:
        return "unmatched"
    top = candidates[0]["confidence"]
    tie = len(candidates) > 1 and abs(candidates[1]["confidence"] - top) < 1e-9
    return "auto" if top >= threshold and not tie else "pending"


def _participant_key(person: dict) -> str:
    return (person.get("email") or person.get("name") or "").strip().lower()


def union_participants(first: list[dict], second: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for person in list(first) + list(second):
        if not isinstance(person, dict):
            continue
        key = _participant_key(person)
        if key and key in seen:
            continue
        seen.add(key)
        out.append(person)
    return out


def merge_records(keep: dict, other: dict) -> dict:
    """Merge ``other`` into ``keep`` (the deal's record): body, transcript and participants from the richer one."""
    richer, poorer = (other, keep) if len(other.get("body") or "") > len(keep.get("body") or "") else (keep, other)
    for key in ("body", "transcript"):
        if richer.get(key):
            keep[key] = richer[key]
    keep["participants"] = union_participants(richer.get("participants") or [], poorer.get("participants") or [])
    for key in ("notes", "summary", "durationSec", "recordingUrl", "title", "repId"):
        if not keep.get(key) and other.get(key):
            keep[key] = other[key]
    meta = keep.get("meta") if isinstance(keep.get("meta"), dict) else {}
    keep["meta"] = meta
    meta["mergedFrom"] = other.get("id")
    merged_ids = meta.get("mergedIds") if isinstance(meta.get("mergedIds"), list) else []
    if other.get("id") and other.get("id") not in merged_ids:
        merged_ids.append(other.get("id"))
    meta["mergedIds"] = merged_ids
    return keep


class LinkContext:
    """Store contents the rules need, loaded once; mutations stay in memory until ``save``."""

    def __init__(self, store: Store, now: Optional[str] = None):
        self.store = store
        self.cfg: Config = store.config
        self.now = parse_iso(now) or _dt.datetime.now(_dt.timezone.utc)
        self.deals: dict[str, dict] = {d["id"]: d for d in store.load_deals() if d.get("id")}
        self.contacts: dict[str, dict] = {c["id"]: c for c in store.load_contacts() if c.get("id")}
        self.companies: dict[str, dict] = {c["id"]: c for c in store.load_companies() if c.get("id")}
        self.reps = store.load_reps()
        self.internal = self.cfg.internal_domains(self.reps)
        self.threshold = float(self.cfg.get("linking.autoAcceptConfidence") or 0.9)
        self.grace = _dt.timedelta(days=float(self.cfg.get("linking.timeGraceDays") or 0))
        self.links_doc = store.load_links()
        self.links: list[dict] = list(self.links_doc.get("links") or [])
        self.unlinked: list[dict] = store.load_unlinked()
        self.deal_interactions: dict[str, list[dict]] = {did: store.load_interactions(did) for did in self.deals}
        self.dirty: set[str] = set()
        self.rejected = {(l.get("interactionId"), l.get("dealId")) for l in self.links if l.get("status") == "rejected"}
        self.accepted = {l.get("interactionId"): l for l in self.links if l.get("status") in ACCEPTED_STATUSES}
        self.deal_emails = {did: self._contact_emails(d) for did, d in self.deals.items()}
        self.deal_domain = {did: self._deal_domain(d) for did, d in self.deals.items()}
        self.deal_names = {did: self._deal_names(d) for did, d in self.deals.items()}
        self.windows = {did: self._window(d) for did, d in self.deals.items()}
        self.hs_meetings = self._index_hubspot_meetings()

    # ---------- lookups ----------
    def is_internal(self, email: Optional[str]) -> bool:
        domain = email_domain(email)
        return bool(domain) and domain in self.internal

    def buyer_emails(self, inter: dict) -> set[str]:
        emails = set()
        for person in inter.get("participants") or []:
            email = (person.get("email") or "").strip().lower() if isinstance(person, dict) else ""
            if email and "@" in email and not self.is_internal(email):
                emails.add(email)
        return emails

    def _contact_emails(self, deal: dict) -> set[str]:
        emails = set()
        for cid in deal.get("contactIds") or []:
            contact = self.contacts.get(cid) or {}
            email = (contact.get("email") or "").strip().lower()
            if email and "@" in email and not self.is_internal(email):
                emails.add(email)
        return emails

    def _deal_domain(self, deal: dict) -> Optional[str]:
        domain = (deal.get("companyDomain") or "").strip().lower()
        if not domain and deal.get("companyId"):
            domain = ((self.companies.get(deal["companyId"]) or {}).get("domain") or "").strip().lower()
        if not domain or domain in self.internal:
            return None
        return domain

    def _deal_names(self, deal: dict) -> list[str]:
        names = [deal.get("name") or ""]
        if deal.get("companyId"):
            names.append((self.companies.get(deal["companyId"]) or {}).get("name") or "")
        return [n for n in names if len(n.strip()) >= MIN_TITLE_NAME]

    def _window(self, deal: dict) -> tuple[Optional[_dt.datetime], Optional[_dt.datetime]]:
        created = parse_iso(deal.get("createdAt"))
        closed = parse_iso(deal.get("closedAt"))
        start = created - self.grace if created else None
        end = closed + self.grace if closed else self.now
        return start, end

    def in_window(self, deal_id: str, at: Optional[_dt.datetime]) -> bool:
        if at is None:
            return False
        start, end = self.windows[deal_id]
        return (start is None or at >= start) and (end is None or at <= end)

    def is_rejected(self, iid: Optional[str], deal_id: Optional[str]) -> bool:
        return (iid, None) in self.rejected or (iid, deal_id) in self.rejected

    def deal_name(self, deal_id: str) -> Optional[str]:
        return (self.deals.get(deal_id) or {}).get("name")

    def _index_hubspot_meetings(self) -> list[dict]:
        index = []
        for deal_id, items in self.deal_interactions.items():
            for record in items:
                if record.get("source") != "hubspot" or record.get("type") != "meeting":
                    continue
                at = parse_iso(record.get("at"))
                if at is None:
                    continue
                index.append({"dealId": deal_id, "record": record, "at": at,
                              "emails": self.buyer_emails(record), "title": normalize_text(record.get("title") or "")})
        return index

    def find(self, iid: str) -> tuple[Optional[str], Optional[dict]]:
        """(dealId or None, record) for an interaction in _unlinked or in any deal file."""
        for record in self.unlinked:
            if record.get("id") == iid:
                return None, record
        for deal_id, items in self.deal_interactions.items():
            for record in items:
                if record.get("id") == iid:
                    return deal_id, record
        return None, None

    def merged_into(self, iid: str) -> Optional[tuple[str, str]]:
        for deal_id, items in self.deal_interactions.items():
            for record in items:
                meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
                if meta.get("mergedFrom") == iid or iid in (meta.get("mergedIds") or []):
                    return deal_id, record.get("id")
        return None

    # ---------- rules ----------
    def _title_hit(self, title: str, deal_id: str) -> Optional[str]:
        if not title:
            return None
        for name in self.deal_names[deal_id]:
            pattern = r"(?<!\w)" + re.escape(normalize_text(name)) + r"(?!\w)"
            if re.search(pattern, title):
                return name
        return None

    def _time_matches(self, inter: dict, at: _dt.datetime, emails: set[str], title: str) -> list[tuple[str, dict]]:
        hits = []
        for meeting in self.hs_meetings:
            if meeting["record"].get("id") == inter.get("id"):
                continue
            if abs(at - meeting["at"]) > TIME_MATCH_WINDOW:
                continue
            if (emails & meeting["emails"]) or (title and title == meeting["title"]):
                hits.append((meeting["dealId"], meeting["record"]))
        return hits

    @staticmethod
    def _offer(per_deal: dict[str, dict], deal_id: str, method: str, **evidence: Any) -> None:
        confidence = CONFIDENCE[method]
        cand = per_deal.get(deal_id)
        if cand is None:
            cand = {"dealId": deal_id, "method": method, "confidence": confidence, "evidence": empty_evidence()}
            per_deal[deal_id] = cand
        elif confidence > cand["confidence"]:
            cand["method"], cand["confidence"] = method, confidence
        for key, value in evidence.items():
            if key == "matchedEmails":
                cand["evidence"]["matchedEmails"] = sorted(set(cand["evidence"]["matchedEmails"]) | set(value))
            elif cand["evidence"].get(key) is None:
                cand["evidence"][key] = value

    def candidates_for(self, inter: dict) -> tuple[list[dict], Optional[str]]:
        """Candidate deals for one unlinked interaction, best first, plus a note when linking was blocked."""
        iid = inter.get("id")
        crm_deal = inter.get("dealId")
        if crm_deal:
            if crm_deal not in self.deals:
                return [], f"crm-associated deal {crm_deal} is not in the store"
            if not self.is_rejected(iid, crm_deal):
                cand = {"dealId": crm_deal, "method": METHOD_CRM, "confidence": CONFIDENCE[METHOD_CRM], "evidence": empty_evidence()}
                return [cand], None
        per_deal: dict[str, dict] = {}
        at = parse_iso(inter.get("at"))
        emails = self.buyer_emails(inter)
        domains = {email_domain(e) for e in emails} - {None}
        title = normalize_text(inter.get("title") or "")
        if inter.get("type") in TIME_MATCH_TYPES and at is not None:
            for deal_id, meeting in self._time_matches(inter, at, emails, title):
                self._offer(per_deal, deal_id, METHOD_TIME, matchedHubspotMeeting=meeting.get("id"))
        for deal_id in self.deals:
            if not self.in_window(deal_id, at):
                continue
            hit = emails & self.deal_emails[deal_id]
            if hit:
                self._offer(per_deal, deal_id, METHOD_EMAIL, matchedEmails=sorted(hit))
            domain = self.deal_domain[deal_id]
            if domain and domain in domains:
                self._offer(per_deal, deal_id, METHOD_DOMAIN, domain=domain)
            name_hit = self._title_hit(title, deal_id)
            if name_hit:
                self._offer(per_deal, deal_id, METHOD_TITLE, titleHit=name_hit)
        cands = [c for c in per_deal.values() if not self.is_rejected(iid, c["dealId"])]
        cands.sort(key=lambda c: (-c["confidence"], c["dealId"]))
        return cands, None

    # ---------- mutations ----------
    def public_candidate(self, cand: dict) -> dict:
        return {"dealId": cand["dealId"], "dealName": self.deal_name(cand["dealId"]),
                "method": cand["method"], "confidence": cand["confidence"]}

    def link_record(self, iid: str, cand: dict, status: str, by: str, candidates: Optional[list[dict]] = None) -> dict:
        return {
            "interactionId": iid,
            "dealId": cand["dealId"],
            "method": cand["method"],
            "confidence": cand["confidence"],
            "status": status,
            "evidence": cand.get("evidence") or empty_evidence(),
            "candidates": [{"dealId": c["dealId"], "confidence": c["confidence"], "method": c["method"],
                            "evidence": c.get("evidence") or empty_evidence()} for c in (candidates or [])],
            "at": now_iso(),
            "by": by,
        }

    def upsert_link(self, record: dict) -> None:
        """Replace every non-rejected link for the interaction; rejected links are kept as history."""
        iid = record.get("interactionId")
        self.links = [l for l in self.links if not (l.get("interactionId") == iid and l.get("status") != "rejected")]
        self.links.append(record)

    def drop_links(self, iid: str, statuses: tuple = ("pending",), deal_id: Optional[str] = None) -> None:
        self.links = [l for l in self.links
                      if not (l.get("interactionId") == iid and l.get("status") in statuses
                              and (deal_id is None or l.get("dealId") == deal_id))]

    def attach(self, inter: dict, deal_id: str) -> None:
        """Put the record into the deal's file: set dealId, default repId to the deal owner, drop candidates."""
        inter["dealId"] = deal_id
        if not inter.get("repId"):
            inter["repId"] = (self.deals.get(deal_id) or {}).get("ownerId")
        inter.pop("candidates", None)
        items = self.deal_interactions.setdefault(deal_id, [])
        for idx, existing in enumerate(items):
            if existing.get("id") == inter.get("id"):
                items[idx] = inter
                break
        else:
            items.append(inter)
        self.dirty.add(deal_id)

    def detach(self, iid: str) -> Optional[dict]:
        """Remove the record from whichever deal file holds it and return it (dealId cleared)."""
        for deal_id, items in self.deal_interactions.items():
            for idx, record in enumerate(items):
                if record.get("id") == iid:
                    del items[idx]
                    self.dirty.add(deal_id)
                    record["dealId"] = None
                    return record
        return None

    def remove_unlinked(self, iid: str) -> Optional[dict]:
        for idx, record in enumerate(self.unlinked):
            if record.get("id") == iid:
                return self.unlinked.pop(idx)
        return None

    def accept(self, inter: dict, cand: dict, status: str, by: str, alternatives: Optional[list[dict]] = None) -> dict:
        """Accept a candidate: merge into the HubSpot meeting for time-match, else attach; write the link."""
        deal_id = cand["dealId"]
        record = self.link_record(inter.get("id"), cand, status, by, alternatives)
        outcome = {"interactionId": inter.get("id"), "dealId": deal_id, "method": cand["method"],
                   "confidence": cand["confidence"], "status": status, "mergedInto": None}
        target = None
        if cand["method"] == METHOD_TIME:
            wanted = (cand.get("evidence") or {}).get("matchedHubspotMeeting")
            target = next((r for r in self.deal_interactions.get(deal_id, []) if r.get("id") == wanted), None)
        if target is not None:
            merge_records(target, inter)
            self.dirty.add(deal_id)
            record["mergedInto"] = target.get("id")
            outcome["mergedInto"] = target.get("id")
        else:
            self.attach(inter, deal_id)
        self.upsert_link(record)
        return outcome

    def pending_view(self, inter: dict) -> dict:
        return {
            "id": inter.get("id"), "at": inter.get("at"), "type": inter.get("type"), "source": inter.get("source"),
            "title": inter.get("title"),
            "participants": [{"name": p.get("name"), "email": p.get("email")} for p in (inter.get("participants") or []) if isinstance(p, dict)],
            "candidates": list(inter.get("candidates") or []),
        }

    def pending_list(self) -> list[dict]:
        return [self.pending_view(i) for i in self.unlinked if i.get("candidates")]

    def link_all(self) -> dict:
        """Run the rules over _unlinked; returns what happened (nothing is written here)."""
        result: dict[str, list] = {"linked": [], "merged": [], "pending": [], "unmatched": [], "notes": []}
        linked_ids = {r.get("id") for items in self.deal_interactions.values() for r in items}
        remaining: list[dict] = []
        for inter in self.unlinked:
            iid = inter.get("id")
            if iid in linked_ids:
                result["notes"].append(f"{iid}: already in a deal file, dropped from _unlinked")
                continue
            accepted = self.accepted.get(iid)
            if accepted and accepted.get("dealId") in self.deals:
                self.attach(inter, accepted["dealId"])
                result["linked"].append({"interactionId": iid, "dealId": accepted["dealId"], "method": accepted.get("method"),
                                         "confidence": accepted.get("confidence"), "status": accepted.get("status"), "mergedInto": None})
                continue
            cands, note = self.candidates_for(inter)
            if note:
                result["notes"].append(f"{iid}: {note}")
            status = decide(cands, self.threshold)
            if status == "auto":
                outcome = self.accept(inter, cands[0], "auto", "linker", cands[1:])
                result["linked"].append(outcome)
                if outcome["mergedInto"]:
                    result["merged"].append({"interactionId": iid, "into": outcome["mergedInto"], "dealId": outcome["dealId"]})
            elif status == "pending":
                inter["candidates"] = [self.public_candidate(c) for c in cands]
                self.upsert_link(self.link_record(iid, cands[0], "pending", "linker", cands))
                remaining.append(inter)
                result["pending"].append(self.pending_view(inter))
            else:
                inter["candidates"] = []
                self.drop_links(iid, ("pending",))
                remaining.append(inter)
                result["unmatched"].append(iid)
        self.unlinked = remaining
        return result

    def save(self) -> list[str]:
        wrote = []
        for deal_id in sorted(self.dirty):
            self.store.save_interactions(deal_id, self.deal_interactions.get(deal_id, []))
            wrote.append(str(self.store.interactions_path(deal_id)))
        self.store.save_unlinked(self.unlinked)
        wrote.append(str(self.store.interactions_dir / "_unlinked.json"))
        self.links_doc["links"] = self.links
        self.store.save_links(self.links_doc)
        wrote.append(str(self.store.data_dir / "links.json"))
        return wrote

    def read_paths(self) -> list[str]:
        return [str(self.store.data_dir / name) for name in ("deals.json", "contacts.json", "companies.json", "reps.json", "links.json")] + \
               [str(self.store.interactions_dir / "_unlinked.json")]


# ---------- commands ----------

def _candidate_from_links(lc: LinkContext, iid: str, deal_id: str) -> Optional[dict]:
    """The stored candidate (method, confidence, evidence) for a pair, from the pending or auto link."""
    for link in lc.links:
        if link.get("interactionId") != iid or link.get("status") == "rejected":
            continue
        if link.get("dealId") == deal_id:
            return {"dealId": deal_id, "method": link.get("method") or METHOD_MANUAL,
                    "confidence": link.get("confidence") or CONFIDENCE[METHOD_MANUAL], "evidence": link.get("evidence") or empty_evidence()}
        for cand in link.get("candidates") or []:
            if cand.get("dealId") == deal_id:
                return {"dealId": deal_id, "method": cand.get("method") or METHOD_MANUAL,
                        "confidence": cand.get("confidence") or CONFIDENCE[METHOD_MANUAL], "evidence": cand.get("evidence") or empty_evidence()}
    return None


def _fail(ctx: dict, message: str) -> int:
    _out(ctx, {"ok": False, "error": message}, f"error: {message}")
    return 1


def _cmd_run(ctx: dict, lc: LinkContext, dry_run: bool) -> int:
    result = lc.link_all()
    wrote = [] if dry_run else lc.save()
    counts = {"linked": len(result["linked"]), "merged": len(result["merged"]), "pending": len(result["pending"]),
              "unmatched": len(result["unmatched"])}
    lc.store.log_run("link", {"action": "run", "dryRun": dry_run}, True, ctx["started"], read=lc.read_paths(), wrote=wrote,
                     notes=", ".join(f"{k}={v}" for k, v in counts.items()) + (" (dry run)" if dry_run else ""))
    payload = {"ok": True, "dryRun": dry_run, "counts": counts, **result}
    text = (f"{'Would link' if dry_run else 'Linked'} {counts['linked']} interactions ({counts['merged']} merged into HubSpot meetings), "
            f"{counts['pending']} pending, {counts['unmatched']} unmatched" + (" [dry run, nothing written]" if dry_run else ""))
    if result["notes"]:
        text += "\n" + "\n".join(f"note: {n}" for n in result["notes"])
    text += "\npending: " + json.dumps(result["pending"], ensure_ascii=False, indent=2)
    _out(ctx, payload, text)
    return 0


def _cmd_pending(ctx: dict, lc: LinkContext) -> int:
    pending = lc.pending_list()
    unmatched = sum(1 for i in lc.unlinked if not i.get("candidates"))
    payload = {"ok": True, "pending": pending, "unmatched": unmatched}
    _out(ctx, payload, json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_confirm(ctx: dict, lc: LinkContext, iid: Optional[str], deal_id: Optional[str], dry_run: bool) -> int:
    if not iid or not deal_id:
        return _fail(ctx, "usage: link confirm <interactionId> <dealId>")
    if deal_id not in lc.deals:
        return _fail(ctx, f"unknown deal {deal_id}")
    where, record = lc.find(iid)
    if record is None:
        merged = lc.merged_into(iid)
        if merged:
            return _fail(ctx, f"{iid} was merged into {merged[1]} on deal {merged[0]}; un-merging is not supported")
        return _fail(ctx, f"unknown interaction {iid}")
    cand = _candidate_from_links(lc, iid, deal_id) or {"dealId": deal_id, "method": METHOD_MANUAL,
                                                        "confidence": CONFIDENCE[METHOD_MANUAL], "evidence": empty_evidence()}
    if where == deal_id:
        lc.upsert_link(lc.link_record(iid, cand, "confirmed", "user"))
        outcome = {"interactionId": iid, "dealId": deal_id, "method": cand["method"], "confidence": cand["confidence"],
                   "status": "confirmed", "mergedInto": None, "alreadyLinked": True}
    else:
        if where is None:
            lc.remove_unlinked(iid)
        else:
            lc.detach(iid)
        outcome = lc.accept(record, cand, "confirmed", "user")
    wrote = [] if dry_run else lc.save()
    lc.store.log_run("link", {"action": "confirm", "interactionId": iid, "dealId": deal_id, "dryRun": dry_run}, True,
                     ctx["started"], read=lc.read_paths(), wrote=wrote)
    payload = {"ok": True, "dryRun": dry_run, **outcome}
    text = f"{'Would confirm' if dry_run else 'Confirmed'} {iid} -> {deal_id} ({cand['method']}, {cand['confidence']})"
    if outcome.get("mergedInto"):
        text += f", merged into {outcome['mergedInto']}"
    _out(ctx, payload, text)
    return 0


def _rejected_record(iid: str, deal_id: Optional[str], cand: Optional[dict]) -> dict:
    cand = cand or {"dealId": deal_id, "method": METHOD_MANUAL, "confidence": CONFIDENCE[METHOD_MANUAL], "evidence": empty_evidence()}
    return {"interactionId": iid, "dealId": deal_id, "method": cand["method"], "confidence": cand["confidence"],
            "status": "rejected", "evidence": cand.get("evidence") or empty_evidence(), "candidates": [], "at": now_iso(), "by": "user"}


def _cmd_reject(ctx: dict, lc: LinkContext, iid: Optional[str], deal_id: Optional[str], dry_run: bool) -> int:
    if not iid:
        return _fail(ctx, "usage: link reject <interactionId> [<dealId>]")
    where, record = lc.find(iid)
    if record is None:
        merged = lc.merged_into(iid)
        if merged:
            return _fail(ctx, f"{iid} was merged into {merged[1]} on deal {merged[0]}; un-merging is not supported")
        return _fail(ctx, f"unknown interaction {iid}")
    rejected: list[dict] = []
    if deal_id:
        cand = _candidate_from_links(lc, iid, deal_id)
        if where == deal_id:
            record = lc.detach(iid)
            lc.unlinked.append(record)
        record["candidates"] = [c for c in (record.get("candidates") or []) if c.get("dealId") != deal_id]
        for link in lc.links:
            if link.get("interactionId") == iid and link.get("status") != "rejected":
                link["candidates"] = [c for c in (link.get("candidates") or []) if c.get("dealId") != deal_id]
        lc.drop_links(iid, ("pending", "auto", "confirmed"), deal_id=deal_id)
        if record.get("candidates"):
            top = record["candidates"][0]
            lc.upsert_link(lc.link_record(iid, {**top, "evidence": empty_evidence()}, "pending", "linker",
                                          [{**c, "evidence": empty_evidence()} for c in record["candidates"]]))
        else:
            lc.drop_links(iid, ("pending",))
        rejected.append(_rejected_record(iid, deal_id, cand))
    else:
        if where is not None:
            cand = _candidate_from_links(lc, iid, where)
            record = lc.detach(iid)
            lc.unlinked.append(record)
            rejected.append(_rejected_record(iid, where, cand))
        record["candidates"] = []
        lc.drop_links(iid, ("pending", "auto", "confirmed"))
        rejected.append(_rejected_record(iid, None, None))
    lc.links.extend(rejected)
    wrote = [] if dry_run else lc.save()
    lc.store.log_run("link", {"action": "reject", "interactionId": iid, "dealId": deal_id, "dryRun": dry_run}, True,
                     ctx["started"], read=lc.read_paths(), wrote=wrote)
    payload = {"ok": True, "dryRun": dry_run, "interactionId": iid, "rejected": [r["dealId"] for r in rejected],
               "remainingCandidates": list(record.get("candidates") or []), "unlinkedFrom": where}
    target = deal_id or "every deal"
    text = f"{'Would reject' if dry_run else 'Rejected'} {iid} for {target}; {len(record.get('candidates') or [])} candidates remain"
    _out(ctx, payload, text)
    return 0


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    if not store.exists():
        return _fail(ctx, "no store; run init")
    action = getattr(args, "action", None) or "run"
    dry_run = bool(getattr(args, "dry_run", False))
    lc = LinkContext(store, ctx.get("now"))
    if action == "run":
        return _cmd_run(ctx, lc, dry_run)
    if action == "pending":
        return _cmd_pending(ctx, lc)
    if action == "confirm":
        return _cmd_confirm(ctx, lc, getattr(args, "interaction_id", None), getattr(args, "deal_id", None), dry_run)
    if action == "reject":
        return _cmd_reject(ctx, lc, getattr(args, "interaction_id", None), getattr(args, "deal_id", None), dry_run)
    return _fail(ctx, f"unknown link action {action!r} (expected run, confirm, reject or pending)")
