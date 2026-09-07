"""`fs.py import demo [--seed N]`: a deterministic synthetic B2B dataset with a before-and-after story.

Northwind Analytics sells a data platform to UK and EU mid-market companies. Four reps, nine months
ending today, a MEDDPICC training four months before the end of the window. Amira Khan applies the
framework throughout, Tom Ellis starts low and rises after the training, Jonas Weber stays low,
Sofia Marin sits in the middle but never asks about the paper process and rarely tests her champion.

Everything is drawn from random.Random(seed) so two runs on the same day produce the same files.
Words live in demo_content.py; this module only assembles them. Standard library only.
"""
from __future__ import annotations

import datetime as _dt
import json
import random
import sys
from typing import Any, Optional

from ..schema.validate import validate_records
from ..store import Store
from ..util import parse_iso, to_iso, transcript_to_body
from . import demo_content as C

WINDOW_MONTHS = 9
TRAINING_MONTHS_BEFORE_END = 4
UNLINKED_COUNT = 6

STAGE_LABELS = {
    "appointmentscheduled": "Appointment Scheduled",
    "qualifiedtobuy": "Qualified To Buy",
    "presentationscheduled": "Presentation Scheduled",
    "decisionmakerboughtin": "Decision Maker Bought-In",
    "contractsent": "Contract Sent",
    "closedwon": "Closed Won",
    "closedlost": "Closed Lost",
}
_A, _Q, _P, _D, _C, _W, _L = ("appointmentscheduled", "qualifiedtobuy", "presentationscheduled", "decisionmakerboughtin",
                              "contractsent", "closedwon", "closedlost")
STAGE_PATTERNS = {
    "won": [[_A, _Q, _P, _D, _C, _W], [_A, _Q, _P, _D, _C, _W], [_A, _Q, _P, _C, _W]],
    "lost": [[_A, _Q, _P, _L], [_A, _Q, _P, _D, _L], [_A, _Q, _P, _C, _L], [_A, _Q, _P, _D, _C, _L]],
    "open": [[_A, _Q, _P, _D], [_A, _Q, _P, _D, _C], [_A, _Q, _P, _D]],
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
LEVEL_WEIGHTS = {"discovery": (35, 50, 15), "evaluation": (25, 50, 25), "proposal": (15, 50, 35), "commit": (10, 45, 45)}
ELEMENT_COUNT = {"high": [3, 4, 4, 5], "medium": [1, 2, 2, 3], "low": [0, 0, 0, 1]}
FOLLOW_PROB = {"high": 0.75, "medium": 0.4, "low": 0.15}
TRANSCRIPT_MIN, TRANSCRIPT_TARGET, TRANSCRIPT_CAP = 380, (420, 720), 760


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def shift_months(day: _dt.date, months: int) -> _dt.date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return _dt.date(year, month, min(day.day, last))


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _words(text: str) -> int:
    return len(text.split())


def _slug_email(first: str, last: str, domain: str) -> str:
    def clean(s: str) -> str:
        return "".join(ch for ch in s.lower().replace(" ", "") if ch.isalnum())
    return f"{clean(first)}.{clean(last)}@{domain}"


def _utc(day: _dt.date, hour: int = 9, minute: int = 0) -> _dt.datetime:
    return _dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=_dt.timezone.utc)


class _Ctx(dict):
    """format_map context that fails loudly on a missing key (a typo in a template is a bug)."""

    def __missing__(self, key: str) -> str:
        raise KeyError(f"demo template placeholder {{{key}}} has no value")


# ---------------------------------------------------------------------------
# the generator
# ---------------------------------------------------------------------------

