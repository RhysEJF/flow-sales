"""`fs.py import transcripts --folder <dir>`: local transcript files into canonical Interactions.

Accepted files: .md, .txt, .vtt, .json (recursively). See docs/other-crms.md for the formats.
Every file becomes one Interaction with id `tx:<sha1 of the path relative to the folder>`,
source "transcripts", type "transcript". It goes to _unlinked unless the file names a deal
(front matter `deal_id:` or JSON `dealId`). A normalised copy lands in cache/transcripts/.
Standard library only.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

from ..schema.validate import validate_records
from ..store import Store
from ..util import email_domain, parse_iso, safe_id, sha1_text, to_iso, transcript_to_body

EXTENSIONS = (".md", ".txt", ".vtt", ".json")
FRONT_MATTER_RE = re.compile(r"\A﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.S)
# "[00:12] Name: text", "00:01:02 Name: text" or plain "Name: text". Speaker: up to five words, no URL-like text.
SPEAKER_LINE_RE = re.compile(r"^\s*(?:\[?(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)\]?\s+)?([A-Za-z][A-Za-z0-9.'\-]*(?:[ ][A-Za-z][A-Za-z0-9.'\-]*){0,4})\s*:\s+(\S.*?)\s*$")
PERSON_RE = re.compile(r"([A-Za-z][A-Za-z0-9 .'\-]{0,60}?)?\s*<\s*([^<>\s]+@[^<>\s]+)\s*>")
BARE_EMAIL_RE = re.compile(r"^[^@\s<>]+@[^@\s<>]+$")
FILENAME_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[-_T ](\d{2})[:.]?(\d{2}))?")
VTT_TIME_RE = re.compile(r"^\s*(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
VTT_VOICE_RE = re.compile(r"<v\s+([^>]+)>(.*?)(?:</v>|$)", re.S)
NOISE_PREFIXES = ("http://", "https://", "note", "notes", "summary", "title", "date", "attendees", "participants", "deal_id", "duration")


# ---------------------------------------------------------------------------
# parsing helpers (also used by the CSV adapter)
# ---------------------------------------------------------------------------

def timestamp_to_seconds(text: Optional[str]) -> Optional[float]:
    """'1:02', '00:01:02', '00:01:02.500' -> seconds."""
    if not text:
        return None
    parts = text.replace(",", ".").split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    total = 0.0
    for n in nums:
        total = total * 60 + n
    return round(total, 3)


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Return (fields, body) for a leading YAML-style block. Values are strings or lists of strings."""
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    fields: dict[str, Any] = {}
    current: Optional[str] = None
    for raw in m.group(1).splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if current and re.match(r"^\s+-\s+", line):
            fields.setdefault(current, []).append(line.split("-", 1)[1].strip().strip("'\""))
            continue
        if re.match(r"^-\s+", line) and current is not None:
            fields.setdefault(current, []).append(line.split("-", 1)[1].strip().strip("'\""))
            continue
        km = re.match(r"^([A-Za-z_][\w\- ]*):\s*(.*)$", line)
        if not km:
            continue
        key = km.group(1).strip().lower().replace("-", "_").replace(" ", "_")
        value = km.group(2).strip()
        if not value:
            fields[key] = []
            current = key
            continue
        current = None
        if value.startswith("[") and value.endswith("]"):
            fields[key] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        else:
            fields[key] = value.strip("'\"")
    return fields, text[m.end():]


def parse_speaker_lines(text: str) -> list[dict]:
    """'Speaker: text' lines (optionally prefixed with a timestamp) into transcript segments.

    Lines that do not start a new segment continue the previous one. Returns [] when the text has
    no speaker lines at all, so callers can fall back to plain prose.
    """
    segments: list[dict] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        m = SPEAKER_LINE_RE.match(line)
        if m and not m.group(2).strip().lower().startswith(NOISE_PREFIXES):
            speaker = m.group(2).strip()
            seg = {"speaker": speaker, "t": timestamp_to_seconds(m.group(1)), "text": m.group(3).strip()}
            segments.append(seg)
        elif segments and line.strip():
            segments[-1]["text"] = (segments[-1]["text"] + " " + line.strip()).strip()
    return segments


