"""Shape validation for canonical records (CONTRACTS section 5) and judge output (section 8).

Adapters call ``validate_records`` before saving. The assessment validator calls
``validate_assessment_shape`` for hard errors and ``assessment_warnings`` for soft
findings (missing optional fields, scored-but-not-applicable elements). Every function
returns a plain list of human-readable strings and never raises on bad data.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from ..config import PHASES
from ..util import parse_iso

KINDS = ("deal", "interaction", "rep", "contact", "company")
INTERACTION_TYPES = ("call", "email", "meeting", "note", "transcript")
DIRECTIONS = ("inbound", "outbound", "internal", "unknown")
OUTCOMES = ("won", "lost", "open")
CONFIDENCES = ("high", "medium", "low")
SPEAKERS = ("buyer", "rep")
ID_PREFIXES: dict[str, tuple[str, ...]] = {
    "deal": ("hs:", "csv:", "demo:"),
    "interaction": ("hs:", "granola:", "tx:", "csv:", "demo:"),
    "rep": ("rep:",),
    "contact": ("c:",),
    "company": ("co:",),
}
ELEMENT_OPTIONAL_FIELDS = ("quote", "speaker", "whyNotHigher", "nextQuestion", "confidence", "behaviour", "behaviourTags")


def _is_int(value: Any) -> bool:
    """True for ints and integral floats, never for bools."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and value.is_integer()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class _Checker:
    """Collects errors for one record; each check appends a message and returns the value."""

    def __init__(self, rec: dict, label: str):
        self.rec = rec
        self.label = label
        self.errors: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(f"{self.label}: {msg}")

    def present(self, key: str) -> bool:
        return self.rec.get(key) is not None

    def string(self, key: str, required: bool = False, allow_empty: bool = False) -> Optional[str]:
        val = self.rec.get(key)
        if val is None:
            if required:
                self.err(f"missing required key '{key}'")
            return None
        if not isinstance(val, str):
            self.err(f"'{key}' must be a string, got {type(val).__name__}")
            return None
        if not val.strip() and not allow_empty:
            self.err(f"'{key}' must not be empty")
            return None
        return val

    def iso(self, key: str, required: bool = False) -> None:
        val = self.rec.get(key)
        if val is None:
            if required:
                self.err(f"missing required timestamp '{key}'")
            return
        if not isinstance(val, str) or parse_iso(val) is None:
            self.err(f"'{key}' is not an ISO 8601 timestamp: {val!r}")

    def enum(self, key: str, allowed: tuple, required: bool = False) -> None:
        val = self.rec.get(key)
        if val is None:
            if required:
                self.err(f"missing required key '{key}' (one of {', '.join(allowed)})")
            return
        if val not in allowed:
            self.err(f"'{key}' must be one of {', '.join(allowed)}, got {val!r}")

    def number(self, key: str, required: bool = False) -> None:
        val = self.rec.get(key)
        if val is None:
            if required:
                self.err(f"missing required number '{key}'")
            return
        if not _is_number(val):
            self.err(f"'{key}' must be a number, got {type(val).__name__}")

    def list_of(self, key: str, item_type: Optional[type] = None, required: bool = False) -> Optional[list]:
        val = self.rec.get(key)
        if val is None:
            if required:
                self.err(f"missing required list '{key}'")
            return None
        if not isinstance(val, list):
            self.err(f"'{key}' must be a list, got {type(val).__name__}")
            return None
        if item_type is not None:
            bad = [i for i, item in enumerate(val) if not isinstance(item, item_type)]
            if bad:
                self.err(f"'{key}' items {bad[:5]} must be {item_type.__name__}")
                return None
        return val

    def mapping(self, key: str, required: bool = False) -> Optional[dict]:
        val = self.rec.get(key)
        if val is None:
            if required:
                self.err(f"missing required object '{key}'")
            return None
        if not isinstance(val, dict):
            self.err(f"'{key}' must be an object, got {type(val).__name__}")
            return None
        return val


def _check_prefix(c: _Checker, kind: str) -> None:
    rid = c.rec.get("id")
    if isinstance(rid, str) and rid and not rid.startswith(ID_PREFIXES[kind]):
        c.err(f"id must start with one of {', '.join(ID_PREFIXES[kind])}")