class DemoGenerator:
    def __init__(self, seed: int, today: _dt.date):
        self.rng = random.Random(seed)
        self.seed = seed
        self.today = today
        self.window_from = shift_months(today, -WINDOW_MONTHS)
        self.training = shift_months(today, -TRAINING_MONTHS_BEFORE_END)
        self.now = _utc(today, 12, 0)
        self.span = (today - self.window_from).days
        self.reps: list[dict] = []
        self.deals: list[dict] = []
        self.contacts: list[dict] = []
        self.companies: list[dict] = []
        self.interactions: dict[str, list[dict]] = {}
        self.unlinked: list[dict] = []
        self.links: list[dict] = []
        self._deal_info: dict[str, dict] = {}
        self._counter: dict[str, int] = {}

    # ----- ids -----
    def _next(self, kind: str) -> int:
        self._counter[kind] = self._counter.get(kind, 0) + 1
        return self._counter[kind]

    # ----- public -----
    def generate(self) -> dict:
        rng = self.rng
        for spec in C.REPS:
            self.reps.append({"id": f"rep:{spec['email']}", "name": spec["name"], "email": spec["email"], "source": "demo"})
        # companies: the shared company gets two deals with the first rep; every other rep gets eight distinct companies
        others = [i for i in range(len(C.COMPANIES)) if i != C.SHARED_COMPANY_INDEX]
        rng.shuffle(others)
        plans: list[tuple[int, int, str, str]] = []  # (rep index, company index, outcome, flag)
        cursor = 0
        for r, spec in enumerate(C.REPS):
            won, lost, opened = spec["mix"]
            outcomes = ["won"] * won + ["lost"] * lost + ["open"] * opened
            rng.shuffle(outcomes)
            if r == 0:
                # the shared company carries one won deal and one open deal
                outcomes.remove("won")
                outcomes.remove("open")
                plans.append((r, C.SHARED_COMPANY_INDEX, "won", "shared-a"))
                plans.append((r, C.SHARED_COMPANY_INDEX, "open", "shared-b"))
            for outcome in outcomes:
                plans.append((r, others[cursor], outcome, ""))
                cursor += 1
        shared_eb: Optional[dict] = None
        company_ids: dict[int, str] = {}
        for r, ci, outcome, flag in plans:
            company = C.COMPANIES[ci]
            if ci not in company_ids:
                cid = f"co:demo:{self._next('company')}"
                company_ids[ci] = cid
                self.companies.append({"id": cid, "name": company["name"], "domain": company["domain"]})
            deal, info = self._build_deal(r, company, company_ids[ci], outcome, flag, shared_eb)
            if flag == "shared-a":
                shared_eb = info["eb_contact"]
            self.deals.append(deal)
            self._deal_info[deal["id"]] = info
        for deal in self.deals:
            self.interactions[deal["id"]] = self._build_interactions(deal, self._deal_info[deal["id"]])
        self._build_unlinked()
        for deal_id, items in self.interactions.items():
            for it in items:
                self.links.append(self._link(it["id"], deal_id))
        return {
            "reps": self.reps, "deals": self.deals, "contacts": self.contacts, "companies": self.companies,
            "interactions": self.interactions, "unlinked": self.unlinked,
            "links": {"version": 1, "links": self.links},
            "config": {
                "window": {"from": self.window_from.isoformat(), "to": self.today.isoformat()},
                "trainingDate": self.training.isoformat(),
                "org": {"name": C.VENDOR["name"], "internalDomains": [C.VENDOR["domain"]]},
            },
        }

    def _link(self, interaction_id: str, deal_id: str) -> dict:
        return {
            "interactionId": interaction_id, "dealId": deal_id, "method": "crm-association", "confidence": 1.0, "status": "auto",
            "evidence": {"matchedEmails": [], "domain": None, "matchedHubspotMeeting": None, "titleHit": None},
            "candidates": [{"dealId": deal_id, "confidence": 1.0}], "at": to_iso(self.now), "by": "linker",
        }

    # ----- deals -----
    def _timing(self, rep_index: int, outcome: str, flag: str) -> tuple[int, Optional[int]]:
        """(created day offset from window start, cycle days or None for open deals)."""
        rng = self.rng
        span = self.span
        training_day = (self.training - self.window_from).days
        if flag == "shared-a":
            return rng.randint(10, 40), rng.randint(120, 150)
        if flag == "shared-b":
            return rng.randint(95, 120), None
        if rep_index == 1 and outcome == "lost":  # Tom's early losses close before the training
            created = rng.randint(0, 45)
            return created, min(rng.randint(50, 95), training_day - created - 5)
        if rep_index == 1 and outcome == "won":  # Tom's wins are worked after the training
            created = rng.randint(training_day - 40, training_day + 20)
            return created, min(rng.randint(55, 95), span - created - 3)
        if outcome == "open":
            return rng.randint(span - 130, span - 40), None
        cycle = rng.randint(45, 130)
        latest = span - cycle - 3
        if self._counter.get(f"closed:{rep_index}", 0) % 2 == 0:  # alternate early and late deals so every rep has both halves
            self._counter[f"closed:{rep_index}"] = 1
            return rng.randint(0, max(0, min(latest, training_day - 30))), cycle
        self._counter[f"closed:{rep_index}"] = 0
        return rng.randint(max(0, min(training_day - 20, latest)), latest), cycle

    def _build_deal(self, rep_index: int, company: dict, company_id: str, outcome: str, flag: str, shared_eb: Optional[dict]) -> tuple[dict, dict]:
        rng = self.rng
        spec = C.REPS[rep_index]
        rep_id = f"rep:{spec['email']}"
        created_day, cycle = self._timing(rep_index, outcome, flag)
        created = _utc(self.window_from + _dt.timedelta(days=created_day), rng.choice([9, 10, 11, 14, 15]), rng.choice([0, 15, 30, 45]))
        closed = created + _dt.timedelta(days=cycle, hours=rng.randint(1, 6)) if cycle else None
        end = closed or (self.now - _dt.timedelta(days=rng.randint(3, 15)))
        pattern = rng.choice(STAGE_PATTERNS[outcome])
        # timestamps: created, then random increasing fractions, last one at close (or the latest move for open deals)
        cuts = sorted(rng.uniform(0.12, 0.9) for _ in range(len(pattern) - 2))
        history = [{"stage": pattern[0], "label": STAGE_LABELS[pattern[0]], "phase": "discovery", "at": to_iso(created)}]
        total = (end - created).total_seconds()
        for stage, cut in zip(pattern[1:-1], cuts):
            at = created + _dt.timedelta(seconds=total * cut)
            history.append({"stage": stage, "label": STAGE_LABELS[stage], "phase": _phase(stage), "at": to_iso(at)})
        last = pattern[-1]
        history.append({"stage": last, "label": STAGE_LABELS[last], "phase": _phase(last), "at": to_iso(end)})

        # cast: contact 1 champion, contact 2 economic buyer, contact 3 procurement; a mentioned IT person
        country = company["country"]
        firsts = rng.sample(C.FIRST_NAMES[country], 4)
        lasts = rng.sample(C.LAST_NAMES[country], 4)
        n_contacts = 3 if flag.startswith("shared") else rng.choice([1, 2, 2, 2, 3, 3])
        contacts: list[dict] = []
        titles = [rng.choice(C.CHAMPION_TITLES), rng.choice(C.EB_TITLES), rng.choice(C.PROC_TITLES)]
        for i in range(3):
            name = f"{firsts[i]} {lasts[i]}"
            person = {"id": f"c:demo:{self._next('contact')}", "name": name, "email": _slug_email(firsts[i], lasts[i], company["domain"]),
                      "title": titles[i], "companyId": company_id, "buyingRole": None, "_first": firsts[i]}
            if i == 1 and flag == "shared-b" and shared_eb is not None:
                person = shared_eb  # the second deal at the shared company reuses the CFO record
            contacts.append(person)
        stored = contacts[:n_contacts]
        for person in stored:
            if not any(c["id"] == person["id"] for c in self.contacts):
                self.contacts.append({k: v for k, v in person.items() if not k.startswith("_")})
        it_name = f"{firsts[3]} {lasts[3]}"
        ind = C.INDUSTRIES[company["industry"]]
        region_uk = company["region"] == "UK"
        amount = float(rng.randint(8, 120) * 1000)
        pct = rng.randint(*ind["pct"])
        info = {
            "rep": spec, "rep_id": rep_id, "rep_index": rep_index, "company": company, "outcome": outcome, "flag": flag,
            "contacts": stored, "champion": contacts[0], "eb": contacts[1], "proc": contacts[2], "eb_contact": contacts[1],
            "it_name": it_name, "history": history, "created": created, "closed": closed, "end": end,
            "ctx": _Ctx({
                "company": company["name"], "domain": company["domain"], "city": company["city"], "country": country,
                "industry": company["industry"], "units": company["units"], "n_units": company["n_units"],
                "rep_first": spec["name"].split()[0], "rep_name": spec["name"],
                "buyer_first": firsts[0], "buyer_name": contacts[0]["name"], "buyer_title": contacts[0]["title"],
                "eb_first": contacts[1]["_first"], "eb_name": contacts[1]["name"], "eb_title": contacts[1]["title"],
                "proc_first": contacts[2]["_first"], "proc_name": contacts[2]["name"], "it_first": firsts[3], "it_name": it_name,
                "kpi": ind["kpi"], "report": ind["report"], "cost_driver": ind["cost_driver"], "system": ind["system"],
                "pct": pct, "pct_target": rng.randint(*ind["pct_target"]), "n_days": rng.randint(*ind["n_days"]),
                "n_target": rng.randint(*ind["n_target"]), "money1": rng.randint(*ind["money1"]), "money2": rng.randint(*ind["money2"]),
                "n_hours": rng.randint(*ind["n_hours"]), "n_people": rng.randint(*ind["n_people"]),
                "cur": "£" if region_uk else "€", "currency": "GBP" if region_uk else "EUR",
                "amount_k": int(amount // 1000), "users": rng.randint(20, 120),
                "region_host": "London" if region_uk else "Frankfurt",
                "product": C.VENDOR["product"], "competitor": C.COMPETITOR, "consultancy": C.CONSULTANCY,
                "fy_end": (rng.choice(["March", "March", "December"]) if region_uk else "December"),
            }),
        }
        names = C.SHARED_DEAL_NAMES if flag.startswith("shared") else C.DEAL_NAME_PATTERNS
        name = (names[0] if flag == "shared-a" else names[1] if flag == "shared-b" else rng.choice(names)).format(company=company["name"])
        deal = {
            "id": f"demo:{1000 + self._next('deal')}", "source": "demo", "name": name,
            "amount": amount, "currency": info["ctx"]["currency"], "pipeline": "default",
            "stage": last, "stageLabel": STAGE_LABELS[last], "phase": _phase(last), "stageHistory": history,
            "outcome": outcome, "createdAt": to_iso(created), "closedAt": to_iso(closed) if closed else None,
            "ownerId": rep_id, "contactIds": [c["id"] for c in stored], "companyId": company_id, "companyDomain": company["domain"],
            "meta": {"demo": {"industry": company["industry"], "region": company["region"], "repProfile": f"{spec['before']}/{spec['after']}"}},
        }
        return deal, info

    # ----- interactions -----
    def _adoption(self, spec: dict, at: _dt.datetime) -> str:
        return spec["after"] if at.date() >= self.training else spec["before"]

    def _business_time(self, start: _dt.datetime, end: _dt.datetime) -> _dt.datetime:
        rng = self.rng
        if end <= start:
            end = start + _dt.timedelta(hours=1)
        at = start + _dt.timedelta(seconds=rng.random() * (end - start).total_seconds())
        if at.weekday() >= 5 and (end - at).days >= 2:
            at += _dt.timedelta(days=7 - at.weekday())
        elif at.weekday() >= 5 and (at - start).days >= 2:
            at -= _dt.timedelta(days=at.weekday() - 4)
        at = at.replace(hour=rng.choice([8, 9, 9, 10, 10, 11, 13, 14, 14, 15, 16]), minute=rng.choice([0, 0, 15, 30, 30, 45]), second=0, microsecond=0)
        return min(max(at, start), end)

    def _intervals(self, info: dict) -> list[tuple[str, _dt.datetime, _dt.datetime]]:
        history = info["history"]
        out = []
        for i, entry in enumerate(history):
            phase = entry["phase"]
            if phase in ("won", "lost"):
                continue
            start = parse_iso(entry["at"])
            end = parse_iso(history[i + 1]["at"]) if i + 1 < len(history) else info["end"]
            out.append((phase, start, end))
        return out

    def _build_interactions(self, deal: dict, info: dict) -> list[dict]:
        rng = self.rng
        intervals = self._intervals(info)
        mandatory: list[tuple[_dt.datetime, str, str]] = []
        preferred: list[tuple[_dt.datetime, str, str]] = []
        optional: list[tuple[_dt.datetime, str, str]] = []
        for phase, start, end in intervals:
            if phase == "discovery":
                mandatory.append((self._business_time(start, min(end, start + _dt.timedelta(days=3))), "call", phase))
                optional.append((self._business_time(start + _dt.timedelta(hours=3), end), "email_recap", phase))
                optional.append((self._business_time(start + _dt.timedelta(hours=1), end), "note", phase))
            elif phase == "evaluation":
                preferred.append((self._business_time(start, end), "meeting", phase))
                optional.append((self._business_time(start, end), "email_question", phase))
                optional.append((self._business_time(start, end), "email_scheduling", phase))
                optional.append((self._business_time(start, end), "note", phase))
            elif phase == "proposal":
                preferred.append((self._business_time(start, end), "call", phase))
                preferred.append((self._business_time(start, end), "email_proposal", phase))
                optional.append((self._business_time(start, end), "email_question", phase))
                optional.append((self._business_time(start, end), "note", phase))
            elif phase == "commit":
                preferred.append((self._business_time(start, end), "meeting", phase))
                optional.append((self._business_time(start, end), "email_question", phase))
                optional.append((self._business_time(start, end), "note", phase))
                optional.append((self._business_time(start, end), "call", phase))
        if info["closed"] is not None:
            mandatory.append((info["closed"] - _dt.timedelta(hours=rng.randint(2, 30)), "email_decision", deal["outcome"]))
        rng.shuffle(optional)
        if rng.random() < 0.65:  # most deals carry at least one internal note
            note = next((ev for ev in optional if ev[1] == "note"), None)
            if note:
                optional.remove(note)
                mandatory.append(note)
        target = rng.choice([4, 5, 5, 6])
        chosen = list(mandatory)
        for pool in (preferred, optional):
            for ev in pool:
                if len(chosen) >= target:
                    break
                chosen.append(ev)
        chosen.sort(key=lambda e: e[0])
        records = []
        for at, kind, phase in chosen:
            records.append(self._interaction(deal, info, at, kind, phase))
        return records

    def _interaction_ctx(self, info: dict, at: _dt.datetime) -> _Ctx:
        rng = self.rng
        ctx = _Ctx(info["ctx"])
        nxt = at + _dt.timedelta(days=rng.randint(3, 9))
        while nxt.weekday() >= 5:
            nxt += _dt.timedelta(days=1)
        ctx["next_day"] = f"{WEEKDAYS[nxt.weekday()]} the {_ordinal(nxt.day)}"
        ctx["next_time"] = rng.choice(["9.30", "10am", "11am", "2pm", "3.30"])
        ctx["deadline"] = "the end of " + MONTHS[(at + _dt.timedelta(weeks=rng.randint(6, 10))).month - 1]
        ctx["board_month"] = MONTHS[(at + _dt.timedelta(days=rng.randint(35, 95))).month - 1]
        ctx["go_live"] = MONTHS[(at + _dt.timedelta(days=rng.randint(90, 150))).month - 1]
        return ctx

    def _people(self, info: dict, who: str) -> dict:
        person = {"rep": None, "buyer": info["champion"], "eb": info["eb"], "proc": info["proc"], "it": None}[who]
        if who == "rep":
            return {"name": info["rep"]["name"], "email": info["rep"]["email"], "role": "rep"}
        if who == "it":
            return {"name": info["it_name"], "email": _slug_email(*info["it_name"].split(" ", 1), info["company"]["domain"]), "role": "buyer"}
        return {"name": person["name"], "email": person["email"], "role": "buyer"}

    def _interaction(self, deal: dict, info: dict, at: _dt.datetime, kind: str, phase: str) -> dict:
        rng = self.rng
        spec = info["rep"]
        adoption = self._adoption(spec, at)
        ctx = self._interaction_ctx(info, at)
        base = {
            "source": "demo", "dealId": deal["id"], "at": to_iso(at), "durationSec": None, "title": "", "body": "", "transcript": [],
            "notes": None, "summary": None, "participants": [], "repId": info["rep_id"], "recordingUrl": None,
            "meta": {"demo": {"adoption": adoption, "afterTraining": at.date() >= self.training, "phase": phase, "elementsAsked": [], "behaviourTags": []}},
        }
        rep_p, champ_p = self._people(info, "rep"), self._people(info, "buyer")
        has_eb = len(info["contacts"]) >= 2
        has_proc = len(info["contacts"]) >= 3
        if kind == "call":
            eb_present = False
            segs, asked, tags, dur = self._dialogue(ctx, info, phase, adoption, eb_present, "call")
            base.update({"id": f"demo:call:{self._next('call')}", "type": "call", "direction": "outbound" if rng.random() < 0.8 else "inbound",
                         "durationSec": dur, "title": rng.choice(C.CALL_TITLES[phase]).format_map(ctx), "body": transcript_to_body(segs),
                         "transcript": segs, "participants": [rep_p, champ_p]})
        elif kind == "meeting":
            eb_present = has_eb and (phase == "commit" or (phase == "proposal" and rng.random() < 0.5))
            participants = [rep_p, champ_p] + ([self._people(info, "eb")] if eb_present else []) + \
                ([self._people(info, "proc")] if has_proc and phase == "commit" and rng.random() < 0.5 else [])
            base.update({"id": f"demo:meeting:{self._next('meeting')}", "type": "meeting", "direction": "outbound",
                         "title": rng.choice(C.MEETING_TITLES[phase]).format_map(ctx), "participants": participants})
            if rng.random() < 0.55:
                segs, asked, tags, dur = self._dialogue(ctx, info, phase, adoption, eb_present, "meeting")
                base.update({"durationSec": dur, "body": transcript_to_body(segs), "transcript": segs})
            else:
                pool = C.MEETING_SUMMARY_HIGH if adoption == "high" or (adoption == "medium" and rng.random() < 0.5) else C.MEETING_SUMMARY_LOW
                summary = rng.choice(pool).format_map(ctx)
                asked, tags = (["M", "E", "DP", "PP", "CO"] if pool is C.MEETING_SUMMARY_HIGH else []), []
                if pool is C.MEETING_SUMMARY_HIGH:
                    tags = ["asked-metrics", "identified-eb", "mapped-decision-process", "secured-next-step"]
                    if "PP" in spec["gaps"]:
                        summary = summary.replace(f" and what the paperwork involves ({ctx['proc_first']}, questionnaire and MSA, three to four weeks)", "")
                        asked.remove("PP")
                base.update({"durationSec": rng.randint(1800, 3600), "body": summary, "summary": summary})
        elif kind == "note":
            pool = C.NOTES_HIGH if adoption == "high" or (adoption == "medium" and rng.random() < 0.5) else C.NOTES_LOW
            if pool is C.NOTES_HIGH and "PP" in spec["gaps"]:
                pool = C.NOTES_HIGH[:1]  # the only high note that says nothing about the paper process
            text = rng.choice(pool).format_map(ctx)
            asked, tags = ([] if pool is C.NOTES_LOW else ["M", "E", "DC", "CO"]), []
            base.update({"id": f"demo:note:{self._next('note')}", "type": "note", "direction": "internal", "title": f"Note: {ctx['company']}",
                         "body": text, "participants": [rep_p]})
        else:  # emails
            subject, body, direction, asked, tags = self._email(kind, ctx, info, adoption, phase)
            participants = [rep_p, champ_p] + ([self._people(info, "eb")] if has_eb and kind in ("email_proposal", "email_decision") else [])
            base.update({"id": f"demo:email:{self._next('email')}", "type": "email", "direction": direction, "title": subject, "body": body,
                         "participants": participants})
        base["meta"]["demo"]["elementsAsked"] = sorted(asked)
        base["meta"]["demo"]["behaviourTags"] = sorted(tags)
        return base

    def _email(self, kind: str, ctx: _Ctx, info: dict, adoption: str, phase: str) -> tuple[str, str, str, list, list]:
        rng = self.rng
        asked: list[str] = []
        tags: list[str] = []
        if kind == "email_recap":
            high = adoption == "high" or (adoption == "medium" and rng.random() < 0.5)
            tpl = C.EMAIL_RECAP_HIGH if high else C.EMAIL_RECAP_LOW
            paragraphs = list(tpl["paragraphs"])
            if high:
                asked, tags = ["M", "E", "DC", "CO"], ["summarised-and-confirmed", "secured-next-step"]
            return (rng.choice(tpl["subject"]).format_map(ctx), _join(paragraphs, C.EMAIL_SIGNOFFS_REP, ctx, rng), "outbound", asked, tags)
        if kind == "email_proposal":
            tags = ["quantified-impact"] if adoption != "low" else []
            paragraphs = list(C.EMAIL_PROPOSAL["paragraphs"])
            if "PP" in info["rep"]["gaps"]:
                paragraphs[3] = f"The commercial terms are attached. Happy to walk through anything on a call, and I would suggest we do that with {ctx['eb_first']} before {ctx['deadline']}."
            return (rng.choice(C.EMAIL_PROPOSAL["subject"]).format_map(ctx), _join(paragraphs, C.EMAIL_SIGNOFFS_REP, ctx, rng), "outbound", asked, tags)
        if kind == "email_scheduling":
            tags = ["secured-next-step", "multi-threaded"] if adoption != "low" else []
            return (rng.choice(C.EMAIL_SCHEDULING["subject"]).format_map(ctx), _join(C.EMAIL_SCHEDULING["paragraphs"], C.EMAIL_SIGNOFFS_REP, ctx, rng), "outbound", asked, tags)
        if kind == "email_question":
            idx = rng.randrange(len(C.EMAIL_INBOUND_QUESTION["paragraphs"]))
            return (C.EMAIL_INBOUND_QUESTION["subject"][idx].format_map(ctx), _join(C.EMAIL_INBOUND_QUESTION["paragraphs"][idx], C.EMAIL_SIGNOFFS_BUYER, ctx, rng), "inbound", asked, tags)
        tpl = C.EMAIL_DECISION_WON if phase == "won" else C.EMAIL_DECISION_LOST
        idx = rng.randrange(len(tpl["paragraphs"]))
        return (rng.choice(tpl["subject"]).format_map(ctx), _join(tpl["paragraphs"][idx], C.EMAIL_SIGNOFFS_BUYER, ctx, rng), "inbound", asked, tags)

    # ----- dialogue assembly -----
    def _dialogue(self, ctx: _Ctx, info: dict, phase: str, adoption: str, eb_present: bool, kind: str) -> tuple[list[dict], list[str], list[str], int]:
        rng = self.rng
        spec = info["rep"]
        turns: list[tuple[str, str]] = []
        tags: set[str] = set()
        asked: list[str] = []
        used: set[str] = set()

        def pick(pool: list) -> Any:
            """Random choice that avoids repeating a fragment inside one conversation."""
            fresh = [p for p in pool if repr(p) not in used] or list(pool)
            item = rng.choice(fresh)
            used.add(repr(item))
            return item

        def add(fragment: list[tuple[str, str]]) -> None:
            for who, text in fragment:
                turns.append((who, text.format_map(ctx)))

        def count() -> int:
            return sum(_words(t) for _, t in turns)

        def scene(element: str) -> None:
            open_tag, follow_tags = C.ELEMENT_SCENES[element]
            turns.append(("rep", pick(C.REP_QUESTIONS[open_tag]).format_map(ctx)))
            tags.add(open_tag)
            asked.append(element)
            w1, w2, w3 = LEVEL_WEIGHTS[phase]
            if info["outcome"] == "won":
                w3 += 10
            elif info["outcome"] == "lost":
                w1 += 10
            level = rng.choices([1, 2, 3], weights=[w1, w2, w3])[0]
            turns.append(("buyer", pick(C.BUYER_STATEMENTS[element][level]).format_map(ctx)))
            if rng.random() < FOLLOW_PROB[adoption]:
                follow = rng.choice(follow_tags)
                turns.append(("rep", pick(C.REP_QUESTIONS[follow]).format_map(ctx)))
                tags.add(follow)
                if follow in C.BUYER_ACKNOWLEDGE:
                    turns.append(("buyer", pick(C.BUYER_ACKNOWLEDGE[follow]).format_map(ctx)))
                else:
                    turns.append(("buyer", pick(C.BUYER_STATEMENTS[element][min(3, level + 1)]).format_map(ctx)))

        # 1. opener and agenda
        add(pick(C.MEETING_OPENERS) if eb_present else pick(C.SMALL_TALK[:5] if phase == "discovery" else C.SMALL_TALK))
        if adoption == "low":
            turns.append(("rep", pick(C.PITCH).format_map(ctx)))
        else:
            add(pick(C.AGENDAS))

        # 2. the elements this rep works in this conversation
        pool = [e for e in C.ELEMENTS_BY_PHASE[phase] if e not in spec["gaps"] and (e not in spec["rare"] or rng.random() < 0.2)]
        n_elements = min(rng.choice(ELEMENT_COUNT[adoption]), len(pool))
        head = pool[: n_elements + 2]
        elements = rng.sample(head, n_elements) if n_elements else []
        elements.sort(key=head.index)
        remaining = [e for e in pool if e not in elements]
        for i, element in enumerate(elements):
            scene(element)
            if rng.random() < 0.25:
                add(pick(C.INTERRUPTIONS))
            elif i == 1 and rng.random() < 0.3:
                turns.append(("rep", pick(C.PITCH).format_map(ctx)))
        if eb_present and adoption != "low":
            turns.append(("rep", pick(C.REP_QUESTIONS["engaged-eb"]).format_map(ctx)))
            tags.add("engaged-eb")
            asked.append("E")
            turns.append(("eb", pick(C.EB_STATEMENTS).format_map(ctx)))
        elif eb_present:
            turns.append(("eb", pick(C.EB_STATEMENTS).format_map(ctx)))
            turns.append(("rep", pick(C.REP_PITCH_PAST_IT).format_map(ctx)))

        # 3. low adoption: the buyer volunteers something and the rep pitches past it; logistics fill the time
        if adoption == "low":
            if rng.random() < 0.7:
                turns.append(("buyer", pick(C.BUYER_VOLUNTEERED).format_map(ctx)))
                turns.append(("rep", pick(C.REP_PITCH_PAST_IT).format_map(ctx)))
            for _ in range(rng.randint(1, 2)):
                turns.append(("rep", pick(C.PITCH).format_map(ctx)))
                add(pick(C.LOGISTICS))
        elif adoption == "medium":
            add(pick(C.LOGISTICS))
            if rng.random() < 0.5:
                turns.append(("rep", pick(C.PITCH).format_map(ctx)))

        # 4. an objection, handled well or badly
        if rng.random() < 0.8:
            obj = pick(C.OBJECTIONS)
            turns.append(("buyer", obj["buyer"].format_map(ctx)))
            strong = adoption == "high" or (adoption == "medium" and rng.random() < 0.5)
            if strong and not (obj["strong"][1] == "asked-paper-process" and "PP" in spec["gaps"]):
                turns.append(("rep", obj["strong"][0].format_map(ctx)))
                tags.add(obj["strong"][1])
                if obj["strong"][1] in C.BUYER_ACKNOWLEDGE:
                    turns.append(("buyer", pick(C.BUYER_ACKNOWLEDGE[obj["strong"][1]]).format_map(ctx)))
            else:
                turns.append(("rep", obj["weak"].format_map(ctx)))

        # 5. pad to a natural length without blowing the cap
        target = rng.randint(*TRANSCRIPT_TARGET) if adoption != "low" else rng.randint(400, 600)
        guard = 0
        while count() < max(TRANSCRIPT_MIN, target) and guard < 16:
            guard += 1
            if adoption == "high" and remaining and len(asked) < 5 and rng.random() < 0.6:
                n_turns, n_asked, saved_tags = len(turns), len(asked), set(tags)
                scene(remaining.pop(0))
                if count() > TRANSCRIPT_CAP:  # roll the scene back rather than overshoot
                    del turns[n_turns:]
                    del asked[n_asked:]
                    tags.intersection_update(saved_tags)
                continue
            # filler pools, unused fragments only; stop when every pool is spent rather than repeat
            pools = [("pitch", C.PITCH), ("logistics", C.LOGISTICS), ("logistics", C.LOGISTICS), ("interrupt", C.INTERRUPTIONS)]
            pools = [(name, [p for p in pool if repr(p) not in used]) for name, pool in pools]
            pools = [(name, fresh) for name, fresh in pools if fresh]
            if not pools:
                break
            name, fresh = rng.choice(pools)
            if name == "pitch":
                text = pick(fresh).format_map(ctx)
                if count() + _words(text) <= TRANSCRIPT_CAP:
                    turns.append(("rep", text))
            else:
                frag = pick(fresh)
                if count() + sum(_words(t) for _, t in frag) <= TRANSCRIPT_CAP:
                    add(frag)

        # 6. closing
        strong_close = adoption == "high" or (adoption == "medium" and rng.random() < 0.5)
        if strong_close:
            add(pick(C.CLOSINGS_STRONG))
            tags.add("secured-next-step")
        else:
            add(pick(C.CLOSINGS_WEAK))

        names = {"rep": info["rep"]["name"], "buyer": info["champion"]["name"], "eb": info["eb"]["name"], "proc": info["proc"]["name"], "it": info["it_name"]}
        segments: list[dict] = []
        t = 0.0
        for who, text in turns:
            text = text[0].upper() + text[1:]  # placeholders such as {report} can start a sentence in lower case
            segments.append({"speaker": names[who], "t": round(t, 1), "text": text})
            t += _words(text) * 0.42 + rng.uniform(0.8, 3.0)
        duration = int(t + rng.randint(30, 240))
        return segments, sorted(set(asked)), sorted(tags), duration

    # ----- unlinked meetings -----
    def _build_unlinked(self) -> None:
        rng = self.rng
        shared = [d for d in self.deals if self._deal_info[d["id"]]["flag"].startswith("shared")]
        eligible = [d for d in self.deals if not self._deal_info[d["id"]]["flag"] and len(d["contactIds"]) >= 2
                    and (parse_iso(d["closedAt"]) if d["closedAt"] else self.now) - parse_iso(d["createdAt"]) > _dt.timedelta(days=20)]
        picks = rng.sample(eligible, 5)
        plan = [
            (picks[0], "buyer", 0), (picks[1], "buyer", 1), (picks[2], "eb", 2),  # email matches
            (picks[3], "it", 3),  # domain only: the IT director is not a CRM contact
            (shared[0], "eb", 4),  # ambiguous: the CFO sits on both Brightwater deals
            (picks[4], "buyer", 5),
        ]
        for n, (deal, who, topic_index) in enumerate(plan, start=1):
            info = self._deal_info[deal["id"]]
            start = parse_iso(deal["createdAt"]) + _dt.timedelta(days=2)
            end = (parse_iso(deal["closedAt"]) if deal["closedAt"] else self.now) - _dt.timedelta(days=2)
            if topic_index == 4:  # inside both Brightwater deal windows
                other = self._deal_info[shared[1]["id"]]
                start = other["created"] + _dt.timedelta(days=2)
                end = info["closed"] - _dt.timedelta(days=2)
            at = self._business_time(start, end)
            phase = _phase_at(info["history"], at)
            adoption = self._adoption(info["rep"], at)
            ctx = self._interaction_ctx(info, at)
            segs, asked, tags, dur = self._dialogue(ctx, info, phase, adoption, False, "meeting")
            summary = C.UNLINKED_SUMMARIES[topic_index].format_map(ctx)
            self.unlinked.append({
                "id": f"demo:meeting:u{n}", "source": "demo", "type": "meeting", "dealId": None, "direction": "outbound", "at": to_iso(at),
                "durationSec": dur, "title": C.UNLINKED_TOPICS[topic_index].format_map(ctx), "body": transcript_to_body(segs), "transcript": segs,
                "notes": None, "summary": summary, "participants": [self._people(info, "rep"), self._people(info, who)], "repId": info["rep_id"],
                "recordingUrl": None,
                "meta": {"demo": {"adoption": adoption, "afterTraining": at.date() >= self.training, "phase": phase, "elementsAsked": asked,
                                  "behaviourTags": tags, "expectedDeal": deal["id"] if topic_index != 4 else None,
                                  "expectedCandidates": [shared[0]["id"], shared[1]["id"]] if topic_index == 4 else [deal["id"]],
                                  "expectedMethod": "domain-match" if topic_index == 3 else "email-match"}},
            })


def _join(paragraphs: list[str], signoffs: list[str], ctx: _Ctx, rng: random.Random) -> str:
    return "\n\n".join(p.format_map(ctx) for p in paragraphs) + "\n\n" + rng.choice(signoffs).format_map(ctx)


def _phase(stage: str) -> str:
    from ..config import DEFAULT_STAGE_PHASES
    return DEFAULT_STAGE_PHASES[stage]


def _phase_at(history: list[dict], at: _dt.datetime) -> str:
    phase = "discovery"
    for entry in history:
        if parse_iso(entry["at"]) <= at and entry["phase"] not in ("won", "lost"):
            phase = entry["phase"]
    return phase


# ---------------------------------------------------------------------------
# command entry point
# ---------------------------------------------------------------------------

def generate(seed: int = 7, today: Optional[_dt.date] = None) -> dict:
    return DemoGenerator(seed, today or _dt.date.today()).generate()


def validate_dataset(ds: dict) -> list[str]:
    errors = validate_records("deal", ds["deals"]) + validate_records("rep", ds["reps"]) + \
        validate_records("contact", ds["contacts"]) + validate_records("company", ds["companies"])
    every = [it for items in ds["interactions"].values() for it in items] + ds["unlinked"]
    errors += validate_records("interaction", every)
    return errors


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    seed = int(getattr(args, "seed", 7) or 7)
    today = (parse_iso(ctx.get("now")) or _dt.datetime.now(_dt.timezone.utc)).date()
    ds = generate(seed, today)
    errors = validate_dataset(ds)
    if errors:
        for line in errors[:25]:
            print(f"  {line}", file=sys.stderr)
        print(f"demo dataset failed validation with {len(errors)} error(s); nothing written", file=sys.stderr)
        return 1
    store.ensure()
    wrote: list[str] = []
    store.save_deals(Store.upsert(store.load_deals(), ds["deals"]))
    store.save_reps(Store.upsert(store.load_reps(), ds["reps"]))
    store.save_contacts(Store.upsert(store.load_contacts(), ds["contacts"]))
    store.save_companies(Store.upsert(store.load_companies(), ds["companies"]))
    wrote += [str(store.data_dir / n) for n in ("deals.json", "reps.json", "contacts.json", "companies.json")]
    for deal_id, items in ds["interactions"].items():
        store.save_interactions(deal_id, items)
        wrote.append(str(store.interactions_path(deal_id)))
    keep = [u for u in store.load_unlinked() if not str(u.get("id", "")).startswith("demo:")]
    store.save_unlinked(keep + ds["unlinked"])
    wrote.append(str(store.interactions_dir / "_unlinked.json"))
    links = store.load_links()
    links["links"] = [l for l in links.get("links", []) if not str(l.get("interactionId", "")).startswith("demo:")] + ds["links"]["links"]
    store.save_links(links)
    wrote.append(str(store.data_dir / "links.json"))
    cfg = store.config
    cfg.set("window", ds["config"]["window"])
    cfg.set("trainingDate", ds["config"]["trainingDate"])
    domains = list(cfg.get("org.internalDomains") or [])
    for d in ds["config"]["org"]["internalDomains"]:
        if d not in domains:
            domains.append(d)
    cfg.set("org.internalDomains", domains)
    if not cfg.get("org.name"):
        cfg.set("org.name", ds["config"]["org"]["name"])
    store.save_config()
    wrote.append(str(store.config_path))

    summary = summarize(ds, seed, str(store.home))
    ctx["summary"] = {"read": [], "wrote": wrote, "notes": summary["notesLine"]}
    if ctx.get("json"):
        print(json.dumps({"ok": True, **summary}, ensure_ascii=False, indent=2))
    else:
        print(summary["text"])
    return 0


def summarize(ds: dict, seed: int, home: str) -> dict:
    deals = ds["deals"]
    by_outcome = {o: sum(1 for d in deals if d["outcome"] == o) for o in ("won", "lost", "open")}
    linked = [it for items in ds["interactions"].values() for it in items]
    by_type: dict[str, int] = {}
    for it in linked:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1
    reps_out = []
    for rep in ds["reps"]:
        mine = [it for it in linked if it["repId"] == rep["id"] and it["direction"] != "inbound"]  # rep-authored only
        before = [it for it in mine if not it["meta"]["demo"]["afterTraining"]]
        after = [it for it in mine if it["meta"]["demo"]["afterTraining"]]
        rate = lambda items: (round(sum(1 for i in items if i["meta"]["demo"]["behaviourTags"]) / len(items), 2) if items else None)  # noqa: E731
        d = [x for x in deals if x["ownerId"] == rep["id"]]
        reps_out.append({"id": rep["id"], "name": rep["name"], "deals": len(d),
                         "won": sum(1 for x in d if x["outcome"] == "won"), "lost": sum(1 for x in d if x["outcome"] == "lost"),
                         "open": sum(1 for x in d if x["outcome"] == "open"), "interactions": len(mine),
                         "adoptionBefore": rate(before), "adoptionAfter": rate(after), "nBefore": len(before), "nAfter": len(after)})
    cfg = ds["config"]
    lines = [
        f"Demo dataset (seed {seed}) written to {home}",
        f"  window {cfg['window']['from']} to {cfg['window']['to']}, training date {cfg['trainingDate']}, vendor {cfg['org']['name']} ({cfg['org']['internalDomains'][0]})",
        f"  deals: {len(deals)} (won {by_outcome['won']}, lost {by_outcome['lost']}, open {by_outcome['open']})   reps: {len(ds['reps'])}   contacts: {len(ds['contacts'])}   companies: {len(ds['companies'])}",
        f"  interactions: {len(linked)} linked (" + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items())) + f"), {len(ds['unlinked'])} unlinked meetings, {len(ds['links']['links'])} links",
    ]
    for r in reps_out:
        lines.append(f"  {r['name']}: {r['won']}W {r['lost']}L {r['open']}O, adoption before {r['adoptionBefore']} (n={r['nBefore']}) after {r['adoptionAfter']} (n={r['nAfter']})")
    lines.append("  next: fs.py link (resolves the 6 unlinked meetings), then plan-assessment")
    return {
        "seed": seed, "home": home, "window": cfg["window"], "trainingDate": cfg["trainingDate"],
        "counts": {"deals": len(deals), "dealsByOutcome": by_outcome, "reps": len(ds["reps"]), "contacts": len(ds["contacts"]),
                   "companies": len(ds["companies"]), "interactions": len(linked), "interactionsByType": by_type,
                   "unlinked": len(ds["unlinked"]), "links": len(ds["links"]["links"])},
        "reps": reps_out, "text": "\n".join(lines),
        "notesLine": f"{len(deals)} deals, {len(linked)} interactions, {len(ds['unlinked'])} unlinked",
    }
