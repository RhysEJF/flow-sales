"""Pure parsers for Granola meeting data. No file or network IO here; standard library only.

Every parser returns a list of "granola meeting dicts" (see new_meeting for the shape). That shape is
the contract between the setup skill (which saves MCP tool output verbatim), the public API client and
the adapter in granola.py, which turns each dict into a canonical Interaction with to_interaction.

Parsers:
- parse_mcp_text: the XML-ish text envelopes returned by the official Granola MCP server
  (list_meetings, get_meetings, get_meeting_transcript), saved verbatim by the setup skill.
- parse_public_api_note: a Note object from GET /v1/notes/{id}?include=transcript on the public API.
- parse_csv: Granola's CSV export (Settings > Profile > Generate CSV). Granola does not document the
  column names, so columns are detected by header keywords; docs/granola.md lists the assumptions.
- parse_markdown: markdown exports written by community tools (front matter plus headed sections).
- parse_cache_json: the legacy plaintext desktop cache (cache-v3/v6.json) from before May 2026, or
  from a Windows install where it can still be decrypted by the user.

Helpers shared by the adapter: normalize_uuid, uuid_from_url, parse_meeting_date, hms_to_seconds,
parse_participant_line, parse_transcript_lines, merge_meetings, to_interaction.
"""
from __future__ import annotations

import csv
import datetime as _dt
import html
import io
import json
import re
from typing import Any, Optional

from ..util import email_domain, parse_iso, sha1_text, to_iso, transcript_to_body

try:  # zoneinfo ships with Python 3.9+, but the tz database may be missing (Windows without tzdata)
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

SOURCE_MCP = "granola:mcp"
SOURCE_API = "granola:public-api"
SOURCE_CSV = "granola:csv"
SOURCE_MARKDOWN = "granola:markdown"
SOURCE_CACHE = "granola:cache"

ROLE_CREATOR = "note creator"
ROLE_ATTENDEE = "attendee"
ROLE_ORGANISER = "organiser"
ROLE_OWNER = "owner"

WEB_URL_PREFIX = "https://notes.granola.ai/d/"

_UTC = _dt.timezone.utc

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HEX32_RE = re.compile(r"^[0-9a-f]{32}$")
_UUID_ANYWHERE_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


# ---------------------------------------------------------------------------
# The export shape
# ---------------------------------------------------------------------------

def new_meeting(**fields: Any) -> dict:
    """A granola meeting dict with every key present. Extra keys used by the adapter:
    created_at, transcript_started_at (absolute ISO of the first transcript segment), extra (source markers)."""
    meeting = {
        "id": None,
        "uuid": None,
        "source": None,
        "title": None,
        "at": None,
        "date_text": None,
        "participants": [],
        "summary_markdown": None,
        "private_notes_markdown": None,
        "transcript": [],
        "calendar_event": None,
        "web_url": None,
        "owner": None,
        "folders": [],
        "duration_sec": None,
        "created_at": None,
        "transcript_started_at": None,
        "extra": {},
    }
    meeting.update(fields)
    return meeting


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------

