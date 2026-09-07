"""`fs.py import granola`: Granola meetings in, unlinked canonical Interactions out. Standard library only.

Three ways in:
- export folder (default; --export-dir, config sources.granola.exportDir, else <home>/cache/granola): files the
  setup skill saved verbatim from the Granola MCP tools (.txt / .xml), public API note JSON, meeting dicts in
  the export shape, CSV and markdown exports. The parser is chosen by extension plus content sniffing.
  Transcript-only files (<uuid>-transcript.txt) merge into their meeting by UUID; duplicates collapse on UUID.
- legacy cache (--cache <path>, or config mode "local-cache" with cachePath): the plaintext desktop cache
  from before May 2026. An encrypted (.enc), missing or document-less cache stops with ENCRYPTED_CACHE_MESSAGE.
- public API (config sources.granola.mode == "api"): GET /v1/notes over the config window, one GET per note
  with the transcript, paged transcript fallback on HTTP 413, every note cached as JSON under
  <home>/cache/granola/, and an updated_after watermark so re-runs only fetch what changed.

One way out (`finish`): to_interaction per meeting, skip meetings with no external participant, validate,
upsert into data/interactions/_unlinked.json (ids already inside a deal's interaction file are left alone),
print a summary, log the run. The API key is never printed or logged.
"""
from __future__ import annotations

import email.utils
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Optional

from ..config import Config
from ..schema.validate import validate_records
from ..store import Store
from ..util import now_iso
from . import granola_parse as gp

ENCRYPTED_CACHE_MESSAGE = "Granola 7.427+ keeps its cache encrypted; use the Granola MCP export or the public API"
DEFAULT_API_BASE_URL = "https://public-api.granola.ai/v1"
API_KEY_ENV = "GRANOLA_API_KEY"
PLUGIN_OPTION_ENV = "CLAUDE_PLUGIN_OPTION_GRANOLA_API_KEY"
SECRETS_KEY = "granola_api_key"
WATERMARK_FILE = "_watermark.json"
DEFAULT_MAC_CACHE = "~/Library/Application Support/Granola/cache-v3.json"
LIST_PAGE_SIZE = 30
TRANSCRIPT_PAGE_SIZE = 100
API_RATE_PER_SEC = 4.5            # the API allows 5 sustained and 25 burst per 5 seconds; stay under both
EXPORT_SUFFIXES = (".json", ".txt", ".xml", ".md", ".csv")
USER_AGENT = "flowsales-granola/1.0"
PARSE_PROBE_BYTES = 16 * 1024 * 1024   # doctor parses caches up to this size to count documents

# Test hooks: tests replace these so no network call or real sleep happens.
URLOPEN = urllib.request.urlopen
SLEEP = time.sleep

_MCP_MARK_RE = re.compile(r"<(?:meetings_data|meeting|transcript)\b", re.IGNORECASE)
_EXPORT_KEYS = frozenset(gp.new_meeting().keys())

KEY_HELP = """No Granola API key found. The public API needs a Business or Enterprise plan. Create a key in the
Granola desktop app (Settings > Connectors > API keys) and put it in one of these places (checked in order):
  1. the environment variable {env} (or the name in config sources.granola.keyEnv)
  2. the plugin user config, exposed as the environment variable {plugin_env}
  3. {secrets} with {{"{secrets_key}": "grn_..."}} and permissions 600
On the Basic plan use the MCP export instead (config set sources.granola.mode mcp). See docs/granola.md."""


# ---------------------------------------------------------------------------
# errors
# ---------------------------------------------------------------------------

class EncryptedCacheError(Exception):
    """The local cache cannot be used: encrypted, missing or without documents."""

    def __init__(self, detail: str, state: str):
        super().__init__(detail)
        self.state = state


class GranolaApiError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, code: Optional[str] = None, path: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.path = path


# ---------------------------------------------------------------------------
# key resolution (never print the key)
# ---------------------------------------------------------------------------

