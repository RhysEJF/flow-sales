"""Build the FlowSales HTML report: one self-contained file. Standard library only.

`run(ctx, args)` collects config, analytics/*.json, deals, reps, assessments, the
interaction metadata the deal pages need and the framework file, pre-renders the charts
with charts.py, embeds everything as one JSON blob in template.html and writes
reports/flowsales-<YYYY-MM-DD>.html (or --out). The page renders its tabs client-side
from that blob. Nothing is recomputed here: analytics numbers are passed through as
they are; the only arithmetic is what a chart needs to draw (ordering, axis extents,
pooling reps past the eighth categorical slot into one "Other" line).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import re
import subprocess
import sys
from html import escape
from pathlib import Path
from typing import Any, Optional

from ..store import Store
from ..util import iso_week, now_iso, parse_iso
from . import charts as C

HERE = Path(__file__).resolve().parent
TEMPLATE_PATH = HERE / "template.html"
DEFAULT_ELEMENTS = [("M", "Metrics"), ("E", "Economic Buyer"), ("DC", "Decision Criteria"), ("DP", "Decision Process"),
                    ("PP", "Paper Process"), ("I", "Pain"), ("CH", "Champion"), ("CO", "Competition")]
MAX_SLOTS = 8
MISSING_STATES = "analytics/deal_states.json is missing: run rollup first"


# ---------------------------------------------------------------- entry point

def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    started = ctx.get("started")
    as_json = bool(ctx.get("json") or getattr(args, "json", False))
    plugin_root = Path(ctx.get("plugin_root") or HERE.parents[2])
    if not store.exists():
        return _fail(as_json, f"no FlowSales store at {store.home}: run init first")
    if not (store.analytics_dir / "deal_states.json").exists():
        return _fail(as_json, MISSING_STATES)
    read: list[str] = []
    payload = collect(store, plugin_root, read)
    html = render(payload, plugin_root)
    out_arg = getattr(args, "out", None)
    if out_arg:
        out = Path(out_arg).expanduser()
        if not out.is_absolute():
            out = Path.cwd() / out
    else:
        out = store.reports_dir / f"flowsales-{_dt.date.today().isoformat()}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    size = out.stat().st_size
    store.log_run("report", {"out": str(out), "open": bool(getattr(args, "open", False))}, True, started or 0.0,
                  read=read, wrote=[str(out)], notes=f"{payload['meta']['counts']['dealStates']} deals, {size} bytes")
    result = {"ok": True, "path": str(out), "bytes": size, "deals": payload["meta"]["counts"]["dealStates"],
              "reps": payload["meta"]["counts"]["reps"], "warnings": payload.get("warnings", [])}
    if as_json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(str(out))
        for w in payload.get("warnings", []):
            print(f"note: {w}", file=sys.stderr)
    if getattr(args, "open", False):
        open_file(out)
    return 0


def _fail(as_json: bool, message: str) -> int:
    if as_json:
        print(json.dumps({"ok": False, "error": message}))
    else:
        print(f"error: {message}", file=sys.stderr)
    return 1


def open_file(path: Path) -> None:
    """Open the report with the platform default handler (open on macOS, xdg-open elsewhere)."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", str(path)])
        elif system == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as exc:
        print(f"could not open {path}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------- collection

def collect(store: Store, plugin_root: Path, read: Optional[list] = None) -> dict:
    """Gather every file the report needs into one JSON-serialisable payload."""
    read = read if read is not None else []
    warnings: list[str] = []
    cfg = store.config.data
    read.append(str(store.config_path))

    def load(name: str, default: Any) -> Any:
        p = store.analytics_dir / f"{name}.json"
        if p.exists():
            read.append(str(p))
            try:
                return store.read_json(p, default)
            except ValueError as exc:
                warnings.append(f"{name}.json could not be parsed ({exc}); section left empty.")
                return default
        return default

    deal_states = load("deal_states", []) or []
    rep_metrics = load("rep_metrics", []) or []
    team_metrics = load("team_metrics", {}) or {}
    timeseries = load("timeseries", {}) or {}
    impact = load("impact", None)

    deals = store.load_deals()
    reps = store.load_reps()
    read.extend(str(p) for p in (store.data_dir / "deals.json", store.data_dir / "reps.json") if p.exists())
    assessments: dict[str, dict] = {}
    for a in store.iter_assessments():
        if a.get("dealId"):
            assessments[a["dealId"]] = a
    read.append(str(store.assessments_dir))
    interactions: dict[str, list] = {}
    n_inter = 0
    for deal_id, it in store.iter_all_interactions():
        if not deal_id:
            continue
        interactions.setdefault(deal_id, []).append(_slim_interaction(it))
        n_inter += 1
    read.append(str(store.interactions_dir))
    unlinked = len(store.load_unlinked())

    slug = cfg.get("framework") or "meddpicc"
    framework = _load_framework(plugin_root, store.home, slug, read)
    if framework is None:
        warnings.append(f"framework file frameworks/{slug}.json not found; suggested questions and anchors are omitted.")
    elements = _element_list(framework, deal_states)
    reps_sorted = sorted(reps, key=lambda r: (str(r.get("name") or ""), str(r.get("id") or "")))
    rep_payload = []
    for i, r in enumerate(reps_sorted):
        rep_payload.append({"id": r.get("id"), "name": r.get("name") or r.get("id"), "email": r.get("email"),
                            "slot": i + 1 if i < MAX_SLOTS else 0})
    known = {r["id"] for r in rep_payload}
    for s in deal_states:
        owner = s.get("ownerId")
        if owner and owner not in known:
            known.add(owner)
            rep_payload.append({"id": owner, "name": owner, "email": None, "slot": 0})

    judged = sorted(a.get("judgedAt") for a in assessments.values() if a.get("judgedAt"))
    models = sorted({str(a.get("model")) for a in assessments.values() if a.get("model")})
    hashes = sorted({str(a.get("rubricHash")) for a in assessments.values() if a.get("rubricHash")})
    org = (cfg.get("org") or {}).get("name") or store.home.parent.name or "your team"
    currency = next((d.get("currency") for d in deals if d.get("currency")), "")
    currencies = sorted({str(d.get("currency")) for d in deals if d.get("currency")})
    window = cfg.get("window") or {}
    meta = {
        "title": f"FlowSales report for {org}",
        "orgName": org,
        "home": str(store.home),
        "generatedAt": now_iso(),
        "window": {"from": window.get("from"), "to": window.get("to")},
        "trainingDate": cfg.get("trainingDate"),
        "currency": currency,
        "currencies": currencies,
        "framework": {"slug": slug, "name": (framework or {}).get("name") or slug.upper(), "version": (framework or {}).get("version"),
                      "maxLevel": (framework or {}).get("maxLevel", 3)},
        "elements": elements,
        "rubricHashes": hashes,
        "models": models or ([str((cfg.get("judge") or {}).get("model"))] if (cfg.get("judge") or {}).get("model") else []),
        "judgedAt": {"min": judged[0] if judged else None, "max": judged[-1] if judged else None},
        "config": {"attribution": cfg.get("attribution") or {}, "judge": cfg.get("judge") or {}, "content": cfg.get("content") or {},
                   "anonymize": cfg.get("anonymize", False), "linking": cfg.get("linking") or {}},
        "sources": [k for k, v in (cfg.get("sources") or {}).items() if isinstance(v, dict) and v.get("enabled")],
        "counts": {"deals": len(deals), "dealStates": len(deal_states), "reps": len(reps), "interactions": n_inter,
                   "assessments": len(assessments), "unlinked": unlinked},
    }
    payload = {
        "meta": meta,
        "reps": rep_payload,
        "deals": [_slim_deal(d) for d in deals],
        "dealStates": deal_states,
        "repMetrics": rep_metrics,
        "teamMetrics": team_metrics,
        "timeseries": timeseries,
        "impact": impact,
        "assessments": assessments,
        "interactions": interactions,
        "framework": framework,
        "warnings": warnings,
    }
    payload["charts"] = build_charts(payload)
    return payload


def _slim_interaction(it: dict) -> dict:
    parts = []
    for p in it.get("participants") or []:
        if isinstance(p, dict):
            parts.append({"name": p.get("name"), "email": p.get("email"), "role": p.get("role")})
    meta = it.get("meta") or {}
    return {"id": it.get("id"), "at": it.get("at"), "type": it.get("type"), "title": it.get("title"), "summary": it.get("summary"),
            "direction": it.get("direction"), "durationSec": it.get("durationSec"), "repId": it.get("repId"), "participants": parts,
            "hasTranscript": bool(it.get("transcript")) or bool(meta.get("hasTranscript")), "bodyChars": len(it.get("body") or "")}


def _slim_deal(d: dict) -> dict:
    keys = ("id", "source", "name", "amount", "currency", "pipeline", "stage", "stageLabel", "phase", "stageHistory", "outcome",
            "createdAt", "closedAt", "ownerId", "companyId", "companyDomain")
    return {k: d.get(k) for k in keys}


def _load_framework(plugin_root: Path, home: Path, slug: str, read: list) -> Optional[dict]:
    for base in (plugin_root / "frameworks", home / "frameworks"):
        p = base / f"{slug}.json"
        if p.exists():
            try:
                with p.open("r", encoding="utf-8") as fh:
                    fw = json.load(fh)
                read.append(str(p))
                return fw if isinstance(fw, dict) else None
            except (OSError, ValueError):
                return None
    return None


def _element_list(framework: Optional[dict], deal_states: list) -> list[dict]:
    if framework and isinstance(framework.get("elements"), list):
        out = [{"code": e.get("code"), "name": e.get("name") or e.get("code")} for e in framework["elements"] if e.get("code")]
        if out:
            return out
    seen: list[str] = []
    for s in deal_states:
        for code in (s.get("elements") or {}):
            if code not in seen:
                seen.append(code)
    names = dict(DEFAULT_ELEMENTS)
    if seen:
        order = [c for c, _ in DEFAULT_ELEMENTS if c in seen] + [c for c in seen if c not in names]
        return [{"code": c, "name": names.get(c, c)} for c in order]
    return [{"code": c, "name": n} for c, n in DEFAULT_ELEMENTS]


# ---------------------------------------------------------------- charts

def build_charts(payload: dict) -> dict:
    """Pre-render every chart with charts.py. A shape mismatch in one analytics file
    disables that chart with a note instead of failing the whole report."""
    charts: dict[str, Any] = {"reps": {}, "deals": {}, "tiles": {}}
    warnings: list = payload.setdefault("warnings", [])

    def safe(name: str, fn, *a, **kw):
        try:
            ch = fn(*a, **kw)
            return ch.as_dict() if isinstance(ch, C.Chart) else ch
        except Exception as exc:  # noqa: BLE001 - one bad file must not kill the report
            warnings.append(f"chart '{name}' skipped: {type(exc).__name__}: {exc}")
            return None

    def dual(name: str, fn, *a):
        """Render at desktop width and again at phone width (NARROW_W). The page swaps the SVG on a
        media query instead of shrinking a wide chart until its labels are unreadable."""
        wide = safe(name, fn, *a)
        if not isinstance(wide, dict):
            return wide
        narrow = safe(f"{name} (narrow)", fn, *a, narrow=True)
        if isinstance(narrow, dict) and narrow.get("svg"):
            wide = dict(wide)
            wide["narrow"] = narrow["svg"]
        return wide

    def dual_map(name: str, fn, *a) -> dict:
        wide = safe(name, fn, *a) or {}
        narrow = safe(f"{name} (narrow)", fn, *a, narrow=True) or {}
        out: dict[str, Any] = {}
        for key, val in wide.items():
            alt = narrow.get(key) if isinstance(narrow, dict) else None
            if isinstance(val, dict) and isinstance(alt, dict) and alt.get("svg"):
                val = dict(val)
                val["narrow"] = alt["svg"]
            out[key] = val
        return out

    charts["tiles"]["overview"] = safe("overview tiles", overview_tiles, payload) or []
    charts["adoptionOverTime"] = dual("adoptionOverTime", adoption_over_time, payload)
    charts["winRateByTertile"] = dual("winRateByTertile", win_rate_by_tertile, payload)
    charts["beforeAfterByRep"] = dual("beforeAfterByRep", before_after_by_rep, payload)
    charts["interactionsByType"] = dual("interactionsByType", interactions_by_type, payload)
    charts["elementWonLost"] = dual("elementWonLost", element_won_lost, payload)
    charts["elementAdoption"] = dual("elementAdoption", element_adoption, payload)
    if payload.get("impact"):
        charts["impactBeforeAfter"] = dual("impactBeforeAfter", impact_before_after, payload)
        charts["tiles"]["impact"] = safe("impact tiles", impact_tiles, payload) or []
    for rep in payload["reps"]:
        charts["reps"][rep["id"]] = dual_map(f"rep {rep['id']}", rep_charts, payload, rep)
    for s in payload["dealStates"]:
        charts["deals"][s["dealId"]] = dual_map(f"deal {s['dealId']}", deal_charts, payload, s)
    return charts


NARROW_W = 330  # widest chart that fits a 390px phone inside the page and figure padding


def _element_names(payload: dict) -> dict:
    return {e["code"]: e["name"] for e in payload["meta"]["elements"]}


def _pct(v: Any) -> str:
    return C.fmt_pct(v)


def overview_tiles(payload: dict) -> list[str]:
    tm = payload.get("teamMetrics") or {}
    tot = tm.get("totals") or {}
    states = payload["dealStates"]
    n_states = len(states)
    n_deals = payload["meta"]["counts"]["deals"]
    n_inter = tot.get("interactions")
    if n_inter is None:
        n_inter = sum(int(s.get("interactions") or 0) for s in states)
    n_applied = tot.get("appliedInteractions")
    if n_applied is None:
        n_applied = sum(int(s.get("appliedInteractions") or 0) for s in states)
    adoption = tot.get("adoptionRate")
    if adoption is None and n_inter:
        adoption = n_applied / n_inter
    won = tot.get("dealsWon", sum(1 for s in states if s.get("outcome") == "won"))
    lost = tot.get("dealsLost", sum(1 for s in states if s.get("outcome") == "lost"))
    win_rate = tm.get("winRate")
    if win_rate is None and (won + lost):
        win_rate = won / (won + lost)
    w = payload["meta"]["window"]
    window_txt = f"{C.fmt_date(w.get('from'))} to {C.fmt_date(w.get('to'))}" if w.get("from") else "window not set"
    return [
        C.stat_tile("Deals audited", C.fmt_num(n_states), sub=f"of {C.fmt_num(n_deals)} deals in window, {window_txt}"),
        C.stat_tile("Interactions scored", C.fmt_num(n_inter), sub=f"{C.fmt_num(n_applied)} with at least one framework behaviour"),
        C.stat_tile("Team adoption rate", _pct(adoption), sub=f"n = {C.fmt_num(n_inter)} interactions"),
        C.stat_tile("Win rate", _pct(win_rate), sub=f"n = {C.fmt_num(won + lost)} closed deals ({C.fmt_num(won)} won, {C.fmt_num(lost)} lost)"),
    ]


def _norm_timeseries(ts: Any) -> tuple[list[str], dict, dict]:
    """Normalise timeseries.json into (weeks, team{week: bucket}, reps{repId: {week: bucket}}).
    Accepts lists of buckets with a 'week' key, dicts keyed by week, or a flat list with repId."""
    def to_map(obj: Any) -> dict:
        if isinstance(obj, dict):
            if obj and all(isinstance(v, dict) for v in obj.values()):
                return {str(k): v for k, v in obj.items()}
            return {}
        if isinstance(obj, list):
            return {str(b.get("week") or b.get("isoWeek") or b.get("period")): b for b in obj if isinstance(b, dict)}
        return {}

    team: dict = {}
    reps: dict = {}
    weeks: list[str] = []
    if isinstance(ts, dict):
        team = to_map(ts.get("team"))
        for key in ("reps", "byRep", "perRep"):
            if isinstance(ts.get(key), dict):
                reps = {str(rid): to_map(v) for rid, v in ts[key].items()}
                break
        if isinstance(ts.get("weeks"), list):
            weeks = [str(w) for w in ts["weeks"]]
    elif isinstance(ts, list):
        for b in ts:
            if not isinstance(b, dict):
                continue
            wk = str(b.get("week") or b.get("isoWeek") or "")
            rid = b.get("repId")
            if rid:
                reps.setdefault(str(rid), {})[wk] = b
            else:
                team[wk] = b
    if not weeks:
        allw = set(team) | {w for m in reps.values() for w in m}
        weeks = sorted(w for w in allw if w and w != "None")
    return weeks, team, reps


def _week_monday(week: str) -> Optional[_dt.date]:
    m = re.fullmatch(r"(\d{4})-W(\d{2})", week or "")
    if not m:
        return None
    try:
        return _dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    except ValueError:
        return None


def _week_label(week: str) -> str:
    d = _week_monday(week)
    if not d:
        return week
    return f"{d.day} {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.month - 1]}"


def _rate(bucket: Optional[dict]) -> Optional[float]:
    if not isinstance(bucket, dict):
        return None
    r = bucket.get("adoptionRate")
    if r is not None:
        return float(r)
    n = bucket.get("interactions")
    a = bucket.get("applied", bucket.get("appliedInteractions"))
    if n and a is not None:
        return float(a) / float(n)
    return None


ROLLING_WEEKS = 4


def _rolling_rate(buckets: dict, weeks: list[str], window: int = ROLLING_WEEKS) -> list[Optional[float]]:
    """Adoption over a trailing window of ISO weeks, weighted by interactions. A week with no interactions in
    the whole window is None. With one to three interactions a week, the plain weekly rate only ever reads 0% or 100%."""
    out: list[Optional[float]] = []
    for i, _w in enumerate(weeks):
        n = a = 0.0
        for w in weeks[max(0, i - window + 1): i + 1]:
            b = buckets.get(w) or {}
            n += float(b.get("interactions") or 0)
            applied = b.get("applied", b.get("appliedInteractions"))
            a += float(applied) if applied is not None else 0.0
        out.append((a / n) if n else None)
    return out


def adoption_over_time(payload: dict, narrow: bool = False) -> Optional[C.Chart]:
    weeks, team, reps_ts = _norm_timeseries(payload.get("timeseries"))
    if not weeks:
        return None
    labels = [_week_label(w) for w in weeks]
    tips = [f"{w} (week of {C.fmt_date(_week_monday(w).isoformat()) if _week_monday(w) else w})" for w in weeks]
    series = []
    pooled_n: dict[str, float] = {}
    pooled_a: dict[str, float] = {}
    pooled_reps = 0
    for rep in payload["reps"]:
        m = reps_ts.get(rep["id"]) or {}
        if not m:
            continue
        if rep["slot"]:
            series.append({"name": rep["name"], "values": _rolling_rate(m, weeks), "color": f"s{rep['slot']}"})
        else:
            pooled_reps += 1
            for w in weeks:
                b = m.get(w) or {}
                n = float(b.get("interactions") or 0)
                a = b.get("applied", b.get("appliedInteractions"))
                pooled_n[w] = pooled_n.get(w, 0.0) + n
                pooled_a[w] = pooled_a.get(w, 0.0) + (float(a) if a is not None else 0.0)
    if pooled_reps:
        pooled = {w: {"interactions": pooled_n.get(w, 0.0), "applied": pooled_a.get(w, 0.0)} for w in weeks}
        series.append({"name": f"Other reps ({pooled_reps}, pooled)", "values": _rolling_rate(pooled, weeks), "color": "s0"})
    if team:
        series.append({"name": "Team", "values": _rolling_rate(team, weeks), "color": "ink2", "dashed": True})
    if not series:
        return None
    vline = None
    training = payload["meta"].get("trainingDate")
    t = parse_iso(training) if training else None
    first, last = _week_monday(weeks[0]), _week_monday(weeks[-1])
    if t and first and last and last > first:
        pos = (t.date() - first).days / (last - first).days
        if 0.0 <= pos <= 1.0:
            vline = {"pos": pos, "label": f"Training {C.fmt_date(training)}"}
    return C.line_chart(labels, series, x_tips=tips, is_rate=True, vline=vline, width=NARROW_W if narrow else 760,
                        height=250 if narrow else 300, end_labels=not narrow,
                        aria=f"Adoption rate, trailing {ROLLING_WEEKS} weeks, one line per rep, team dashed",
                        table_caption=f"Adoption rate by ISO week, trailing {ROLLING_WEEKS}-week window")


def win_rate_by_tertile(payload: dict, narrow: bool = False) -> Optional[C.Chart]:
    rows = (payload.get("teamMetrics") or {}).get("winRateByAdoptionTertile") or []
    if not rows:
        return None
    cats, vals, labels, tips, trows = [], [], [], [], []
    for r in rows:
        name = str(r.get("tertile", "")).capitalize() + " adoption"
        cats.append(name)
        vals.append(r.get("winRate"))
        n = r.get("n")
        labels.append(f"{_pct(r.get('winRate'))} (n={C.fmt_num(n)})")
        extra = [("win rate", _pct(r.get("winRate")), "s1"), ("deals", C.fmt_num(n), "")]
        if r.get("closed") is not None:
            extra.append(("closed deals", C.fmt_num(r.get("closed")), ""))
        if r.get("medianCycleDays") is not None:
            extra.append(("median cycle days", C.fmt_num(r.get("medianCycleDays")), ""))
        mixed = len(payload["meta"].get("currencies") or []) > 1
        if r.get("avgAmount") is not None and not mixed:
            extra.append(("avg amount", C.fmt_money(r.get("avgAmount"), payload["meta"].get("currency")), ""))
        rng = r.get("adoptionRange")
        if isinstance(rng, list) and len(rng) == 2:
            extra.append(("adoption range", f"{_pct(rng[0])} to {_pct(rng[1])}", ""))
        tips.append(C.tip(name, extra))
        trows.append((name, _pct(r.get("winRate")), C.fmt_num(n), C.fmt_num(r.get("medianCycleDays")),
                      "mixed currencies" if mixed else C.fmt_money(r.get("avgAmount"), payload["meta"].get("currency"))))
    return C.bar_chart(cats, vals, value_fmt=C.fmt_pct, is_rate=True, bar_labels=labels, tips=tips,
                       width=NARROW_W if narrow else 520, height=240 if narrow else 260,
                       aria="Win rate by adoption tertile", table_caption="Win rate by adoption tertile",
                       table_headers=["Tertile", "Win rate", "Deals (n)", "Median cycle days", "Avg amount"], table_rows=trows)


def before_after_by_rep(payload: dict, narrow: bool = False) -> Optional[C.Chart]:
    rm = payload.get("repMetrics") or []
    if not rm:
        return None
    by_id = {(m.get("repId") or m.get("id") or m.get("ownerId")): m for m in rm}
    has_training = bool(payload["meta"].get("trainingDate"))
    panels, trows = [], []
    for rep in payload["reps"]:
        m = by_id.get(rep["id"])
        if not m:
            continue
        b = m.get("beforeTraining") or {}
        a = m.get("afterTraining") or {}
        if not has_training and not (b.get("n") or a.get("n")):
            continue
        br, ar = b.get("adoptionRate"), a.get("adoptionRate")
        panels.append({"title": rep["name"], "values": [br, ar],
                       "labels": [f"{_pct(br)} ({C.fmt_num(b.get('n'))})", f"{_pct(ar)} ({C.fmt_num(a.get('n'))})"],
                       "tips": [C.tip(f"{rep['name']}: before training", [("adoption", _pct(br), "ba-before"), ("interactions", C.fmt_num(b.get("n")), "")]),
                                C.tip(f"{rep['name']}: after training", [("adoption", _pct(ar), "ba-after"), ("interactions", C.fmt_num(a.get("n")), "")])]})
        pb, pa = _pct_points(br), _pct_points(ar)
        trows.append((rep["name"], _pct(br), C.fmt_num(b.get("n")), _pct(ar), C.fmt_num(a.get("n")),
                      f"{pa - pb:+d} pts" if pb is not None and pa is not None else "n/a"))
    if not panels:
        return None
    return C.small_multiples(panels, ["Before", "After"], ["ba-before", "ba-after"], value_fmt=C.fmt_pct, is_rate=True,
                             cols=2 if narrow else 4, panel_w=156 if narrow else 150,
                             aria="Adoption before and after training, one panel per rep", table_caption="Adoption before and after training by rep",
                             table_headers=["Rep", "Before", "n before", "After", "n after", "Lift"], table_rows=trows)


def interactions_by_type(payload: dict, narrow: bool = False) -> Optional[C.Chart]:
    by_type = ((payload.get("teamMetrics") or {}).get("dataCoverage") or {}).get("interactionsByType") or {}
    if not by_type:
        return None
    items = sorted(by_type.items(), key=lambda kv: (-float(kv[1] or 0), kv[0]))
    return C.hbar_chart([k for k, _ in items], [v for _, v in items], value_fmt=C.fmt_num, width=NARROW_W if narrow else 420, aria="Interactions by type",
                        table_caption="Interactions by type", table_headers=["Type", "Interactions"])


def element_won_lost(payload: dict, narrow: bool = False) -> Optional[C.Chart]:
    rows = (payload.get("teamMetrics") or {}).get("elementWeakness") or []
    if not rows:
        return None
    names = _element_names(payload)
    by_code = {r.get("element") or r.get("code"): r for r in rows}
    codes = [e["code"] for e in payload["meta"]["elements"] if e["code"] in by_code] or list(by_code)
    max_level = payload["meta"]["framework"].get("maxLevel", 3)
    return C.grouped_bars(codes, [{"name": "Won deals", "values": [by_code[c].get("avgLevelWon") for c in codes], "color": "s1"},
                                  {"name": "Lost deals", "values": [by_code[c].get("avgLevelLost") for c in codes], "color": "s2"}],
                          value_fmt=C.fmt_level, y_max=max_level, width=NARROW_W if narrow else 560, height=240 if narrow else 260,
                          aria="Average element level on won versus lost deals",
                          table_caption="Average level after decay, won vs lost", category_names=[f"{c} {names.get(c, c)}" for c in codes])


def element_adoption(payload: dict, narrow: bool = False) -> Optional[C.Chart]:
    rows = (payload.get("teamMetrics") or {}).get("elementWeakness") or []
    if not rows:
        return None
    names = _element_names(payload)
    by_code = {r.get("element") or r.get("code"): r for r in rows}
    codes = [e["code"] for e in payload["meta"]["elements"] if e["code"] in by_code] or list(by_code)
    return C.hbar_chart([f"{c} {names.get(c, c)}" for c in codes], [by_code[c].get("adoptionRate") for c in codes], value_fmt=C.fmt_pct,
                        is_rate=True, width=NARROW_W if narrow else 520, label_max=118 if narrow else 160,
                        aria="Adoption rate by element", table_caption="Adoption rate by element",
                        table_headers=["Element", "Adoption rate"])


def impact_before_after(payload: dict, narrow: bool = False) -> Optional[C.Chart]:
    im = payload.get("impact") or {}
    vals_b = [im.get("adoptionBefore"), im.get("winRateBefore")]
    vals_a = [im.get("adoptionAfter"), im.get("winRateAfter")]
    if all(v is None for v in vals_b + vals_a):
        return None
    labels = [[f"{_pct(vals_b[0])} (n={C.fmt_num(im.get('adoptionBeforeN'))})", f"{_pct(vals_b[1])} (n={C.fmt_num(im.get('closedBefore'))})"],
              [f"{_pct(vals_a[0])} (n={C.fmt_num(im.get('adoptionAfterN'))})", f"{_pct(vals_a[1])} (n={C.fmt_num(im.get('closedAfter'))})"]]
    return C.grouped_bars(["Adoption rate", "Win rate"], [{"name": "Before training", "values": vals_b, "color": "ba-before"},
                                                          {"name": "After training", "values": vals_a, "color": "ba-after"}],
                          value_fmt=C.fmt_pct, is_rate=True, bar_labels=labels, width=NARROW_W if narrow else 480, height=240 if narrow else 260,
                          aria="Adoption and win rate before and after training", table_caption="Before and after training")


def _pct_points(v: Any) -> Optional[int]:
    """The whole-number percentage the page prints for v (same rounding as fmt_pct), or None."""
    txt = C.fmt_pct(v)
    return None if txt == "n/a" else int(txt[:-1])


def impact_tiles(payload: dict) -> list[str]:
    im = payload.get("impact") or {}
    cur = payload["meta"].get("currency")
    # Deltas are taken between the rounded figures the tile prints, so 62% beside 38% reads +24 and never +25.
    lift = None
    if _pct_points(im.get("adoptionBefore")) is not None and _pct_points(im.get("adoptionAfter")) is not None:
        lift = _pct_points(im["adoptionAfter"]) - _pct_points(im["adoptionBefore"])
    wlift = None
    if _pct_points(im.get("winRateBefore")) is not None and _pct_points(im.get("winRateAfter")) is not None:
        wlift = _pct_points(im["winRateAfter"]) - _pct_points(im["winRateBefore"])
    def _delta(points: Optional[float]) -> tuple[Optional[str], Optional[bool]]:
        """Zero reads 'no change' in neutral, never '-0 pts' in red."""
        if points is None:
            return None, None
        r = int(round(points))
        if r == 0:
            return "no change vs before", None
        return f"{r:+d} pts vs before", r > 0

    lift_txt, lift_good = _delta(lift)
    wlift_txt, wlift_good = _delta(wlift)
    return [
        C.stat_tile("Influenced deals", C.fmt_num(im.get("influencedCount")), sub=f"{C.fmt_money_total(im.get('influencedAmount'), im.get('influencedAmountByCurrency'), cur)} of {C.fmt_money_total(im.get('wonAmount'), im.get('wonAmountByCurrency'), cur)} won in {im.get('quarter', 'the quarter')}"),
        C.stat_tile("Won deals in quarter", C.fmt_num(im.get("wonCount")), sub=C.fmt_money_total(im.get("wonAmount"), im.get("wonAmountByCurrency"), cur)),
        C.stat_tile("Adoption after training", _pct(im.get("adoptionAfter")), sub=f"before {_pct(im.get('adoptionBefore'))}, n = {C.fmt_num(im.get('adoptionBeforeN'))} then {C.fmt_num(im.get('adoptionAfterN'))} interactions",
                    delta=lift_txt, delta_good=lift_good),
        C.stat_tile("Win rate after training", _pct(im.get("winRateAfter")), sub=f"before {_pct(im.get('winRateBefore'))}, n = {C.fmt_num(im.get('closedBefore'))} then {C.fmt_num(im.get('closedAfter'))} closed deals",
                    delta=wlift_txt, delta_good=wlift_good),
    ]


def rep_charts(payload: dict, rep: dict, narrow: bool = False) -> dict:
    out: dict[str, Any] = {}
    names = _element_names(payload)
    metrics = {(m.get("repId") or m.get("id") or m.get("ownerId")): m for m in (payload.get("repMetrics") or [])}
    m = metrics.get(rep["id"]) or {}
    weeks, _team, reps_ts = _norm_timeseries(payload.get("timeseries"))
    series = reps_ts.get(rep["id"]) or {}
    spark = None
    if weeks and series:
        spark = C.sparkline([_rate(series.get(w)) for w in weeks], labels=[f"{w} (week of {_week_label(w)})" for w in weeks], width=160, height=36,
                            aria=f"Weekly adoption rate for {rep['name']}", table_caption="Weekly adoption rate")
    out["adoptionTile"] = C.stat_tile("Adoption rate", _pct(m.get("adoptionRate")), sub=f"n = {C.fmt_num(m.get('interactions'))} interactions, weekly trend below" if spark else f"n = {C.fmt_num(m.get('interactions'))} interactions", spark=spark)
    by_el = m.get("adoptionByElement") or {}
    if by_el:
        codes = [e["code"] for e in payload["meta"]["elements"] if e["code"] in by_el] or list(by_el)
        out["byElement"] = C.hbar_chart([f"{c} {names.get(c, c)}" for c in codes], [by_el.get(c) for c in codes], value_fmt=C.fmt_pct, is_rate=True,
                                        width=NARROW_W if narrow else 440, label_max=118 if narrow else 160,
                                        aria=f"Adoption by element for {rep['name']}", table_caption="Adoption by element",
                                        table_headers=["Element", "Adoption rate"]).as_dict()
    b = m.get("beforeTraining") or {}
    a = m.get("afterTraining") or {}
    if payload["meta"].get("trainingDate") or b.get("n") or a.get("n"):
        out["beforeAfter"] = C.grouped_bars(["Adoption rate"], [{"name": "Before training", "values": [b.get("adoptionRate")], "color": "ba-before"},
                                                                {"name": "After training", "values": [a.get("adoptionRate")], "color": "ba-after"}],
                                            value_fmt=C.fmt_pct, is_rate=True, width=280 if narrow else 300, height=210,
                                            bar_labels=[[f"{_pct(b.get('adoptionRate'))} (n={C.fmt_num(b.get('n'))})"], [f"{_pct(a.get('adoptionRate'))} (n={C.fmt_num(a.get('n'))})"]],
                                            aria=f"Adoption before and after training for {rep['name']}", table_caption="Before and after training",
                                            table_rows=[["Adoption rate", f"{_pct(b.get('adoptionRate'))} (n={C.fmt_num(b.get('n'))})", f"{_pct(a.get('adoptionRate'))} (n={C.fmt_num(a.get('n'))})"]]).as_dict()
    return out


def deal_charts(payload: dict, state: dict, narrow: bool = False) -> dict:
    names = _element_names(payload)
    els = state.get("elements") or {}
    codes = [e["code"] for e in payload["meta"]["elements"]] or list(els)
    cells = []
    for c in codes:
        e = els.get(c) or {}
        cells.append({"code": c, "name": names.get(c, c), "level": e.get("level") if e else None, "decayed": e.get("decayed", False),
                      "firstAt": e.get("firstAt"), "lastAt": e.get("lastAt")})
    return {"elements": C.heatmap_cells(cells, max_level=payload["meta"]["framework"].get("maxLevel", 3),
                                        size=36 if narrow else 46, gap=4 if narrow else 6,
                                        aria="Element levels for this deal", table_caption="Element levels after decay").as_dict()}


# ---------------------------------------------------------------- rendering

def _mark_svg(plugin_root: Path) -> str:
    """Inline the FlowSales wordmark: strip the xmlns and fixed size so CSS controls it."""
    p = plugin_root / "assets" / "flowsales-mark.svg"
    try:
        svg = p.read_text(encoding="utf-8")
    except OSError:
        return '<span class="mark-text">FlowSales</span>'
    svg = re.sub(r'\s+xmlns(:\w+)?="[^"]*"', "", svg)
    svg = re.sub(r'\s+(width|height)="[^"]*"', "", svg, count=2)
    return svg.strip()


def render(payload: dict, plugin_root: Path) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    meta = payload["meta"]
    w = meta.get("window") or {}
    window_txt = f"{C.fmt_date(w.get('from'))} to {C.fmt_date(w.get('to'))}" if w.get("from") else "not set"
    html = (template
            .replace("__FS_TITLE__", escape(meta["title"]))
            .replace("__FS_WINDOW__", escape(window_txt))
            .replace("__FS_ORG__", escape(str(meta.get("orgName") or "your team")))
            .replace("__FS_GENERATED__", escape(C.fmt_date(meta["generatedAt"]) + " " + meta["generatedAt"][11:16] + " UTC"))
            .replace("__FS_MARK__", _mark_svg(plugin_root))
            .replace("__FS_DATA__", blob))
    return html