def normalize_uuid(value: Any) -> Optional[str]:
    """Return a lower-case hyphenated UUID when value is one (with or without hyphens), else None."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if _UUID_RE.match(s):
        return s
    if _HEX32_RE.match(s):
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
    return None


def uuid_from_url(url: Any) -> Optional[str]:
    """The document UUID inside a notes.granola.ai/d/<uuid> link (or any URL carrying a UUID)."""
    if not url:
        return None
    m = _UUID_ANYWHERE_RE.search(str(url))
    return m.group(0).lower() if m else None


def uuid_from_path(path: Any) -> Optional[str]:
    """A UUID embedded in a file name such as <uuid>.txt or <uuid>-transcript.txt."""
    if not path:
        return None
    name = str(path).replace("\\", "/").rsplit("/", 1)[-1]
    m = _UUID_ANYWHERE_RE.search(name)
    if m:
        return m.group(0).lower()
    stem = name.split(".", 1)[0]
    for piece in re.split(r"[-_ ]", stem):
        u = normalize_uuid(piece)
        if u:
            return u
    return normalize_uuid(stem.replace("-transcript", ""))


# ---------------------------------------------------------------------------
# Dates and durations
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p", "%b %d, %Y, %I:%M %p", "%B %d, %Y, %I:%M %p",
    "%b %d, %Y %I:%M:%S %p", "%B %d, %Y %I:%M:%S %p",
    "%b %d, %Y %H:%M", "%B %d, %Y %H:%M", "%b %d, %Y, %H:%M", "%B %d, %Y, %H:%M",
    "%b %d, %Y %H:%M:%S", "%B %d, %Y %H:%M:%S",
    "%b %d, %Y", "%B %d, %Y", "%b %d %Y %I:%M %p", "%B %d %Y %I:%M %p", "%b %d %Y", "%B %d %Y",
    "%d %b %Y %I:%M %p", "%d %B %Y %I:%M %p", "%d %b %Y, %I:%M %p", "%d %B %Y, %I:%M %p",
    "%d %b %Y %H:%M", "%d %B %Y %H:%M", "%d %b %Y, %H:%M", "%d %B %Y, %H:%M",
    "%d %b %Y %H:%M:%S", "%d %B %Y %H:%M:%S", "%d %b %Y", "%d %B %Y",
    "%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
    "%m/%d/%y %I:%M %p", "%m/%d/%y %H:%M", "%m/%d/%y",
    "%d.%m.%Y %H:%M", "%d.%m.%Y",
]
_WEEKDAY_RE = re.compile(r"^(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+", re.IGNORECASE)
_ORDINAL_RE = re.compile(r"(\d)(st|nd|rd|th)\b", re.IGNORECASE)
_UTC_SUFFIX_RE = re.compile(r"\s*(?:\(?(?:UTC|GMT|Z)\)?)$", re.IGNORECASE)
_TZ_ABBR_RE = re.compile(r"\s+\(?[A-Z]{2,5}\)?$")
_ISO_OFFSET_RE = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})$")
_ISO_NAIVE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:[.,]\d+)?)?)?$")


def _tzinfo(tz: Any) -> _dt.tzinfo:
    if tz is None:
        return _UTC
    if isinstance(tz, _dt.tzinfo):
        return tz
    name = str(tz).strip()
    if not name or name.upper() in ("UTC", "Z", "GMT"):
        return _UTC
    if ZoneInfo is None:
        return _UTC
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - unknown zone or missing tz database
        return _UTC


def _localize(naive: _dt.datetime, tz: Any, force_utc: bool = False) -> _dt.datetime:
    return naive.replace(tzinfo=_UTC if force_utc else _tzinfo(tz))


def parse_meeting_date(text: Any, tz: Any = None) -> Optional[str]:
    """Parse a Granola date string ("Feb 4, 2026 7:30 PM", ISO, US or UK numeric forms) into ISO UTC.

    Strings without an explicit offset are local time in tz (a zone name or tzinfo; UTC by default).
    Numbers are epoch seconds or milliseconds. Returns None when nothing matches.
    """
    if text is None:
        return None
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        value = float(text)
        if value > 1e11:  # milliseconds
            value = value / 1000.0
        try:
            return to_iso(_dt.datetime.fromtimestamp(value, tz=_UTC))
        except (OverflowError, OSError, ValueError):
            return None
    s = str(text).strip()
    if not s:
        return None
    s = s.replace(" ", " ").replace(" ", " ")
    s = re.sub(r"\s+", " ", s).strip()
    force_utc = False
    m = _UTC_SUFFIX_RE.search(s)
    if m and m.start() > 0 and not s[:m.start()].endswith("T"):
        s = s[:m.start()].strip()
        force_utc = True
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        if _ISO_OFFSET_RE.search(s) and len(s) > 10:
            d = parse_iso(s)
            if d:
                return to_iso(d)
        if _ISO_NAIVE_RE.match(s):
            try:
                d = _dt.datetime.fromisoformat(s.replace(",", "."))
            except ValueError:
                d = None
            if d is not None:
                if d.tzinfo is None:
                    d = _localize(d, tz, force_utc)
                return to_iso(d)
    if re.fullmatch(r"\d{11,14}", s):
        return parse_meeting_date(int(s), tz)
    cleaned = _WEEKDAY_RE.sub("", s)
    cleaned = _ORDINAL_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"\s+at\s+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    candidates = [cleaned]
    stripped = _TZ_ABBR_RE.sub("", cleaned)
    if stripped != cleaned:
        candidates.append(stripped)
    for cand in candidates:
        for fmt in _DATE_FORMATS:
            try:
                d = _dt.datetime.strptime(cand, fmt)
            except ValueError:
                continue
            return to_iso(_localize(d, tz, force_utc))
    return None


_HMS_RE = re.compile(r"^(?:(\d{1,2}):)?(\d{1,3}):(\d{2})(?:[.,](\d{1,3}))?$")


def hms_to_seconds(text: Any) -> Optional[float]:
    """'00:00:15' or '1:02:03.5' or '00:15' (mm:ss) to seconds."""
    if text is None:
        return None
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text)
    m = _HMS_RE.match(str(text).strip())
    if not m:
        return None
    hours, minutes, seconds, frac = m.groups()
    total = int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)
    if frac:
        total += int(frac.ljust(3, "0")) / 1000.0
    return float(total)


def parse_duration_text(text: Any) -> Optional[int]:
    """'1860', '31:00', '00:31:00', '31 min', '1h 5m', '1.5h' to whole seconds."""
    if text is None:
        return None
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return int(text) if text > 0 else None
    s = str(text).strip().lower()
    if not s:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return int(float(s)) or None
    hms = hms_to_seconds(s)
    if hms is not None:
        return int(hms) or None
    total = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours|m|min|mins|minute|minutes|s|sec|secs|second|seconds)\b", s):
        value = float(num)
        if unit.startswith("h"):
            total += value * 3600
        elif unit.startswith("m"):
            total += value * 60
        else:
            total += value
    return int(total) or None


def _seconds_between(start: Any, end: Any) -> Optional[int]:
    a, b = parse_iso(start), parse_iso(end)
    if a is None or b is None:
        return None
    delta = int((b - a).total_seconds())
    return delta if delta > 0 else None


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------

def normalize_role(text: Any) -> str:
    t = (str(text or "")).strip().lower()
    if not t:
        return ROLE_ATTENDEE
    if "creator" in t or t in ("you", "me", "note taker", "note-taker", "notetaker", "host"):
        return ROLE_CREATOR
    if "organi" in t:
        return ROLE_ORGANISER
    if "owner" in t:
        return ROLE_OWNER
    return ROLE_ATTENDEE


def make_participant(name: Any = None, email: Any = None, company: Any = None, role: Any = None) -> Optional[dict]:
    email_s = (str(email).strip().lower() if email else "") or None
    if email_s and not _EMAIL_RE.fullmatch(email_s):
        email_s = None
    name_s = re.sub(r"\s+", " ", str(name or "")).strip(" -*•") or None
    company_s = re.sub(r"\s+", " ", str(company or "")).strip() or None
    if not name_s and not email_s:
        return None
    return {"name": name_s, "email": email_s, "company": company_s, "role": normalize_role(role)}


def parse_participant_line(line: str) -> Optional[dict]:
    """'John Doe (note creator) from Acme <john@acme.com>' -> participant dict. Role, company and email optional."""
    if not line:
        return None
    s = html.unescape(line).strip()
    s = re.sub(r"^[-*•]\s*", "", s).strip()
    if not s or s.lower() in ("none", "unknown", "n/a"):
        return None
    email = None
    m = re.search(r"<\s*([^<>\s]+@[^<>\s]+)\s*>", s)
    if m:
        email = m.group(1)
        s = (s[:m.start()] + s[m.end():]).strip()
    elif _EMAIL_RE.fullmatch(s):
        return make_participant(None, s)
    else:
        m2 = re.search(r"\(\s*([^()\s]+@[^()\s]+)\s*\)", s)
        if m2:
            email = m2.group(1)
            s = (s[:m2.start()] + s[m2.end():]).strip()
    role = None
    m = re.search(r"\(([^()]*)\)", s)
    if m:
        role = m.group(1).strip()
        s = (s[:m.start()] + " " + s[m.end():]).strip()
    company = None
    m = re.search(r"\s+from\s+(.+)$", s)
    if m:
        company = m.group(1).strip().rstrip(",")
        s = s[:m.start()].strip()
    s = s.strip(" ,;:-")
    if not s and not email:
        return None
    return make_participant(s or None, email, company, role)


def participant_key(p: dict) -> str:
    return (p.get("email") or "").lower() or (p.get("name") or "").lower()


_ROLE_RANK = {ROLE_OWNER: 3, ROLE_CREATOR: 2, ROLE_ORGANISER: 1, ROLE_ATTENDEE: 0}


def add_participant(participants: list[dict], new: Optional[dict]) -> None:
    """Union by email (or name when no email): fill missing name and company, keep the strongest role."""
    if not new:
        return
    key = participant_key(new)
    if not key:
        return
    for existing in participants:
        if participant_key(existing) == key or (
            new.get("email") and existing.get("email") == new.get("email")
        ) or (
            not new.get("email") and not existing.get("email") and existing.get("name") and new.get("name")
            and existing["name"].lower() == new["name"].lower()
        ):
            if not existing.get("name") and new.get("name"):
                existing["name"] = new["name"]
            if not existing.get("email") and new.get("email"):
                existing["email"] = new["email"]
            if not existing.get("company") and new.get("company"):
                existing["company"] = new["company"]
            if _ROLE_RANK.get(new.get("role"), 0) > _ROLE_RANK.get(existing.get("role"), 0):
                existing["role"] = new["role"]
            return
    participants.append(dict(new))


def split_people_cell(text: Any) -> list[dict]:
    """'Sam Rep <sam@vendor.com>; Priya Shah <priya@acme.com>' or newline/comma separated names and emails."""
    if not text:
        return []
    raw = str(text)
    if ";" in raw or "\n" in raw or "|" in raw:
        tokens = re.split(r"[;\n|]+", raw)
    else:
        # commas separate people unless they sit inside 'Last, First' pairs; assume separators
        tokens = raw.split(",")
    out: list[dict] = []
    for tok in tokens:
        p = parse_participant_line(tok.strip())
        add_participant(out, p)
    return out


def owner_from_participants(participants: list[dict]) -> Optional[dict]:
    for role in (ROLE_OWNER, ROLE_CREATOR):
        for p in participants:
            if p.get("role") == role:
                return {"name": p.get("name"), "email": p.get("email")}
    return None


# ---------------------------------------------------------------------------
# Transcript lines
# ---------------------------------------------------------------------------

_TS_PAT = r"(?:\d{1,2}:)?\d{1,3}:\d{2}(?:[.,]\d{1,3})?"
_TS_LEAD_RE = re.compile(
    rf"^\s*(?:[-*]\s+)?(?:[\[(]\s*(?P<a>{_TS_PAT})\s*[\])]|(?P<b>{_TS_PAT}))\s*(?:[-:]\s*)?(?P<rest>.*)$"
)
_SPEAKER_RE = re.compile(
    rf"^\s*(?:\*\*)?(?P<speaker>[^:*\[\]()]{{1,60}}?)(?:\*\*)?\s*(?:[\[(]\s*(?P<ts>{_TS_PAT})\s*[\])])?\s*(?:\*\*)?\s*:\s*(?P<text>.*)$"
)


def _plausible_speaker(s: str) -> bool:
    s = s.strip()
    if not s or len(s) > 60 or s.lower().startswith("http"):
        return False
    if not re.search(r"[A-Za-z]", s):
        return False
    if s.endswith("."):
        return False
    return len(s.split()) <= 5


def _match_transcript_line(line: str) -> Optional[tuple[Optional[float], Optional[str], str]]:
    """Return (t, speaker, text) for a labelled line, else None."""
    ts: Optional[float] = None
    rest = line
    m = _TS_LEAD_RE.match(line)
    if m:
        ts = hms_to_seconds(m.group("a") or m.group("b"))
        rest = m.group("rest")
    sm = _SPEAKER_RE.match(rest)
    if sm and _plausible_speaker(sm.group("speaker")):
        if ts is None and sm.group("ts"):
            ts = hms_to_seconds(sm.group("ts"))
        return ts, sm.group("speaker").strip().strip("*").strip(), sm.group("text").strip()
    if ts is not None:
        return ts, None, rest.strip()
    return None


def looks_like_transcript(text: str) -> bool:
    """True when at least half of the non-empty lines carry a timestamp or a speaker label."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return False
    hits = sum(1 for ln in lines if _match_transcript_line(ln) is not None)
    return hits * 2 >= len(lines)