def _validate_stage_history(c: _Checker) -> None:
    history = c.list_of("stageHistory", dict)
    for i, entry in enumerate(history or []):
        sub = _Checker(entry, f"{c.label} stageHistory[{i}]")
        sub.iso("at", required=True)
        sub.string("stage", allow_empty=True)
        sub.string("label", allow_empty=True)
        sub.enum("phase", tuple(PHASES))
        c.errors.extend(sub.errors)


def _validate_deal(c: _Checker) -> None:
    c.string("source", required=True)
    c.string("name", required=True)
    c.number("amount")
    c.string("currency")
    c.string("pipeline", allow_empty=True)
    c.string("stage", required=True, allow_empty=True)
    c.string("stageLabel", allow_empty=True)
    c.enum("phase", tuple(PHASES), required=True)
    c.enum("outcome", OUTCOMES, required=True)
    c.iso("createdAt", required=True)
    c.iso("closedAt")
    c.string("ownerId")
    c.list_of("contactIds", str)
    c.string("companyId")
    c.string("companyDomain", allow_empty=True)
    c.mapping("meta")
    _validate_stage_history(c)


def _validate_participants(c: _Checker) -> None:
    participants = c.list_of("participants", dict)
    for i, person in enumerate(participants or []):
        sub = _Checker(person, f"{c.label} participants[{i}]")
        sub.string("name", allow_empty=True)
        sub.string("email", allow_empty=True)
        sub.string("role", allow_empty=True)
        c.errors.extend(sub.errors)


def _validate_interaction(c: _Checker) -> None:
    c.string("source", required=True)
    c.enum("type", INTERACTION_TYPES, required=True)
    c.string("dealId")
    c.enum("direction", DIRECTIONS)
    c.iso("at", required=True)
    c.number("durationSec")
    c.string("title", allow_empty=True)
    body = c.rec.get("body")
    if not isinstance(body, str):
        c.err("'body' must be a string (adapters set it to \"\" when the source has no text)")
    transcript = c.list_of("transcript", dict)
    for i, seg in enumerate(transcript or []):
        if not isinstance(seg.get("text"), str):
            c.err(f"transcript[{i}] needs a string 'text'")
            break
    c.string("notes", allow_empty=True)
    c.string("summary", allow_empty=True)
    _validate_participants(c)
    c.string("repId")
    c.string("recordingUrl", allow_empty=True)
    c.mapping("meta")


def _validate_rep(c: _Checker) -> None:
    c.string("name", required=True)
    c.string("email", allow_empty=True)
    c.string("source")


def _validate_contact(c: _Checker) -> None:
    c.string("name", allow_empty=True)
    c.string("email", allow_empty=True)
    c.string("title", allow_empty=True)
    c.string("companyId")
    c.string("buyingRole", allow_empty=True)


def _validate_company(c: _Checker) -> None:
    c.string("name", required=True)
    c.string("domain", allow_empty=True)


_VALIDATORS: dict[str, Callable[[_Checker], None]] = {
    "deal": _validate_deal,
    "interaction": _validate_interaction,
    "rep": _validate_rep,
    "contact": _validate_contact,
    "company": _validate_company,
}


def validate_records(kind: str, records: Any) -> list[str]:
    """Return every contract violation in ``records`` for the given record kind (empty list when clean)."""
    if kind not in KINDS:
        raise ValueError(f"unknown record kind {kind!r}; expected one of {', '.join(KINDS)}")
    if not isinstance(records, list):
        return [f"{kind}: records must be a list, got {type(records).__name__}"]
    errors: list[str] = []
    seen: dict[str, int] = {}
    for idx, rec in enumerate(records):
        label = f"{kind}[{idx}]"
        if not isinstance(rec, dict):
            errors.append(f"{label}: must be an object, got {type(rec).__name__}")
            continue
        rid = rec.get("id")
        if isinstance(rid, str) and rid:
            label = f"{label} {rid}"
        c = _Checker(rec, label)
        c.string("id", required=True)
        _check_prefix(c, kind)
        if isinstance(rid, str) and rid:
            if rid in seen:
                c.err(f"duplicate id (first seen at index {seen[rid]})")
            else:
                seen[rid] = idx
        _VALIDATORS[kind](c)
        errors.extend(c.errors)
    return errors


