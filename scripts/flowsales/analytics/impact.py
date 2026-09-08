"""Quarter attribution: analytics/impact.json (CONTRACTS section 9) plus analytics/impact-<quarter>.md.

Reads analytics/deal_states.json when present, otherwise computes the deal states in memory through
the rollup functions. Standard library only.
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from collections import Counter
from typing import Any, Optional

from ..store import Store
from ..util import parse_iso, quarter_bounds, to_iso
from . import rollup

RICH_TYPES = ("call", "meeting", "transcript")
SMALL_N = 10


def compute_impact(quarter: str, deal_states: list[dict], records: list[dict], cfg: Any, coverage: Optional[dict] = None,
                   now: Any = None, rep_names: Optional[dict] = None) -> dict:
    cfg = rollup._as_config(cfg)
    quarter = quarter.strip().upper()
    start, end = quarter_bounds(quarter)
    now = rollup._as_dt(now)
    rep_names = rep_names or {}
    training_raw = cfg.get("trainingDate")
    training = parse_iso(training_raw) if training_raw else None
    split = training or start
    split_label = str(training_raw)[:10] if training else f"the quarter start ({start.date().isoformat()})"
    attribution = cfg.get("attribution") if isinstance(cfg.get("attribution"), dict) else {}
    min_b = rollup._int(attribution.get("influencedMinBehaviours")) or 3
    min_i = rollup._int(attribution.get("influencedMinInteractions")) or 2
    w_from, w_to = cfg.window
    period = f"after {str(training_raw)[:10]}" if training else f"inside the config window {w_from or 'start'} to {w_to or 'end'}"
    rule = (f"A won deal closed in {quarter} counts as influenced when it shows at least {min_b} framework behaviours "
            f"across at least {min_i} interactions {period}, and at least one element moved from 0 or 1 to 2 or 3 "
            f"in one of those interactions.")

    def closed_in_quarter(state: dict) -> bool:
        at = parse_iso(state.get("closedAt"))
        return at is not None and start <= at < end

    won_q = [s for s in deal_states if s.get("outcome") == "won" and closed_in_quarter(s)]
    influenced = [s for s in won_q if (s.get("influenced") or {}).get("isInfluenced")]
    rows = []
    for s in influenced:
        inf = s.get("influenced") or {}
        rows.append({
            "dealId": s.get("dealId"), "name": s.get("name"), "amount": s.get("amount"), "currency": s.get("currency"),
            "ownerId": s.get("ownerId"), "ownerName": rep_names.get(s.get("ownerId")),
            "movedElements": list(inf.get("movedElements") or []), "behaviours": inf.get("behaviours"),
            "interactions": inf.get("interactions"), "closedAt": s.get("closedAt"),
        })

    before_r = [r for r in records if r.get("at") is not None and r["at"] < split]
    after_r = [r for r in records if r.get("at") is not None and r["at"] >= split]
    closed = [s for s in deal_states if s.get("outcome") in rollup.CLOSED_OUTCOMES and parse_iso(s.get("closedAt")) is not None]
    before_d = [s for s in closed if parse_iso(s["closedAt"]) < split]
    after_d = [s for s in closed if parse_iso(s["closedAt"]) >= split]
    adoption_before = rollup.ratio(sum(1 for r in before_r if r["applied"]), len(before_r))
    adoption_after = rollup.ratio(sum(1 for r in after_r if r["applied"]), len(after_r))

    # caveats
    caveats = [
        f"Attribution is correlational, not causal: deals that showed framework behaviours after {split_label} "
        "may have been the deals that were already progressing, and the reps who adopted first may be the stronger reps."
    ]
    win_start = parse_iso(w_from) if w_from else None
    after_days = max(0, int((now - split).total_seconds() // 86400))
    if win_start is not None and split > win_start:
        before_days = int((split - win_start).total_seconds() // 86400)
        caveats.append(f"The after period is younger: {after_days} days from {split_label} to {now.date().isoformat()} "
                       f"against {before_days} days before it, so after-period deals have had less time to close and "
                       "their win rate is provisional.")
    else:
        caveats.append(f"The after period is younger: only {after_days} days have passed since {split_label}, so "
                       "after-period deals have had less time to close and their win rate is provisional.")
    cov = coverage or {}
    by_type = cov.get("interactionsByType") or dict(Counter(r.get("type") or "unknown" for r in records))
    rich = sum(v for k, v in by_type.items() if k in RICH_TYPES)
    thin = sum(v for k, v in by_type.items() if k not in RICH_TYPES)
    caveats.append(f"Evidence comes from {rich} calls, meetings or transcripts and {thin} emails, notes or other records; "
                   "emails and notes carry less quotable buyer evidence, so levels on deals that live in email run low.")
    without = cov.get("dealsWithoutInteractions") or 0
    unlinked = cov.get("unlinkedInteractions") or 0
    unassessed = cov.get("interactionsUnassessed") or 0
    if without or unlinked or unassessed:
        caveats.append(f"{without} deals have no linked interactions, {unlinked} interactions are unlinked and "
                       f"{unassessed} linked interactions are unassessed; they are excluded from every number here.")
    if len(won_q) < SMALL_N or len(before_d) < SMALL_N or len(after_d) < SMALL_N:
        caveats.append(f"Small numbers: {len(won_q)} won deals in {quarter}, {len(before_d)} closed deals before and "
                       f"{len(after_d)} after {split_label}; fewer than {SMALL_N} in a group means the rates move with a single deal.")
    if training is None:
        caveats.append(f"No training date is configured, so before and after are split at {split_label}.")

    return {
        "quarter": quarter, "quarterStart": to_iso(start), "quarterEnd": to_iso(end),
        "trainingDate": str(training_raw)[:10] if training else None, "splitDate": to_iso(split), "rule": rule,
        "influencedDeals": rows, "influencedCount": len(rows),
        "influencedAmount": round(sum(rollup._num(s.get("amount"), 0.0) for s in influenced), 2),
        "influencedAmountByCurrency": rollup.amount_by_currency(influenced),
        "wonCount": len(won_q), "wonAmount": round(sum(rollup._num(s.get("amount"), 0.0) for s in won_q), 2),
        "wonAmountByCurrency": rollup.amount_by_currency(won_q),
        "adoptionBefore": adoption_before, "adoptionAfter": adoption_after,
        "adoptionBeforeN": len(before_r), "adoptionAfterN": len(after_r),
        "winRateBefore": rollup._win_rate(before_d), "winRateAfter": rollup._win_rate(after_d),
        "closedBefore": len(before_d), "closedAfter": len(after_d),
        "caveats": caveats, "generatedAt": to_iso(now),
    }


def _pct(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _money(amount: Any, currency: Optional[str]) -> str:
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        return "n/a"
    return f"{currency + ' ' if currency else ''}{amount:,.0f}"


def _money_total(total: Any, by_currency: Optional[dict], fallback_currency: Optional[str]) -> str:
    """One currency: the plain total. Several: each currency's own sum, never added together."""
    if isinstance(by_currency, dict) and len(by_currency) > 1:
        return " + ".join(_money(v, k) for k, v in sorted(by_currency.items()))
    if isinstance(by_currency, dict) and len(by_currency) == 1:
        (cur, val), = by_currency.items()
        return _money(val, cur)
    return _money(total, fallback_currency)