def parse_transcript_lines(text: str, labelled: Optional[bool] = None) -> list[dict]:
    """Lines like '[00:00:15] Name: text' (also 'mm:ss', '**Name:**', 'Name (00:15): text', bare 'Name: text').

    Continuation lines join the previous segment. When labelled is False (or None and the text does not
    look labelled) every non-empty line becomes an 'Unknown' segment without a time.
    """
    if not text:
        return []
    if labelled is None:
        labelled = looks_like_transcript(text)
    segments: list[dict] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        parsed = _match_transcript_line(line) if labelled else None
        if parsed is not None:
            t, speaker, body = parsed
            segments.append({"speaker": speaker or "Unknown", "t": t, "text": body})
        elif segments and labelled:
            segments[-1]["text"] = (segments[-1]["text"] + " " + line.strip()).strip()
        else:
            segments.append({"speaker": "Unknown", "t": None, "text": line.strip()})
    return [s for s in segments if s["text"]]


def transcript_span_seconds(segments: list[dict]) -> Optional[int]:
    """Duration implied by a transcript: last end (or last start) minus first start."""
    times = [s.get("t") for s in segments if isinstance(s.get("t"), (int, float))]
    if not times:
        return None
    first = min(times)
    ends = [s.get("end") for s in segments if isinstance(s.get("end"), (int, float))]
    last = max(ends) if ends else max(times)
    span = int(round(last - first)) if ends else int(round(last))
    return span if span > 0 else None


# ---------------------------------------------------------------------------
# (a) MCP text envelopes
# ---------------------------------------------------------------------------

_ATTR_RE = re.compile(r"""([A-Za-z_][\w.:-]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>]+))""")
_MEETING_OPEN_RE = re.compile(r"<meeting\b([^<>]*?)(/?)>", re.IGNORECASE)
_MEETING_CLOSE_RE = re.compile(r"</meeting\s*>", re.IGNORECASE)
_TRANSCRIPT_BLOCK_RE = re.compile(r"<transcript\b([^<>]*)>(.*?)</transcript\s*>", re.IGNORECASE | re.DOTALL)


def _block_re(names: str) -> "re.Pattern[str]":
    return re.compile(rf"<(?:{names})\b[^<>]*>(.*?)</(?:{names})\s*>", re.IGNORECASE | re.DOTALL)


_PARTICIPANTS_BLOCK_RE = _block_re("known_participants|participants|attendees|people")
_SUMMARY_BLOCK_RE = _block_re("summary|enhanced_notes|ai_notes|notes_summary|meeting_notes")
_PRIVATE_BLOCK_RE = _block_re("private_notes|my_notes|user_notes|personal_notes|private")
_NOTES_BLOCK_RE = _block_re("notes")


def parse_tag_attrs(attr_text: str) -> dict:
    attrs: dict = {}
    for m in _ATTR_RE.finditer(attr_text or ""):
        key = m.group(1).lower()
        val = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))
        attrs[key] = html.unescape(val or "")
    return attrs


def _first_attr(attrs: dict, *names: str) -> Optional[str]:
    for n in names:
        v = attrs.get(n)
        if v not in (None, ""):
            return v
    return None


def _strip_block(text: str) -> Optional[str]:
    if text is None:
        return None
    t = text.strip("\r\n")
    t = re.sub(r"^\s*\n", "", t)
    t = t.strip()
    return t or None


def _parse_participant_block(block_text: str) -> list[dict]:
    out: list[dict] = []
    for line in (block_text or "").splitlines():
        add_participant(out, parse_participant_line(line))
    return out


def _parse_transcript_block(attr_text: str, body: str) -> tuple[Optional[str], list[dict]]:
    attrs = parse_tag_attrs(attr_text)
    raw_id = _first_attr(attrs, "meeting_id", "meetingid", "id", "document_id", "note_id", "uuid")
    segments = parse_transcript_lines(html.unescape(body) if "&lt;" in body or "&amp;" in body else body, labelled=True)
    return (normalize_uuid(raw_id) or raw_id), segments


def parse_mcp_text(text: str, tz: Any = None, fallback_id: Any = None) -> list[dict]:
    """Parse text returned by the Granola MCP tools (saved verbatim, one or more tool responses per file).

    Handles <meetings_data> with <meeting id=".." title=".." date=".."> elements (any attribute order,
    self-closing or not), <known_participants> lines, <summary> and private-notes blocks, and
    <transcript meeting_id=".."> blocks (inside a meeting or on their own). A transcript-only file yields a
    meeting dict with the transcript and the id only; the adapter merges it by UUID with the meeting from
    another file. fallback_id (usually the UUID in the file name) is used when a transcript has no id.
    """
    if not text:
        return []
    meetings: list[dict] = []
    by_id: dict[str, dict] = {}
    consumed: list[tuple[int, int]] = []
    fallback_uuid = normalize_uuid(fallback_id) or (str(fallback_id) if fallback_id else None)

    for m in _MEETING_OPEN_RE.finditer(text):
        attrs = parse_tag_attrs(m.group(1))
        self_closing = bool(m.group(2))
        start = m.end()
        if self_closing:
            content, end = "", m.end()
        else:
            close = _MEETING_CLOSE_RE.search(text, start)
            nxt = _MEETING_OPEN_RE.search(text, start)
            if close and (not nxt or close.start() < nxt.start()):
                content, end = text[start:close.start()], close.end()
            elif nxt:
                content, end = text[start:nxt.start()], nxt.start()
            else:
                content, end = text[start:], len(text)
        if any(s <= m.start() < e for s, e in consumed):
            continue
        consumed.append((m.start(), end))
        raw_id = _first_attr(attrs, "id", "meeting_id", "document_id", "uuid", "note_id")
        uuid = normalize_uuid(raw_id)
        date_text = _first_attr(attrs, "date", "datetime", "start", "start_time", "time", "created", "created_at", "when")
        meeting = new_meeting(
            id=uuid or raw_id,
            uuid=uuid,
            source=SOURCE_MCP,
            title=_first_attr(attrs, "title", "name", "subject"),
            at=parse_meeting_date(date_text, tz),
            date_text=date_text,
            web_url=_first_attr(attrs, "url", "web_url", "link") or (WEB_URL_PREFIX + uuid if uuid else None),
            duration_sec=parse_duration_text(_first_attr(attrs, "duration", "duration_sec", "length")),
            created_at=parse_meeting_date(_first_attr(attrs, "created_at", "created"), tz),
        )
        folder = _first_attr(attrs, "folder", "folders")
        if folder:
            meeting["folders"] = [f.strip() for f in re.split(r"[;,|]", folder) if f.strip()]
        participants: list[dict] = []
        for block in _PARTICIPANTS_BLOCK_RE.findall(content):
            for p in _parse_participant_block(block):
                add_participant(participants, p)
        meeting["participants"] = participants
        meeting["owner"] = owner_from_participants(participants)
        summaries = [_strip_block(b) for b in _SUMMARY_BLOCK_RE.findall(content)]
        summaries = [s for s in summaries if s]
        privates = [_strip_block(b) for b in _PRIVATE_BLOCK_RE.findall(content)]
        privates = [s for s in privates if s]
        notes_blocks = [_strip_block(b) for b in _NOTES_BLOCK_RE.findall(content)]
        notes_blocks = [s for s in notes_blocks if s]
        if not summaries and notes_blocks:
            summaries, notes_blocks = notes_blocks, []
        privates.extend(notes_blocks)
        meeting["summary_markdown"] = "\n\n".join(summaries) or None
        meeting["private_notes_markdown"] = "\n\n".join(privates) or None
        for attr_text, body in _TRANSCRIPT_BLOCK_RE.findall(content):
            _tid, segments = _parse_transcript_block(attr_text, body)
            if segments and len(segments) >= len(meeting["transcript"]):
                meeting["transcript"] = segments
        if meeting["transcript"] and not meeting["duration_sec"]:
            meeting["duration_sec"] = transcript_span_seconds(meeting["transcript"])
        meetings.append(meeting)
        key = meeting["uuid"] or meeting["id"]
        if key:
            by_id[key] = meeting

    # transcript blocks outside any <meeting> element
    remaining = text
    for s, e in sorted(consumed, reverse=True):
        remaining = remaining[:s] + remaining[e:]
    for attr_text, body in _TRANSCRIPT_BLOCK_RE.findall(remaining):
        tid, segments = _parse_transcript_block(attr_text, body)
        if not segments:
            continue
        if not tid:
            if len(meetings) == 1:
                tid = meetings[0]["uuid"] or meetings[0]["id"]
            else:
                tid = fallback_uuid
        target = by_id.get(tid) if tid else None
        if target is None:
            target = new_meeting(id=tid, uuid=normalize_uuid(tid), source=SOURCE_MCP,
                                 web_url=(WEB_URL_PREFIX + normalize_uuid(tid)) if normalize_uuid(tid) else None)
            meetings.append(target)
            if tid:
                by_id[tid] = target
        if len(segments) >= len(target["transcript"]):
            target["transcript"] = segments
            target["duration_sec"] = target["duration_sec"] or transcript_span_seconds(segments)

    if not meetings and fallback_uuid and "<" not in text[:200] and looks_like_transcript(text):
        segments = parse_transcript_lines(text, labelled=True)
        if segments:
            meetings.append(new_meeting(id=fallback_uuid, uuid=normalize_uuid(fallback_uuid), source=SOURCE_MCP,
                                        transcript=segments, duration_sec=transcript_span_seconds(segments),
                                        web_url=(WEB_URL_PREFIX + normalize_uuid(fallback_uuid)) if normalize_uuid(fallback_uuid) else None))
    return meetings