def resolve_granola_key(cfg: Optional[Config], home: Path) -> tuple[Optional[str], Optional[str]]:
    """Return (key, where). `where` names the source and is safe to print; the key itself never is."""
    names: list[str] = []
    env_name = cfg.get("sources.granola.keyEnv") if cfg is not None else None
    for name in (env_name, API_KEY_ENV, PLUGIN_OPTION_ENV):
        if name and name not in names:
            names.append(str(name))
    for name in names:
        val = os.environ.get(name)
        if val and val.strip():
            return val.strip(), f"environment variable {name}"
    secrets = Path(home) / "secrets.json"
    if secrets.exists():
        try:
            with secrets.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return None, None
        val = data.get(SECRETS_KEY) if isinstance(data, dict) else None
        if val:
            return str(val).strip(), f"{secrets} key {SECRETS_KEY}"
    return None, None


# ---------------------------------------------------------------------------
# public API client
# ---------------------------------------------------------------------------

class GranolaClient:
    """Small urllib client for https://public-api.granola.ai/v1: bearer auth, throttle, retry, paging.

    Throttling spaces requests at 1/rate seconds (4.5 per second by default, under the documented 5 sustained
    and 25 per 5 seconds burst). 429 and 5xx responses are retried honouring Retry-After; network errors are
    retried with exponential backoff. `urlopen`, `sleep` and `clock` are injectable for tests.
    """

    def __init__(self, key: str, base_url: str = DEFAULT_API_BASE_URL, rate_per_sec: float = API_RATE_PER_SEC,
                 max_retries: int = 5, timeout: float = 60.0, sleep: Optional[Callable[[float], None]] = None,
                 clock: Optional[Callable[[], float]] = None, urlopen: Optional[Callable[..., Any]] = None):
        if not key:
            raise ValueError("GranolaClient needs an API key")
        self._key = key
        self.base_url = (base_url or DEFAULT_API_BASE_URL).rstrip("/")
        self.rate = float(rate_per_sec)
        self.max_retries = max(0, int(max_retries))
        self.timeout = timeout
        self._sleep = sleep
        self._clock = clock or time.monotonic
        self._urlopen = urlopen
        self._next_allowed = self._clock()
        self.request_count = 0
        self.retry_count = 0
        self.calls: list[dict] = []   # {"path", "params"}; never the headers

    def __repr__(self) -> str:  # keep the key out of tracebacks and logs
        return f"GranolaClient({self.base_url})"

    # ---------- transport (override or inject in tests) ----------
    def _http(self, url: str, headers: dict) -> tuple[int, dict, bytes]:
        opener = self._urlopen or URLOPEN
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with opener(req, timeout=self.timeout) as resp:  # noqa: S310 - https to the configured host
                hdrs = {str(k).lower(): str(v) for k, v in resp.headers.items()}
                return int(resp.status), hdrs, resp.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            hdrs = {str(k).lower(): str(v) for k, v in (exc.headers.items() if exc.headers is not None else [])}
            try:
                exc.close()
            except Exception:  # noqa: BLE001 - closing the error body is best effort
                pass
            return int(exc.code), hdrs, raw or b""

    # ---------- throttle and retry ----------
    def _throttle(self) -> float:
        if self.rate <= 0:
            return 0.0
        now = self._clock()
        wait = self._next_allowed - now
        if wait > 0:
            self._do_sleep(wait)
            now = now + wait
        self._next_allowed = now + 1.0 / self.rate
        return max(0.0, wait)

    def _do_sleep(self, seconds: float) -> None:
        (self._sleep or SLEEP)(max(0.0, float(seconds)))

    @staticmethod
    def _retry_after_seconds(hdrs: dict) -> Optional[float]:
        raw = hdrs.get("retry-after")
        if not raw:
            return None
        s = str(raw).strip()
        try:
            return max(0.0, float(s))
        except ValueError:
            pass
        try:
            when = email.utils.parsedate_to_datetime(s)
        except (TypeError, ValueError, IndexError):
            return None
        if when is None:
            return None
        return max(0.0, when.timestamp() - time.time())

    def _backoff(self, attempt: int, retry_after: Optional[float] = None) -> None:
        delay = retry_after if retry_after is not None else min(2.0 ** attempt, 30.0)
        self._do_sleep(delay)

    # ---------- core request ----------
    def get(self, path: str, params: Optional[dict] = None) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        url = self.base_url + path
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
        self.calls.append({"path": path, "params": clean})
        headers = {"Authorization": f"Bearer {self._key}", "Accept": "application/json", "User-Agent": USER_AGENT}
        attempt = 0
        while True:
            self._throttle()
            self.request_count += 1
            try:
                status, hdrs, raw = self._http(url, headers)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                if attempt >= self.max_retries:
                    raise GranolaApiError(f"network error calling GET {path}: {exc}", path=path) from exc
                self._backoff(attempt)
                attempt += 1
                self.retry_count += 1
                continue
            if 200 <= status < 300:
                if not raw or status == 204:
                    return None
                try:
                    return json.loads(raw.decode("utf-8"))
                except ValueError as exc:
                    raise GranolaApiError(f"Granola returned non-JSON for GET {path}", status=status, path=path) from exc
            payload = _error_payload(raw)
            if status == 429 or status >= 500:
                if attempt >= self.max_retries:
                    raise GranolaApiError(f"HTTP {status} on GET {path} after {attempt} retries: {payload.get('message') or ''}".rstrip(": "),
                                          status=status, code=payload.get("code"), path=path)
                self._backoff(attempt, retry_after=self._retry_after_seconds(hdrs))
                attempt += 1
                self.retry_count += 1
                continue
            message = payload.get("message") or payload.get("error") or f"HTTP {status}"
            raise GranolaApiError(f"HTTP {status} on GET {path}: {message}", status=status, code=payload.get("code"), path=path)

    # ---------- endpoints ----------
    def list_notes(self, created_after: Optional[str] = None, created_before: Optional[str] = None,
                   updated_after: Optional[str] = None, page_size: int = LIST_PAGE_SIZE) -> Iterator[dict]:
        """GET /v1/notes paged by cursor. Yields NoteSummary objects."""
        cursor: Optional[str] = None
        seen: set[str] = set()
        while True:
            page = self.get("/notes", {"created_after": created_after, "created_before": created_before,
                                       "updated_after": updated_after, "page_size": page_size, "cursor": cursor}) or {}
            for note in page.get("notes") or []:
                if isinstance(note, dict):
                    yield note
            cursor = page.get("cursor")
            if not page.get("hasMore") or not cursor or cursor in seen:
                return
            seen.add(cursor)

    def iter_transcript(self, note_id: str, page_size: int = TRANSCRIPT_PAGE_SIZE) -> Iterator[dict]:
        """GET /v1/notes/{id}/transcript paged by cursor."""
        cursor: Optional[str] = None
        seen: set[str] = set()
        while True:
            page = self.get(f"/notes/{note_id}/transcript", {"page_size": page_size, "cursor": cursor}) or {}
            for item in page.get("transcript") or []:
                if isinstance(item, dict):
                    yield item
            cursor = page.get("cursor")
            if not page.get("hasMore") or not cursor or cursor in seen:
                return
            seen.add(cursor)

    def get_note(self, note_id: str) -> tuple[dict, bool]:
        """GET /v1/notes/{id}?include=transcript; on HTTP 413 fetch the note bare and page the transcript.
        Returns (note with 'transcript' filled, paged)."""
        try:
            note = self.get(f"/notes/{note_id}", {"include": "transcript"})
            return (note if isinstance(note, dict) else {}), False
        except GranolaApiError as exc:
            if exc.status != 413:
                raise
        note = self.get(f"/notes/{note_id}") or {}
        if not isinstance(note, dict):
            note = {}
        note["transcript"] = list(self.iter_transcript(note_id))
        return note, True


