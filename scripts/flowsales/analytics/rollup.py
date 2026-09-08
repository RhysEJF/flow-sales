"""Analytics rollup (CONTRACTS section 9): deal states, rep metrics, team metrics, weekly timeseries.

The compute_* functions are pure (plain dicts in, plain dicts out) so impact.py and packs.py can
reuse them in memory when the analytics files are missing. run() wires them to the store.
Standard library only.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from ..config import Config
from ..store import Store
from ..util import iso_week, parse_iso, to_iso

PHASE_ORDER = ["discovery", "evaluation", "proposal", "commit", "won", "lost"]
OPEN_PHASES = PHASE_ORDER[:4]
CLOSED_OUTCOMES = ("won", "lost")
COVERAGE_BANDS = (("0-1", 0, 1), ("2-3", 2, 3), ("4-5", 4, 5), ("6-8", 6, None))
TERTILES = ("low", "mid", "high")
DEFAULT_COMMIT_GATE = {"all": 2, "E": 3, "CH": 3, "PP": 2}
DEFAULT_QUALIFY_OUT = {"maxTotal": 9, "minInteractions": 4}
DEFAULT_DECAY_DAYS = 45
ROUND = 3
_DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}")
_UTC = _dt.timezone.utc
_MIN_DT = _dt.datetime.min.replace(tzinfo=_UTC)

# ---------- framework ----------

# code, name, applicableFrom, stageExpectations, behaviourTags, nextQuestionAt1, level-2 example quote
_BUILTIN_ELEMENTS = [
    ("M", "Metrics", "discovery", {"discovery": 2, "evaluation": 2, "proposal": 2, "commit": 2},
     ["asked-metrics", "quantified-impact"], "What does this problem cost you today, in days or money?",
     "Month-end close takes us 11 days; we need it under 5 by the next audit."),
    ("E", "Economic Buyer", "evaluation", {"evaluation": 2, "proposal": 2, "commit": 3},
     ["identified-eb", "asked-eb-access", "engaged-eb"], "Who signs a purchase of this size?",
     "Our CFO, Dana, signs anything over 25k and wants to see it before the board meets."),
    ("DC", "Decision Criteria", "evaluation", {"evaluation": 2, "proposal": 2, "commit": 2},
     ["mapped-decision-criteria", "shaped-decision-criteria"], "What are the three things a solution must do for you to pick it?",
     "It has to integrate with NetSuite, close in under five days and pass our security review."),
    ("DP", "Decision Process", "evaluation", {"evaluation": 1, "proposal": 2, "commit": 2},
     ["mapped-decision-process", "agreed-mutual-plan"], "What are the steps between here and a signed order, and who owns each one?",
     "Finance reviews in week one, then IT signs off, then it goes to Dana for approval."),
    ("PP", "Paper Process", "proposal", {"proposal": 1, "commit": 2},
     ["asked-paper-process"], "Who reviews the contract, and how long did that take last time?",
     "Legal needs two weeks for any new vendor agreement and procurement raises the PO after that."),
    ("I", "Pain", "discovery", {"discovery": 2, "evaluation": 2, "proposal": 2, "commit": 2},
     ["identified-pain", "implicated-pain"], "What happens if this is still the case at the next audit?",
     "Every month the finance team loses a week reconciling spreadsheets by hand."),
    ("CH", "Champion", "discovery", {"discovery": 2, "evaluation": 2, "proposal": 2, "commit": 3},
     ["tested-champion", "developed-champion"], "Would you be willing to bring this to your leadership team?",
     "I have already put this on the agenda for our ops review next week."),
    ("CO", "Competition", "proposal", {"proposal": 2, "commit": 2},
     ["named-competition", "tested-status-quo", "positioned-differentiation"],
     "Which other options are you looking at, and what do you like about them?",
     "We are also looking at BlackLine, mainly because our auditors already know it."),
]


def builtin_framework() -> dict:
    """Minimal MEDDPICC definition used when frameworks/<slug>.json is not present."""
    elements = []
    for code, name, applicable_from, expectations, tags, next_q, example in _BUILTIN_ELEMENTS:
        elements.append({
            "code": code, "name": name,
            "definition": f"{name}: what the buyer has said, on the record, about this part of the decision.",
            "questions": [next_q], "evidenceSignals": ["A named person", "A number or a date", "A consequence stated by the buyer"],
            "anchors": {"0": "Not mentioned in any interaction.", "1": "Mentioned without specifics, or only by the rep.",
                        "2": "Specific and quoted from the buyer: a name, a number, a step or a date.",
                        "3": "Confirmed by the buyer with ownership or consequence, and consistent across interactions."},
            "exampleQuotes": {"1": "", "2": example, "3": ""},
            "nextQuestionAt1": next_q, "behaviourTags": list(tags), "failureModes": [],
            "stageExpectations": dict(expectations), "applicableFrom": applicable_from,
        })
    return {
        "slug": "meddpicc", "name": "MEDDPICC", "version": "builtin", "maxLevel": 3, "elements": elements,
        "generalBehaviourTags": ["secured-next-step", "multi-threaded", "summarised-and-confirmed"],
        "scoring": {"quoteRequiredAbove": 1, "decayDays": DEFAULT_DECAY_DAYS, "commitGate": dict(DEFAULT_COMMIT_GATE),
                    "qualifyOut": dict(DEFAULT_QUALIFY_OUT)},
        "sources": ["built-in fallback definition (frameworks/meddpicc.json not found)"],
    }


def load_framework(plugin_root: Path | str, slug: str) -> tuple[dict, str]:
    """(framework, source): the file under plugin_root/frameworks when present, else the built-in definition."""
    path = Path(plugin_root) / "frameworks" / f"{slug}.json"
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as fh:
                fw = json.load(fh)
        except (OSError, ValueError):
            fw = None
        if isinstance(fw, dict) and fw.get("elements"):
            return fw, str(path)
    return builtin_framework(), "builtin"


def element_codes(framework: dict) -> list[str]:
    return [e.get("code") for e in (framework.get("elements") or []) if isinstance(e, dict) and e.get("code")]


def element_index(framework: dict) -> dict[str, dict]:
    return {e.get("code"): e for e in (framework.get("elements") or []) if isinstance(e, dict) and e.get("code")}


# ---------- small helpers ----------

def _int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def _num(value: Any, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def amount_by_currency(states: Iterable[dict]) -> dict[str, float]:
    """Sum deal amounts per currency code; money is never converted (CONTRACTS 9)."""
    out: dict[str, float] = {}
    for s in states:
        cur = str(s.get("currency") or "unknown")
        out[cur] = round(out.get(cur, 0.0) + _num(s.get("amount"), 0.0), 2)
    return dict(sorted(out.items()))


def ratio(numerator: float, denominator: float) -> Optional[float]:
    """None when the denominator is zero; every ratio in the outputs goes through here."""
    if not denominator:
        return None
    return round(numerator / denominator, ROUND)


def average(values: list) -> Optional[float]:
    vals = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not vals:
        return None
    return round(sum(vals) / len(vals), ROUND)


def _as_config(cfg: Any) -> Config:
    if isinstance(cfg, Config):
        return cfg
    return Config(dict(cfg or {}), Path("config.json"))


def _as_dt(value: Any) -> _dt.datetime:
    if isinstance(value, _dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=_UTC)
    return parse_iso(value) or _dt.datetime.now(_UTC)


def _phase_rank(phase: Optional[str]) -> int:
    return PHASE_ORDER.index(phase) if phase in PHASE_ORDER else -1


def _sort_key(rec: dict) -> tuple:
    return (rec["at"] is None, rec["at"] or _MIN_DT, rec.get("interactionId") or "")


def window_bounds(cfg: Config) -> tuple[Optional[_dt.datetime], Optional[_dt.datetime]]:
    """Inclusive window bounds; a date-only 'to' covers the whole day (same rule as the planner)."""
    start_raw, end_raw = cfg.window
    start = parse_iso(start_raw) if start_raw else None
    end = parse_iso(end_raw) if end_raw else None
    if end is not None and _DATE_ONLY.fullmatch(str(end_raw).strip()):
        end = end + _dt.timedelta(days=1) - _dt.timedelta(microseconds=1)
    return start, end


def _within(at: Optional[_dt.datetime], start: Optional[_dt.datetime], end: Optional[_dt.datetime]) -> bool:
    if at is None:
        return False
    if start is not None and at < start:
        return False
    if end is not None and at > end:
        return False
    return True


def deal_in_window(deal: dict, start: Optional[_dt.datetime], end: Optional[_dt.datetime]) -> bool:
    if start is None and end is None:
        return True
    return _within(parse_iso(deal.get("createdAt")), start, end) or _within(parse_iso(deal.get("closedAt")), start, end)


def deal_outcome(deal: dict, cfg: Config) -> str:
    outcome = str(deal.get("outcome") or "").lower()
    if outcome in ("won", "lost", "open"):
        return outcome
    phase = deal.get("phase") or cfg.phase_for_stage(deal.get("stage"), deal.get("stageLabel"))
    return phase if phase in CLOSED_OUTCOMES else "open"


def stage_timeline(deal: dict, cfg: Config) -> list[dict]:
    """stageHistory entries with a usable time, in time order: {at, phase, stage, label}."""
    timeline = []
    for entry in deal.get("stageHistory") or []:
        if not isinstance(entry, dict):
            continue
        at = parse_iso(entry.get("at"))
        if at is None:
            continue
        phase = entry.get("phase") or cfg.phase_for_stage(entry.get("stage"), entry.get("label"))
        timeline.append({"at": at, "phase": phase, "stage": entry.get("stage"), "label": entry.get("label")})
    timeline.sort(key=lambda e: e["at"])
    return timeline


def current_phase(deal: dict, cfg: Config) -> str:
    if deal.get("phase") in PHASE_ORDER:
        return deal["phase"]
    if deal.get("stage") or deal.get("stageLabel"):
        return cfg.phase_for_stage(deal.get("stage"), deal.get("stageLabel"))
    return "evaluation"


def reference_phase(deal: dict, cfg: Config, outcome: Optional[str] = None) -> Optional[str]:
    """The phase stage gaps are judged against: current phase for open deals, last phase before close otherwise."""
    outcome = outcome or deal_outcome(deal, cfg)
    if outcome in CLOSED_OUTCOMES:
        for entry in reversed(stage_timeline(deal, cfg)):
            if entry["phase"] in OPEN_PHASES:
                return entry["phase"]
        return None
    phase = current_phase(deal, cfg)
    return phase if phase in OPEN_PHASES else None


def phase_ends(deal: dict, cfg: Config, outcome: str, closed_at: Optional[_dt.datetime]) -> dict[str, _dt.datetime]:
    """When the deal left each phase (last exit wins). A closed deal leaves its final open phase at closedAt."""
    ends: dict[str, _dt.datetime] = {}
    prev: Optional[dict] = None
    for entry in stage_timeline(deal, cfg):
        if prev is not None and entry["phase"] != prev["phase"]:
            ends[prev["phase"]] = entry["at"]
        prev = entry
    if outcome in CLOSED_OUTCOMES and prev is not None and prev["phase"] in OPEN_PHASES and closed_at is not None:
        ends[prev["phase"]] = closed_at
    return ends


# ---------- assessment entries ----------

def effective_evidence(block: dict) -> int:
    """Evidence usable for scoring: above 1 only when the quote was verified; otherwise capped at 1."""
    ev = max(0, _int(block.get("evidence")))
    if ev <= 1:
        return ev
    return ev if block.get("verified") is True else 1


def assessed_entries(assessment: Optional[dict], interactions: Optional[list], codes: list[str],
                     default_rep: Optional[str] = None) -> list[dict]:
    """Normalised, time-ordered assessment entries (one per interaction id) with effective evidence per element."""
    stored = {i.get("id"): i for i in (interactions or []) if isinstance(i, dict) and i.get("id")}
    seen: set[str] = set()
    out: list[dict] = []
    for entry in (assessment or {}).get("interactions") or []:
        if not isinstance(entry, dict):
            continue
        iid = entry.get("interactionId")
        if not iid or iid in seen:
            continue
        seen.add(iid)
        inter = stored.get(iid) or {}
        at = parse_iso(entry.get("at") or inter.get("at"))
        raw_elements = entry.get("elements") if isinstance(entry.get("elements"), dict) else {}
        applicable = entry.get("applicable")
        if not isinstance(applicable, list):
            applicable = list(raw_elements.keys())
        applicable = [c for c in applicable if c in codes]
        elements: dict[str, dict] = {}
        tags_all: list[str] = []
        for code in codes:
            block = raw_elements.get(code)
            if not isinstance(block, dict):
                continue
            tags = [t for t in (block.get("behaviourTags") or []) if isinstance(t, str) and t]
            elements[code] = {
                "evidence": effective_evidence(block), "rawEvidence": _int(block.get("evidence")),
                "speaker": block.get("speaker"), "behaviour": _int(block.get("behaviour")) == 1 or bool(tags),
                "tags": tags, "quote": block.get("quote"), "verified": block.get("verified"),
            }
            tags_all.extend(tags)
        out.append({
            "interactionId": iid, "at": at, "atIso": to_iso(at) if at else None,
            "type": inter.get("type") or entry.get("type"), "repId": inter.get("repId") or default_rep,
            "phaseAtTime": entry.get("phaseAtTime"), "applicable": applicable, "elements": elements,
            "tags": tags_all, "applied": bool(tags_all),
        })
    out.sort(key=_sort_key)
    return out


def _evidence(rec: dict, code: str) -> int:
    block = rec["elements"].get(code)
    return block["evidence"] if block else 0


def _coverage2(entries: list[dict], codes: list[str]) -> int:
    return sum(1 for code in codes if any(_evidence(r, code) >= 2 for r in entries))


# ---------- deal state ----------

def compute_deal_state(deal: dict, assessment: Optional[dict], interactions: Optional[list], framework: dict,
                       cfg: Any, now: Any) -> dict:
    cfg = _as_config(cfg)
    now = _as_dt(now)
    codes = element_codes(framework)
    index = element_index(framework)
    max_level = _int(framework.get("maxLevel")) or 3
    scoring = framework.get("scoring") if isinstance(framework.get("scoring"), dict) else {}
    decay_days = _num(cfg.get("attribution.decayDays"), _num(scoring.get("decayDays"), DEFAULT_DECAY_DAYS))
    outcome = deal_outcome(deal, cfg)
    closed_at = parse_iso(deal.get("closedAt")) if outcome in CLOSED_OUTCOMES else None
    created_at = parse_iso(deal.get("createdAt"))
    win_start, win_end = window_bounds(cfg)
    reference_at = closed_at or (win_end if outcome == "open" else None) or now
    stored = [i for i in (interactions or []) if isinstance(i, dict)]
    entries = assessed_entries(assessment, stored, codes, default_rep=deal.get("ownerId"))
    assessed = assessment is not None

    # element levels with decay
    elements: dict[str, dict] = {}
    levels: dict[str, int] = {}
    for code in codes:
        raw = 0
        first_at = None
        for rec in entries:
            ev = _evidence(rec, code)
            if ev >= 1 and first_at is None:
                first_at = rec["at"]
            raw = max(raw, ev)
        last_support = None
        support_id = None
        if raw >= 1:
            band = 2 if raw >= 2 else 1
            for rec in entries:
                ev = _evidence(rec, code)
                if ev >= band and rec["at"] is not None:
                    last_support = rec["at"]
                if ev == raw:
                    support_id = rec["interactionId"]
        level, decayed = raw, False
        if raw >= 2 and last_support is not None and reference_at is not None:
            if (reference_at - last_support).total_seconds() > decay_days * 86400:
                level, decayed = raw - 1, True
        elements[code] = {"level": level, "firstAt": to_iso(first_at), "lastAt": to_iso(last_support),
                          "interactionId": support_id, "decayed": decayed}
        levels[code] = level

    total = sum(levels.values())
    max_total = max_level * len(codes)
    coverage2 = sum(1 for v in levels.values() if v >= 2)
    coverage3 = sum(1 for v in levels.values() if v >= 3)

    # gate
    gate_cfg = scoring.get("commitGate") if isinstance(scoring.get("commitGate"), dict) else DEFAULT_COMMIT_GATE
    qo_cfg = scoring.get("qualifyOut") if isinstance(scoring.get("qualifyOut"), dict) else DEFAULT_QUALIFY_OUT
    gate_all = _int(gate_cfg.get("all")) or 2
    commit_ok = bool(codes) and all(levels[c] >= gate_all for c in codes) and all(
        levels[c] >= _int(v) for c, v in gate_cfg.items() if c != "all" and c in levels)
    ref_phase = reference_phase(deal, cfg, outcome)
    past_evaluation = _phase_rank(ref_phase) > _phase_rank("evaluation")
    zero_eb_or_champion = any(levels.get(c) == 0 for c in ("E", "CH") if c in levels)
    qualify_out = (total <= _int(qo_cfg.get("maxTotal")) and len(entries) >= _int(qo_cfg.get("minInteractions"))) or (
        past_evaluation and zero_eb_or_champion)
    if commit_ok:
        gate = "commit-eligible"
    elif qualify_out:
        gate = "qualify-out"
    elif coverage2 >= 6:
        gate = "upside"
    else:
        gate = "pipeline"

    # evidence quality: share of element scores of 2 or more that come from buyer quotes
    hi = [rec["elements"][c] for rec in entries for c in codes if rec["elements"].get(c) and rec["elements"][c]["evidence"] >= 2]
    eqi = ratio(sum(1 for b in hi if b.get("speaker") == "buyer"), len(hi))

    applied = sum(1 for r in entries if r["applied"])
    behaviours = sum(len(r["tags"]) for r in entries)
    n_interactions = len(entries) if assessed else len(stored)

    # coverage at phase end
    ends = phase_ends(deal, cfg, outcome, closed_at)
    coverage_at_phase_end = {}
    for phase in OPEN_PHASES:
        end_at = ends.get(phase)
        if end_at is None:
            continue
        coverage_at_phase_end[phase] = _coverage2([r for r in entries if r["at"] is not None and r["at"] < end_at], codes)

    # stage gaps against the framework expectations for the reference phase
    stage_gaps = []
    if ref_phase in OPEN_PHASES:
        for code in codes:
            expectations = (index.get(code) or {}).get("stageExpectations") or {}
            expected = _int(expectations.get(ref_phase))
            if expected > 0 and levels[code] < expected:
                stage_gaps.append({"phase": ref_phase, "element": code, "expected": expected, "actual": levels[code]})

    # influenced
    attribution = cfg.get("attribution") if isinstance(cfg.get("attribution"), dict) else {}
    min_b = _int(attribution.get("influencedMinBehaviours")) or 3
    min_i = _int(attribution.get("influencedMinInteractions")) or 2
    training_raw = cfg.get("trainingDate")
    training = parse_iso(training_raw) if training_raw else None
    if training is not None:
        period_from, period_to = training, None
        period_text = f"after {str(training_raw)[:10]}"
    else:
        period_from, period_to = win_start, win_end
        w_from, w_to = cfg.window
        period_text = f"inside window {w_from or 'start'} to {w_to or 'end'}"
    running = {code: 0 for code in codes}
    moved: dict[str, tuple[int, int]] = {}
    b_count = 0
    i_count = 0
    for rec in entries:
        in_period = rec["at"] is not None and _within(rec["at"], period_from, period_to)
        for code in codes:
            ev = _evidence(rec, code)
            prev = running[code]
            if ev > prev:
                running[code] = ev
                if in_period and prev <= 1 and ev >= 2 and code not in moved:
                    moved[code] = (prev, ev)
        if in_period:
            b_count += len(rec["tags"])
            if rec["tags"]:
                i_count += 1
    moved_codes = [c for c in codes if c in moved]
    is_influenced = outcome == "won" and b_count >= min_b and i_count >= min_i and bool(moved_codes)
    rule = f"{b_count} behaviours across {i_count} interactions {period_text}"
    if moved_codes:
        rule += " and " + ", ".join(f"{c} moved {moved[c][0]} to {moved[c][1]}" for c in moved_codes)
    if outcome != "won":
        rule += f"; deal is {outcome}, not won"
    rule += f" (rule: won deal, at least {min_b} behaviours across at least {min_i} interactions, one element moved from 0-1 to 2-3)"

    cycle_days = None
    if closed_at is not None and created_at is not None:
        cycle_days = max(0, int((closed_at - created_at).total_seconds() // 86400))
    stored_times = [parse_iso(i.get("at")) for i in stored]
    stored_times = [t for t in stored_times if t is not None]

    return {
        "dealId": deal.get("id"), "name": deal.get("name"), "outcome": outcome, "ownerId": deal.get("ownerId"),
        "amount": deal.get("amount"), "currency": deal.get("currency"), "closedAt": to_iso(closed_at) if closed_at else None,
        "createdAt": deal.get("createdAt"), "cycleDays": cycle_days,
        "stage": deal.get("stage"), "stageLabel": deal.get("stageLabel"), "phase": ref_phase,
        "elements": elements, "total": total, "maxTotal": max_total, "coverage2": coverage2, "coverage3": coverage3,
        "gate": gate, "evidenceQualityIndex": eqi,
        "interactions": n_interactions, "behaviours": behaviours, "appliedInteractions": applied,
        "dealAdoption": ratio(applied, len(entries)) if assessed else None,
        "coverageAtPhaseEnd": coverage_at_phase_end, "stageGaps": stage_gaps,
        "influenced": {"isInfluenced": is_influenced, "rule": rule, "behaviours": b_count, "interactions": i_count,
                       "movedElements": moved_codes},
        "assessed": assessed, "interactionsStored": len(stored),
        "lastInteractionAt": to_iso(max(stored_times)) if stored_times else None,
    }


# ---------- records (flattened assessed interactions, one per interaction) ----------

def build_records(inputs: dict, cfg: Any, framework: dict) -> list[dict]:
    cfg = _as_config(cfg)
    codes = element_codes(framework)
    records: list[dict] = []
    assessments = inputs.get("assessments") or {}
    interactions = inputs.get("interactions") or {}
    for deal in inputs.get("deals") or []:
        did = deal.get("id")
        assessment = assessments.get(did)
        if not assessment:
            continue
        for rec in assessed_entries(assessment, interactions.get(did), codes, default_rep=deal.get("ownerId")):
            rec["dealId"] = did
            rec["ownerId"] = deal.get("ownerId")
            records.append(rec)
    records.sort(key=_sort_key)
    return records


def select_reps(reps: list[dict], deal_states: list[dict], records: list[dict], cfg: Any) -> list[dict]:
    """reps.json entries plus any owner or rep id seen in the data, filtered by config.reps when it is a list."""
    cfg = _as_config(cfg)
    known: dict[str, dict] = {r["id"]: dict(r) for r in reps or [] if isinstance(r, dict) and r.get("id")}
    for rid in [s.get("ownerId") for s in deal_states] + [r.get("repId") for r in records]:
        if rid and rid not in known:
            known[rid] = {"id": rid, "name": None, "email": None, "source": "derived"}
    allowed = cfg.get("reps")
    if isinstance(allowed, list):
        wanted = set(allowed)
        return [rep for rid, rep in known.items() if rid in wanted]
    return list(known.values())


def _element_adoption(records: list[dict], codes: list[str]) -> dict[str, Optional[float]]:
    applicable: Counter = Counter()
    applied: Counter = Counter()
    for rec in records:
        for code in rec["applicable"]:
            applicable[code] += 1
            block = rec["elements"].get(code)
            if block and block["behaviour"]:
                applied[code] += 1
    return {code: ratio(applied[code], applicable[code]) for code in codes}


def _ranked(adoption: dict, codes: list[str], lowest: bool, k: int = 3) -> list[str]:
    scored = [(adoption[c], i, c) for i, c in enumerate(codes) if adoption.get(c) is not None]
    scored.sort(key=lambda t: (t[0] if lowest else -t[0], t[1]))
    return [c for _, _, c in scored[:k]]


def _eqi(records: list[dict]) -> Optional[float]:
    hi = [b for rec in records for b in rec["elements"].values() if b["evidence"] >= 2]
    return ratio(sum(1 for b in hi if b.get("speaker") == "buyer"), len(hi))


def _split_training(records: list[dict], training: Optional[_dt.datetime]) -> tuple[list[dict], list[dict]]:
    if training is None:
        return [], []
    before = [r for r in records if r["at"] is not None and r["at"] < training]
    after = [r for r in records if r["at"] is not None and r["at"] >= training]
    return before, after


def _adoption_block(records: list[dict]) -> dict:
    return {"adoptionRate": ratio(sum(1 for r in records if r["applied"]), len(records)), "n": len(records)}


def _win_rate(states: list[dict]) -> Optional[float]:
    won = sum(1 for s in states if s.get("outcome") == "won")
    closed = sum(1 for s in states if s.get("outcome") in CLOSED_OUTCOMES)
    return ratio(won, closed)


# ---------- rep metrics ----------

def compute_rep_metrics(reps: list[dict], deal_states: list[dict], records: list[dict], framework: dict, cfg: Any) -> list[dict]:
    cfg = _as_config(cfg)
    codes = element_codes(framework)
    training = parse_iso(cfg.get("trainingDate")) if cfg.get("trainingDate") else None
    out = []
    for rep in reps:
        rid = rep.get("id")
        recs = [r for r in records if r.get("repId") == rid]
        states = [s for s in deal_states if s.get("ownerId") == rid]
        won = [s for s in states if s.get("outcome") == "won"]
        lost = [s for s in states if s.get("outcome") == "lost"]
        open_ = [s for s in states if s.get("outcome") == "open"]
        applied = sum(1 for r in recs if r["applied"])
        adoption = _element_adoption(recs, codes)
        before, after = _split_training(recs, training)
        b_block, a_block = _adoption_block(before), _adoption_block(after)
        lift = None
        if b_block["adoptionRate"] is not None and a_block["adoptionRate"] is not None:
            lift = round(a_block["adoptionRate"] - b_block["adoptionRate"], ROUND)
        tags = Counter(t for r in recs for t in r["tags"])
        out.append({
            "repId": rid, "name": rep.get("name"), "email": rep.get("email"),
            "interactions": len(recs), "appliedInteractions": applied, "adoptionRate": ratio(applied, len(recs)),
            "adoptionByElement": adoption, "behaviourTagCounts": dict(sorted(tags.items())),
            "dealsWon": len(won), "dealsLost": len(lost), "dealsOpen": len(open_),
            "winRate": ratio(len(won), len(won) + len(lost)),
            "avgCoverageAtClose": {"won": average([s.get("coverage2") for s in won]), "lost": average([s.get("coverage2") for s in lost])},
            "avgTotalWon": average([s.get("total") for s in won]), "avgTotalLost": average([s.get("total") for s in lost]),
            "beforeTraining": b_block, "afterTraining": a_block, "adoptionLift": lift,
            "weakestElements": _ranked(adoption, codes, True), "strongestElements": _ranked(adoption, codes, False),
            "evidenceQualityIndex": _eqi(recs),
        })
    return out


# ---------- team metrics ----------

def _band_of(value: int) -> str:
    for label, lo, hi in COVERAGE_BANDS:
        if value >= lo and (hi is None or value <= hi):
            return label
    return COVERAGE_BANDS[-1][0] if value >= 0 else COVERAGE_BANDS[0][0]


def data_coverage(inputs: dict, records: list[dict]) -> dict:
    by_type: Counter = Counter()
    deals_with_transcripts = 0
    without: list[str] = []
    stored_ids: set[str] = set()
    n_stored = 0
    interactions = inputs.get("interactions") or {}
    for deal in inputs.get("deals") or []:
        items = [i for i in (interactions.get(deal.get("id")) or []) if isinstance(i, dict)]
        if not items:
            without.append(deal.get("id"))
        if any(i.get("transcript") or i.get("type") == "transcript" for i in items):
            deals_with_transcripts += 1
        for item in items:
            by_type[item.get("type") or "unknown"] += 1
            n_stored += 1
            if item.get("id"):
                stored_ids.add(item["id"])
    assessed_ids = {r["interactionId"] for r in records}
    return {
        "interactionsByType": dict(sorted(by_type.items())), "interactionsStored": n_stored,
        "dealsWithTranscripts": deals_with_transcripts, "dealsWithoutInteractions": len(without),
        "dealsWithoutInteractionIds": without, "unlinkedInteractions": len(inputs.get("unlinked") or []),
        "interactionsAssessed": len(records), "interactionsUnassessed": len(stored_ids - assessed_ids),
    }


def compute_team_metrics(deal_states: list[dict], records: list[dict], reps: list[dict], framework: dict, cfg: Any,
                         coverage: Optional[dict] = None) -> dict:
    cfg = _as_config(cfg)
    codes = element_codes(framework)
    index = element_index(framework)
    won = [s for s in deal_states if s.get("outcome") == "won"]
    lost = [s for s in deal_states if s.get("outcome") == "lost"]
    open_ = [s for s in deal_states if s.get("outcome") == "open"]
    closed = won + lost
    applied = sum(1 for r in records if r["applied"])
    totals = {
        "deals": len(deal_states), "dealsAssessed": sum(1 for s in deal_states if s.get("assessed")),
        "dealsWon": len(won), "dealsLost": len(lost), "dealsOpen": len(open_), "reps": len(reps),
        "interactions": len(records), "appliedInteractions": applied, "adoptionRate": ratio(applied, len(records)),
        "behaviours": sum(len(r["tags"]) for r in records),
        "amountWon": round(sum(_num(s.get("amount"), 0.0) for s in won), 2),
        "amountWonByCurrency": amount_by_currency(won),
        "currencies": sorted({str(s.get("currency")) for s in deal_states if s.get("currency")}),
    }

    # win rate by adoption tertile (closed deals, cut points on dealAdoption)
    scored = sorted([s for s in closed if s.get("dealAdoption") is not None], key=lambda s: s["dealAdoption"])
    groups: dict[str, list[dict]] = {t: [] for t in TERTILES}
    if scored:
        vals = [s["dealAdoption"] for s in scored]
        n = len(vals)
        q1, q2 = vals[n // 3], vals[(2 * n) // 3]
        groups["low"] = [s for s in scored if s["dealAdoption"] < q1]
        groups["mid"] = [s for s in scored if q1 <= s["dealAdoption"] < q2]
        groups["high"] = [s for s in scored if s["dealAdoption"] >= q2]
    tertiles = []
    for name in TERTILES:
        group = groups[name]
        cycles = [s["cycleDays"] for s in group if isinstance(s.get("cycleDays"), (int, float)) and not isinstance(s.get("cycleDays"), bool)]
        adoptions = [s["dealAdoption"] for s in group]
        tertiles.append({
            "tertile": name, "n": len(group), "winRate": _win_rate(group),
            "medianCycleDays": round(float(statistics.median(cycles)), 1) if cycles else None,
            "avgAmount": average([_num(s.get("amount"), 0.0) for s in group]) if group else None,
            "adoptionRange": [min(adoptions), max(adoptions)] if adoptions else None,
        })

    # win rate by coverage at phase end
    by_coverage = {}
    for phase in ("discovery", "evaluation"):
        rows = []
        for label, _lo, _hi in COVERAGE_BANDS:
            group = []
            for s in closed:
                value = (s.get("coverageAtPhaseEnd") or {}).get(phase)
                if isinstance(value, int) and not isinstance(value, bool) and _band_of(value) == label:
                    group.append(s)
            rows.append({"coverageBand": label, "n": len(group), "winRate": _win_rate(group)})
        by_coverage[phase] = rows

    team_adoption = _element_adoption(records, codes)
    weakness = []
    for code in codes:
        weakness.append({
            "element": code, "name": (index.get(code) or {}).get("name"),
            "avgLevelWon": average([(s.get("elements") or {}).get(code, {}).get("level") for s in won]),
            "avgLevelLost": average([(s.get("elements") or {}).get(code, {}).get("level") for s in lost]),
            "adoptionRate": team_adoption[code],
        })

    training_raw = cfg.get("trainingDate")
    training = parse_iso(training_raw) if training_raw else None
    before_r, after_r = _split_training(records, training)
    before_d: list[dict] = []
    after_d: list[dict] = []
    if training is not None:
        for s in closed:
            at = parse_iso(s.get("closedAt"))
            if at is None:
                continue
            (before_d if at < training else after_d).append(s)
    before_after = {
        "trainingDate": str(training_raw) if training else None,
        "before": {**_adoption_block(before_r), "dealsClosed": len(before_d), "winRate": _win_rate(before_d)},
        "after": {**_adoption_block(after_r), "dealsClosed": len(after_d), "winRate": _win_rate(after_d)},
    }

    data_cov = dict(coverage or {})
    data_cov.setdefault("interactionsByType", dict(sorted(Counter(r.get("type") or "unknown" for r in records).items())))
    data_cov.setdefault("dealsWithTranscripts", None)
    data_cov.setdefault("dealsWithoutInteractions", sum(1 for s in deal_states if not s.get("interactions")))
    data_cov.setdefault("unlinkedInteractions", None)
    data_cov.setdefault("interactionsAssessed", len(records))
    data_cov.setdefault("interactionsUnassessed", None)

    return {
        "totals": totals, "winRate": _win_rate(closed), "winRateByAdoptionTertile": tertiles,
        "winRateByCoverageAtPhaseEnd": by_coverage, "elementWeakness": weakness, "beforeAfter": before_after,
        "dataCoverage": data_cov,
    }


# ---------- timeseries ----------

def _week_start(d: _dt.datetime) -> _dt.datetime:
    d = d.astimezone(_UTC)
    return (d - _dt.timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def compute_timeseries(records: list[dict], reps: list[dict], framework: dict, cfg: Any) -> dict:
    cfg = _as_config(cfg)
    codes = element_codes(framework)
    start, end = window_bounds(cfg)
    dated = [r for r in records if r["at"] is not None]
    points = [d for d in [start, end] + [r["at"] for r in dated] if d is not None]
    weeks: list[str] = []
    if points:
        cur, last = _week_start(min(points)), _week_start(max(points))
        while cur <= last:
            weeks.append(iso_week(cur))
            cur += _dt.timedelta(days=7)
    rep_ids = [r.get("id") for r in reps if isinstance(r, dict) and r.get("id")]
    for rec in dated:
        if rec.get("repId") and rec["repId"] not in rep_ids:
            rep_ids.append(rec["repId"])

    def empty(week: str) -> dict:
        return {"week": week, "interactions": 0, "applied": 0, "adoptionRate": None, "byElement": {c: 0 for c in codes}}

    team = {w: empty(w) for w in weeks}
    per_rep = {rid: {w: empty(w) for w in weeks} for rid in rep_ids}
    for rec in dated:
        week = iso_week(rec["at"])
        targets = [team.get(week)]
        if rec.get("repId") in per_rep:
            targets.append(per_rep[rec["repId"]].get(week))
        for bucket in targets:
            if bucket is None:
                continue
            bucket["interactions"] += 1
            bucket["applied"] += 1 if rec["applied"] else 0
            for code in codes:
                block = rec["elements"].get(code)
                if block and block["behaviour"]:
                    bucket["byElement"][code] += 1

    def finish(buckets: dict) -> list[dict]:
        out = []
        for w in weeks:
            b = buckets[w]
            b["adoptionRate"] = ratio(b["applied"], b["interactions"])
            out.append(b)
        return out

    return {"weeks": weeks, "team": finish(team), "reps": {rid: finish(per_rep[rid]) for rid in rep_ids}}


# ---------- store wiring ----------

def load_inputs(store: Store) -> dict:
    """Everything the analytics need, read once: deals in the window, reps, interactions, assessments, links."""
    cfg = store.config
    start, end = window_bounds(cfg)
    all_deals = [d for d in store.load_deals() if isinstance(d, dict) and d.get("id")]
    deals = [d for d in all_deals if deal_in_window(d, start, end)]
    read = [str(store.data_dir / "deals.json"), str(store.data_dir / "reps.json"), str(store.assessments_dir)]
    interactions = {}
    for deal in deals:
        interactions[deal["id"]] = store.load_interactions(deal["id"])
        read.append(str(store.interactions_path(deal["id"])))
    assessments = {a.get("dealId"): a for a in store.iter_assessments() if isinstance(a, dict) and a.get("dealId")}
    return {
        "deals": deals, "allDeals": all_deals, "reps": store.load_reps(), "interactions": interactions,
        "unlinked": store.load_unlinked(), "assessments": assessments, "companies": store.load_companies(),
        "links": store.load_links(), "read": read,
    }


def compute_all(inputs: dict, framework: dict, cfg: Any, now: Any) -> dict:
    cfg = _as_config(cfg)
    now = _as_dt(now)
    assessments = inputs.get("assessments") or {}
    interactions = inputs.get("interactions") or {}
    deal_states = [compute_deal_state(d, assessments.get(d.get("id")), interactions.get(d.get("id")) or [], framework, cfg, now)
                   for d in inputs.get("deals") or []]
    records = build_records(inputs, cfg, framework)
    reps = select_reps(inputs.get("reps") or [], deal_states, records, cfg)
    rep_metrics = compute_rep_metrics(reps, deal_states, records, framework, cfg)
    coverage = data_coverage(inputs, records)
    team_metrics = compute_team_metrics(deal_states, records, reps, framework, cfg, coverage)
    timeseries = compute_timeseries(records, reps, framework, cfg)
    return {"deal_states": deal_states, "rep_metrics": rep_metrics, "team_metrics": team_metrics,
            "timeseries": timeseries, "records": records, "reps": reps}


def _args_dict(args: Any) -> dict:
    try:
        items = dict(vars(args))
    except TypeError:
        return {}
    return {k: v for k, v in items.items() if k not in ("command", "home", "json") and v is not None}


def _fmt(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    want_json = bool(ctx.get("json") or getattr(args, "json", False))
    if not store.exists():
        msg = f"no FlowSales store at {store.home} (run init first)"
        print(json.dumps({"ok": False, "error": msg}) if want_json else f"error: {msg}", file=sys.stderr)
        return 1
    cfg = store.config
    framework, source = load_framework(ctx["plugin_root"], cfg.framework)
    inputs = load_inputs(store)
    out = compute_all(inputs, framework, cfg, _as_dt(ctx.get("now")))
    wrote = [str(store.write_json(f"analytics/{name}.json", out[name]))
             for name in ("deal_states", "rep_metrics", "team_metrics", "timeseries")]
    read = list(inputs["read"]) + ([source] if source != "builtin" else [])
    totals = out["team_metrics"]["totals"]
    summary = {
        "ok": True, "deals": totals["deals"], "dealsAssessed": totals["dealsAssessed"], "dealsWon": totals["dealsWon"],
        "dealsLost": totals["dealsLost"], "dealsOpen": totals["dealsOpen"], "reps": totals["reps"],
        "interactions": totals["interactions"], "adoptionRate": totals["adoptionRate"],
        "winRate": out["team_metrics"]["winRate"], "framework": source, "wrote": wrote,
    }
    store.log_run("rollup", _args_dict(args), True, ctx["started"], read=read, wrote=wrote, notes=f"framework: {source}")
    if want_json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"Rollup: {totals['deals']} deals ({totals['dealsAssessed']} assessed, {totals['dealsWon']} won, "
              f"{totals['dealsLost']} lost, {totals['dealsOpen']} open), {totals['reps']} reps, "
              f"{totals['interactions']} assessed interactions, adoption {_fmt(totals['adoptionRate'])}, "
              f"win rate {_fmt(out['team_metrics']['winRate'])}.")
        print(f"Framework: {source}")
        print(f"Wrote {len(wrote)} files to {store.analytics_dir}")
    return 0