# ---------------------------------------------------------------------------
# (b) Public API note
# ---------------------------------------------------------------------------

def _speaker_name(item: dict, owner_name: Optional[str]) -> str:
    sp = item.get("speaker")
    if isinstance(sp, str):
        return sp.strip() or "Unknown"
    sp = sp or {}
    if sp.get("name"):
        return str(sp["name"]).strip()
    attribution = (sp.get("attribution") or "").lower()
    if attribution == "me":
        return owner_name or "Me"
    if attribution == "them":
        return "Them"
    if sp.get("diarization_label"):
        return str(sp["diarization_label"]).strip()
    source = (sp.get("source") or "").lower()
    if source == "microphone":
        return owner_name or "Me"
    if source in ("speaker", "system"):
        return "Them"
    if isinstance(item.get("speaker_name"), str):
        return item["speaker_name"]
    return "Unknown"


def _abs_or_relative_seconds(value: Any, base: Optional[_dt.datetime]) -> tuple[Optional[float], Optional[_dt.datetime]]:
    """Transcript times may be absolute ISO strings or relative seconds. Returns (relative seconds, absolute dt)."""
    if value is None:
        return None, None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), None
    s = str(value).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return float(s), None
    d = parse_iso(s)
    if d is None:
        return hms_to_seconds(s), None
    if base is None:
        return 0.0, d
    return (d - base).total_seconds(), d


def transcript_items_to_segments(items: list[dict], owner_name: Optional[str]) -> tuple[list[dict], Optional[str]]:
    """Public API transcript items -> segments {speaker, t, text, end}; also the absolute start of the first item."""
    segments: list[dict] = []
    base: Optional[_dt.datetime] = None
    for item in items or []:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        start_raw = item.get("start_time", item.get("start_timestamp", item.get("start")))
        end_raw = item.get("end_time", item.get("end_timestamp", item.get("end")))
        if base is None and isinstance(start_raw, str):
            d = parse_iso(start_raw) if not re.fullmatch(r"\d+(?:\.\d+)?", start_raw.strip()) else None
            if d is not None:
                base = d
        t, _ = _abs_or_relative_seconds(start_raw, base)
        end, _ = _abs_or_relative_seconds(end_raw, base)
        segments.append({"speaker": _speaker_name(item, owner_name), "t": t, "text": text, "end": end})
    if segments and all(isinstance(s.get("t"), (int, float)) for s in segments):
        first = min(s["t"] for s in segments)
        if first > 0 and base is None:
            # relative seconds that do not start at zero stay as they are; absolute times are rebased above
            pass
    return segments, (to_iso(base) if base else None)


def parse_public_api_note(note_json: dict, transcript_items: Optional[list] = None, tz: Any = None) -> list[dict]:
    """GET /v1/notes/{id}?include=transcript object -> [meeting dict]. transcript_items (from the paged
    /transcript endpoint) override note_json['transcript'] when given."""
    if not isinstance(note_json, dict):
        return []
    note = note_json
    if isinstance(note.get("note"), dict) and not note.get("id"):
        note = note["note"]
    nid = note.get("id")
    web_url = note.get("web_url") or note.get("url")
    uuid = uuid_from_url(web_url) or normalize_uuid(nid) or normalize_uuid(note.get("document_id"))
    owner_raw = note.get("owner") or note.get("creator") or {}
    owner = None
    if isinstance(owner_raw, dict) and (owner_raw.get("name") or owner_raw.get("email")):
        owner = {"name": owner_raw.get("name") or None, "email": (owner_raw.get("email") or "").lower() or None}
    elif isinstance(owner_raw, str) and owner_raw:
        p = parse_participant_line(owner_raw)
        owner = {"name": p.get("name"), "email": p.get("email")} if p else None

    cal_raw = note.get("calendar_event")
    calendar_event = None
    if isinstance(cal_raw, dict) and cal_raw:
        invitees = []
        for inv in cal_raw.get("invitees") or cal_raw.get("attendees") or []:
            if isinstance(inv, dict) and inv.get("email"):
                invitees.append({"email": str(inv["email"]).lower()})
            elif isinstance(inv, str) and "@" in inv:
                invitees.append({"email": inv.lower()})
        organiser = cal_raw.get("organiser") or cal_raw.get("organizer")
        if isinstance(organiser, dict):
            organiser = organiser.get("email")
        calendar_event = {
            "event_title": cal_raw.get("event_title") or cal_raw.get("title") or cal_raw.get("summary"),
            "scheduled_start_time": cal_raw.get("scheduled_start_time") or cal_raw.get("start_time"),
            "scheduled_end_time": cal_raw.get("scheduled_end_time") or cal_raw.get("end_time"),
            "invitees": invitees,
            "organiser": (str(organiser).lower() if organiser else None),
            "calendar_event_id": cal_raw.get("calendar_event_id") or cal_raw.get("id"),
        }

    participants: list[dict] = []
    for a in note.get("attendees") or []:
        if isinstance(a, dict):
            add_participant(participants, make_participant(a.get("name"), a.get("email"), a.get("company"), ROLE_ATTENDEE))
        elif isinstance(a, str):
            add_participant(participants, parse_participant_line(a))
    if calendar_event:
        for inv in calendar_event["invitees"]:
            add_participant(participants, make_participant(None, inv["email"], None, ROLE_ATTENDEE))
        if calendar_event.get("organiser"):
            add_participant(participants, make_participant(None, calendar_event["organiser"], None, ROLE_ORGANISER))
    if owner:
        add_participant(participants, make_participant(owner.get("name"), owner.get("email"), None, ROLE_OWNER))

    items = transcript_items if transcript_items is not None else (note.get("transcript") or [])
    segments, started_at = transcript_items_to_segments(items if isinstance(items, list) else [], owner.get("name") if owner else None)

    created_at = parse_meeting_date(note.get("created_at"), tz)
    at = None
    if calendar_event and calendar_event.get("scheduled_start_time"):
        at = parse_meeting_date(calendar_event["scheduled_start_time"], tz)
    at = at or started_at or created_at

    duration = None
    if calendar_event:
        duration = _seconds_between(calendar_event.get("scheduled_start_time"), calendar_event.get("scheduled_end_time"))
    if duration is None:
        duration = transcript_span_seconds(segments)

    folders = []
    for f in note.get("folder_membership") or note.get("folders") or []:
        name = f.get("name") if isinstance(f, dict) else (f if isinstance(f, str) else None)
        if name and name not in folders:
            folders.append(name)

    title = note.get("title") or (calendar_event or {}).get("event_title")
    meeting = new_meeting(
        id=nid or uuid,
        uuid=uuid,
        source=SOURCE_API,
        title=title,
        at=at,
        date_text=note.get("created_at"),
        participants=participants,
        summary_markdown=(note.get("summary_markdown") or note.get("summary_text") or None),
        private_notes_markdown=(note.get("private_notes_markdown") or note.get("private_notes_text") or None),
        transcript=segments,
        calendar_event=calendar_event,
        web_url=web_url or (WEB_URL_PREFIX + uuid if uuid else None),
        owner=owner,
        folders=folders,
        duration_sec=duration,
        created_at=created_at,
        transcript_started_at=started_at,
        extra={k: note[k] for k in ("updated_at", "workspace_id") if note.get(k)},
    )
    return [meeting]


