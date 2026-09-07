"""Small shared helpers. Standard library only."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from typing import Any, Iterable, Optional

ISO_Z = "%Y-%m-%dT%H:%M:%SZ"


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime(ISO_Z)


def parse_iso(value: Optional[str]) -> Optional[_dt.datetime]:
    """Parse ISO 8601 (date or datetime, with or without Z/offset) into an aware UTC datetime."""
    if not value:
        return None
    s = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return _dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=_dt.timezone.utc)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = _dt.datetime.fromisoformat(s)
    except ValueError:
        # epoch milliseconds as a digit string (HubSpot timestamps and BETWEEN filter values)
        if re.fullmatch(r"\d+", s):
            return _dt.datetime.fromtimestamp(int(s) / 1000.0, tz=_dt.timezone.utc)
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return d.astimezone(_dt.timezone.utc)


def to_iso(d: Optional[_dt.datetime]) -> Optional[str]:
    if d is None:
        return None
    return d.astimezone(_dt.timezone.utc).strftime(ISO_Z)


def epoch_ms_to_iso(ms: Any) -> Optional[str]:
    try:
        return to_iso(_dt.datetime.fromtimestamp(int(ms) / 1000.0, tz=_dt.timezone.utc))
    except (TypeError, ValueError):
        return None


def iso_week(d: _dt.datetime) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def quarter_bounds(q: str) -> tuple[_dt.datetime, _dt.datetime]:
    """'2026-Q3' -> (start, end_exclusive) in UTC."""
    m = re.fullmatch(r"(\d{4})-Q([1-4])", q.strip().upper())
    if not m:
        raise ValueError(f"bad quarter: {q!r} (expected YYYY-Qn)")
    year, n = int(m.group(1)), int(m.group(2))
    start = _dt.datetime(year, 3 * (n - 1) + 1, 1, tzinfo=_dt.timezone.utc)
    end = _dt.datetime(year + (1 if n == 4 else 0), 1 if n == 4 else 3 * n + 1, 1, tzinfo=_dt.timezone.utc)
    return start, end


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def safe_id(identifier: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", identifier.replace(":", "_"))


def normalize_text(text: str) -> str:
    """Lower-case, collapse whitespace, strip smart quotes, for quote verification."""
    t = (text or "").lower()
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("—", "-").replace("–", "-")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def email_domain(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return None
    return email.rsplit("@", 1)[1].strip().lower() or None


def chunked(items: Iterable[Any], size: int) -> Iterable[list]:
    batch: list = []
    for it in items:
        batch.append(it)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def get_dotted(obj: dict, key: str, default: Any = None) -> Any:
    cur: Any = obj
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_dotted(obj: dict, key: str, value: Any) -> None:
    parts = key.split(".")
    cur = obj
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def transcript_to_body(segments: list[dict]) -> str:
    lines = []
    for seg in segments or []:
        speaker = (seg.get("speaker") or "Unknown").strip()
        text = (seg.get("text") or "").strip()
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)