def parse_vtt(text: str) -> list[dict]:
    segments: list[dict] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = VTT_TIME_RE.match(lines[i])
        if not m:
            i += 1
            continue
        hours = m.group(1)
        start = (int(hours[:-1]) * 3600 if hours else 0) + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4).ljust(3, "0")) / 1000.0
        i += 1
        cue: list[str] = []
        while i < len(lines) and lines[i].strip():
            cue.append(lines[i].strip())
            i += 1
        body = " ".join(cue).strip()
        if not body:
            continue
        vm = VTT_VOICE_RE.search(body)
        if vm:
            speaker, spoken = vm.group(1).strip(), re.sub(r"</?v[^>]*>", "", body).strip()
            spoken = spoken[len(speaker):].strip() if spoken.startswith(speaker) else spoken
        else:
            sm = SPEAKER_LINE_RE.match(body)
            speaker, spoken = (sm.group(2).strip(), sm.group(3).strip()) if sm else ("Unknown", body)
        spoken = re.sub(r"<[^>]+>", "", spoken).strip()
        if segments and segments[-1]["speaker"] == speaker and abs(start - (segments[-1].get("_end") or start)) < 0.01:
            segments[-1]["text"] += " " + spoken
        else:
            segments.append({"speaker": speaker, "t": round(start, 3), "text": spoken})
    return segments


def parse_json_transcript(obj: Any) -> tuple[dict, list[dict]]:
    """Return (meta, segments) from a JSON export: a list of segments, or an object holding them."""
    meta: dict[str, Any] = {}
    raw_segments: Any = None
    if isinstance(obj, list):
        raw_segments = obj
    elif isinstance(obj, dict):
        for key in ("segments", "transcript", "utterances", "entries"):
            if isinstance(obj.get(key), list):
                raw_segments = obj[key]
                break
        for key in ("title", "date", "at", "participants", "attendees", "deal_id", "dealId", "summary", "duration", "durationSec"):
            if key in obj:
                meta[key] = obj[key]
    segments: list[dict] = []
    for item in raw_segments or []:
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("content") or ""
        if not str(text).strip():
            continue
        t = item.get("t", item.get("start", item.get("time")))
        if isinstance(t, str):
            t = timestamp_to_seconds(t)
        segments.append({"speaker": str(item.get("speaker") or item.get("name") or "Unknown").strip(), "t": t, "text": str(text).strip()})
    return meta, segments


def parse_person(text: Any) -> Optional[dict]:
    """'Name <email>', 'email', 'Name' or {name, email} -> {name, email}."""
    if isinstance(text, dict):
        name, email = (text.get("name") or "").strip(), (text.get("email") or "").strip().lower() or None
        return {"name": name or (email.split("@")[0] if email else ""), "email": email} if (name or email) else None
    s = str(text or "").strip().strip("-").strip()
    if not s:
        return None
    m = PERSON_RE.search(s)
    if m:
        email = m.group(2).strip().lower()
        name = (m.group(1) or "").strip().strip("'\"") or email.split("@")[0]
        return {"name": name, "email": email}
    if BARE_EMAIL_RE.match(s):
        return {"name": s.split("@")[0], "email": s.lower()}
    return {"name": s.strip("'\""), "email": None}


def people_from_text(text: str) -> list[dict]:
    """Every 'Name <email>' occurrence in free text (attendee lines above a transcript)."""
    out = []
    for m in PERSON_RE.finditer(text):
        email = m.group(2).strip().lower()
        name = (m.group(1) or "").strip(" ,;:-'\"") or email.split("@")[0]
        name = re.sub(r"^(attendees|participants|with)\s*:?\s*", "", name, flags=re.I).strip() or email.split("@")[0]
        out.append({"name": name, "email": email})
    return out


def date_from_filename(name: str) -> Optional[_dt.datetime]:
    m = FILENAME_DATE_RE.search(name)
    if not m:
        return None
    try:
        return _dt.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0), int(m.group(5) or 0), tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def title_from_filename(name: str) -> str:
    stem = Path(name).stem
    stem = FILENAME_DATE_RE.sub("", stem).strip(" -_")
    return re.sub(r"[-_]+", " ", stem).strip() or Path(name).stem


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [v.strip() for v in re.split(r"[;,]", str(value)) if v.strip()] if "<" not in str(value) or ";" in str(value) or "," in str(value) else [value]