def render_markdown(impact: dict) -> str:
    q = impact["quarter"]
    rows = impact.get("influencedDeals") or []
    currencies = Counter(r.get("currency") for r in rows if r.get("currency"))
    currency = currencies.most_common(1)[0][0] if currencies else None
    won_amount = impact.get("wonAmount") or 0.0
    won_by = impact.get("wonAmountByCurrency") or {}
    inf_by = impact.get("influencedAmountByCurrency") or {}
    mixed = isinstance(won_by, dict) and len(won_by) > 1
    share = "n/a" if mixed or not won_amount else _pct(rollup.ratio(impact.get("influencedAmount") or 0.0, won_amount))
    share_txt = "share not computed across currencies" if mixed else f"{share} of the won amount"
    split = impact.get("trainingDate") or f"quarter start ({(impact.get('quarterStart') or '')[:10]})"
    lines = [
        f"# Impact: {q}", "",
        f"Generated {impact.get('generatedAt')}. Training date: {impact.get('trainingDate') or 'not set'}.", "",
        "## Headline", "",
        f"- Won deals closed in {q}: {impact.get('wonCount')} ({_money_total(won_amount, won_by, currency)})",
        f"- Influenced by the framework: {impact.get('influencedCount')} of {impact.get('wonCount')} "
        f"({_money_total(impact.get('influencedAmount'), inf_by, currency)}, {share_txt})",
        f"- Adoption before {split}: {_pct(impact.get('adoptionBefore'))} (n = {impact.get('adoptionBeforeN')} interactions); "
        f"after: {_pct(impact.get('adoptionAfter'))} (n = {impact.get('adoptionAfterN')})",
        f"- Win rate before {split}: {_pct(impact.get('winRateBefore'))} (n = {impact.get('closedBefore')} closed deals); "
        f"after: {_pct(impact.get('winRateAfter'))} (n = {impact.get('closedAfter')})",
        "", "## The rule, in words", "", impact.get("rule") or "", "",
        "## Influenced deals", "",
    ]
    if rows:
        lines += ["| Deal | Owner | Amount | Moved elements | Behaviours |", "|---|---|---|---|---|"]
        for r in rows:
            owner = r.get("ownerName") or r.get("ownerId") or "unknown"
            moved = ", ".join(r.get("movedElements") or []) or "none"
            lines.append(f"| {r.get('name') or r.get('dealId')} | {owner} | {_money(r.get('amount'), r.get('currency'))} | "
                         f"{moved} | {r.get('behaviours')} across {r.get('interactions')} interactions |")
    else:
        lines.append(f"No won deal closed in {q} meets the rule.")
    lines += [
        "", "## Adoption before and after", "",
        "| Period | Adoption | Assessed interactions |", "|---|---|---|",
        f"| Before {split} | {_pct(impact.get('adoptionBefore'))} | {impact.get('adoptionBeforeN')} |",
        f"| After {split} | {_pct(impact.get('adoptionAfter'))} | {impact.get('adoptionAfterN')} |",
        "", "## Win rate before and after", "",
        "| Period | Win rate | Closed deals |", "|---|---|---|",
        f"| Before {split} | {_pct(impact.get('winRateBefore'))} | {impact.get('closedBefore')} |",
        f"| After {split} | {_pct(impact.get('winRateAfter'))} | {impact.get('closedAfter')} |",
        "", "## Caveats", "",
    ]
    lines += [f"- {c}" for c in impact.get("caveats") or []]
    return "\n".join(lines).replace("\u2014", ":") + "\n"


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    want_json = bool(ctx.get("json") or getattr(args, "json", False))
    quarter = str(getattr(args, "quarter", None) or "").strip().upper()
    try:
        quarter_bounds(quarter)
    except ValueError as exc:
        msg = str(exc)
        store.log_run("impact", {"quarter": quarter}, False, ctx["started"], notes=msg)
        print(json.dumps({"ok": False, "error": msg}) if want_json else f"error: {msg}", file=sys.stderr)
        return 1
    if not store.exists():
        msg = f"no FlowSales store at {store.home} (run init first)"
        print(json.dumps({"ok": False, "error": msg}) if want_json else f"error: {msg}", file=sys.stderr)
        return 1
    cfg = store.config
    framework, source = rollup.load_framework(ctx["plugin_root"], cfg.framework)
    now = rollup._as_dt(ctx.get("now"))
    inputs = rollup.load_inputs(store)
    read = list(inputs["read"])
    deal_states = store.read_json("analytics/deal_states.json")
    computed_in_memory = not isinstance(deal_states, list)
    if computed_in_memory:
        deal_states = rollup.compute_all(inputs, framework, cfg, now)["deal_states"]
    else:
        read.append(str(store.analytics_dir / "deal_states.json"))
    records = rollup.build_records(inputs, cfg, framework)
    coverage = rollup.data_coverage(inputs, records)
    rep_names = {r.get("id"): r.get("name") for r in inputs["reps"] if isinstance(r, dict)}
    impact = compute_impact(quarter, deal_states, records, cfg, coverage=coverage, now=now, rep_names=rep_names)
    impact["computedInMemory"] = computed_in_memory
    json_path = store.write_json("analytics/impact.json", impact)
    md_path = store.analytics_dir / f"impact-{quarter}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(impact), encoding="utf-8")
    wrote = [str(json_path), str(md_path)]
    store.log_run("impact", {"quarter": quarter}, True, ctx["started"], read=read, wrote=wrote,
                  notes="deal states computed in memory" if computed_in_memory else f"framework: {source}")
    if want_json:
        print(json.dumps({"ok": True, **impact, "wrote": wrote}, indent=2, ensure_ascii=False))
    else:
        print(f"Impact {quarter}: {impact['influencedCount']} of {impact['wonCount']} won deals influenced "
              f"({_money_total(impact['influencedAmount'], impact.get('influencedAmountByCurrency'), None)} of "
              f"{_money_total(impact['wonAmount'], impact.get('wonAmountByCurrency'), None)}). Adoption {_pct(impact['adoptionBefore'])} "
              f"before, {_pct(impact['adoptionAfter'])} after; win rate {_pct(impact['winRateBefore'])} before, "
              f"{_pct(impact['winRateAfter'])} after.")
        print(f"Wrote {md_path}")
    return 0