# ---------------------------------------------------------------------------
# (c) CSV export
# ---------------------------------------------------------------------------

def _norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (h or "").lower()).strip()


def _pick_column(headers: list[str], needles: tuple[str, ...], taken: set[int]) -> Optional[int]:
    """First column whose normalised header has a word starting with a needle (or containing a multi-word needle)."""
    for idx, h in enumerate(headers):
        if idx in taken:
            continue
        words = h.split()
        for n in needles:
            if " " in n:
                if n in h:
                    return idx
            elif any(w.startswith(n) for w in words):
                return idx
    return None


CSV_COLUMN_NEEDLES: dict[str, tuple[str, ...]] = {
    "id": ("id", "uuid", "document"),
    "transcript": ("transcript",),
    "summary": ("summary", "enhanced", "ai note", "ai summary", "generated"),
    "notes": ("note", "my note", "private"),
    "attendees": ("attendee", "participant", "people", "invitee", "guest", "with"),
    "owner": ("creator", "owner", "author", "host"),
    "title": ("title", "name", "subject", "meeting"),
    "date": ("date", "created", "start", "time", "when", "scheduled"),
    "duration": ("duration", "length"),
    "url": ("url", "link", "share"),
    "folder": ("folder", "space", "workspace"),
    "organiser": ("organi",),
}


def detect_csv_columns(headers: list[str]) -> dict[str, int]:
    norm = [_norm_header(h) for h in headers]
    taken: set[int] = set()
    cols: dict[str, int] = {}
    for key in ("id", "transcript", "summary", "notes", "attendees", "owner", "organiser", "title", "date", "duration", "url", "folder"):
        idx = _pick_column(norm, CSV_COLUMN_NEEDLES[key], taken)
        if key == "id" and idx is not None and norm[idx] not in ("id", "uuid", "note id", "document id", "meeting id", "granola id"):
            # avoid grabbing e.g. 'identified needs' as the id column
            if not any(norm[idx].endswith(s) for s in (" id", "uuid")):
                idx = None
        if idx is not None:
            cols[key] = idx
            taken.add(idx)
    return cols


def parse_csv(text: str, tz: Any = None) -> list[dict]:
    """Granola CSV export -> meeting dicts. See docs/granola.md for the column assumptions."""
    if not text or not text.strip():
        return []
    body = text.lstrip("﻿")
    sample = body[:4096]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        pass
    reader = csv.reader(io.StringIO(body), delimiter=delimiter)
    rows = [r for r in reader]
    if not rows:
        return []
    headers = rows[0]
    cols = detect_csv_columns(headers)
    if "title" not in cols and "summary" not in cols and "transcript" not in cols:
        return []
    out: list[dict] = []

    def cell(row: list[str], key: str) -> Optional[str]:
        idx = cols.get(key)
        if idx is None or idx >= len(row):
            return None
        v = row[idx]
        v = v.strip() if isinstance(v, str) else v
        return v or None

    for n, row in enumerate(rows[1:], start=2):
        if not any((c or "").strip() for c in row):
            continue
        title = cell(row, "title")
        date_text = cell(row, "date")
        raw_id = cell(row, "id")
        url = cell(row, "url")
        uuid = uuid_from_url(url) or normalize_uuid(raw_id)
        if not raw_id and not uuid:
            raw_id = "csv-" + sha1_text(f"{title or ''}|{date_text or ''}|{n}")[:16]
        participants = split_people_cell(cell(row, "attendees"))
        owner = None
        owner_cell = cell(row, "owner")
        if owner_cell:
            p = parse_participant_line(owner_cell)
            if p:
                p["role"] = ROLE_OWNER
                add_participant(participants, p)
                owner = {"name": p.get("name"), "email": p.get("email")}
        org_cell = cell(row, "organiser")
        if org_cell:
            p = parse_participant_line(org_cell)
            if p:
                p["role"] = ROLE_ORGANISER
                add_participant(participants, p)
        transcript_text = cell(row, "transcript")
        segments = parse_transcript_lines(transcript_text) if transcript_text else []
        folder = cell(row, "folder")
        meeting = new_meeting(
            id=uuid or raw_id,
            uuid=uuid,
            source=SOURCE_CSV,
            title=title,
            at=parse_meeting_date(date_text, tz),
            date_text=date_text,
            participants=participants,
            summary_markdown=cell(row, "summary"),
            private_notes_markdown=cell(row, "notes"),
            transcript=segments,
            web_url=url or (WEB_URL_PREFIX + uuid if uuid else None),
            owner=owner,
            folders=[f.strip() for f in re.split(r"[;,|]", folder) if f.strip()] if folder else [],
            duration_sec=parse_duration_text(cell(row, "duration")) or transcript_span_seconds(segments),
            extra={"csvRow": n},
        )
        out.append(meeting)
    return out


# ---------------------------------------------------------------------------
# (d) Markdown exports
# ---------------------------------------------------------------------------

_FM_LIST_ITEM_RE = re.compile(r"^\s*-\s*(.*)$")


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Minimal YAML front matter: 'key: value', 'key: [a, b]', block lists of '- item'. Returns (fields, body)."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return {}, text
    fields: dict = {}
    key: Optional[str] = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = _FM_LIST_ITEM_RE.match(raw)
        if item and key is not None and (raw.startswith(" ") or raw.startswith("-")) and (fields.get(key) in (None, "", []) or isinstance(fields.get(key), list)):
            if not isinstance(fields.get(key), list):
                fields[key] = []
            fields[key].append(_unquote(item.group(1)))
            continue
        m = re.match(r"^([A-Za-z_][\w -]*?)\s*:\s*(.*)$", raw)
        if not m:
            continue
        key = m.group(1).strip().lower().replace(" ", "_")
        value = m.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            fields[key] = [_unquote(x) for x in value[1:-1].split(",") if x.strip()]
        else:
            fields[key] = _unquote(value)
    body = "\n".join(lines[end + 1:])
    return fields, body


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def _split_sections(body: str) -> tuple[Optional[str], str, list[tuple[str, str]]]:
    """Return (h1 title, preamble text, [(heading, text)])."""
    title = None
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in body.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            level, heading = len(m.group(1)), m.group(2).strip()
            if level == 1 and title is None and not sections:
                title = heading
                continue
            sections.append((heading, []))
            continue
        if sections:
            sections[-1][1].append(line)
        else:
            preamble.append(line)
    return title, "\n".join(preamble).strip(), [(h, "\n".join(ls).strip()) for h, ls in sections]


def _people_from_value(value: Any) -> list[dict]:
    out: list[dict] = []
    if isinstance(value, list):
        for v in value:
            if isinstance(v, dict):
                add_participant(out, make_participant(v.get("name"), v.get("email"), v.get("company"), v.get("role")))
            else:
                add_participant(out, parse_participant_line(str(v)))
    elif isinstance(value, str):
        for p in split_people_cell(value):
            add_participant(out, p)
    return out


def _people_from_lines(text: str) -> list[dict]:
    out: list[dict] = []
    for line in (text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line)
        if line.strip():
            add_participant(out, parse_participant_line(line))
    return out


