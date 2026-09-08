"""validate-assessment: schema check, quote verification and capping (CONTRACTS 8.2).

After validation every ``evidence`` value in the file is admissible: a score above the
framework's ``scoring.quoteRequiredAbove`` carries a quote the validator found in the
interaction body (``verified: true``); otherwise the score was capped at 1, the element
flagged (``quote-unverified`` or ``quote-missing``) and the original kept in ``cappedFrom``
so a corrected quote on a later run restores it. ``verified`` is stamped only on entries
that carry a quote. The validator never raises on a missing optional field; it reports it.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Iterable, Optional

from ..schema.validate import assessment_warnings, validate_assessment_shape
from ..store import Store
from ..util import normalize_text, now_iso

FUZZY_THRESHOLD = 0.85
FLAG_UNVERIFIED = "quote-unverified"
FLAG_MISSING = "quote-missing"
OWNED_FLAGS = (FLAG_UNVERIFIED, FLAG_MISSING)
QUOTE_TRIM = " \"'`.…"
MIN_ANCHOR_WORD = 4
MAX_ANCHOR_WORDS = 12
MAX_ANCHOR_HITS = 40


def _out(ctx: dict, payload: dict, text: str) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(text)


def _is_int(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or (isinstance(value, float) and value.is_integer())


def _read_json(path: Path | str) -> Any:
    try:
        with Path(path).open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# ---------- quote verification ----------

def clean_quote(quote: str) -> str:
    """Normalised quote without surrounding quotation marks or ellipses."""
    return normalize_text(quote).strip(QUOTE_TRIM).strip()


def _anchor_offsets(quote: str, body: str) -> set[int]:
    """Window starts implied by the positions of the quote's longer words in the body."""
    n, m = len(quote), len(body)
    limit = m - n
    offsets: set[int] = set()
    words = sorted({w for w in quote.split() if len(w) >= MIN_ANCHOR_WORD}, key=len, reverse=True)[:MAX_ANCHOR_WORDS]
    for word in words:
        pos = quote.find(word)
        start = 0
        hits = 0
        while hits < MAX_ANCHOR_HITS:
            idx = body.find(word, start)
            if idx < 0:
                break
            offsets.add(min(max(idx - pos, 0), limit))
            start = idx + 1
            hits += 1
    return offsets


def _scan(matcher: difflib.SequenceMatcher, body: str, n: int, starts: Iterable[int],
          best: float, best_start: int) -> tuple[float, int]:
    for start in starts:
        matcher.set_seq1(body[start:start + n])
        if matcher.real_quick_ratio() <= best or matcher.quick_ratio() <= best:
            continue
        ratio = matcher.ratio()
        if ratio > best:
            best, best_start = ratio, start
        if best >= 1.0:
            break
    return best, best_start


