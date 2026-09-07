"""plan-assessment: write judge batches (CONTRACTS section 7) and print the volume estimate.

A deal is planned when --force is set, it has no assessment yet, or the assessment's
rubricHash or inputHash no longer match. inputHash covers only the interactions the judge
reads (non-empty body), so a new empty record does not trigger a re-judge. When a deal is
split across batches, priorState for part k is derived from the existing assessment's
scores for the interactions in the parts before k; part 1 and unsplit deals start at zero.
"""
from __future__ import annotations

import datetime as _dt
import json
import random
import re
from pathlib import Path
from typing import Any, Iterable, Optional

from ..config import Config
from ..schema.validate import element_codes
from ..store import Store
from ..util import parse_iso, sha1_text, sha256_of

BATCH_OVERHEAD_TOKENS = 1500
CHARS_PER_TOKEN = 4
SAMPLE_SEED = 7
DEFAULT_MAX_CHARS = 60000
_DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}")
_FAR_FUTURE = _dt.datetime.max.replace(tzinfo=_dt.timezone.utc)


def _out(ctx: dict, payload: dict, text: str) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text)


# ---------- framework ----------

def framework_path(plugin_root: Path | str, slug: str) -> Path:
    return Path(plugin_root) / "frameworks" / f"{slug}.json"


def load_framework(plugin_root: Path | str, slug: str) -> tuple[dict, Path]:
    """Load frameworks/<slug>.json from the plugin root; raise FileNotFoundError with a clear message."""
    path = framework_path(plugin_root, slug)
    if not path.exists():
        raise FileNotFoundError(
            f"framework file not found: {path} (config.framework is {slug!r}). "
            "Add the file under frameworks/ or point config.framework at an existing one."
        )
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not data.get("elements"):
        raise ValueError(f"framework file {path} has no 'elements' list")
    return data, path


def rubric_hash_of(framework: dict) -> str:
    """sha256 of the canonical JSON (sorted keys, no whitespace), per CONTRACTS section 11."""
    return sha256_of(framework)


def est_tokens(chars: int) -> int:
    return chars // CHARS_PER_TOKEN + BATCH_OVERHEAD_TOKENS


# ---------- deal selection ----------

def window_bounds(cfg: Config) -> tuple[Optional[_dt.datetime], Optional[_dt.datetime]]:
    """Inclusive window bounds; a date-only 'to' covers the whole day."""
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
    """A deal is in the window when its createdAt or its closedAt falls inside it."""
    if start is None and end is None:
        return True
    return _within(parse_iso(deal.get("createdAt")), start, end) or _within(parse_iso(deal.get("closedAt")), start, end)


def select_deals(deals: list[dict], cfg: Config, only: Optional[Iterable[str]] = None) -> list[dict]:
    """Deals to consider: explicit ids win; otherwise the config window and rep filter apply."""
    if only:
        wanted = set(only)
        return [d for d in deals if d.get("id") in wanted]
    start, end = window_bounds(cfg)
    reps = cfg.get("reps", "all")
    allowed = set(reps) if isinstance(reps, list) else None
    chosen = []
    for deal in deals:
        if not deal_in_window(deal, start, end):
            continue
        if allowed is not None and deal.get("ownerId") not in allowed:
            continue
        chosen.append(deal)
    return chosen


# ---------- phases ----------

def stage_timeline(deal: dict, cfg: Config) -> list[tuple[_dt.datetime, str]]:
    """(at, phase) pairs from stageHistory in time order; entries without a usable time are ignored."""
    timeline = []
    for entry in deal.get("stageHistory") or []:
        if not isinstance(entry, dict):
            continue
        at = parse_iso(entry.get("at"))
        if at is None:
            continue
        phase = entry.get("phase") or cfg.phase_for_stage(entry.get("stage"), entry.get("label"))
        timeline.append((at, phase))
    timeline.sort(key=lambda pair: pair[0])
    return timeline


def current_phase(deal: dict, cfg: Config) -> str:
    if deal.get("stage") or deal.get("stageLabel"):
        return cfg.phase_for_stage(deal.get("stage"), deal.get("stageLabel"))
    return deal.get("phase") or "evaluation"


def phase_at_time(deal: dict, at: Optional[_dt.datetime], cfg: Config,
                  timeline: Optional[list[tuple[_dt.datetime, str]]] = None) -> str:
    """Phase of the last stage entry at or before ``at``; before the first entry, the first entry's phase."""
    if timeline is None:
        timeline = stage_timeline(deal, cfg)
    if not timeline:
        return current_phase(deal, cfg)
    if at is None:
        return timeline[-1][1]
    phase = timeline[0][1]
    for entry_at, entry_phase in timeline:
        if entry_at <= at:
            phase = entry_phase
        else:
            break
    return phase


# ---------- interactions and hashes ----------

def _time_key(inter: dict) -> tuple:
    at = parse_iso(inter.get("at"))
    return (0 if at else 1, at or _FAR_FUTURE, inter.get("id") or "")