def parse_markdown(text: str, path: Any = None, tz: Any = None) -> list[dict]:
    """Markdown export (front matter + sections) -> [meeting dict]. Front matter keys used: title, date
    (or created / start / at), attendees (or participants / people), id (granola_id, uuid, document_id),
    url (web_url, granola_url, link), folder(s), owner (creator), summary, duration. Sections: Summary /
    Enhanced Notes / AI Notes / Notes / Key Points / Action Items feed the summary; My Notes / Private Notes /
    Personal Notes feed private notes; Transcript feeds the transcript; Attendees / Participants add people."""
    if text is None:
        return []
    fields, body = parse_front_matter(text.lstrip("﻿"))
    h1, preamble, sections = _split_sections(body)
    title = fields.get("title") or h1
    date_text = None
    for k in ("date", "datetime", "created", "created_at", "start", "start_time", "at", "when", "time"):
        if fields.get(k):
            date_text = str(fields[k])
            break
    participants: list[dict] = []
    for k in ("attendees", "participants", "people", "invitees", "guests"):
        if fields.get(k):
            for p in _people_from_value(fields[k]):
                add_participant(participants, p)
    owner = None
    for k in ("owner", "creator", "author", "host", "note_creator"):
        if fields.get(k):
            p = parse_participant_line(str(fields[k])) if not isinstance(fields[k], dict) else make_participant(fields[k].get("name"), fields[k].get("email"))
            if p:
                p["role"] = ROLE_OWNER
                add_participant(participants, p)
                owner = {"name": p.get("name"), "email": p.get("email")}
            break
    summary_parts: list[str] = []
    private_parts: list[str] = []
    transcript_text: Optional[str] = None

    # metadata lines in the preamble: 'Date: ...', '**Attendees:** ...'
    remaining_preamble: list[str] = []
    for line in preamble.splitlines():
        m = re.match(r"^\s*(?:[-*]\s*)?\**\s*([A-Za-z ]{2,20}?)\s*\**\s*:\s*\**\s*(.+?)\s*$", line)
        key = m.group(1).strip().lower() if m else ""
        if m and key in ("date", "when", "time", "created", "start") and not date_text:
            date_text = m.group(2).strip().strip("*")
            continue
        if m and key in ("attendees", "participants", "people", "with", "invitees"):
            for p in split_people_cell(m.group(2).strip().strip("*")):
                add_participant(participants, p)
            continue
        if m and key in ("owner", "creator", "author", "host", "note creator") and not owner:
            p = parse_participant_line(m.group(2).strip().strip("*"))
            if p:
                p["role"] = ROLE_OWNER
                add_participant(participants, p)
                owner = {"name": p.get("name"), "email": p.get("email")}
            continue
        remaining_preamble.append(line)
    pre = "\n".join(remaining_preamble).strip()

    for heading, content in sections:
        h = heading.lower()
        if "transcript" in h:
            transcript_text = (transcript_text + "\n" + content) if transcript_text else content
        elif any(k in h for k in ("my notes", "private", "personal")):
            if content:
                private_parts.append(content)
        elif any(k in h for k in ("attendee", "participant", "people", "invitee")):
            for p in _people_from_lines(content):
                add_participant(participants, p)
        elif content:
            summary_parts.append(f"## {heading}\n{content}" if not any(k in h for k in ("summary", "enhanced", "ai notes")) else content)

    if pre:
        if not sections and not transcript_text and looks_like_transcript(pre):
            transcript_text = pre
        else:
            summary_parts.insert(0, pre)
    if fields.get("summary") and not summary_parts:
        summary_parts.append(str(fields["summary"]))
    if fields.get("notes") and isinstance(fields.get("notes"), str) and not private_parts:
        private_parts.append(str(fields["notes"]))

    segments = parse_transcript_lines(transcript_text) if transcript_text else []
    url = None
    for k in ("url", "web_url", "granola_url", "link", "granola_link", "source_url"):
        if fields.get(k):
            url = str(fields[k])
            break
    raw_id = None
    for k in ("granola_id", "id", "uuid", "document_id", "note_id", "meeting_id"):
        if fields.get(k):
            raw_id = str(fields[k])
            break
    uuid = normalize_uuid(raw_id) or uuid_from_url(url) or uuid_from_path(path)
    if not raw_id and not uuid:
        raw_id = "md-" + sha1_text(str(path) if path else f"{title or ''}|{date_text or ''}")[:16]
    folders: list[str] = []
    for k in ("folder", "folders", "granola_folder"):
        v = fields.get(k)
        if isinstance(v, list):
            folders.extend(str(x) for x in v if str(x).strip())
        elif isinstance(v, str) and v.strip():
            folders.extend(f.strip() for f in re.split(r"[;,|/]", v) if f.strip())
    if owner is None:
        owner = owner_from_participants(participants)
    duration = parse_duration_text(fields.get("duration") or fields.get("duration_sec")) or transcript_span_seconds(segments)
    meeting = new_meeting(
        id=uuid or raw_id,
        uuid=uuid,
        source=SOURCE_MARKDOWN,
        title=title or (str(path).replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0] if path else None),
        at=parse_meeting_date(date_text, tz),
        date_text=date_text,
        participants=participants,
        summary_markdown="\n\n".join(p for p in summary_parts if p).strip() or None,
        private_notes_markdown="\n\n".join(private_parts).strip() or None,
        transcript=segments,
        web_url=url or (WEB_URL_PREFIX + uuid if uuid else None),
        owner=owner,
        folders=folders,
        duration_sec=duration,
        extra={"path": str(path)} if path else {},
    )
    return [meeting]


# ---------------------------------------------------------------------------
# (e) Legacy plaintext desktop cache
# ---------------------------------------------------------------------------

def _pm_inline(node: Any) -> str:
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    t = node.get("type")
    if t == "text":
        text = node.get("text") or ""
        marks = [m.get("type") for m in node.get("marks") or [] if isinstance(m, dict)]
        href = None
        for m in node.get("marks") or []:
            if isinstance(m, dict) and m.get("type") == "link":
                href = (m.get("attrs") or {}).get("href")
        if "bold" in marks or "strong" in marks:
            text = f"**{text}**"
        if "italic" in marks or "em" in marks:
            text = f"*{text}*"
        if "code" in marks:
            text = f"`{text}`"
        if href:
            text = f"[{text}]({href})"
        return text
    if t in ("hardBreak", "hard_break"):
        return "\n"
    return "".join(_pm_inline(c) for c in node.get("content") or [])


def prosemirror_to_markdown(node: Any, depth: int = 0) -> str:
    """A small ProseMirror JSON to markdown converter (headings, paragraphs, lists, quotes, code, marks)."""
    if node is None:
        return ""
    if isinstance(node, str):
        s = node.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                return prosemirror_to_markdown(json.loads(s), depth)
            except ValueError:
                pass
        if "<" in s and ">" in s and re.search(r"</?[a-z][^>]*>", s):
            s = re.sub(r"<br\s*/?>", "\n", s)
            s = re.sub(r"</(p|div|li|h[1-6])>", "\n", s)
            s = re.sub(r"<[^>]+>", "", s)
            return html.unescape(s).strip()
        return s
    if isinstance(node, list):
        return "\n\n".join(x for x in (prosemirror_to_markdown(c, depth) for c in node) if x)
    if not isinstance(node, dict):
        return ""
    t = node.get("type")
    content = node.get("content") or []
    indent = "  " * depth
    if t == "doc":
        return "\n\n".join(x for x in (prosemirror_to_markdown(c, depth) for c in content) if x).strip()
    if t == "heading":
        level = int((node.get("attrs") or {}).get("level") or 1)
        return f"{'#' * min(level, 6)} {_pm_inline(node).strip()}"
    if t == "paragraph":
        return _pm_inline(node).strip()
    if t in ("bulletList", "bullet_list", "orderedList", "ordered_list"):
        ordered = t in ("orderedList", "ordered_list")
        lines = []
        for i, item in enumerate(content, start=1):
            marker = f"{i}." if ordered else "-"
            inner = prosemirror_to_markdown(item, depth + 1).strip()
            if not inner:
                continue
            first, _, rest = inner.partition("\n")
            lines.append(f"{indent}{marker} {first}")
            if rest:
                lines.append(rest)
        return "\n".join(lines)
    if t in ("listItem", "list_item", "taskItem", "task_item"):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "paragraph":
                parts.append(_pm_inline(c).strip())
            else:
                parts.append(prosemirror_to_markdown(c, depth))
        return "\n".join(p for p in parts if p)
    if t == "blockquote":
        inner = prosemirror_to_markdown(content, depth)
        return "\n".join(f"> {ln}" for ln in inner.splitlines())
    if t in ("codeBlock", "code_block"):
        return "```\n" + _pm_inline(node) + "\n```"
    if t == "text":
        return _pm_inline(node)
    return "\n\n".join(x for x in (prosemirror_to_markdown(c, depth) for c in content) if x)