def _duration(value: Any, segments: list[dict]) -> Optional[int]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, str) and value.strip():
        if ":" in value:
            secs = timestamp_to_seconds(value.strip())
            return int(secs) if secs is not None else None
        digits = re.sub(r"[^\d.]", "", value)
        if digits:
            return int(float(digits) * (60 if "min" in value.lower() else 1))
    last = [s["t"] for s in segments if isinstance(s.get("t"), (int, float))]
    return int(max(last) + 30) if last else None


# ---------------------------------------------------------------------------
# one file -> one interaction
# ---------------------------------------------------------------------------

def import_file(path: Path, root: Path, internal_domains: set[str]) -> dict:
    rel = path.relative_to(root).as_posix()
    ext = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")
    fields: dict[str, Any] = {}
    segments: list[dict] = []
    prose = ""
    if ext == ".json":
        try:
            obj = json.loads(text)
        except ValueError as exc:
            raise ValueError(f"{rel}: not valid JSON ({exc})") from exc
        fields, segments = parse_json_transcript(obj)
    elif ext == ".vtt":
        segments = parse_vtt(text)
    else:
        fields, rest = parse_front_matter(text)
        segments = parse_speaker_lines(rest)
        prose = rest.strip()
        # attendee lines above the first speaker line
        head = rest.split("\n", 1)[0] if not segments else rest[: rest.find(segments[0]["text"])] if segments[0]["text"] in rest else rest[:400]
        for person in people_from_text(head):
            fields.setdefault("_people", []).append(person)

    # timestamp
    when = None
    for key in ("date", "at"):
        if fields.get(key):
            raw = str(fields[key]).strip()
            when = parse_iso(raw.replace(" ", "T", 1) if re.match(r"^\d{4}-\d{2}-\d{2} \d", raw) else raw)
            if when:
                break
    when = when or date_from_filename(path.name) or _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc)
    source_of_time = "front-matter" if fields.get("date") or fields.get("at") else ("filename" if date_from_filename(path.name) else "mtime")

    # participants
    people: list[dict] = []
    for raw in _as_list(fields.get("participants") or fields.get("attendees")):
        person = parse_person(raw)
        if person:
            people.append(person)
    people += fields.get("_people", [])
    seen: set[str] = set()
    participants: list[dict] = []
    for person in people:
        key = (person.get("email") or person.get("name") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        domain = email_domain(person.get("email"))
        role = "rep" if domain and domain in internal_domains else ("buyer" if person.get("email") else "unknown")
        participants.append({"name": person.get("name") or "", "email": person.get("email"), "role": role})
    rep = next((p for p in participants if p["role"] == "rep" and p.get("email")), None)

    deal_id = fields.get("deal_id") or fields.get("dealId") or None
    deal_id = str(deal_id).strip() if deal_id else None
    body = transcript_to_body(segments) if segments else prose
    record = {
        "id": f"tx:{sha1_text(rel)}",
        "source": "transcripts",
        "type": "transcript",
        "dealId": deal_id,
        "direction": "unknown",
        "at": to_iso(when),
        "durationSec": _duration(fields.get("duration") or fields.get("durationSec"), segments),
        "title": str(fields.get("title") or "").strip() or title_from_filename(path.name),
        "body": body,
        "transcript": segments,
        "notes": None,
        "summary": (str(fields["summary"]).strip() or None) if fields.get("summary") else None,
        "participants": participants,
        "repId": f"rep:{rep['email']}" if rep else None,
        "recordingUrl": None,
        "meta": {"transcripts": {"path": rel, "format": ext.lstrip("."), "timeFrom": source_of_time,
                                 "modifiedAt": to_iso(_dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc))}},
    }
    return record


def scan_folder(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.name.startswith("."))


# ---------------------------------------------------------------------------
# command
# ---------------------------------------------------------------------------