def best_window_ratio(quote: str, body: str) -> float:
    """Best SequenceMatcher ratio between the quote and any body window of the quote's length."""
    n, m = len(quote), len(body)
    if n == 0 or m == 0:
        return 0.0
    if n >= m:
        return difflib.SequenceMatcher(None, body, quote, autojunk=False).ratio()
    step = max(1, n // 4)
    limit = m - n
    candidates = set(range(0, limit + 1, step))
    candidates.add(limit)
    candidates |= _anchor_offsets(quote, body)
    matcher = difflib.SequenceMatcher(None, "", quote, autojunk=False)
    best, best_start = _scan(matcher, body, n, sorted(candidates), 0.0, 0)
    if best < 1.0:
        around = range(max(0, best_start - step), min(limit, best_start + step) + 1)
        best, best_start = _scan(matcher, body, n, around, best, best_start)
    return best


def verify_quote(quote: Optional[str], body: Optional[str]) -> tuple[bool, float]:
    """(verified, match ratio): substring after normalisation, else fuzzy window at or above 0.85."""
    q = clean_quote(quote or "")
    b = normalize_text(body or "")
    if not q or not b:
        return False, 0.0
    if q in b:
        return True, 1.0
    ratio = best_window_ratio(q, b)
    return ratio >= FUZZY_THRESHOLD, ratio


# ---------- batch and framework lookup ----------

def locate_batches(assessment: dict, store: Store) -> tuple[list[dict], Optional[dict]]:
    """All batches for the assessment's deal (split deals have several) and the primary one."""
    found: dict[Any, dict] = {}
    primary: Optional[dict] = None
    batch_file = assessment.get("batchFile")
    if isinstance(batch_file, str) and batch_file:
        batch = _read_json(batch_file)
        if isinstance(batch, dict) and isinstance(batch.get("interactions"), list):
            primary = batch
            found[batch.get("batchId") or batch_file] = batch
    deal_id = assessment.get("dealId") or (primary or {}).get("dealId")
    if deal_id:
        plan = store.read_json("work/plan.json", None) or {}
        files = [e.get("file") for e in (plan.get("batches") or [])
                 if isinstance(e, dict) and e.get("dealId") == deal_id and e.get("file")]
        if not files and store.batches_dir.exists():
            for path in sorted(store.batches_dir.glob("*.json")):
                batch = _read_json(path)
                if isinstance(batch, dict) and batch.get("dealId") == deal_id:
                    files.append(str(path))
        for file in files:
            batch = _read_json(file)
            if isinstance(batch, dict) and isinstance(batch.get("interactions"), list):
                found.setdefault(batch.get("batchId") or file, batch)
    batches = sorted(found.values(), key=lambda b: (not _is_int(b.get("batchId")), b.get("batchId") or 0))
    if primary is None and batches:
        wanted = assessment.get("batchId")
        primary = next((b for b in batches if wanted is not None and b.get("batchId") == wanted), batches[0])
    return batches, primary


def merge_batches(batches: list[dict], primary: dict) -> dict:
    """One batch-shaped view whose interactions are the union of the deal's batches (primary first)."""
    merged: list[dict] = []
    seen: set[str] = set()
    for batch in [primary] + [b for b in batches if b is not primary]:
        for inter in batch.get("interactions") or []:
            iid = inter.get("interactionId") if isinstance(inter, dict) else None
            if isinstance(iid, str) and iid not in seen:
                seen.add(iid)
                merged.append(inter)
    return {"dealId": primary.get("dealId"), "interactions": merged}


def load_framework_for(primary: dict, plugin_root: Path | str, store: Store) -> tuple[Optional[dict], Optional[str]]:
    """The framework named by the batch (frameworkFile, then frameworks/<slug>.json under the plugin root)."""
    candidates: list[Path] = []
    if primary.get("frameworkFile"):
        candidates.append(Path(str(primary["frameworkFile"])))
    slug = primary.get("framework") or store.config.framework
    candidates.append(Path(plugin_root) / "frameworks" / f"{slug}.json")
    for path in candidates:
        if path.exists():
            data = _read_json(path)
            if isinstance(data, dict):
                return data, None
    tried = ", ".join(str(p) for p in candidates)
    return None, f"framework file not found (tried {tried})"


def quote_required_above(framework: dict) -> int:
    raw = (framework.get("scoring") or {}).get("quoteRequiredAbove", 1)
    return int(raw) if _is_int(raw) else 1


# ---------- corrections ----------

def _normalise_block(block: dict) -> None:
    """Coerce structured fields the rollup relies on; leave prose fields alone."""
    behaviour = block.get("behaviour")
    block["behaviour"] = 1 if behaviour in (1, True) else 0
    if not isinstance(block.get("behaviourTags"), list):
        block["behaviourTags"] = []
    quote = block.get("quote")
    if isinstance(quote, str) and not quote.strip():
        block["quote"] = None
    if isinstance(block.get("evidence"), float) and _is_int(block["evidence"]):
        block["evidence"] = int(block["evidence"])
    if "speaker" not in block:
        block["speaker"] = None


def _process_element(block: dict, body: Optional[str], quote_above: int, report: dict, label: str) -> None:
    """Verify the quote, cap when needed, restore a previous cap when the quote now verifies."""
    raw_flags = block.get("flags") if isinstance(block.get("flags"), list) else []
    flags = [f for f in raw_flags if f not in OWNED_FLAGS]
    _normalise_block(block)
    level = int(block["evidence"]) if _is_int(block.get("evidence")) else None
    quote = block.get("quote")
    if body is None:
        report["warnings"].append(f"{label}: quote could not be checked (interaction not in the batch)")
    if isinstance(quote, str):
        if body is None:
            pass
        else:
            ok, ratio = verify_quote(quote, body)
            block["verified"] = ok
            block["quoteMatch"] = round(ratio, 3)
            if ok:
                report["verified"] += 1
                capped_from = block.pop("cappedFrom", None)
                if _is_int(capped_from) and level is not None and int(capped_from) > level:
                    block["evidence"] = int(capped_from)
                    report["restored"] += 1
            else:
                report["unverified"] += 1
                flags.append(FLAG_UNVERIFIED)
                if level is not None and level > 1:
                    block["cappedFrom"] = level
                    block["evidence"] = 1
                    report["capped"] += 1
    elif level is not None and level > quote_above:
        block["cappedFrom"] = level
        block["evidence"] = 1
        block["verified"] = False
        flags.append(FLAG_MISSING)
        report["capped"] += 1
    block["flags"] = flags


def _process_assessment(assessment: dict, merged: dict, framework: dict, report: dict) -> None:
    infos = {i["interactionId"]: i for i in merged["interactions"]}
    quote_above = quote_required_above(framework)
    for entry in assessment["interactions"]:
        if not isinstance(entry, dict):
            continue
        iid = entry.get("interactionId")
        info = infos.get(iid)
        if info is not None:
            for key in ("at", "phaseAtTime"):
                if entry.get(key) is None and info.get(key) is not None:
                    entry[key] = info[key]
        elements = entry.get("elements")
        if not isinstance(elements, dict):
            continue
        body = (info.get("body") or "") if info is not None else None
        for code, block in elements.items():
            if isinstance(block, dict):
                _process_element(block, body, quote_above, report, f"{iid}.{code}")


def _stamp(assessment: dict, primary: dict, batches: list[dict], report: dict) -> None:
    for key in ("rubricHash", "inputHash"):
        if primary.get(key) is not None:
            if assessment.get(key) not in (None, primary[key]):
                report["warnings"].append(f"{key} {assessment[key]} replaced by the batch value {primary[key]}")
            assessment[key] = primary[key]
    if primary.get("batchId") is not None:
        assessment["batchId"] = primary["batchId"]
    if len(batches) > 1:
        assessment["batchIds"] = [b.get("batchId") for b in batches]
    for key in ("batchFile", "framework", "dealId"):
        if not assessment.get(key) and primary.get(key):
            assessment[key] = primary[key]
    if not assessment.get("judgedAt"):
        assessment["judgedAt"] = now_iso()
        report["warnings"].append("judgedAt was missing; stamped with the validation time")
    assessment["validatedAt"] = now_iso()


def _new_report(path: Path) -> dict:
    return {"ok": False, "file": str(path), "dealId": None, "batchId": None, "errors": [], "warnings": [],
            "capped": 0, "verified": 0, "unverified": 0, "restored": 0, "wrote": False}


def validate_file(path: Path | str, store: Store, plugin_root: Path | str) -> dict:
    """Validate, correct and rewrite one assessment file; return the report dict (never raises on bad data)."""
    path = Path(path).expanduser().absolute()
    report = _new_report(path)
    assessment = _read_json(path)
    if assessment is None:
        report["errors"].append(f"cannot read {path} as JSON")
        return report
    if not isinstance(assessment, dict):
        report["errors"].append("assessment must be a JSON object")
        return report
    report["dealId"] = assessment.get("dealId")
    batches, primary = locate_batches(assessment, store)
    if not batches or primary is None:
        report["errors"].append(
            f"no batch found for dealId {assessment.get('dealId')!r}: run plan-assessment first, "
            "or set 'batchFile' in the assessment"
        )
        return report
    report["batchId"] = primary.get("batchId")
    framework, problem = load_framework_for(primary, plugin_root, store)
    if framework is None:
        report["errors"].append(problem or "framework not found")
        return report
    merged = merge_batches(batches, primary)
    report["errors"].extend(validate_assessment_shape(assessment, merged, framework))
    report["warnings"].extend(assessment_warnings(assessment, merged, framework))
    if not isinstance(assessment.get("interactions"), list):
        return report
    _process_assessment(assessment, merged, framework, report)
    _stamp(assessment, primary, batches, report)
    assessment["validation"] = {
        "at": assessment["validatedAt"], "errors": len(report["errors"]), "warnings": len(report["warnings"]),
        "capped": report["capped"], "verified": report["verified"], "unverified": report["unverified"],
        "restored": report["restored"],
    }
    store.write_json(path, assessment)
    report["wrote"] = True
    report["ok"] = not report["errors"]
    return report


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    # A judge agent usually runs from another directory and passes an absolute file path.
    # When no store exists at --home or cwd, use the store the assessment file belongs to,
    # so the run is logged there instead of creating a stray .flow-sales/ elsewhere.
    target = Path(args.file).expanduser().absolute()
    if not store.exists() and target.parent.name == "assessments" and (target.parent.parent / "config.json").exists():
        store = Store(target.parent.parent)
    report = validate_file(args.file, store, ctx["plugin_root"])
    store.log_run("validate-assessment", {"file": str(args.file)}, report["ok"], ctx["started"],
                  read=[report["file"]], wrote=[report["file"]] if report["wrote"] else [],
                  notes=f"errors={len(report['errors'])} warnings={len(report['warnings'])} capped={report['capped']}")
    _out(ctx, report, json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1