def judgeable(interactions: list[dict]) -> list[dict]:
    """Interactions with a non-empty body, in time order (unparseable times last)."""
    items = [i for i in interactions if isinstance(i, dict) and isinstance(i.get("body"), str) and i["body"].strip()]
    items.sort(key=_time_key)
    return items


def input_hash(interactions: list[dict]) -> str:
    """sha256 over the sorted (interaction id, sha1 of body) pairs."""
    pairs = sorted([inter.get("id") or "", sha1_text(inter.get("body") or "")] for inter in interactions)
    return sha256_of(pairs)


def needs_planning(assessment: Optional[dict], rubric_hash: str, input_hash_value: str, force: bool) -> tuple[bool, str]:
    if force:
        return True, "forced"
    if not assessment:
        return True, "no assessment"
    if assessment.get("inputHash") != input_hash_value:
        return True, "interactions changed"
    if assessment.get("rubricHash") != rubric_hash:
        return True, "rubric changed"
    return False, "unchanged"


def split_batches(interactions: list[dict], max_chars: int) -> list[list[dict]]:
    """Greedy split in time order; a batch always holds at least one interaction."""
    parts: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    for inter in interactions:
        length = len(inter.get("body") or "")
        if current and size + length > max_chars:
            parts.append(current)
            current, size = [], 0
        current.append(inter)
        size += length
    if current:
        parts.append(current)
    return parts


def element_levels(assessment: Optional[dict], codes: list[str], only_ids: Optional[set[str]] = None) -> dict[str, int]:
    """Max evidence per element in an assessment, optionally restricted to some interaction ids."""
    levels = {code: 0 for code in codes}
    for entry in (assessment or {}).get("interactions") or []:
        if not isinstance(entry, dict):
            continue
        if only_ids is not None and entry.get("interactionId") not in only_ids:
            continue
        for code, block in (entry.get("elements") or {}).items():
            if code not in levels or not isinstance(block, dict):
                continue
            evidence = block.get("evidence")
            if isinstance(evidence, (int, float)) and not isinstance(evidence, bool):
                levels[code] = max(levels[code], int(evidence))
    return levels


# ---------- batch documents ----------

def batch_interaction(inter: dict, phase: str) -> dict:
    return {
        "interactionId": inter.get("id"),
        "at": inter.get("at"),
        "type": inter.get("type"),
        "source": inter.get("source"),
        "direction": inter.get("direction"),
        "phaseAtTime": phase,
        "title": inter.get("title"),
        "participants": inter.get("participants") or [],
        "body": inter.get("body") or "",
    }


def build_batch(batch_id: int, deal: dict, part: list[dict], prior: dict[str, int], framework_slug: str,
                framework_file: Path, rubric_hash: str, input_hash_value: str, output_file: Path,
                cfg: Config, timeline: list[tuple[_dt.datetime, str]], part_no: int, parts: int, reason: str) -> dict:
    deal_view = {k: v for k, v in deal.items() if k != "meta"}
    interactions = [batch_interaction(i, phase_at_time(deal, parse_iso(i.get("at")), cfg, timeline)) for i in part]
    return {
        "batchId": batch_id,
        "dealId": deal.get("id"),
        "framework": framework_slug,
        "frameworkFile": str(framework_file),
        "rubricHash": rubric_hash,
        "inputHash": input_hash_value,
        "batchFile": None,
        "part": part_no,
        "parts": parts,
        "reason": reason,
        "deal": deal_view,
        "priorState": prior,
        "interactions": interactions,
        "outputFile": str(output_file),
    }


def _clear_batches(store: Store) -> int:
    removed = 0
    if store.batches_dir.exists():
        for path in list(store.batches_dir.glob("*.json")) + list(store.batches_dir.glob("*.json.tmp")):
            path.unlink()
            removed += 1
    return removed


def _args_dict(args: Any) -> dict:
    return {
        "force": bool(getattr(args, "force", False)),
        "sample": getattr(args, "sample", None),
        "deal": getattr(args, "deal", None),
    }