def _emit(ctx: dict, payload: dict, text: str, err: bool = False) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text, file=sys.stderr if err else sys.stdout)


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    folder_arg = getattr(args, "folder", None) or store.config.get("sources.transcripts.folder")
    if not folder_arg:
        _emit(ctx, {"ok": False, "error": "no folder"}, "import transcripts needs --folder <dir> (or sources.transcripts.folder in config)", err=True)
        return 1
    folder = Path(folder_arg).expanduser().resolve()
    if not folder.is_dir():
        _emit(ctx, {"ok": False, "error": f"folder not found: {folder}"}, f"folder not found: {folder}", err=True)
        return 1
    files = scan_folder(folder)
    if not files:
        _emit(ctx, {"ok": False, "error": "no transcript files"}, f"no .md, .txt, .vtt or .json files under {folder}", err=True)
        return 1
    internal = store.config.internal_domains(store.load_reps())
    known_deals = {d["id"] for d in store.load_deals()}
    records: list[dict] = []
    problems: list[str] = []
    for path in files:
        try:
            records.append(import_file(path, folder, internal))
        except (ValueError, OSError) as exc:
            problems.append(str(exc))
    errors = validate_records("interaction", records)
    if errors or problems:
        for line in (problems + errors)[:30]:
            print(f"  {line}", file=sys.stderr)
        _emit(ctx, {"ok": False, "errors": problems + errors}, f"{len(problems) + len(errors)} problem(s); nothing written", err=True)
        return 1

    warnings: list[str] = []
    linked: dict[str, list[dict]] = {}
    unlinked: list[dict] = []
    for rec in records:
        deal_id = rec.get("dealId")
        if deal_id and deal_id not in known_deals:
            warnings.append(f"{rec['meta']['transcripts']['path']}: deal_id {deal_id} is not in the store; left unlinked")
            rec["meta"]["transcripts"]["declaredDealId"] = deal_id
            rec["dealId"] = None
            deal_id = None
        if deal_id:
            linked.setdefault(deal_id, []).append(rec)
        else:
            unlinked.append(rec)

    store.ensure()
    wrote: list[str] = []
    cache_dir = store.cache_dir / "transcripts"
    for rec in records:
        store.write_json(cache_dir / f"{safe_id(rec['id'])}.json", rec)
    wrote.append(str(cache_dir))
    new_ids = {r["id"] for r in records}
    links = store.load_links()
    links["links"] = [l for l in links.get("links", []) if l.get("interactionId") not in new_ids]
    for deal_id, items in linked.items():
        store.save_interactions(deal_id, Store.upsert(store.load_interactions(deal_id), items))
        wrote.append(str(store.interactions_path(deal_id)))
        for rec in items:
            links["links"].append({"interactionId": rec["id"], "dealId": deal_id, "method": "crm-association", "confidence": 1.0, "status": "auto",
                                   "evidence": {"matchedEmails": [], "domain": None, "matchedHubspotMeeting": None, "titleHit": None, "declaredIn": "front matter"},
                                   "candidates": [{"dealId": deal_id, "confidence": 1.0}], "at": ctx.get("now"), "by": "linker"})
    if unlinked or new_ids:
        keep = [u for u in store.load_unlinked() if u.get("id") not in new_ids]
        store.save_unlinked(keep + unlinked)
        wrote.append(str(store.interactions_dir / "_unlinked.json"))
    store.save_links(links)
    wrote.append(str(store.data_dir / "links.json"))
    cfg = store.config
    cfg.set("sources.transcripts.folder", str(folder))
    store.save_config()

    with_segments = sum(1 for r in records if r["transcript"])
    by_time = {}
    for r in records:
        k = r["meta"]["transcripts"]["timeFrom"]
        by_time[k] = by_time.get(k, 0) + 1
    summary = {"ok": True, "folder": str(folder), "files": len(files), "imported": len(records), "withSegments": with_segments,
               "linked": sum(len(v) for v in linked.values()), "unlinked": len(unlinked), "timestampSource": by_time, "warnings": warnings}
    ctx["summary"] = {"read": [str(folder)], "wrote": wrote, "notes": f"{len(records)} transcripts ({with_segments} with speaker segments), {len(unlinked)} unlinked"}
    text = [f"Imported {len(records)} transcript file(s) from {folder}",
            f"  with speaker segments: {with_segments}   linked by deal_id: {summary['linked']}   unlinked: {len(unlinked)}",
            "  timestamps from: " + ", ".join(f"{k} {v}" for k, v in sorted(by_time.items()))]
    text += [f"  warning: {w}" for w in warnings]
    if unlinked:
        text.append("  next: fs.py link to attach the unlinked transcripts to deals")
    _emit(ctx, summary, "\n".join(text))
    return 0