# ---------- assessment (judge output) ----------

def element_codes(framework: dict) -> list[str]:
    """Element codes in framework order."""
    return [e.get("code") for e in (framework.get("elements") or []) if isinstance(e, dict) and e.get("code")]


def tag_vocabulary(framework: dict) -> dict[str, set[str]]:
    """Allowed behaviour tags per element: the element's own tags plus the general ones."""
    general = set(framework.get("generalBehaviourTags") or [])
    vocab: dict[str, set[str]] = {}
    for element in framework.get("elements") or []:
        if isinstance(element, dict) and element.get("code"):
            vocab[element["code"]] = set(element.get("behaviourTags") or []) | general
    return vocab


def max_level(framework: dict) -> int:
    raw = framework.get("maxLevel", 3)
    return int(raw) if _is_int(raw) else 3


def batch_interaction_ids(batch: Optional[dict]) -> set[str]:
    return {
        i.get("interactionId")
        for i in ((batch or {}).get("interactions") or [])
        if isinstance(i, dict) and isinstance(i.get("interactionId"), str)
    }


def _validate_element_entry(entry: Any, label: str, top: int, tags: set[str]) -> list[str]:
    """Hard errors for one element score block."""
    if not isinstance(entry, dict):
        return [f"{label} must be an object"]
    errors: list[str] = []
    evidence = entry.get("evidence")
    if not _is_int(evidence):
        errors.append(f"{label}.evidence must be an integer 0..{top}, got {evidence!r}")
    elif not 0 <= int(evidence) <= top:
        errors.append(f"{label}.evidence {evidence} out of range 0..{top}")
    behaviour = entry.get("behaviour")
    if behaviour is not None and behaviour not in (0, 1, True, False):
        errors.append(f"{label}.behaviour must be 0 or 1, got {behaviour!r}")
    raw_tags = entry.get("behaviourTags")
    if raw_tags is not None:
        if not isinstance(raw_tags, list):
            errors.append(f"{label}.behaviourTags must be a list")
        else:
            unknown = [t for t in raw_tags if t not in tags]
            if unknown:
                errors.append(f"{label}.behaviourTags outside vocabulary: {unknown}")
    confidence = entry.get("confidence")
    if confidence is not None and confidence not in CONFIDENCES:
        errors.append(f"{label}.confidence must be one of {', '.join(CONFIDENCES)}, got {confidence!r}")
    speaker = entry.get("speaker")
    if speaker is not None and speaker not in SPEAKERS:
        errors.append(f"{label}.speaker must be buyer, rep or null, got {speaker!r}")
    quote = entry.get("quote")
    if quote is not None and not isinstance(quote, str):
        errors.append(f"{label}.quote must be a string or null")
    for key in ("whyNotHigher", "nextQuestion"):
        if entry.get(key) is not None and not isinstance(entry.get(key), str):
            errors.append(f"{label}.{key} must be a string")
    if entry.get("flags") is not None and not isinstance(entry.get("flags"), list):
        errors.append(f"{label}.flags must be a list")
    if entry.get("verified") is not None and not isinstance(entry.get("verified"), bool):
        errors.append(f"{label}.verified must be a boolean")
    return errors


def validate_assessment_shape(assessment: Any, batch: Optional[dict], framework: dict) -> list[str]:
    """Hard schema errors for a judge output file, checked against its batch and framework."""
    if not isinstance(assessment, dict):
        return ["assessment must be a JSON object"]
    batch = batch or {}
    errors: list[str] = []
    known_ids = batch_interaction_ids(batch)
    codes = element_codes(framework)
    vocab = tag_vocabulary(framework)
    top = max_level(framework)
    deal_id = assessment.get("dealId")
    if not isinstance(deal_id, str) or not deal_id:
        errors.append("dealId must be a non-empty string")
    elif batch.get("dealId") and deal_id != batch.get("dealId"):
        errors.append(f"dealId {deal_id} does not match the batch dealId {batch.get('dealId')}")
    interactions = assessment.get("interactions")
    if not isinstance(interactions, list):
        errors.append("interactions must be a list")
        return errors
    seen: set[str] = set()
    for idx, entry in enumerate(interactions):
        label = f"interactions[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        iid = entry.get("interactionId")
        if not isinstance(iid, str) or not iid:
            errors.append(f"{label}.interactionId is missing")
        else:
            label = f"{label} ({iid})"
            if iid not in known_ids:
                errors.append(f"{label}: interactionId is not in the batch")
            if iid in seen:
                errors.append(f"{label}: duplicate interactionId")
            seen.add(iid)
        errors.extend(_validate_interaction_entry(entry, label, codes, vocab, top))
    return errors