def _cache_state(obj: Any) -> dict:
    if not isinstance(obj, dict):
        return {}
    cache = obj.get("cache", obj)
    if isinstance(cache, str):
        try:
            cache = json.loads(cache)
        except ValueError:
            return {}
    if not isinstance(cache, dict):
        return {}
    state = cache.get("state", cache)
    return state if isinstance(state, dict) else {}


def cache_document_count(obj: Any) -> int:
    docs = _cache_state(obj).get("documents") or {}
    return len(docs) if isinstance(docs, (dict, list)) else 0


def parse_cache_json(obj: Any, tz: Any = None) -> list[dict]:
    """Legacy plaintext cache-v3/v6.json (already json-loaded) -> meeting dicts."""
    state = _cache_state(obj)
    docs = state.get("documents") or {}
    if isinstance(docs, list):
        docs = {d.get("id"): d for d in docs if isinstance(d, dict) and d.get("id")}
    if not isinstance(docs, dict):
        return []
    transcripts = state.get("transcripts") or {}
    panels = state.get("documentPanels") or {}
    metas = state.get("meetingsMetadata") or {}
    lists = state.get("documentLists") or {}
    lists_meta = state.get("documentListsMetadata") or {}
    folders_by_doc: dict[str, list[str]] = {}
    if isinstance(lists, dict):
        for list_id, doc_ids in lists.items():
            title = (lists_meta.get(list_id) or {}).get("title") if isinstance(lists_meta, dict) else None
            for did in doc_ids or []:
                folders_by_doc.setdefault(str(did), []).append(title or str(list_id))
    out: list[dict] = []
    for doc_id, doc in docs.items():
        if not isinstance(doc, dict) or doc.get("deleted_at"):
            continue
        uuid = normalize_uuid(doc.get("id") or doc_id) or str(doc.get("id") or doc_id)
        people = doc.get("people") or {}
        creator = people.get("creator") or people.get("organizer") or {}
        owner = None
        if isinstance(creator, dict) and (creator.get("name") or creator.get("displayName") or creator.get("email")):
            owner = {"name": creator.get("name") or creator.get("displayName"), "email": (creator.get("email") or "").lower() or None}
        participants: list[dict] = []
        for a in people.get("attendees") or []:
            if isinstance(a, dict):
                add_participant(participants, make_participant(a.get("displayName") or a.get("name"), a.get("email"), None, ROLE_ATTENDEE))
        meta = metas.get(uuid) or metas.get(doc_id) or {}
        for a in (meta.get("attendees") or []) if isinstance(meta, dict) else []:
            if isinstance(a, dict):
                add_participant(participants, make_participant(a.get("name") or a.get("displayName"), a.get("email"), None, ROLE_ATTENDEE))
        gcal = doc.get("google_calendar_event") or {}
        calendar_event = None
        if isinstance(gcal, dict) and gcal:
            invitees = []
            for a in gcal.get("attendees") or []:
                if isinstance(a, dict) and a.get("email"):
                    invitees.append({"email": str(a["email"]).lower()})
                    role = ROLE_ORGANISER if a.get("organizer") else ROLE_ATTENDEE
                    add_participant(participants, make_participant(a.get("displayName") or a.get("name"), a.get("email"), None, role))
            organiser = (gcal.get("organizer") or {}).get("email") if isinstance(gcal.get("organizer"), dict) else gcal.get("organizer")
            if organiser:
                add_participant(participants, make_participant(None, organiser, None, ROLE_ORGANISER))
            calendar_event = {
                "event_title": gcal.get("summary"),
                "scheduled_start_time": (gcal.get("start") or {}).get("dateTime") if isinstance(gcal.get("start"), dict) else gcal.get("start"),
                "scheduled_end_time": (gcal.get("end") or {}).get("dateTime") if isinstance(gcal.get("end"), dict) else gcal.get("end"),
                "invitees": invitees,
                "organiser": str(organiser).lower() if organiser else None,
                "calendar_event_id": gcal.get("id"),
            }
        if owner:
            add_participant(participants, make_participant(owner.get("name"), owner.get("email"), None, ROLE_CREATOR))
        # transcript
        entries = transcripts.get(uuid) or transcripts.get(doc_id) or []
        entries = [e for e in entries if isinstance(e, dict)]
        entries.sort(key=lambda e: (e.get("sequence_number") if isinstance(e.get("sequence_number"), (int, float)) else 0, str(e.get("start_timestamp") or "")))
        items = []
        for e in entries:
            speaker = e.get("speaker")
            if not speaker:
                speaker = {"source": "microphone" if e.get("source") == "microphone" else "speaker"}
            items.append({"speaker": speaker if isinstance(speaker, dict) else {"name": speaker},
                          "text": e.get("text"), "start_time": e.get("start_timestamp"), "end_time": e.get("end_timestamp")})
        segments, started_at = transcript_items_to_segments(items, owner.get("name") if owner else None)
        # summary from panels
        summary_parts: list[str] = []
        doc_panels = panels.get(uuid) or panels.get(doc_id) or {}
        panel_iter = doc_panels.values() if isinstance(doc_panels, dict) else (doc_panels if isinstance(doc_panels, list) else [])
        for panel in panel_iter:
            if not isinstance(panel, dict):
                continue
            md = prosemirror_to_markdown(panel.get("content"))
            if md:
                summary_parts.append(md)
        summary = "\n\n".join(summary_parts).strip() or None
        private = doc.get("notes_markdown") or doc.get("notes_plain") or None
        if not private and doc.get("notes"):
            private = prosemirror_to_markdown(doc.get("notes")) or None
        created_at = parse_meeting_date(doc.get("created_at"), tz)
        at = None
        if calendar_event and calendar_event.get("scheduled_start_time"):
            at = parse_meeting_date(calendar_event["scheduled_start_time"], tz)
        at = at or started_at or created_at
        duration = transcript_span_seconds(segments)
        if duration is None and calendar_event:
            duration = _seconds_between(calendar_event.get("scheduled_start_time"), calendar_event.get("scheduled_end_time"))
        extra = {k: doc.get(k) for k in ("hubspot_note_url", "attio_shared_at", "affinity_note_id", "workspace_id", "creation_source", "privacy_mode_enabled") if doc.get(k) not in (None, "", False)}
        out.append(new_meeting(
            id=uuid,
            uuid=normalize_uuid(uuid),
            source=SOURCE_CACHE,
            title=doc.get("title") or (calendar_event or {}).get("event_title"),
            at=at,
            date_text=doc.get("created_at"),
            participants=participants,
            summary_markdown=summary,
            private_notes_markdown=private,
            transcript=segments,
            calendar_event=calendar_event,
            web_url=(WEB_URL_PREFIX + normalize_uuid(uuid)) if normalize_uuid(uuid) else None,
            owner=owner,
            folders=folders_by_doc.get(uuid, []) + [f for f in folders_by_doc.get(str(doc_id), []) if f not in folders_by_doc.get(uuid, [])],
            duration_sec=duration,
            created_at=created_at,
            transcript_started_at=started_at,
            extra=extra,
        ))
    return out


# ---------------------------------------------------------------------------
# Dedupe and merge
# ---------------------------------------------------------------------------