def _error_payload(raw: bytes | str | None) -> dict:
    if not raw:
        return {}
    try:
        text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {"message": text[:200]}
    except ValueError:
        return {"message": (raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw))[:200]}


# ---------------------------------------------------------------------------
# watermark and note cache
# ---------------------------------------------------------------------------

def read_watermark(cache_dir: Path) -> Optional[dict]:
    p = Path(cache_dir) / WATERMARK_FILE
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) and obj.get("updated_after") else None


def write_watermark(cache_dir: Path, updated_after: str, extra: Optional[dict] = None) -> Path:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / WATERMARK_FILE
    obj = {"updated_after": updated_after, "writtenAt": now_iso()}
    obj.update(extra or {})
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(p)
    return p


def _safe_file_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._") or "note"


def note_cache_name(note: dict) -> str:
    """<uuid>.json when the note carries a web_url with the document UUID, else <id>.json."""
    uuid = gp.uuid_from_url(note.get("web_url")) or gp.normalize_uuid(note.get("id"))
    return f"{uuid or _safe_file_stem(str(note.get('id') or 'note'))}.json"


def _api_date_start(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return str(value).strip()


def _api_date_end(value: Optional[str]) -> Optional[str]:
    """created_before is exclusive, so a bare window date is widened to the end of that day."""
    if not value:
        return None
    s = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s + "T23:59:59Z"
    return s


def pull_api(client: GranolaClient, cfg: Config, cache_dir: Path, tz: Any = None,
             log: Optional[Callable[[str], None]] = None) -> tuple[list[dict], dict]:
    """Walk the notes list for the config window (incrementally after the first run), cache every note as
    JSON and return the parsed meetings plus stats. The watermark is only advanced after a complete walk."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    window_from, window_to = cfg.window
    watermark = read_watermark(cache_dir)
    updated_after = watermark.get("updated_after") if watermark else None
    run_started = now_iso()
    listed = fetched = paged = 0
    meetings: list[dict] = []
    wrote: list[str] = []
    for summary in client.list_notes(created_after=_api_date_start(window_from), created_before=_api_date_end(window_to),
                                     updated_after=updated_after):
        listed += 1
        note_id = summary.get("id")
        if not note_id:
            continue
        note, was_paged = client.get_note(str(note_id))
        if not note:
            continue
        fetched += 1
        paged += 1 if was_paged else 0
        for k in ("title", "owner", "created_at", "updated_at"):
            note.setdefault(k, summary.get(k))
        path = cache_dir / note_cache_name(note)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(note, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        wrote.append(str(path))
        meetings.extend(gp.parse_public_api_note(note, tz=tz))
        if log and fetched % 10 == 0:
            log(f"{fetched} notes fetched ({client.request_count} requests)")
    write_watermark(cache_dir, run_started, {"window": {"from": window_from, "to": window_to},
                                             "notesListed": listed, "previous": updated_after})
    stats = {
        "filesRead": fetched,
        "api": {"baseUrl": client.base_url, "window": {"from": window_from, "to": window_to},
                "updatedAfter": updated_after, "watermark": run_started, "notesListed": listed,
                "notesFetched": fetched, "transcriptsPaged": paged,
                "requests": client.request_count, "retries": client.retry_count},
        "wrote": wrote,
        "warnings": [],
    }
    return meetings, stats


# ---------------------------------------------------------------------------
# legacy cache
# ---------------------------------------------------------------------------

def inspect_cache_path(path: Path) -> tuple[str, str]:
    """('ok' | 'encrypted' | 'missing' | 'stub' | 'unreadable', detail). Parses files up to PARSE_PROBE_BYTES."""
    path = Path(path)
    if path.suffix.lower() == ".enc":
        return "encrypted", f"{path} is an encrypted cache (Granola 7.427+)"
    if not path.exists():
        enc = path.with_name(path.name + ".enc")
        if enc.exists():
            return "encrypted", f"{path} is missing and {enc.name} is encrypted (Granola 7.427+)"
        return "missing", f"{path} does not exist"
    try:
        size = path.stat().st_size
        if size > PARSE_PROBE_BYTES:
            return "ok", f"{path} ({size // (1024 * 1024)} MB plaintext cache, not probed)"
        with path.open("r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return "unreadable", f"{path} is not readable JSON ({type(exc).__name__})"
    n = gp.cache_document_count(obj)
    if n == 0:
        return "stub", f"{path} holds no documents ({size} bytes)"
    return "ok", f"{path} ({n} documents, {max(1, size // 1024)} KB)"


def load_cache(path: Path, tz: Any = None) -> tuple[list[dict], dict]:
    """Parse a legacy plaintext cache. Raises EncryptedCacheError when it cannot be used."""
    path = Path(path)
    state, detail = inspect_cache_path(path)
    if state != "ok":
        raise EncryptedCacheError(detail, state)
    with path.open("r", encoding="utf-8") as fh:
        obj = json.load(fh)
    n = gp.cache_document_count(obj)
    if n == 0:
        raise EncryptedCacheError(f"{path} holds no documents", "stub")
    return gp.parse_cache_json(obj, tz), {"filesRead": 1, "documents": n, "warnings": []}


# ---------------------------------------------------------------------------
# export folder
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def _is_export_shape(item: dict) -> bool:
    src = item.get("source")
    if isinstance(src, str) and src.startswith("granola:"):
        return True
    return "participants" in item and ("transcript" in item or "summary_markdown" in item)


def _parse_json_export(obj: Any, path: Path, tz: Any = None) -> tuple[list[dict], str]:
    """Route a decoded JSON file: MCP tool result saved as JSON, legacy cache, export-shape dicts, API notes."""
    fallback = gp.uuid_from_path(path)
    if isinstance(obj, str):
        if _MCP_MARK_RE.search(obj):
            return gp.parse_mcp_text(obj, tz, fallback_id=fallback), "mcp"
        return [], "unrecognised"
    if isinstance(obj, dict):
        content = obj.get("content")
        if isinstance(content, list) and content and all(isinstance(c, dict) and "text" in c for c in content):
            text = "\n".join(str(c.get("text") or "") for c in content)
            return gp.parse_mcp_text(text, tz, fallback_id=fallback), "mcp"
        if gp.cache_document_count(obj) > 0:
            return gp.parse_cache_json(obj, tz), "cache"
    items: list
    if isinstance(obj, list):
        items = obj
    elif isinstance(obj, dict) and isinstance(obj.get("notes"), list) and not _is_export_shape(obj):
        items = obj["notes"]
    elif isinstance(obj, dict) and isinstance(obj.get("meetings"), list) and not _is_export_shape(obj):
        items = obj["meetings"]
    else:
        items = [obj]
    out: list[dict] = []
    kind: Optional[str] = None
    for item in items:
        if not isinstance(item, dict):
            continue
        if _is_export_shape(item):
            meeting = gp.new_meeting()
            meeting.update(item)
            if not meeting.get("uuid"):
                meeting["uuid"] = gp.normalize_uuid(meeting.get("id")) or gp.uuid_from_url(meeting.get("web_url"))
            out.append(meeting)
            kind = kind or "export"
        else:
            out.extend(gp.parse_public_api_note(item, tz=tz))
            kind = kind or "api"
    return out, kind or "unrecognised"


def parse_export_file(path: Path, tz: Any = None) -> tuple[list[dict], str]:
    """Pick the parser for one file by extension and content. Returns (meetings, kind)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return gp.parse_csv(_read_text(path), tz), "csv"
    if suffix == ".md":
        return gp.parse_markdown(_read_text(path), path=path, tz=tz), "markdown"
    if suffix == ".json":
        return _parse_json_export(json.loads(_read_text(path)), path, tz)
    if suffix in (".txt", ".xml"):
        text = _read_text(path)
        if _MCP_MARK_RE.search(text):
            return gp.parse_mcp_text(text, tz, fallback_id=gp.uuid_from_path(path)), "mcp"
        stripped = text.lstrip()
        if stripped.startswith(("{", "[")):
            try:
                return _parse_json_export(json.loads(stripped), path, tz)
            except ValueError:
                pass
        if gp.uuid_from_path(path) and gp.looks_like_transcript(text):
            return gp.parse_mcp_text(text, tz, fallback_id=gp.uuid_from_path(path)), "mcp"
        return [], "unrecognised"
    return [], "unrecognised"


def export_files(export_dir: Path) -> list[Path]:
    """Every importable file under the folder, sorted; names starting with '_' or '.' are skipped."""
    export_dir = Path(export_dir)
    if not export_dir.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(export_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXPORT_SUFFIXES:
            continue
        rel = p.relative_to(export_dir)
        if any(part.startswith((".", "_")) for part in rel.parts):
            continue
        out.append(p)
    return out


def read_export_dir(export_dir: Path, tz: Any = None) -> tuple[list[dict], dict]:
    meetings: list[dict] = []
    stats: dict = {"filesRead": 0, "filesSkipped": 0, "byKind": {}, "warnings": []}
    for path in export_files(export_dir):
        try:
            found, kind = parse_export_file(path, tz)
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            stats["filesSkipped"] += 1
            stats["warnings"].append(f"{path.name}: {type(exc).__name__}: {exc}")
            continue
        stats["filesRead"] += 1
        stats["byKind"][kind] = stats["byKind"].get(kind, 0) + 1
        if not found:
            stats["warnings"].append(f"{path.name}: no meetings recognised ({kind})")
        meetings.extend(found)
    return meetings, stats


# ---------------------------------------------------------------------------
# the common ending
# ---------------------------------------------------------------------------

def linked_interaction_ids(store: Store) -> set[str]:
    """Ids already present inside a deal's interaction file (anything but _unlinked.json)."""
    ids: set[str] = set()
    if not store.interactions_dir.exists():
        return ids
    for p in sorted(store.interactions_dir.glob("*.json")):
        if p.name == "_unlinked.json":
            continue
        for it in store.read_json(p, []) or []:
            if isinstance(it, dict) and it.get("id"):
                ids.add(str(it["id"]))
    return ids


def has_external_participant(interaction: dict) -> bool:
    return any(p.get("role") == "buyer" for p in interaction.get("participants") or [] if isinstance(p, dict))


def finish(store: Store, cfg: Config, meetings: Iterable[dict], mode: str, source: str, stats: Optional[dict] = None) -> dict:
    """Meetings -> validated Interactions -> _unlinked.json. Returns the summary dict (without durations)."""
    stats = dict(stats or {})
    reps = store.load_reps()
    internal = cfg.internal_domains(reps)
    merged = gp.merge_meetings([m for m in meetings if isinstance(m, dict)])
    linked = linked_interaction_ids(store)
    records: dict[str, dict] = {}
    skipped_internal = already_linked = 0
    invalid: list[str] = []
    for meeting in merged:
        rec = gp.to_interaction(meeting, cfg, internal_domains=internal, reps=reps)
        if not has_external_participant(rec):
            skipped_internal += 1
            continue
        errors = validate_records("interaction", [rec])
        if errors:
            invalid.extend(errors)
            continue
        if rec["id"] in linked:
            already_linked += 1
            continue
        records[rec["id"]] = rec
    existing = store.load_unlinked()
    wrote: list[str] = list(stats.pop("wrote", []) or [])
    if records:
        store.save_unlinked(Store.upsert(existing, list(records.values())))
        wrote.append(str(store.interactions_dir / "_unlinked.json"))
        total_unlinked = len(store.load_unlinked())
    else:
        total_unlinked = len(existing)
    summary = {
        "ok": True,
        "mode": mode,
        "source": source,
        "filesRead": int(stats.pop("filesRead", 0) or 0),
        "meetingsParsed": len(merged),
        "transcriptsPresent": sum(1 for m in merged if m.get("transcript")),
        "skippedInternal": skipped_internal,
        "writtenUnlinked": len(records),
        "alreadyLinked": already_linked,
        "invalid": len(invalid),
        "validationErrors": invalid[:20],
        "unlinkedTotal": total_unlinked,
        "warnings": list(stats.pop("warnings", []) or []),
        "wrote": wrote,
    }
    summary.update(stats)
    return summary


# ---------------------------------------------------------------------------
# command
# ---------------------------------------------------------------------------

def select_mode(granola_cfg: dict, cache_arg: Optional[str], export_arg: Optional[str]) -> str:
    if cache_arg:
        return "cache"
    if export_arg:
        return "export"
    mode = str(granola_cfg.get("mode") or "").strip().lower()
    if mode == "api":
        return "api"
    if mode in ("local-cache", "cache") and granola_cfg.get("cachePath"):
        return "cache"
    return "export"


def _emit(ctx: dict, payload: dict, text: str, err: bool = False) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text, file=sys.stderr if err else sys.stdout)


def _text(s: dict) -> str:
    lines = [
        f"Granola import ({s['mode']}: {s['source']})",
        f"  files read: {s['filesRead']}   meetings parsed: {s['meetingsParsed']}   transcripts present: {s['transcriptsPresent']}",
        f"  skipped internal-only: {s['skippedInternal']}   already linked: {s['alreadyLinked']}   "
        f"written unlinked: {s['writtenUnlinked']}   (unlinked total: {s['unlinkedTotal']})",
    ]
    api = s.get("api")
    if api:
        since = f" changed since {api['updatedAfter']}" if api.get("updatedAfter") else ""
        lines.append(f"  api: {api['notesListed']} notes listed{since}, {api['notesFetched']} fetched "
                     f"({api['transcriptsPaged']} transcripts paged), {api['requests']} requests, {api['retries']} retries; "
                     f"next run starts from {api['watermark']}")
    if s.get("invalid"):
        lines.append(f"  invalid records skipped: {s['invalid']} (details with --json)")
        for e in s.get("validationErrors") or []:
            lines.append(f"    {e}")
    for w in s.get("warnings") or []:
        lines.append(f"  warning: {w}")
    if s.get("writtenUnlinked"):
        lines.append("Next: fs.py link attaches the new interactions to deals.")
    lines.append(f"  took {s.get('durationMs', 0) / 1000:.1f}s")
    return "\n".join(lines)


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    started = ctx.get("started") or time.time()
    if not store.exists():
        _emit(ctx, {"ok": False, "error": "no store; run init"}, f"No FlowSales store at {store.home}. Run: fs.py init", err=True)
        return 1
    cfg = store.config
    g = cfg.get("sources.granola") or {}
    tz = g.get("timezone") or None
    cache_arg = getattr(args, "cache", None)
    export_arg = getattr(args, "export_dir", None)
    mode = select_mode(g, cache_arg, export_arg)
    args_dict = {"source": "granola", "mode": mode, "cache": cache_arg, "exportDir": export_arg}
    read: list[str] = []
    source = ""

    def progress(msg: str) -> None:
        if not ctx.get("json"):
            print(f"  {msg}", file=sys.stderr)

    try:
        if mode == "cache":
            path = Path(cache_arg or g.get("cachePath") or DEFAULT_MAC_CACHE).expanduser()
            source = str(path)
            meetings, stats = load_cache(path, tz)
            read.append(str(path))
        elif mode == "api":
            key, _where = resolve_granola_key(cfg, store.home)
            if not key:
                text = KEY_HELP.format(env=API_KEY_ENV, plugin_env=PLUGIN_OPTION_ENV,
                                       secrets=store.home / "secrets.json", secrets_key=SECRETS_KEY)
                store.log_run("import granola", args_dict, False, started, notes="no API key")
                _emit(ctx, {"ok": False, "error": "no Granola API key", "help": text}, text, err=True)
                return 1
            client = GranolaClient(key, base_url=g.get("apiBaseUrl") or DEFAULT_API_BASE_URL,
                                   rate_per_sec=float(g.get("requestsPerSecond") or API_RATE_PER_SEC))
            source = client.base_url
            cache_dir = store.cache_dir / "granola"
            meetings, stats = pull_api(client, cfg, cache_dir, tz=tz, log=progress)
            read.append(f"granola-api:{client.base_url}")
            stats["wrote"] = [str(cache_dir)] if stats.get("wrote") else []
        else:
            export_dir = Path(export_arg or g.get("exportDir") or (store.cache_dir / "granola")).expanduser()
            source = str(export_dir)
            if not export_dir.is_dir():
                text = (f"No Granola export folder at {export_dir}. Run the granola setup skill to export meetings over MCP, "
                        f"or point --export-dir at a folder of CSV, markdown or API JSON files (docs/granola.md).")
                store.log_run("import granola", args_dict, False, started, notes=f"missing export folder {export_dir}")
                _emit(ctx, {"ok": False, "error": "no export folder", "path": str(export_dir), "help": text}, text, err=True)
                return 1
            meetings, stats = read_export_dir(export_dir, tz)
            read.append(str(export_dir))
    except EncryptedCacheError as exc:
        store.log_run("import granola", args_dict, False, started, read=read, notes=f"{exc.state}: {exc}")
        if ctx.get("json"):
            print(json.dumps({"ok": False, "error": ENCRYPTED_CACHE_MESSAGE, "state": exc.state, "detail": str(exc)}))
        else:
            print(ENCRYPTED_CACHE_MESSAGE)
        return 1
    except GranolaApiError as exc:
        store.log_run("import granola", args_dict, False, started, read=read, notes=f"{type(exc).__name__}: {exc}")
        _emit(ctx, {"ok": False, "error": str(exc), "status": exc.status, "code": exc.code}, f"error: {exc}", err=True)
        return 2

    summary = finish(store, cfg, meetings, mode=mode, source=source, stats=stats)
    summary["read"] = read
    summary["durationMs"] = int((time.time() - started) * 1000)
    store.log_run("import granola", args_dict, True, started, read=read, wrote=summary["wrote"],
                  notes=(f"{mode}: {summary['filesRead']} files, {summary['meetingsParsed']} meetings, "
                         f"{summary['transcriptsPresent']} transcripts, {summary['skippedInternal']} internal skipped, "
                         f"{summary['writtenUnlinked']} written unlinked, {summary['alreadyLinked']} already linked"))
    _emit(ctx, summary, _text(summary))
    return 0


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

def _check(checks: list[dict], name: str, ok: bool, detail: str, fix: Optional[str] = None) -> dict:
    entry = {"check": name, "ok": bool(ok), "detail": detail, "fix": None if ok else fix}
    checks.append(entry)
    return entry


def granola_checks(store: Store, cfg: Config) -> list[dict]:
    """Doctor items for the Granola source: {check, ok, detail, fix}. Never includes the API key."""
    checks: list[dict] = []
    g = cfg.get("sources.granola") or {}
    mode = str(g.get("mode") or "local-cache").strip().lower()
    export_dir = Path(g["exportDir"]).expanduser() if g.get("exportDir") else store.cache_dir / "granola"
    files = export_files(export_dir)
    transcripts = [p for p in files if p.stem.lower().endswith("-transcript")]
    surfaces: list[str] = []

    if files:
        surfaces.append(f"{len(files)} export files in {export_dir}")
    _check(checks, "granola-export", bool(files),
           f"{export_dir}: {len(files)} export files ({len(transcripts)} transcripts)" if files else f"no export files in {export_dir}",
           "run the granola setup skill to export meetings over MCP, or drop CSV, markdown or API JSON files into the folder (docs/granola.md)")

    if mode == "api":
        key, where = resolve_granola_key(cfg, store.home)
        _check(checks, "granola-api-key", bool(key), f"API key found in {where}" if key else "no API key found",
               f"export {API_KEY_ENV}=grn_... or add {SECRETS_KEY} to {store.home / 'secrets.json'} (Business or Enterprise plan; docs/granola.md)")
        if key:
            surfaces.append("public API")
            if not key.startswith("grn_"):
                _check(checks, "granola-api-key-format", False, "the key does not start with grn_ (Granola API keys do)",
                       "create a key in the Granola desktop app: Settings > Connectors > API keys")
        wm = read_watermark(store.cache_dir / "granola")
        _check(checks, "granola-api-watermark", True,
               f"incremental since {wm['updated_after']}" if wm else "no watermark yet; the first run pulls the whole window")
    elif mode in ("local-cache", "cache"):
        configured = bool(g.get("cachePath"))
        cache_path = Path(g.get("cachePath") or DEFAULT_MAC_CACHE).expanduser()
        state, detail = inspect_cache_path(cache_path)
        if state == "ok":
            surfaces.append(f"plaintext cache {cache_path}")
        # an unconfigured, unusable cache is only a problem when there is no export folder to fall back on
        ok = state == "ok" or (not configured and bool(files))
        if ok and state != "ok":
            detail = f"no cache configured ({detail}); the export folder is used instead"
        _check(checks, "granola-cache", ok, detail,
               ENCRYPTED_CACHE_MESSAGE + " (config set sources.granola.mode mcp, then the granola setup skill; docs/granola.md)")

    n_unlinked = sum(1 for it in store.load_unlinked() if isinstance(it, dict) and it.get("source") == "granola")
    _check(checks, "granola-unlinked", True, f"{n_unlinked} Granola interactions waiting in _unlinked.json"
           + (" (run fs.py link)" if n_unlinked else ""))
    _check(checks, "granola", bool(surfaces), ("usable: " + "; ".join(surfaces)) if surfaces else f"no usable Granola source (mode {mode})",
           "export meetings with the granola setup skill (all plans) or set sources.granola.mode api with a grn_ key (Business or Enterprise); docs/granola.md")
    return checks