def _validate_interaction_entry(entry: dict, label: str, codes: list[str], vocab: dict[str, set[str]], top: int) -> list[str]:
    errors: list[str] = []
    applicable = entry.get("applicable")
    if not isinstance(applicable, list):
        errors.append(f"{label}.applicable must be a list of element codes")
        applicable = []
    for code in applicable:
        if code not in codes:
            errors.append(f"{label}.applicable: unknown element {code!r}")
    elements = entry.get("elements")
    if not isinstance(elements, dict):
        errors.append(f"{label}.elements must be an object")
        return errors
    for code in applicable:
        if code in codes and code not in elements:
            errors.append(f"{label}.elements: applicable element {code} has no entry")
    for code, block in elements.items():
        if code not in codes:
            errors.append(f"{label}.elements: unknown element {code!r}")
            continue
        errors.extend(_validate_element_entry(block, f"{label}.elements.{code}", top, vocab.get(code, set())))
    for key in ("notApplicableReason", "hygiene"):
        if entry.get(key) is not None and not isinstance(entry.get(key), dict):
            errors.append(f"{label}.{key} must be an object")
    if entry.get("summary") is not None and not isinstance(entry.get("summary"), str):
        errors.append(f"{label}.summary must be a string")
    return errors


def assessment_warnings(assessment: Any, batch: Optional[dict], framework: dict) -> list[str]:
    """Soft findings: missing optional fields, scored elements outside applicable, mismatched framework."""
    if not isinstance(assessment, dict):
        return []
    batch = batch or {}
    warnings: list[str] = []
    codes = element_codes(framework)
    quote_above = _quote_required_above(framework)
    slug = framework.get("slug")
    if slug and assessment.get("framework") and assessment.get("framework") != slug:
        warnings.append(f"framework {assessment.get('framework')!r} differs from the batch framework {slug!r}")
    for key in ("judgedAt", "model", "dealNotes"):
        if assessment.get(key) is None:
            warnings.append(f"missing optional field '{key}'")
    interactions = assessment.get("interactions")
    if not isinstance(interactions, list):
        return warnings
    for idx, entry in enumerate(interactions):
        if not isinstance(entry, dict):
            continue
        iid = entry.get("interactionId") or f"#{idx}"
        label = f"interactions[{idx}] ({iid})"
        for key in ("at", "phaseAtTime", "hygiene", "summary"):
            if entry.get(key) is None:
                warnings.append(f"{label}: missing optional field '{key}'")
        applicable = entry.get("applicable") if isinstance(entry.get("applicable"), list) else []
        reasons = entry.get("notApplicableReason") if isinstance(entry.get("notApplicableReason"), dict) else {}
        for code in codes:
            if code not in applicable and code not in reasons:
                warnings.append(f"{label}: element {code} is neither applicable nor explained in notApplicableReason")
        for code in reasons:
            if code in applicable:
                warnings.append(f"{label}: element {code} is both applicable and in notApplicableReason")
        elements = entry.get("elements") if isinstance(entry.get("elements"), dict) else {}
        for code, block in elements.items():
            if not isinstance(block, dict):
                continue
            if code in codes and code not in applicable:
                warnings.append(f"{label}.elements.{code}: scored but not in applicable")
            missing = [k for k in ELEMENT_OPTIONAL_FIELDS if k not in block]
            if missing:
                warnings.append(f"{label}.elements.{code}: missing optional fields {missing}")
            evidence = block.get("evidence")
            if _is_int(evidence) and int(evidence) > quote_above and block.get("speaker") is None:
                warnings.append(f"{label}.elements.{code}: evidence {evidence} without a speaker")
    return warnings


def _quote_required_above(framework: dict) -> int:
    raw = (framework.get("scoring") or {}).get("quoteRequiredAbove", 1)
    return int(raw) if _is_int(raw) else 1