def _empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def merge_two(a: dict, b: dict) -> dict:
    """Merge two dicts describing the same meeting: fill gaps, keep the longer summary and transcript, union people."""
    if _empty(a.get("title")) and not _empty(b.get("title")):
        a, b = b, a
    r = dict(a)
    for k in ("id", "uuid", "title", "at", "date_text", "calendar_event", "web_url", "owner", "duration_sec",
              "created_at", "transcript_started_at", "source"):
        if _empty(r.get(k)) and not _empty(b.get(k)):
            r[k] = b[k]
    if b.get("uuid") and (not r.get("uuid")):
        r["uuid"] = b["uuid"]
    if r.get("uuid") and (not r.get("id") or (str(r.get("id")).startswith("not_") and b.get("id") == r["uuid"])):
        r["id"] = r["uuid"]
    for k in ("summary_markdown", "private_notes_markdown"):
        if b.get(k) and (not r.get(k) or len(b[k]) > len(r[k])):
            r[k] = b[k]
    if len(b.get("transcript") or []) > len(r.get("transcript") or []):
        r["transcript"] = b["transcript"]
        if b.get("transcript_started_at"):
            r["transcript_started_at"] = b["transcript_started_at"]
    if b.get("calendar_event") and r.get("calendar_event") is b.get("calendar_event"):
        pass
    if b.get("calendar_event") and b.get("at") and b.get("calendar_event", {}).get("scheduled_start_time"):
        r["at"] = b["at"]  # a calendar-backed time beats a parsed locale string
        if b.get("duration_sec"):
            r["duration_sec"] = b["duration_sec"]
    participants = [dict(p) for p in r.get("participants") or []]
    for p in b.get("participants") or []:
        add_participant(participants, p)
    r["participants"] = participants
    folders = list(r.get("folders") or [])
    for f in b.get("folders") or []:
        if f not in folders:
            folders.append(f)
    r["folders"] = folders
    sources = []
    for s in [a.get("source"), b.get("source")] + list(a.get("sources") or []) + list(b.get("sources") or []):
        if s and s not in sources:
            sources.append(s)
    r["sources"] = sources
    extra = dict(b.get("extra") or {})
    extra.update(r.get("extra") or {})
    r["extra"] = extra
    if not r.get("owner"):
        r["owner"] = owner_from_participants(participants)
    return r


def merge_meetings(meetings: list[dict]) -> list[dict]:
    """Dedupe on uuid (falling back to id); later records fill gaps in earlier ones."""
    out: dict[str, dict] = {}
    order: list[str] = []
    anon = 0
    for m in meetings:
        if not isinstance(m, dict):
            continue
        key = m.get("uuid") or (str(m.get("id")) if m.get("id") else None)
        if not key:
            anon += 1
            key = f"anon-{anon}"
        if key in out:
            out[key] = merge_two(out[key], m)
        else:
            out[key] = dict(m)
            order.append(key)
    return [out[k] for k in order]


# ---------------------------------------------------------------------------
# Canonical Interaction
# ---------------------------------------------------------------------------

def _internal_domains_from(cfg: Any, reps: Optional[list[dict]]) -> set[str]:
    try:
        return set(cfg.internal_domains(reps))
    except AttributeError:
        pass
    domains: set[str] = set()
    if isinstance(cfg, dict):
        for d in (cfg.get("org", {}) or {}).get("internalDomains") or []:
            if d:
                domains.add(str(d).lower())
    for rep in reps or []:
        dom = email_domain(rep.get("email"))
        if dom:
            domains.add(dom)
    return domains


def _rep_id_for(email: Optional[str], reps: Optional[list[dict]]) -> Optional[str]:
    if not email:
        return None
    for rep in reps or []:
        if (rep.get("email") or "").lower() == email.lower() and rep.get("id"):
            return rep["id"]
    return f"rep:{email.lower()}"


def to_interaction(meeting: dict, cfg: Any, internal_domains: Optional[set[str]] = None, reps: Optional[list[dict]] = None) -> dict:
    """Map a granola meeting dict to a canonical Interaction (docs/CONTRACTS.md section 5)."""
    internal = {d.lower() for d in internal_domains} if internal_domains is not None else _internal_domains_from(cfg, reps)
    owner = meeting.get("owner") or {}
    owner_email = (owner.get("email") or "").lower() or None
    owner_name = owner.get("name") or None
    if owner_email and email_domain(owner_email):
        internal = set(internal)  # copy before adding the note-taker's own domain
        internal.add(email_domain(owner_email))

    participants: list[dict] = []
    companies: dict[str, str] = {}
    seen: set[str] = set()
    for p in meeting.get("participants") or []:
        email = (p.get("email") or "").strip().lower() or None
        name = (p.get("name") or "").strip() or (email.split("@", 1)[0] if email else "Unknown")
        key = email or name.lower()
        if key in seen:
            continue
        seen.add(key)
        role_text = (p.get("role") or "").lower()
        is_rep = False
        if email:
            is_rep = email == owner_email or (email_domain(email) in internal)
        else:
            is_rep = role_text in (ROLE_CREATOR, ROLE_OWNER) or (owner_name is not None and name.lower() == owner_name.lower())
        participants.append({"name": name, "email": email, "role": "rep" if is_rep else "buyer"})
        if p.get("company"):
            companies[email or name] = p["company"]

    cal = meeting.get("calendar_event") or {}
    at_dt = (parse_iso(cal.get("scheduled_start_time")) if cal else None) or parse_iso(meeting.get("at")) \
        or parse_iso(meeting.get("transcript_started_at")) or parse_iso(meeting.get("created_at"))
    at = to_iso(at_dt) if at_dt else None

    duration = meeting.get("duration_sec")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        duration = _seconds_between(cal.get("scheduled_start_time"), cal.get("scheduled_end_time")) if cal else None
    if duration is None:
        duration = transcript_span_seconds(meeting.get("transcript") or [])
    duration = int(duration) if duration else None

    segments: list[dict] = []
    has_times = False
    for seg in meeting.get("transcript") or []:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        speaker = (seg.get("speaker") or "Unknown").strip()
        if speaker.lower() == "me" and owner_name:
            speaker = owner_name
        t = seg.get("t")
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            has_times = True
            t = float(t)
        else:
            t = 0.0
        segments.append({"speaker": speaker, "t": t, "text": text})

    summary = meeting.get("summary_markdown") or None
    private = meeting.get("private_notes_markdown") or None
    if segments:
        body = transcript_to_body(segments)
    else:
        parts = []
        if summary:
            parts.append("Notes:\n" + summary.strip())
        if private:
            parts.append("Private notes:\n" + private.strip())
        body = "\n\n".join(parts)

    uuid = meeting.get("uuid") or normalize_uuid(meeting.get("id"))
    ident = uuid or (str(meeting.get("id")) if meeting.get("id") else None) or ("md-" + sha1_text(json.dumps(meeting, sort_keys=True, default=str))[:16])
    rep_email = owner_email or next((p["email"] for p in participants if p["role"] == "rep" and p.get("email")), None)
    title = meeting.get("title") or (cal.get("event_title") if cal else None) or "Untitled Granola meeting"

    meta: dict = {
        "granola_source": meeting.get("source"),
        "granola_id": meeting.get("id"),
        "uuid": uuid,
        "web_url": meeting.get("web_url") or (WEB_URL_PREFIX + uuid if uuid else None),
        "calendar_event_id": cal.get("calendar_event_id") if cal else None,
        "organiser": cal.get("organiser") if cal else None,
        "scheduled_start_time": cal.get("scheduled_start_time") if cal else None,
        "scheduled_end_time": cal.get("scheduled_end_time") if cal else None,
        "folders": list(meeting.get("folders") or []),
        "date_text": meeting.get("date_text"),
        "hasTranscript": bool(segments),
        "transcriptTimestamps": has_times,
        "participantCompanies": companies,
        "externalParticipants": sum(1 for p in participants if p["role"] == "buyer"),
    }
    if meeting.get("sources"):
        meta["granola_sources"] = list(meeting["sources"])
    for k, v in (meeting.get("extra") or {}).items():
        meta.setdefault(k, v)

    return {
        "id": f"granola:{ident}",
        "source": "granola",
        "type": "meeting",
        "dealId": None,
        "direction": "unknown",
        "at": at,
        "durationSec": duration,
        "title": title,
        "body": body,
        "transcript": segments,
        "notes": private,
        "summary": summary,
        "participants": participants,
        "repId": _rep_id_for(rep_email, reps),
        "recordingUrl": None,
        "meta": meta,
    }


def is_internal_only(interaction: dict) -> bool:
    """True when two or more people are known and every one of them is internal (role rep).
    Meetings with a single known participant (the note-taker) or none are kept: they may be ad-hoc sales calls."""
    people = interaction.get("participants") or []
    return len(people) >= 2 and all(p.get("role") == "rep" for p in people)
