"""JSON packs for the standup skill (briefing-data) and the retro skill (retro-data).

Both commands always print JSON. When the analytics files are missing they compute the numbers in
memory through the rollup functions instead of failing. Standard library only.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from collections import Counter
from typing import Any, Optional

from ..store import Store
from ..util import iso_week, parse_iso, safe_id, to_iso
from . import rollup

ANALYTICS_FILES = ("deal_states", "rep_metrics", "team_metrics", "timeseries")
STALE_DAYS = 14
_UTC = _dt.timezone.utc
_MIN_DT = _dt.datetime.min.replace(tzinfo=_UTC)


# ---------- shared ----------

def resolve_rep(reps: list[dict], query: Optional[str], extra_ids: Optional[set] = None) -> Optional[dict]:
    """Match a rep by id, email or name (case-insensitive); a unique partial name match also counts."""
    q = str(query or "").strip()
    ql = q.lower()
    if not q:
        return None
    reps = [r for r in reps or [] if isinstance(r, dict)]
    for rep in reps:
        if rep.get("id") == q:
            return rep
    for rep in reps:
        email = str(rep.get("email") or "").lower()
        if email and ql in (email, f"rep:{email}"):
            return rep
    for rep in reps:
        if str(rep.get("id") or "").lower() == ql or str(rep.get("name") or "").lower() == ql:
            return rep
    partial = [rep for rep in reps if ql in str(rep.get("name") or "").lower()]
    if len(partial) == 1:
        return partial[0]
    for rid in extra_ids or ():
        if rid and (rid == q or str(rid).lower() == ql):
            return {"id": rid, "name": None, "email": None, "source": "derived"}
    return None


def load_bundle(ctx: dict) -> dict:
    """Store inputs plus the four analytics files, computed in memory when any of them is missing."""
    store: Store = ctx["store"]
    cfg = store.config
    framework, source = rollup.load_framework(ctx["plugin_root"], cfg.framework)
    inputs = rollup.load_inputs(store)
    now = rollup._as_dt(ctx.get("now"))
    files = {name: store.read_json(f"analytics/{name}.json") for name in ANALYTICS_FILES}
    read = list(inputs["read"]) + [str(store.analytics_dir / f"{n}.json") for n, v in files.items() if v is not None]
    missing = [n for n, v in files.items() if v is None]
    if missing:
        computed = rollup.compute_all(inputs, framework, cfg, now)
        for name in missing:
            files[name] = computed[name]
    return {"store": store, "cfg": cfg, "framework": framework, "frameworkSource": source, "inputs": inputs, "now": now,
            "records": rollup.build_records(inputs, cfg, framework), "computedInMemory": bool(missing),
            "missing": missing, "read": read, **files}


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def _fail(ctx: dict, command: str, args_dict: dict, message: str) -> int:
    _print({"ok": False, "error": message})
    ctx["store"].log_run(command, args_dict, False, ctx["started"], notes=message)
    return 1


def _days_between(later: Optional[_dt.datetime], earlier: Optional[_dt.datetime]) -> Optional[int]:
    if later is None or earlier is None:
        return None
    return int((later - earlier).total_seconds() // 86400)


def _state_for(bundle: dict, deal: dict) -> dict:
    states = {s.get("dealId"): s for s in bundle["deal_states"] if isinstance(s, dict)}
    state = states.get(deal.get("id"))
    if state is None:
        inputs = bundle["inputs"]
        interactions = inputs["interactions"].get(deal.get("id"))
        if interactions is None:
            interactions = bundle["store"].load_interactions(deal.get("id"))
        state = rollup.compute_deal_state(deal, inputs["assessments"].get(deal.get("id")), interactions,
                                          bundle["framework"], bundle["cfg"], bundle["now"])
    return state


def _stored(bundle: dict, deal_id: str) -> list[dict]:
    items = bundle["inputs"]["interactions"].get(deal_id)
    if items is None:
        items = bundle["store"].load_interactions(deal_id)
    items = [i for i in items or [] if isinstance(i, dict)]
    items.sort(key=lambda i: (parse_iso(i.get("at")) or _MIN_DT, i.get("id") or ""))
    return items


def _last_interaction_at(items: list[dict], ref: _dt.datetime) -> Optional[_dt.datetime]:
    times = [parse_iso(i.get("at")) for i in items]
    times = [t for t in times if t is not None and t <= ref]
    return max(times) if times else None


def _weakest_levels(state: dict, codes: list[str], k: int = 3) -> list[str]:
    elements = state.get("elements") or {}
    return sorted(codes, key=lambda c: ((elements.get(c) or {}).get("level", 0), codes.index(c)))[:k]


def _rep_block(bundle: dict, rep: dict) -> dict:
    metrics = next((m for m in bundle["rep_metrics"] if isinstance(m, dict) and m.get("repId") == rep.get("id")), {})
    return {
        "id": rep.get("id"), "name": rep.get("name"), "email": rep.get("email"),
        "adoptionRate": metrics.get("adoptionRate"), "interactions": metrics.get("interactions"),
        "winRate": metrics.get("winRate"), "weakestElements": metrics.get("weakestElements") or [],
        "strongestElements": metrics.get("strongestElements") or [], "evidenceQualityIndex": metrics.get("evidenceQualityIndex"),
        "adoptionByElement": metrics.get("adoptionByElement") or {},
    }


def _slim(bucket: dict) -> dict:
    return {k: bucket.get(k) for k in ("week", "interactions", "applied", "adoptionRate")}


def _rep_buckets(bundle: dict, rep_id: Optional[str]) -> list[dict]:
    reps = (bundle["timeseries"] or {}).get("reps") or {}
    return [b for b in (reps.get(rep_id) or []) if isinstance(b, dict)]


def _team_buckets(bundle: dict) -> list[dict]:
    return [b for b in ((bundle["timeseries"] or {}).get("team") or []) if isinstance(b, dict)]


# ---------- briefing-data ----------

def briefing(ctx: dict, args: Any) -> int:
    args_dict = {"rep": getattr(args, "rep", None), "date": getattr(args, "date", None)}
    bundle = load_bundle(ctx)
    inputs, cfg, framework = bundle["inputs"], bundle["cfg"], bundle["framework"]
    rep = resolve_rep(inputs["reps"], args_dict["rep"], {d.get("ownerId") for d in inputs["allDeals"]})
    if rep is None:
        return _fail(ctx, "briefing-data", args_dict, f"rep not found: {args_dict['rep']!r} (try the id, email or name)")
    if args_dict["date"]:
        ref = parse_iso(args_dict["date"])
        if ref is None:
            return _fail(ctx, "briefing-data", args_dict, f"bad date: {args_dict['date']!r} (expected YYYY-MM-DD)")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(args_dict["date"]).strip()):
            ref = ref.replace(hour=23, minute=59, second=59)
    else:
        ref = bundle["now"]
    codes = rollup.element_codes(framework)
    index = rollup.element_index(framework)
    companies = {c.get("id"): c for c in inputs["companies"] if isinstance(c, dict)}
    rep_deals = [d for d in inputs["allDeals"] if d.get("ownerId") == rep.get("id")]
    active = [d for d in rep_deals if rollup.deal_outcome(d, cfg) == "open"]
    active.sort(key=lambda d: (-rollup._num(d.get("amount"), 0.0), d.get("id") or ""))

    deals_out = []
    total_unassessed = 0
    for deal in active:
        did = deal.get("id")
        state = _state_for(bundle, deal)
        assessment = inputs["assessments"].get(did) or {}
        entry_map = {e.get("interactionId"): e for e in assessment.get("interactions") or [] if isinstance(e, dict)}
        stored = _stored(bundle, did)
        elements = {}
        for code in codes:
            st = (state.get("elements") or {}).get(code) or {}
            block = ((entry_map.get(st.get("interactionId")) or {}).get("elements") or {}).get(code) or {}
            elements[code] = {"level": st.get("level", 0), "decayed": bool(st.get("decayed")), "interactionId": st.get("interactionId"),
                              "lastAt": st.get("lastAt"), "quote": block.get("quote"), "speaker": block.get("speaker")}
        phase = state.get("phase") or rollup.current_phase(deal, cfg)
        timeline = rollup.stage_timeline(deal, cfg)
        stage_since = timeline[-1]["at"] if timeline else parse_iso(deal.get("createdAt"))
        last_at = _last_interaction_at(stored, ref)
        phase_rank = rollup._phase_rank(phase)
        applicable = [c for c in codes if phase_rank < 0 or rollup._phase_rank((index.get(c) or {}).get("applicableFrom") or "discovery") <= phase_rank]
        focus = []
        for code in sorted(applicable, key=lambda c: (elements[c]["level"], codes.index(c)))[:3]:
            el = index.get(code) or {}
            questions = el.get("questions") or []
            focus.append({"element": code, "name": el.get("name"), "level": elements[code]["level"],
                          "nextQuestion": el.get("nextQuestionAt1") or (questions[0] if questions else None),
                          "exampleQuote": (el.get("exampleQuotes") or {}).get("2") or None})
        assessed_ids = set(entry_map)
        unassessed = sum(1 for i in stored if i.get("id") not in assessed_ids)
        total_unassessed += unassessed
        company = companies.get(deal.get("companyId")) or {}
        deals_out.append({
            "dealId": did, "name": deal.get("name"), "company": company.get("name") or deal.get("companyDomain"),
            "amount": deal.get("amount"), "currency": deal.get("currency"), "stage": deal.get("stage"),
            "stageLabel": deal.get("stageLabel"), "phase": phase, "daysInStage": _days_between(ref, stage_since),
            "daysSinceLastInteraction": _days_between(ref, last_at), "lastInteractionAt": to_iso(last_at),
            "gate": state.get("gate"), "total": state.get("total"), "maxTotal": state.get("maxTotal"),
            "coverage2": state.get("coverage2"), "elements": elements, "stageGaps": state.get("stageGaps") or [],
            "focus": focus,
            "lastInteractions": [{"id": i.get("id"), "at": i.get("at"), "type": i.get("type"), "title": i.get("title"),
                                  "summary": i.get("summary")} for i in stored[::-1][:3]],
            "unassessedInteractions": unassessed,
        })

    rep_deal_ids = {d.get("id") for d in rep_deals}
    pending = []
    for link in (inputs["links"] or {}).get("links") or []:
        if not isinstance(link, dict) or link.get("status") != "pending":
            continue
        candidates = [c for c in (link.get("candidates") or []) if isinstance(c, dict)]
        hits = sorted({c.get("dealId") for c in candidates if c.get("dealId") in rep_deal_ids} | ({link.get("dealId")} & rep_deal_ids))
        if hits:
            pending.append({"interactionId": link.get("interactionId"), "at": link.get("at"), "method": link.get("method"),
                            "candidates": candidates, "repDeals": hits})

    week = iso_week(ref)
    last4 = [_slim(b) for b in _rep_buckets(bundle, rep.get("id")) if str(b.get("week")) <= week][-4:]
    team_last4 = [_slim(b) for b in _team_buckets(bundle) if str(b.get("week")) <= week][-4:]
    totals = (bundle["team_metrics"] or {}).get("totals") or {}
    pack = {
        "ok": True, "generatedAt": to_iso(bundle["now"]), "date": ref.date().isoformat(), "rep": _rep_block(bundle, rep),
        "deals": deals_out, "pendingLinks": pending, "unassessedInteractions": total_unassessed,
        "adoptionLast4Weeks": last4,
        "team": {"adoptionRate": totals.get("adoptionRate"), "winRate": (bundle["team_metrics"] or {}).get("winRate"),
                 "reps": totals.get("reps"), "last4Weeks": team_last4},
        "framework": {"slug": framework.get("slug"), "name": framework.get("name"), "source": bundle["frameworkSource"]},
        "computedInMemory": bundle["computedInMemory"],
    }
    _print(pack)
    ctx["store"].log_run("briefing-data", args_dict, True, ctx["started"], read=bundle["read"],
                         notes="analytics computed in memory" if bundle["computedInMemory"] else "")
    return 0


# ---------- retro-data ----------

def _parse_week(raw: Optional[str], now: _dt.datetime) -> Optional[_dt.datetime]:
    text = str(raw or "").strip().upper() or iso_week(now)
    m = re.fullmatch(r"(\d{4})-W(\d{1,2})", text)
    if not m:
        return None
    try:
        return _dt.datetime.fromisocalendar(int(m.group(1)), int(m.group(2)), 1).replace(tzinfo=_UTC)
    except ValueError:
        return None


def _pooled(buckets: dict, weeks: list[str]) -> dict:
    n = sum((buckets.get(w) or {}).get("interactions") or 0 for w in weeks)
    a = sum((buckets.get(w) or {}).get("applied") or 0 for w in weeks)
    return {"weeks": weeks, "interactions": n, "applied": a, "adoptionRate": rollup.ratio(a, n)}


def _bucket(buckets: dict, week: str) -> dict:
    return _slim(buckets.get(week) or {"week": week, "interactions": 0, "applied": 0, "adoptionRate": None})


def retro(ctx: dict, args: Any) -> int:
    args_dict = {"rep": getattr(args, "rep", None), "week": getattr(args, "week", None)}
    bundle = load_bundle(ctx)
    inputs, cfg, framework, now = bundle["inputs"], bundle["cfg"], bundle["framework"], bundle["now"]
    rep = resolve_rep(inputs["reps"], args_dict["rep"], {d.get("ownerId") for d in inputs["allDeals"]})
    if rep is None:
        return _fail(ctx, "retro-data", args_dict, f"rep not found: {args_dict['rep']!r} (try the id, email or name)")
    monday = _parse_week(args_dict["week"], now)
    if monday is None:
        return _fail(ctx, "retro-data", args_dict, f"bad week: {args_dict['week']!r} (expected YYYY-Www)")
    rid = rep.get("id")
    week = iso_week(monday)
    week_end = monday + _dt.timedelta(days=7)
    prev_week = iso_week(monday - _dt.timedelta(days=1))
    ref = min(week_end - _dt.timedelta(seconds=1), now)
    codes = rollup.element_codes(framework)

    rep_buckets = {str(b.get("week")): b for b in _rep_buckets(bundle, rid)}
    team_buckets = {str(b.get("week")): b for b in _team_buckets(bundle)}
    four_weeks = [iso_week(monday - _dt.timedelta(days=7 * k)) for k in range(3, -1, -1)]
    totals = (bundle["team_metrics"] or {}).get("totals") or {}
    adoption = {
        "thisWeek": _bucket(rep_buckets, week), "lastWeek": _bucket(rep_buckets, prev_week),
        "fourWeekAverage": _pooled(rep_buckets, four_weeks),
        "team": {"thisWeek": _bucket(team_buckets, week), "lastWeek": _bucket(team_buckets, prev_week),
                 "fourWeekAverage": _pooled(team_buckets, four_weeks), "overall": totals.get("adoptionRate")},
    }

    def in_week(at: Optional[_dt.datetime]) -> bool:
        return at is not None and monday <= at < week_end

    rep_deals = [d for d in inputs["allDeals"] if d.get("ownerId") == rid]
    owners = {d.get("id"): d.get("ownerId") for d in inputs["allDeals"]}
    by_type: Counter = Counter()
    for did, items in inputs["interactions"].items():
        for item in items or []:
            if not isinstance(item, dict):
                continue
            rep_of = item.get("repId") or owners.get(did)
            if rep_of == rid and in_week(parse_iso(item.get("at"))):
                by_type[item.get("type") or "unknown"] += 1
    for item in inputs["unlinked"]:
        if isinstance(item, dict) and item.get("repId") == rid and in_week(parse_iso(item.get("at"))):
            by_type[item.get("type") or "unknown"] += 1
    week_records = [r for r in bundle["records"] if r.get("repId") == rid and in_week(r.get("at"))]
    tags = Counter(t for r in week_records for t in r["tags"])

    moved = []
    closed = []
    stale = []
    for deal in rep_deals:
        did = deal.get("id")
        timeline = rollup.stage_timeline(deal, cfg)
        for i in range(1, len(timeline)):
            entry = timeline[i]
            if in_week(entry["at"]):
                prev = timeline[i - 1]
                moved.append({"dealId": did, "name": deal.get("name"), "at": to_iso(entry["at"]),
                              "from": {"stage": prev["stage"], "label": prev["label"], "phase": prev["phase"]},
                              "to": {"stage": entry["stage"], "label": entry["label"], "phase": entry["phase"]}})
        outcome = rollup.deal_outcome(deal, cfg)
        if outcome in rollup.CLOSED_OUTCOMES and in_week(parse_iso(deal.get("closedAt"))):
            state = _state_for(bundle, deal)
            closed.append({
                "dealId": did, "name": deal.get("name"), "outcome": outcome, "amount": deal.get("amount"),
                "currency": deal.get("currency"), "closedAt": deal.get("closedAt"), "cycleDays": state.get("cycleDays"),
                "total": state.get("total"), "maxTotal": state.get("maxTotal"), "coverage2": state.get("coverage2"),
                "gate": state.get("gate"), "evidenceQualityIndex": state.get("evidenceQualityIndex"),
                "elements": {c: ((state.get("elements") or {}).get(c) or {}).get("level", 0) for c in codes},
                "weakestElements": _weakest_levels(state, codes), "stageGaps": state.get("stageGaps") or [],
                "dealAdoption": state.get("dealAdoption"),
            })
        if outcome == "open":
            last_at = _last_interaction_at(_stored(bundle, did), ref)
            days = _days_between(ref, last_at or parse_iso(deal.get("createdAt")))
            if days is not None and days >= STALE_DAYS:
                stale.append({"dealId": did, "name": deal.get("name"), "amount": deal.get("amount"), "currency": deal.get("currency"),
                              "phase": rollup.current_phase(deal, cfg), "lastInteractionAt": to_iso(last_at),
                              "daysSinceLastInteraction": days})
    moved.sort(key=lambda m: m["at"])
    stale.sort(key=lambda s: -s["daysSinceLastInteraction"])

    store: Store = bundle["store"]
    focus_path = store.retros_dir / safe_id(str(rid)) / f"{prev_week}.md"
    previous_focus = None
    if focus_path.exists():
        try:
            for line in focus_path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("Focus:"):
                    previous_focus = line.strip()[len("Focus:"):].strip()
                    break
        except OSError:
            previous_focus = None

    rep_block = _rep_block(bundle, rep)
    team_metrics = bundle["team_metrics"] or {}
    weakness = [w for w in team_metrics.get("elementWeakness") or [] if isinstance(w, dict) and w.get("adoptionRate") is not None]
    team_weakest = [w["element"] for w in sorted(weakness, key=lambda w: (w["adoptionRate"], codes.index(w["element"]) if w["element"] in codes else 99))[:3]]
    rep_rate, team_rate = rep_block.get("adoptionRate"), totals.get("adoptionRate")
    comparison = {
        "adoptionRate": {"rep": rep_rate, "team": team_rate,
                         "delta": round(rep_rate - team_rate, rollup.ROUND) if rep_rate is not None and team_rate is not None else None},
        "thisWeek": {"rep": adoption["thisWeek"]["adoptionRate"], "team": adoption["team"]["thisWeek"]["adoptionRate"]},
        "winRate": {"rep": rep_block.get("winRate"), "team": team_metrics.get("winRate")},
        "weakestElements": {"rep": rep_block.get("weakestElements"), "team": team_weakest},
    }
    pack = {
        "ok": True, "generatedAt": to_iso(now), "rep": rep_block, "week": week, "weekStart": to_iso(monday),
        "weekEnd": to_iso(week_end), "previousWeek": prev_week, "adoption": adoption,
        "interactionsByType": dict(sorted(by_type.items())), "behaviourTags": dict(sorted(tags.items())),
        "dealsMoved": moved, "dealsClosed": closed, "staleDeals": stale, "staleAfterDays": STALE_DAYS,
        "previousRetroFocus": previous_focus, "previousRetroPath": str(focus_path), "comparison": comparison,
        "computedInMemory": bundle["computedInMemory"],
    }
    _print(pack)
    store.log_run("retro-data", args_dict, True, ctx["started"], read=bundle["read"],
                  notes="analytics computed in memory" if bundle["computedInMemory"] else "")
    return 0