def _summary_text(plan_doc: dict, plan_path: Path) -> str:
    totals = plan_doc["totals"]
    skipped = plan_doc["skipped"]
    lines = []
    if totals["batches"]:
        lines.append(
            f"Planned {totals['batches']} batches for {totals['deals']} deals: {totals['interactions']} interactions, "
            f"{totals['chars']:,} chars, ~{totals['estTokens']:,} tokens"
        )
    else:
        lines.append("Nothing to plan: every considered deal is unchanged or has no judgeable interactions")
    lines.append(
        f"Framework: {plan_doc['framework']} (rubric {plan_doc['rubricHash'][:19]}...), "
        f"max {plan_doc['maxInteractionChars']:,} chars per batch"
    )
    lines.append(
        f"Considered {plan_doc['considered']} deals; skipped {skipped['unchanged']} unchanged, "
        f"{skipped['withoutInteractions']} without judgeable interactions"
    )
    if skipped["notFound"]:
        lines.append(f"Not found: {', '.join(skipped['notFound'])}")
    if plan_doc["batches"]:
        lines.append("Batches:")
        for b in plan_doc["batches"]:
            lines.append(
                f"  {b['batchId']:>3}  {b['dealId']}  {b['dealName'] or ''}  {b['interactions']} interactions  "
                f"{b['chars']:,} chars  ~{b['estTokens']:,} tokens  part {b['part']}/{b['parts']}  {b['file']}"
            )
    lines.append(f"Plan written to {plan_path}")
    return "\n".join(lines)


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    if not store.exists():
        _out(ctx, {"ok": False, "error": "no store; run init"}, "No FlowSales store here. Run: fs.py init")
        return 1
    cfg = store.config
    try:
        framework, framework_file = load_framework(ctx["plugin_root"], cfg.framework)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        store.log_run("plan-assessment", _args_dict(args), False, ctx["started"], notes=str(exc))
        _out(ctx, {"ok": False, "error": str(exc)}, f"error: {exc}")
        return 1
    rubric_hash = rubric_hash_of(framework)
    codes = element_codes(framework)
    max_chars = int(cfg.get("judge.maxInteractionChars") or DEFAULT_MAX_CHARS)
    force = bool(getattr(args, "force", False))
    only = list(getattr(args, "deal", None) or []) or None

    deals = store.load_deals()
    known_ids = {d.get("id") for d in deals}
    not_found = [d for d in (only or []) if d not in known_ids]
    considered = sorted(select_deals(deals, cfg, only), key=lambda d: d.get("id") or "")
    read = [str(store.data_dir / "deals.json"), str(framework_file)]

    plans: list[tuple[dict, list[dict], Optional[dict], str, str]] = []
    skipped_unchanged = 0
    skipped_empty = 0
    for deal in considered:
        deal_id = deal.get("id")
        read.append(str(store.interactions_path(deal_id)))
        inters = judgeable(store.load_interactions(deal_id))
        if not inters:
            skipped_empty += 1
            continue
        input_hash_value = input_hash(inters)
        assessment = store.load_assessment(deal_id)
        plan, reason = needs_planning(assessment, rubric_hash, input_hash_value, force)
        if not plan:
            skipped_unchanged += 1
            continue
        plans.append((deal, inters, assessment, input_hash_value, reason))

    sample = getattr(args, "sample", None)
    if sample is not None and 0 <= int(sample) < len(plans):
        plans = random.Random(SAMPLE_SEED).sample(plans, int(sample))
        plans.sort(key=lambda p: p[0].get("id") or "")

    store.ensure()
    _clear_batches(store)
    batches_meta: list[dict] = []
    wrote: list[str] = []
    batch_no = 0
    for deal, inters, assessment, input_hash_value, reason in plans:
        parts = split_batches(inters, max_chars)
        timeline = stage_timeline(deal, cfg)
        earlier_ids: set[str] = set()
        for part_no, part in enumerate(parts, start=1):
            batch_no += 1
            if part_no > 1 and assessment:
                prior = element_levels(assessment, codes, earlier_ids)
            else:
                prior = {code: 0 for code in codes}
            path = store.batches_dir / f"{batch_no}.json"
            batch = build_batch(batch_no, deal, part, prior, cfg.framework, framework_file, rubric_hash,
                                input_hash_value, store.assessment_path(deal.get("id")), cfg, timeline,
                                part_no, len(parts), reason)
            batch["batchFile"] = str(path)
            store.write_json(path, batch)
            wrote.append(str(path))
            chars = sum(len(i["body"]) for i in batch["interactions"])
            batches_meta.append({
                "batchId": batch_no, "dealId": deal.get("id"), "dealName": deal.get("name"), "file": str(path),
                "interactions": len(part), "chars": chars, "estTokens": est_tokens(chars),
                "part": part_no, "parts": len(parts), "reason": reason,
            })
            earlier_ids |= {i.get("id") for i in part}

    totals = {
        "deals": len(plans),
        "batches": len(batches_meta),
        "interactions": sum(b["interactions"] for b in batches_meta),
        "chars": sum(b["chars"] for b in batches_meta),
        "estTokens": sum(b["estTokens"] for b in batches_meta),
    }
    plan_doc = {
        "plannedAt": ctx.get("now"),
        "rubricHash": rubric_hash,
        "framework": cfg.framework,
        "frameworkFile": str(framework_file),
        "maxInteractionChars": max_chars,
        "considered": len(considered),
        "batches": batches_meta,
        "totals": totals,
        "skipped": {"unchanged": skipped_unchanged, "withoutInteractions": skipped_empty, "notFound": not_found},
    }
    plan_path = store.write_json("work/plan.json", plan_doc)
    wrote.append(str(plan_path))
    store.log_run("plan-assessment", _args_dict(args), True, ctx["started"], read=read, wrote=wrote,
                  notes=f"{totals['batches']} batches for {totals['deals']} deals, ~{totals['estTokens']} tokens")
    _out(ctx, {"ok": True, "planFile": str(plan_path), **plan_doc}, _summary_text(plan_doc, plan_path))
    return 0
