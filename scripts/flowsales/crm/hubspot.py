"""HubSpot adapter: a small urllib client plus the pull walk that turns HubSpot objects into canonical records.

Standard library only. Endpoints, property names and association type ids follow the research reference
(experiences/flow-sales/research/hubspot-access.md, sections 2, 4, 5 and 7). Legacy /crm/v3 and /crm/v4
paths are used on purpose: HubSpot keeps them available alongside the date-based versions.

Read paths only in `pull`. The write helpers on the client exist for the seeding script (developer test
accounts) and are never called by `pull`.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from ..config import Config, resolve_hubspot_token
from ..store import Store
from ..util import chunked, email_domain, now_iso, parse_iso, to_iso

DEFAULT_BASE_URL = "https://api.hubapi.com"
USER_AGENT = "flowsales/0.1 (+https://github.com/RhysEJF/flow-sales)"

SEARCH_PAGE_LIMIT = 200          # search max per page
SEARCH_RESULT_CAP = 10000        # search returns 400 beyond 10,000 results per query
BATCH_READ_LIMIT = 100           # batch read inputs
BATCH_READ_HISTORY_LIMIT = 50    # batch read inputs when propertiesWithHistory is requested
ASSOC_BATCH_LIMIT = 1000         # v4 association batch read inputs
ASSOC_PAGE_LIMIT = 500           # single-record association listing page size
OWNERS_PAGE_LIMIT = 500

# Scopes the read-only walk needs (research doc section 4.1).
REQUIRED_READ_SCOPES = [
    "crm.objects.deals.read",
    "crm.objects.contacts.read",
    "crm.objects.companies.read",
    "crm.objects.owners.read",
    "crm.schemas.deals.read",
    "sales-email-read",
]

# Properties per object (research doc section 2.1 and 2.6).
DEAL_PROPERTIES = [
    "dealname", "amount", "deal_currency_code", "pipeline", "dealstage", "hs_is_closed_won", "hs_is_closed",
    "closedate", "createdate", "hubspot_owner_id", "hs_lastmodifieddate",
]
DEAL_HISTORY_PROPERTIES = ["dealstage", "closedate", "amount", "hubspot_owner_id"]
CONTACT_PROPERTIES = ["email", "firstname", "lastname", "jobtitle", "hs_buying_role", "hs_lastmodifieddate"]
COMPANY_PROPERTIES = ["name", "domain", "hs_lastmodifieddate"]
CALL_PROPERTIES = [
    "hs_timestamp", "hs_call_title", "hs_call_body", "hs_call_duration", "hs_call_direction", "hs_call_disposition",
    "hs_call_status", "hs_call_recording_url", "hs_call_summary", "hubspot_owner_id", "hs_lastmodifieddate",
]
EMAIL_PROPERTIES = [
    "hs_timestamp", "hs_email_subject", "hs_email_direction", "hs_email_headers", "hs_email_status",
    "hubspot_owner_id", "hs_lastmodifieddate",
]
EMAIL_BODY_PROPERTIES = ["hs_email_text", "hs_email_html"]
MEETING_PROPERTIES = [
    "hs_timestamp", "hs_meeting_title", "hs_meeting_body", "hs_meeting_start_time", "hs_meeting_end_time",
    "hs_meeting_outcome", "hubspot_owner_id", "hs_lastmodifieddate",
]
MEETING_INTERNAL_NOTES = "hs_internal_meeting_notes"
NOTE_PROPERTIES = ["hs_timestamp", "hs_note_body", "hubspot_owner_id", "hs_lastmodifieddate"]

# HubSpot object type name -> canonical interaction type.
ENGAGEMENT_TYPES = {"calls": "call", "emails": "email", "meetings": "meeting", "notes": "note"}

# HubSpot-defined association type ids (research doc section 2.4, official table).
ASSOCIATION_TYPE_IDS = {
    ("deals", "contacts"): 3, ("contacts", "deals"): 4,
    ("deals", "companies"): 341, ("companies", "deals"): 342,
    ("deals", "companies", "primary"): 5, ("companies", "deals", "primary"): 6,
    ("deals", "calls"): 205, ("calls", "deals"): 206,
    ("deals", "emails"): 209, ("emails", "deals"): 210,
    ("deals", "meetings"): 211, ("meetings", "deals"): 212,
    ("deals", "notes"): 213, ("notes", "deals"): 214,
    ("contacts", "calls"): 193, ("calls", "contacts"): 194,
    ("contacts", "emails"): 197, ("emails", "contacts"): 198,
    ("contacts", "meetings"): 199, ("meetings", "contacts"): 200,
    ("contacts", "notes"): 201, ("notes", "contacts"): 202,
    ("contacts", "companies"): 279, ("companies", "contacts"): 280,
    ("contacts", "companies", "primary"): 1, ("companies", "contacts", "primary"): 2,
}

CALL_DIRECTIONS = {"INBOUND": "inbound", "OUTBOUND": "outbound"}
EMAIL_DIRECTIONS = {"EMAIL": "outbound", "FORWARDED_EMAIL": "outbound", "INCOMING_EMAIL": "inbound"}


# ---------------------------------------------------------------------------
# errors
# ---------------------------------------------------------------------------
class HubSpotError(Exception):
    """Any non-retryable HubSpot API failure."""

    def __init__(self, message: str, status: Optional[int] = None, category: Optional[str] = None,
                 correlation_id: Optional[str] = None, body: Any = None, path: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.category = category
        self.correlation_id = correlation_id
        self.body = body
        self.path = path


class ScopeError(HubSpotError):
    """403 MISSING_SCOPES. `required_scopes` carries errors[].context.requiredGranularScopes."""

    def __init__(self, message: str, required_scopes: list[str], **kw: Any):
        super().__init__(message, **kw)
        self.required_scopes = required_scopes


class RateLimitError(HubSpotError):
    """429 that cannot be waited out (daily cap) or retries exhausted."""


class SearchCapError(HubSpotError):
    """A search matched more than 10,000 results; the caller must narrow the query."""


def parse_error_body(raw: bytes | str | None) -> dict:
    if not raw:
        return {}
    try:
        text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        data = json.loads(text)
        return data if isinstance(data, dict) else {"message": str(data)}
    except (ValueError, TypeError):
        return {"message": (raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw))[:500]}


def required_scopes_from(payload: dict) -> list[str]:
    scopes: list[str] = []
    for err in payload.get("errors") or []:
        ctx = (err or {}).get("context") or {}
        for key in ("requiredGranularScopes", "requiredScopes"):
            for s in ctx.get(key) or []:
                if s not in scopes:
                    scopes.append(s)
    return scopes


def error_from_response(status: int, payload: dict, path: str) -> HubSpotError:
    category = payload.get("category") or payload.get("errorType")
    message = payload.get("message") or f"HTTP {status}"
    corr = payload.get("correlationId")
    kw = {"status": status, "category": category, "correlation_id": corr, "body": payload, "path": path}
    if category == "MISSING_SCOPES" or "requiredGranularScopes" in json.dumps(payload):
        scopes = required_scopes_from(payload)
        text = f"HubSpot refused {path}: missing scopes {', '.join(scopes) if scopes else '(unlisted)'}"
        return ScopeError(text, scopes, **kw)
    if status == 401:
        return HubSpotError(f"HubSpot rejected the token ({message})", **kw)
    if category == "RATE_LIMITS" or status == 429:
        return RateLimitError(f"HubSpot rate limit: {message}", **kw)
    return HubSpotError(f"HubSpot {status} on {path}: {message}", **kw)


# ---------------------------------------------------------------------------
# throttle
# ---------------------------------------------------------------------------
class TokenBucket:
    """Simple token bucket: `rate` requests per second, burst up to `capacity`. rate <= 0 disables throttling."""

    def __init__(self, rate: float, capacity: Optional[float] = None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        self.rate = float(rate)
        self.capacity = float(capacity if capacity is not None else max(1.0, self.rate))
        self.tokens = self.capacity
        self.clock = clock
        self.sleep = sleep
        self.last = clock()

    def acquire(self) -> float:
        """Take one token, sleeping if needed. Returns the seconds slept."""
        if self.rate <= 0:
            return 0.0
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        waited = 0.0
        if self.tokens < 1.0:
            waited = (1.0 - self.tokens) / self.rate
            self.sleep(waited)
            self.last = self.clock()
            self.tokens = 0.0
        else:
            self.tokens -= 1.0
        return waited


# ---------------------------------------------------------------------------
# client
# ---------------------------------------------------------------------------
class HubSpotClient:
    """Thin JSON client over urllib with bearer auth, retry with backoff, throttling and paging helpers.

    Tests subclass it and override `_http` to serve canned responses.
    """

    def __init__(self, token: str, base_url: str = DEFAULT_BASE_URL, rate_per_sec: float = 4.0,
                 max_retries: int = 5, timeout: float = 60.0, sleep: Optional[Callable[[float], None]] = None,
                 clock: Optional[Callable[[], float]] = None):
        if not token:
            raise ValueError("HubSpotClient needs a token")
        self.token = token
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.max_retries = max(0, int(max_retries))
        self.timeout = timeout
        self._sleep = sleep or time.sleep
        self._clock = clock or time.monotonic
        self.bucket = TokenBucket(rate_per_sec, clock=self._clock, sleep=self._sleep)
        self.request_count = 0
        self.retry_count = 0
        self.last_rate_headers: dict[str, str] = {}

    # ---------- transport (override in tests) ----------
    def _http(self, method: str, url: str, body: Optional[bytes], headers: dict) -> tuple[int, dict, bytes]:
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - https to the configured host
                return int(resp.status), {k: v for k, v in resp.headers.items()}, resp.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            return int(exc.code), {k: v for k, v in (exc.headers or {}).items()}, raw or b""

    # ---------- core request ----------
    def request(self, method: str, path: str, params: Optional[dict] = None, body: Any = None) -> Any:
        url = self.base_url + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json", "User-Agent": USER_AGENT}
        data: Optional[bytes] = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        attempt = 0
        while True:
            self.bucket.acquire()
            self.request_count += 1
            try:
                status, hdrs, raw = self._http(method, url, data, headers)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                if attempt >= self.max_retries:
                    raise HubSpotError(f"network error calling {method} {path}: {exc}", path=path) from exc
                self._backoff(attempt)
                attempt += 1
                self.retry_count += 1
                continue
            self._remember_rate_headers(hdrs)
            if 200 <= status < 300:
                if not raw or status == 204:
                    return None
                try:
                    return json.loads(raw.decode("utf-8"))
                except ValueError as exc:
                    raise HubSpotError(f"HubSpot returned non-JSON for {method} {path}", status=status, path=path) from exc
            payload = parse_error_body(raw)
            if status == 429:
                policy = str(payload.get("policyName") or "").upper()
                if "DAILY" in policy:
                    raise RateLimitError(f"HubSpot daily API limit reached ({payload.get('message')})",
                                         status=status, category="RATE_LIMITS", body=payload, path=path)
                if attempt >= self.max_retries:
                    raise RateLimitError(f"HubSpot rate limit on {path} after {attempt} retries: {payload.get('message')}",
                                         status=status, category="RATE_LIMITS", body=payload, path=path)
                self._backoff(attempt, retry_after=self._retry_after_seconds(hdrs))
                attempt += 1
                self.retry_count += 1
                continue
            if status >= 500 and attempt < self.max_retries:
                self._backoff(attempt, retry_after=self._retry_after_seconds(hdrs))
                attempt += 1
                self.retry_count += 1
                continue
            raise error_from_response(status, payload, path)

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: Any = None, params: Optional[dict] = None) -> Any:
        return self.request("POST", path, params=params, body=body if body is not None else {})

    def patch(self, path: str, body: Any) -> Any:
        return self.request("PATCH", path, body=body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    # ---------- retry helpers ----------
    def _remember_rate_headers(self, hdrs: dict) -> None:
        self.last_rate_headers = {k: v for k, v in hdrs.items() if str(k).lower().startswith("x-hubspot-ratelimit")}

    @staticmethod
    def _retry_after_seconds(hdrs: dict) -> Optional[float]:
        """HubSpot documents Retry-After in milliseconds; the HTTP standard says seconds. Handle both."""
        for k, v in hdrs.items():
            if str(k).lower() == "retry-after":
                try:
                    n = float(v)
                except (TypeError, ValueError):
                    return None
                if n > 100:  # anything above 100 is surely milliseconds
                    n = n / 1000.0
                return max(0.5, min(n, 60.0))
        return None

    def _backoff(self, attempt: int, retry_after: Optional[float] = None) -> None:
        if retry_after is not None:
            delay = retry_after
        else:
            delay = min(30.0, 1.0 * (2 ** attempt))
        delay += random.uniform(0, 0.25)
        self._sleep(delay)

    # ---------- account ----------
    def token_info(self) -> dict:
        """POST /oauth/v2/private-apps/get/access-token-info -> {userId, hubId, appId, scopes[]}."""
        return self.post("/oauth/v2/private-apps/get/access-token-info", {"tokenKey": self.token}) or {}

    def owners(self, archived: bool = False) -> list[dict]:
        out: list[dict] = []
        after: Optional[str] = None
        while True:
            params: dict[str, Any] = {"limit": OWNERS_PAGE_LIMIT}
            if archived:
                params["archived"] = "true"
            if after:
                params["after"] = after
            page = self.get("/crm/v3/owners", params) or {}
            out.extend(page.get("results") or [])
            after = _next_after(page)
            if not after:
                return out

    def owner_by_user_id(self, user_id: Any) -> Optional[dict]:
        try:
            return self.get(f"/crm/v3/owners/{user_id}", {"idProperty": "userId", "archived": "false"})
        except HubSpotError as exc:
            if exc.status == 404:
                return None
            raise

    def pipelines(self, object_type: str = "deals") -> list[dict]:
        page = self.get(f"/crm/v3/pipelines/{object_type}") or {}
        return page.get("results") or []

    # ---------- search ----------
    def search_pages(self, object_type: str, body: dict) -> Iterator[dict]:
        """Yield raw search pages, following `paging.next.after`. Raises SearchCapError at the 10,000 wall."""
        body = dict(body)
        body.setdefault("limit", SEARCH_PAGE_LIMIT)
        after: Optional[Any] = None
        while True:
            if after is not None:
                body["after"] = after
            page = self.post(f"/crm/v3/objects/{object_type}/search", body) or {}
            yield page
            after = _next_after(page)
            if not after:
                return
            try:
                if int(after) >= SEARCH_RESULT_CAP:
                    raise SearchCapError(f"search on {object_type} passed the {SEARCH_RESULT_CAP} result cap", path=f"/crm/v3/objects/{object_type}/search")
            except (TypeError, ValueError):
                pass

    def search(self, object_type: str, filter_groups: list[dict], properties: list[str],
               sorts: Optional[list[dict]] = None, query: Optional[str] = None, limit: int = SEARCH_PAGE_LIMIT,
               max_results: Optional[int] = None) -> list[dict]:
        body: dict[str, Any] = {"filterGroups": filter_groups, "properties": properties, "limit": limit}
        if sorts:
            body["sorts"] = sorts
        if query:
            body["query"] = query
        results: list[dict] = []
        for page in self.search_pages(object_type, body):
            total = page.get("total")
            if isinstance(total, int) and total > SEARCH_RESULT_CAP:
                raise SearchCapError(f"search on {object_type} matches {total} results (cap {SEARCH_RESULT_CAP})",
                                     path=f"/crm/v3/objects/{object_type}/search")
            results.extend(page.get("results") or [])
            if max_results is not None and len(results) >= max_results:
                return results[:max_results]
        return results

    def search_range(self, object_type: str, filters: list[dict], date_property: str, start_ms: int, end_ms: int,
                     properties: list[str], sorts: Optional[list[dict]] = None,
                     max_results: Optional[int] = None) -> list[dict]:
        """Search with `date_property BETWEEN start_ms..end_ms` added to `filters`.

        When the 10,000 cap is hit the range is halved and both halves are searched (recursively).
        """
        sorts = sorts or [{"propertyName": date_property, "direction": "DESCENDING"}]
        results: list[dict] = []
        # Breadth-first: a capped range is halved and both halves queued, so the coarse searches
        # happen first and every leaf search is narrow enough to stay under the cap.
        queue: list[tuple[int, int]] = [(int(start_ms), int(end_ms))]
        while queue:
            lo, hi = queue.pop(0)
            group = {"filters": list(filters) + [{"propertyName": date_property, "operator": "BETWEEN",
                                                  "value": str(lo), "highValue": str(hi)}]}
            remaining = None if max_results is None else max_results - len(results)
            try:
                results.extend(self.search(object_type, [group], properties, sorts=sorts, max_results=remaining))
            except SearchCapError:
                if hi - lo < 2:
                    raise
                mid = (lo + hi) // 2
                queue.append((lo, mid))
                queue.append((mid + 1, hi))
                continue
            if max_results is not None and len(results) >= max_results:
                return results[:max_results]
        return results

    # ---------- batch reads ----------
    def batch_read(self, object_type: str, ids: list, properties: list[str],
                   properties_with_history: Optional[list[str]] = None, id_property: Optional[str] = None) -> list[dict]:
        size = BATCH_READ_HISTORY_LIMIT if properties_with_history else BATCH_READ_LIMIT
        unique = list(dict.fromkeys(str(i) for i in ids if i is not None and str(i) != ""))
        out: list[dict] = []
        for chunk in chunked(unique, size):
            body: dict[str, Any] = {"properties": properties, "inputs": [{"id": i} for i in chunk]}
            if properties_with_history:
                body["propertiesWithHistory"] = properties_with_history
            if id_property:
                body["idProperty"] = id_property
            page = self.post(f"/crm/v3/objects/{object_type}/batch/read", body) or {}
            out.extend(page.get("results") or [])
        return out

    # ---------- associations ----------
    def batch_associations(self, from_type: str, to_type: str, ids: list) -> dict[str, list[dict]]:
        """POST /crm/v4/associations/{from}/{to}/batch/read -> {fromId: [{toObjectId, associationTypes[]}]}."""
        unique = list(dict.fromkeys(str(i) for i in ids if i is not None and str(i) != ""))
        out: dict[str, list[dict]] = {i: [] for i in unique}
        for chunk in chunked(unique, ASSOC_BATCH_LIMIT):
            page = self.post(f"/crm/v4/associations/{from_type}/{to_type}/batch/read",
                             {"inputs": [{"id": i} for i in chunk]}) or {}
            for res in page.get("results") or []:
                fid = str((res.get("from") or {}).get("id"))
                tos = list(res.get("to") or [])
                if _next_after(res):  # more than one page for this record: walk the single-record endpoint
                    tos = self.associations(from_type, fid, to_type)
                out[fid] = tos
        return out

    def associations(self, from_type: str, from_id: str, to_type: str) -> list[dict]:
        out: list[dict] = []
        after: Optional[str] = None
        while True:
            params: dict[str, Any] = {"limit": ASSOC_PAGE_LIMIT}
            if after:
                params["after"] = after
            page = self.get(f"/crm/v4/objects/{from_type}/{from_id}/associations/{to_type}", params) or {}
            out.extend(page.get("results") or [])
            after = _next_after(page)
            if not after:
                return out

    # ---------- writes (seeding only; never used by pull) ----------
    def create(self, object_type: str, properties: dict, associations: Optional[list[dict]] = None) -> dict:
        body: dict[str, Any] = {"properties": properties}
        if associations:
            body["associations"] = associations
        return self.post(f"/crm/v3/objects/{object_type}", body) or {}

    def update(self, object_type: str, object_id: str, properties: dict) -> dict:
        return self.patch(f"/crm/v3/objects/{object_type}/{object_id}", {"properties": properties}) or {}

    def archive(self, object_type: str, object_id: str) -> None:
        self.delete(f"/crm/v3/objects/{object_type}/{object_id}")

    def batch_archive(self, object_type: str, ids: list) -> None:
        for chunk in chunked([str(i) for i in ids], BATCH_READ_LIMIT):
            self.post(f"/crm/v3/objects/{object_type}/batch/archive", {"inputs": [{"id": i} for i in chunk]})


def _next_after(page: dict) -> Optional[str]:
    nxt = ((page or {}).get("paging") or {}).get("next") or {}
    after = nxt.get("after")
    return str(after) if after not in (None, "") else None


# ---------------------------------------------------------------------------
# raw cache
# ---------------------------------------------------------------------------
class HubSpotCache:
    """Raw API objects under cache/hubspot/<type>/<id>.json plus a few top-level JSON files."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def path(self, kind: str, obj_id: str) -> Path:
        return self.root / kind / f"{obj_id}.json"

    def has(self, kind: str, obj_id: str) -> bool:
        return self.path(kind, obj_id).exists()

    def read(self, kind: str, obj_id: str) -> Optional[dict]:
        p = self.path(kind, obj_id)
        if not p.exists():
            return None
        try:
            with p.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def write(self, kind: str, obj_id: str, obj: dict, properties: Optional[list[str]] = None) -> None:
        p = self.path(kind, obj_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        if properties is not None:
            obj = dict(obj)
            obj["_flowsales"] = {"properties": list(properties), "cachedAt": now_iso()}
        tmp = p.with_name(p.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False)
        tmp.replace(p)

    def read_meta(self, name: str, default: Any = None) -> Any:
        p = self.root / f"{name}.json"
        if not p.exists():
            return default
        try:
            with p.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return default

    def write_meta(self, name: str, obj: Any) -> None:
        p = self.root / f"{name}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
        tmp.replace(p)


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------
class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "table", "ul", "ol", "pre"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in ("script", "style", "head"):
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "head"):
            self._skip = max(0, self._skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def strip_html(text: Optional[str]) -> str:
    """Turn an HTML fragment into plain text (block tags become line breaks). Plain text passes through."""
    if not text:
        return ""
    if "<" not in text or ">" not in text:
        return _html.unescape(text).strip()
    parser = _TextExtractor()
    try:
        parser.feed(text)
        parser.close()
    except Exception:  # noqa: BLE001 - malformed markup: fall back to a crude strip
        return re.sub(r"<[^>]+>", " ", _html.unescape(text)).strip()
    out = "".join(parser.parts)
    out = re.sub(r"[ \t\r\f\v]+", " ", out)
    out = re.sub(r" *\n *", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _truthy(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes")


def _float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso(value: Any) -> Optional[str]:
    return to_iso(parse_iso(value)) if value not in (None, "") else None


def _ms(value: Any) -> Optional[int]:
    d = parse_iso(value)
    return int(d.timestamp() * 1000) if d else None


def _join_text(*parts: Optional[str]) -> str:
    seen: list[str] = []
    for p in parts:
        p = (p or "").strip()
        if p and p not in seen:
            seen.append(p)
    return "\n\n".join(seen)


def _person_name(first: Optional[str], last: Optional[str], fallback: Optional[str] = None) -> Optional[str]:
    name = " ".join(x.strip() for x in (first or "", last or "") if x and x.strip()).strip()
    return name or fallback


def parse_email_headers(raw: Any) -> dict[str, list[dict]]:
    """hs_email_headers is a JSON string {from:{email,firstName,lastName}, to:[...], cc:[...], bcc:[...]}.

    Returns {"from": [...], "to": [...], "cc": [...], "bcc": [...]} with {name, email} entries (emails lower-cased).
    Tolerates double-encoded JSON, missing keys and malformed input.
    """
    out: dict[str, list[dict]] = {"from": [], "to": [], "cc": [], "bcc": []}
    data: Any = raw
    for _ in range(2):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                return out
    if not isinstance(data, dict):
        return out

    def person(p: Any) -> Optional[dict]:
        if isinstance(p, str):
            return {"name": None, "email": p.strip().lower()} if "@" in p else None
        if not isinstance(p, dict):
            return None
        email = (p.get("email") or "").strip().lower() or None
        name = _person_name(p.get("firstName") or p.get("firstname"), p.get("lastName") or p.get("lastname"),
                            p.get("name"))
        if not email and not name:
            return None
        return {"name": name, "email": email}

    for key in ("from", "to", "cc", "bcc"):
        val = data.get(key)
        items = val if isinstance(val, list) else ([val] if val else [])
        for it in items:
            p = person(it)
            if p:
                out[key].append(p)
    return out


def direction_for(hs_type: str, props: dict) -> str:
    """Map HubSpot direction fields to inbound / outbound / internal / unknown."""
    if hs_type == "calls":
        return CALL_DIRECTIONS.get(str(props.get("hs_call_direction") or "").upper(), "unknown")
    if hs_type == "emails":
        return EMAIL_DIRECTIONS.get(str(props.get("hs_email_direction") or "").upper(), "unknown")
    if hs_type == "notes":
        return "internal"
    return "unknown"


def outcome_for(props: dict, phase: Optional[str] = None) -> str:
    won = _truthy(props.get("hs_is_closed_won"))
    closed = _truthy(props.get("hs_is_closed"))
    if won:
        return "won"
    if closed:
        return "lost"
    if closed is None and phase in ("won", "lost"):
        return phase
    return "open"


def stage_history_from(raw: dict, stage_label: dict[str, str], phase_of: Callable[[Optional[str]], str]) -> list[dict]:
    """propertiesWithHistory.dealstage (newest first) -> [{stage, label, phase, at}] oldest first."""
    versions = ((raw.get("propertiesWithHistory") or {}).get("dealstage")) or []
    entries: list[tuple[int, dict]] = []
    for v in versions:
        stage = v.get("value")
        at = _iso(v.get("timestamp"))
        if not stage or not at:
            continue
        entries.append((_ms(at) or 0, {"stage": stage, "label": stage_label.get(stage, stage), "phase": phase_of(stage), "at": at}))
    entries.sort(key=lambda e: e[0])
    history = [e[1] for e in entries]
    if not history:
        props = raw.get("properties") or {}
        stage = props.get("dealstage")
        if stage:
            history = [{"stage": stage, "label": stage_label.get(stage, stage), "phase": phase_of(stage),
                        "at": _iso(props.get("createdate")) or _iso(raw.get("createdAt")) or now_iso()}]
    return history


def _history_versions(raw: dict, prop: str) -> list[dict]:
    versions = ((raw.get("propertiesWithHistory") or {}).get(prop)) or []
    out = []
    for v in versions:
        at = _iso(v.get("timestamp"))
        if at:
            out.append({"value": v.get("value"), "at": at})
    out.sort(key=lambda e: e["at"])
    return out


# ---------------------------------------------------------------------------
# canonical conversion
# ---------------------------------------------------------------------------
class _Context:
    """Everything the converters need, gathered once per pull."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.stage_label: dict[str, str] = {}
        self.stage_pipeline: dict[str, str] = {}
        self.pipeline_label: dict[str, str] = {}
        self.owners: dict[str, dict] = {}          # ownerId -> raw owner
        self.owner_by_email: dict[str, str] = {}   # email -> ownerId
        self.contacts: dict[str, dict] = {}        # contactId -> raw
        self.companies: dict[str, dict] = {}       # companyId -> raw
        self.internal_domains: set[str] = set()
        content = cfg.get("content") or {}
        self.email_bodies = content.get("emailBodies", True) is not False
        self.internal_notes = content.get("internalNotes", True) is not False

    def phase_of(self, stage_id: Optional[str]) -> str:
        return self.cfg.phase_for_stage(stage_id, self.stage_label.get(stage_id or ""))

    def rep_participant(self, owner_id: Optional[str]) -> Optional[dict]:
        o = self.owners.get(str(owner_id)) if owner_id else None
        if not o:
            return None
        return {"name": _person_name(o.get("firstName"), o.get("lastName"), o.get("email")),
                "email": (o.get("email") or "").lower() or None, "role": "rep"}

    def contact_participant(self, contact_id: str) -> Optional[dict]:
        c = self.contacts.get(str(contact_id))
        if not c:
            return None
        p = c.get("properties") or {}
        email = (p.get("email") or "").lower() or None
        return {"name": _person_name(p.get("firstname"), p.get("lastname"), email), "email": email,
                "role": "rep" if self.is_internal(email) else "buyer"}

    def is_internal(self, email: Optional[str]) -> bool:
        if not email:
            return False
        e = email.lower()
        if e in self.owner_by_email:
            return True
        dom = email_domain(e)
        return bool(dom and dom in self.internal_domains)


def rep_record(owner: dict) -> dict:
    email = (owner.get("email") or "").strip().lower() or None
    return {"id": f"rep:{owner.get('id')}", "name": _person_name(owner.get("firstName"), owner.get("lastName"), email),
            "email": email, "source": "hubspot"}


def contact_record(raw: dict, company_id: Optional[str]) -> dict:
    p = raw.get("properties") or {}
    email = (p.get("email") or "").strip().lower() or None
    return {"id": f"c:{raw.get('id')}", "name": _person_name(p.get("firstname"), p.get("lastname"), email),
            "email": email, "title": p.get("jobtitle") or None, "companyId": f"co:{company_id}" if company_id else None,
            "buyingRole": p.get("hs_buying_role") or None}


def company_record(raw: dict) -> dict:
    p = raw.get("properties") or {}
    domain = (p.get("domain") or "").strip().lower() or None
    return {"id": f"co:{raw.get('id')}", "name": p.get("name") or domain or f"company {raw.get('id')}", "domain": domain}


def deal_record(raw: dict, ctx: _Context, contact_ids: list[str], company_ids: list[dict]) -> dict:
    p = raw.get("properties") or {}
    deal_id = str(raw.get("id"))
    stage = p.get("dealstage") or None
    phase = ctx.phase_of(stage)
    outcome = outcome_for(p, phase)
    history = stage_history_from(raw, ctx.stage_label, ctx.phase_of)
    primary: Optional[str] = None
    for c in company_ids:
        if 5 in c.get("typeIds", []):
            primary = c["id"]
            break
    if primary is None and company_ids:
        primary = company_ids[0]["id"]
    company = ctx.companies.get(primary or "") or {}
    domain = ((company.get("properties") or {}).get("domain") or "").strip().lower() or None
    closed_at = _iso(p.get("closedate")) if outcome in ("won", "lost") else None
    owner = p.get("hubspot_owner_id")
    return {
        "id": f"hs:{deal_id}",
        "source": "hubspot",
        "name": p.get("dealname") or f"deal {deal_id}",
        "amount": _float(p.get("amount")),
        "currency": p.get("deal_currency_code") or None,
        "pipeline": p.get("pipeline") or None,
        "stage": stage,
        "stageLabel": ctx.stage_label.get(stage or "", stage),
        "phase": phase,
        "stageHistory": history,
        "outcome": outcome,
        "createdAt": _iso(p.get("createdate")) or _iso(raw.get("createdAt")),
        "closedAt": closed_at,
        "ownerId": f"rep:{owner}" if owner else None,
        "contactIds": [f"c:{c}" for c in contact_ids],
        "companyId": f"co:{primary}" if primary else None,
        "companyDomain": domain,
        "meta": {
            "hubspotId": deal_id,
            "pipelineLabel": ctx.pipeline_label.get(p.get("pipeline") or "", None),
            "expectedCloseAt": _iso(p.get("closedate")) if outcome == "open" else None,
            "lastModifiedAt": _iso(p.get("hs_lastmodifieddate")) or _iso(raw.get("updatedAt")),
            "isClosedWon": _truthy(p.get("hs_is_closed_won")),
            "isClosed": _truthy(p.get("hs_is_closed")),
            "amountHistory": _history_versions(raw, "amount"),
            "closedateHistory": _history_versions(raw, "closedate"),
            "ownerHistory": [{"value": f"rep:{v['value']}" if v.get("value") else None, "at": v["at"]}
                             for v in _history_versions(raw, "hubspot_owner_id")],
            "companyIds": [f"co:{c['id']}" for c in company_ids],
        },
    }


def interaction_record(hs_type: str, raw: dict, deal_id: str, ctx: _Context, contact_ids: list[str]) -> dict:
    p = raw.get("properties") or {}
    obj_id = str(raw.get("id"))
    kind = ENGAGEMENT_TYPES[hs_type]
    owner_id = p.get("hubspot_owner_id") or None
    direction = direction_for(hs_type, p)
    participants: list[dict] = []
    seen_emails: set[str] = set()

    def add(part: Optional[dict]) -> None:
        if not part:
            return
        key = part.get("email") or f"name:{part.get('name')}"
        if key in seen_emails:
            return
        seen_emails.add(key)
        participants.append(part)

    title: Optional[str] = None
    body = ""
    notes: Optional[str] = None
    summary: Optional[str] = None
    duration: Optional[int] = None
    recording: Optional[str] = None
    at = _iso(p.get("hs_timestamp"))
    meta: dict[str, Any] = {"hubspotType": hs_type, "hubspotId": obj_id,
                            "lastModifiedAt": _iso(p.get("hs_lastmodifieddate")) or _iso(raw.get("updatedAt"))}

    if hs_type == "calls":
        title = p.get("hs_call_title") or None
        summary = (p.get("hs_call_summary") or "").strip() or None
        body = _join_text(title, strip_html(p.get("hs_call_body")), summary)
        ms = _float(p.get("hs_call_duration"))
        duration = int(round(ms / 1000.0)) if ms else None
        recording = p.get("hs_call_recording_url") or None
        meta.update({"status": p.get("hs_call_status"), "disposition": p.get("hs_call_disposition"),
                     "rawDirection": p.get("hs_call_direction")})
    elif hs_type == "emails":
        title = p.get("hs_email_subject") or None
        headers = parse_email_headers(p.get("hs_email_headers"))
        if ctx.email_bodies:
            text = (p.get("hs_email_text") or "").strip() or strip_html(p.get("hs_email_html"))
            body = _join_text(title, text)
        else:
            body = (title or "").strip()
        for position in ("from", "to", "cc", "bcc"):
            for person in headers[position]:
                email = person.get("email")
                if ctx.is_internal(email) or (position == "from" and direction == "outbound"):
                    role = "rep"
                else:
                    role = "buyer"
                add({"name": person.get("name"), "email": email, "role": role})
        meta.update({"status": p.get("hs_email_status"), "rawDirection": p.get("hs_email_direction"),
                     "from": [h.get("email") for h in headers["from"]], "to": [h.get("email") for h in headers["to"]],
                     "cc": [h.get("email") for h in headers["cc"]], "bodyIncluded": ctx.email_bodies})
    elif hs_type == "meetings":
        title = p.get("hs_meeting_title") or None
        body = _join_text(title, strip_html(p.get("hs_meeting_body")))
        if ctx.internal_notes:
            internal = strip_html(p.get(MEETING_INTERNAL_NOTES))
            if internal:
                notes = internal
                body = _join_text(body, "Internal notes:\n" + internal)
        start = _iso(p.get("hs_meeting_start_time"))
        end = _iso(p.get("hs_meeting_end_time"))
        at = at or start
        if start and end:
            s, e = _ms(start), _ms(end)
            if s is not None and e is not None and e >= s:
                duration = int((e - s) / 1000)
        meta.update({"outcome": p.get("hs_meeting_outcome"), "startAt": start, "endAt": end,
                     "internalNotesIncluded": ctx.internal_notes})
    elif hs_type == "notes":
        body = strip_html(p.get("hs_note_body"))
        first = body.split("\n", 1)[0].strip() if body else ""
        title = (first[:77] + "...") if len(first) > 80 else (first or None)

    # rep participant (the owner), then the associated contacts
    add(ctx.rep_participant(owner_id))
    for cid in contact_ids:
        add(ctx.contact_participant(cid))

    rep_id = f"rep:{owner_id}" if owner_id else None
    if rep_id is None:
        for part in participants:
            oid = ctx.owner_by_email.get((part.get("email") or "").lower())
            if oid:
                rep_id = f"rep:{oid}"
                break

    return {
        "id": f"hs:{kind}:{obj_id}",
        "source": "hubspot",
        "type": kind,
        "dealId": f"hs:{deal_id}",
        "direction": direction,
        "at": at,
        "durationSec": duration,
        "title": title,
        "body": body or "",
        "transcript": None,
        "notes": notes,
        "summary": summary,
        "participants": participants,
        "repId": rep_id,
        "recordingUrl": recording,
        "meta": meta,
    }


def link_record(interaction_id: str, deal_id: str, type_ids: list[int], at: str) -> dict:
    return {
        "interactionId": interaction_id,
        "dealId": deal_id,
        "method": "crm-association",
        "confidence": 1.0,
        "status": "auto",
        "evidence": {"matchedEmails": [], "domain": None, "matchedHubspotMeeting": None, "titleHit": None,
                     "associationTypeIds": type_ids},
        "candidates": [{"dealId": deal_id, "confidence": 1.0}],
        "at": at,
        "by": "linker",
    }


# ---------------------------------------------------------------------------
# the pull walk
# ---------------------------------------------------------------------------
def window_bounds(cfg: Config) -> tuple[int, int]:
    """Config window -> (start_ms, end_ms) in UTC; `to` is inclusive to the last millisecond of the day."""
    w_from, w_to = cfg.window
    end = parse_iso(w_to) if w_to else None
    if end is None:
        end = _dt.datetime.now(_dt.timezone.utc)
    if w_to and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(w_to).strip()):
        end = end + _dt.timedelta(days=1) - _dt.timedelta(milliseconds=1)
    start = parse_iso(w_from) if w_from else None
    if start is None:
        start = end - _dt.timedelta(days=365)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _type_ids(assoc: dict) -> list[int]:
    ids: list[int] = []
    for t in assoc.get("associationTypes") or []:
        try:
            ids.append(int(t.get("typeId")))
        except (TypeError, ValueError):
            continue
    return ids


def _lastmod_ms(raw: Optional[dict]) -> int:
    if not raw:
        return -1
    p = raw.get("properties") or {}
    return _ms(p.get("hs_lastmodifieddate")) or _ms(raw.get("updatedAt")) or -1


def resolve_owner(client: HubSpotClient, cfg: Config, owner: str) -> tuple[dict, list[dict]]:
    """The HubSpot owner record for an email, or for "me" (config me.email). Returns (owner, all owners)."""
    email = (cfg.get("me.email") or "") if owner.strip().lower() == "me" else owner
    email = (email or "").strip().lower()
    if not email:
        raise HubSpotError("--owner me needs your email in config (me.email); setup asks for it")
    owners = client.owners(archived=False)
    for o in owners:
        if str(o.get("email") or "").strip().lower() == email:
            return o, owners
    raise HubSpotError(f"no HubSpot owner with the email {email}; check the address, or leave --owner off to pull every deal")


def register_pipelines(ctx: "_Context", cfg: Config, hs_cfg: dict, pipelines: list[dict], warnings: list[str],
                       log: Optional[Callable[[str], None]] = None) -> tuple[list[str], list[dict]]:
    """Fill the context with pipeline and stage labels and report stages without a phase mapping.
    Returns (configured pipelines, unmapped stages). Shared by the REST pull and the connector-cache import."""
    log = log or (lambda msg: None)
    for pl in pipelines:
        pid = str(pl.get("id"))
        ctx.pipeline_label[pid] = pl.get("label") or pid
        for st in pl.get("stages") or []:
            sid = str(st.get("id"))
            ctx.stage_label[sid] = st.get("label") or sid
            ctx.stage_pipeline[sid] = pid
    configured_pipelines = [str(p) for p in (hs_cfg.get("pipelines") or []) if p]
    unknown_pipelines = [p for p in configured_pipelines if p not in ctx.pipeline_label]
    if unknown_pipelines:
        warnings.append(f"configured pipelines not found in the portal: {', '.join(unknown_pipelines)}")
    stage_mapping = cfg.get("stagePhases") or {}
    unmapped = [{"pipelineId": ctx.stage_pipeline[s], "stageId": s, "label": l, "suggestedPhase": ctx.phase_of(s)}
                for s, l in ctx.stage_label.items()
                if s not in stage_mapping and (not configured_pipelines or ctx.stage_pipeline[s] in configured_pipelines)]
    log(f"pipelines: {len(pipelines)} ({len(ctx.stage_label)} stages, {len(unmapped)} without a phase mapping)")

    return configured_pipelines, unmapped


def assemble_and_save(store: Store, cfg: Config, ctx: "_Context", *, deal_ids: list[str], deals_raw: dict[str, dict],
                      assoc: dict[str, dict[str, list[dict]]], objects: dict[str, dict[str, dict]],
                      eng_contacts: dict[str, dict[str, list[str]]], contact_company: dict[str, Optional[str]],
                      owners: list[dict], warnings: list[str], log: Callable[[str], None],
                      cache: Optional["HubSpotCache"] = None,
                      fetch_archived_owners: Optional[Callable[[], list[dict]]] = None) -> dict:
    """Turn raw HubSpot objects into canonical records and save them through the store.

    Shared by the REST pull (objects fetched with a token) and the connector-cache import (objects saved
    verbatim from the HubSpot MCP tools). Returns deals, reps, contacts, companies, interaction counts,
    links, validation and the list of files written."""
    # 6. owners
    owners = list(owners)
    referenced = {str((r.get("properties") or {}).get("hubspot_owner_id")) for r in deals_raw.values()}
    for kind in ENGAGEMENT_TYPES:
        referenced |= {str((r.get("properties") or {}).get("hubspot_owner_id")) for r in objects[kind].values()}
    referenced.discard("None")
    referenced.discard("")
    if fetch_archived_owners is not None and referenced - {str(o.get("id")) for o in owners}:
        try:
            owners += fetch_archived_owners()
        except HubSpotError as exc:
            warnings.append(f"archived owners not readable: {exc}")
    if cache is not None:
        cache.write_meta("owners", owners)
    for o in owners:
        ctx.owners[str(o.get("id"))] = o
        if o.get("email"):
            ctx.owner_by_email[str(o["email"]).lower()] = str(o.get("id"))
    ctx.contacts = objects["contacts"]
    ctx.companies = objects["companies"]
    reps = [rep_record(o) for o in owners if str(o.get("id")) in referenced]
    ctx.internal_domains = cfg.internal_domains(reps)
    log(f"owners: {len(owners)} ({len(reps)} referenced)")

    # 7. convert
    deals: list[dict] = []
    for did in deal_ids:
        raw = deals_raw[did]
        c_ids = [str(a.get("toObjectId")) for a in assoc["contacts"].get(did, [])]
        co_ids = [{"id": str(a.get("toObjectId")), "typeIds": _type_ids(a)} for a in assoc["companies"].get(did, [])]
        deals.append(deal_record(raw, ctx, c_ids, co_ids))
    contacts = [contact_record(raw, contact_company.get(cid)) for cid, raw in objects["contacts"].items()]
    companies = [company_record(raw) for raw in objects["companies"].values() if raw.get("id")]
    now = now_iso()
    per_deal: dict[str, list[dict]] = {}
    links: list[dict] = []
    counts = {v: 0 for v in ENGAGEMENT_TYPES.values()}
    for did in deal_ids:
        for kind in ENGAGEMENT_TYPES:
            for a in assoc[kind].get(did, []):
                oid = str(a.get("toObjectId"))
                raw = objects[kind].get(oid)
                if not raw:
                    continue
                rec = interaction_record(kind, raw, did, ctx, eng_contacts[kind].get(oid, []))
                per_deal.setdefault(f"hs:{did}", []).append(rec)
                links.append(link_record(rec["id"], f"hs:{did}", _type_ids(a), now))
                counts[ENGAGEMENT_TYPES[kind]] += 1

    # 8. validate (optional module written separately)
    validation = _validate({"deal": deals, "rep": reps, "contact": contacts, "company": companies,
                            "interaction": [i for items in per_deal.values() for i in items]})

    # 9. save through the store (upsert by id)
    wrote: list[str] = []
    store.save_deals(Store.upsert(store.load_deals(), deals))
    wrote.append("data/deals.json")
    store.save_reps(Store.upsert(store.load_reps(), reps))
    wrote.append("data/reps.json")
    store.save_contacts(Store.upsert(store.load_contacts(), contacts))
    wrote.append("data/contacts.json")
    store.save_companies(Store.upsert(store.load_companies(), companies))
    wrote.append("data/companies.json")
    for deal_id, items in per_deal.items():
        store.save_interactions(deal_id, Store.upsert(store.load_interactions(deal_id), items))
        wrote.append(str(store.interactions_path(deal_id).relative_to(store.home)))
    link_doc = store.load_links()
    existing = {(l.get("interactionId"), l.get("dealId")): l for l in link_doc.get("links", [])}
    for l in links:
        key = (l["interactionId"], l["dealId"])
        old = existing.get(key)
        if old and old.get("status") in ("confirmed", "rejected"):
            continue
        existing[key] = l
    link_doc["links"] = list(existing.values())
    store.save_links(link_doc)
    wrote.append("data/links.json")

    return {"deals": deals, "reps": reps, "contacts": contacts, "companies": companies, "counts": counts,
            "links": links, "validation": validation, "wrote": wrote}


def pull(store: Store, cfg: Optional[Config] = None, since: Optional[str] = None, limit_deals: Optional[int] = None,
         client: Optional[HubSpotClient] = None, log: Optional[Callable[[str], None]] = None,
         owner: Optional[str] = None) -> dict:
    """Walk HubSpot for the configured window and save canonical records through the Store.

    `owner` (an email, or "me" for config me.email) narrows the walk to deals that person owns: what a rep's
    stand-up needs, a fraction of the portal. Returns a summary dict with counts and the request count.
    Raises HubSpotError / ScopeError on API failures.
    """
    cfg = cfg or store.config
    log = log or (lambda msg: None)
    hs_cfg = cfg.get("sources.hubspot") or {}
    if client is None:
        token = resolve_hubspot_token(cfg, store.home)
        if not token:
            raise HubSpotError("no HubSpot token found (see docs/hubspot.md)")
        client = HubSpotClient(token, base_url=hs_cfg.get("baseUrl") or DEFAULT_BASE_URL,
                               rate_per_sec=float(hs_cfg.get("requestsPerSecond") or 4.0))
    store.ensure()
    cache = HubSpotCache(store.cache_dir / "hubspot")
    started = time.time()
    warnings: list[str] = []

    since_ms: Optional[int] = None
    if since:
        since_ms = _ms(since)
        if since_ms is None:
            raise ValueError(f"bad --since value: {since!r} (expected an ISO date)")
    refresh_all = since_ms is not None
    start_ms, end_ms = window_bounds(cfg)
    ctx = _Context(cfg)
    owners_early: Optional[list[dict]] = None
    owner_rec: Optional[dict] = None
    if owner:
        owner_rec, owners_early = resolve_owner(client, cfg, owner)
        log(f"owner: {owner_rec.get('email')} (id {owner_rec.get('id')}), pulling their deals only")

    # 1. pipelines -> stage labels and phases
    pipelines = client.pipelines("deals")
    cache.write_meta("pipelines", pipelines)
    configured_pipelines, unmapped = register_pipelines(ctx, cfg, hs_cfg, pipelines, warnings, log)

    # 2. deal search: closed deals by closedate, open deals by createdate
    base_filters: list[dict] = []
    if configured_pipelines:
        if len(configured_pipelines) == 1:
            base_filters.append({"propertyName": "pipeline", "operator": "EQ", "value": configured_pipelines[0]})
        else:
            base_filters.append({"propertyName": "pipeline", "operator": "IN", "values": configured_pipelines})
    if since_ms is not None:
        base_filters.append({"propertyName": "hs_lastmodifieddate", "operator": "GTE", "value": str(since_ms)})
    if owner_rec is not None:
        base_filters.append({"propertyName": "hubspot_owner_id", "operator": "EQ", "value": str(owner_rec.get("id"))})
    closed = client.search_range("deals", base_filters + [{"propertyName": "hs_is_closed", "operator": "EQ", "value": "true"}],
                                 "closedate", start_ms, end_ms, DEAL_PROPERTIES, max_results=limit_deals)
    open_limit = None if limit_deals is None else max(0, limit_deals - len(closed))
    opened: list[dict] = []
    if open_limit is None or open_limit > 0:
        opened = client.search_range("deals", base_filters + [{"propertyName": "hs_is_closed", "operator": "EQ", "value": "false"}],
                                     "createdate", start_ms, end_ms, DEAL_PROPERTIES, max_results=open_limit)
    found: dict[str, dict] = {}
    for d in closed + opened:
        found.setdefault(str(d.get("id")), d)
    deal_ids = list(found.keys())
    if limit_deals is not None:
        deal_ids = deal_ids[:limit_deals]
    log(f"deals: {len(deal_ids)} in window ({len(closed)} closed, {len(opened)} open)")

    # 3. deal detail with property history (incremental)
    deals_raw: dict[str, dict] = {}
    need: list[str] = []
    deals_from_cache = 0
    for did in deal_ids:
        cached = cache.read("deals", did)
        if cached and not refresh_all and _lastmod_ms(cached) >= _lastmod_ms(found[did]) and cached.get("propertiesWithHistory"):
            deals_raw[did] = cached
            deals_from_cache += 1
        else:
            need.append(did)
    for raw in client.batch_read("deals", need, DEAL_PROPERTIES, properties_with_history=DEAL_HISTORY_PROPERTIES):
        did = str(raw.get("id"))
        cache.write("deals", did, raw, DEAL_PROPERTIES)
        deals_raw[did] = raw
    missing = [d for d in deal_ids if d not in deals_raw]
    if missing:
        warnings.append(f"{len(missing)} deals from search were not returned by batch read (archived?)")
    deal_ids = [d for d in deal_ids if d in deals_raw]
    log(f"deal detail: {len(deals_raw) - deals_from_cache} fetched, {deals_from_cache} from cache")

    # 4. deal associations
    assoc: dict[str, dict[str, list[dict]]] = {}
    for to_type in ("contacts", "companies", "calls", "emails", "meetings", "notes"):
        assoc[to_type] = client.batch_associations("deals", to_type, deal_ids) if deal_ids else {}
        cache.write_meta(f"associations/deals-{to_type}", assoc[to_type])
    contact_ids = sorted({str(a.get("toObjectId")) for m in assoc["contacts"].values() for a in m})
    company_ids = sorted({str(a.get("toObjectId")) for m in assoc["companies"].values() for a in m})
    engagement_ids = {t: sorted({str(a.get("toObjectId")) for m in assoc[t].values() for a in m}) for t in ENGAGEMENT_TYPES}
    log("associations: " + ", ".join(f"{len(engagement_ids[t])} {t}" for t in ENGAGEMENT_TYPES)
        + f", {len(contact_ids)} contacts, {len(company_ids)} companies")

    # 5. object bodies (incremental: cached ids are skipped unless --since)
    email_props = EMAIL_PROPERTIES + (EMAIL_BODY_PROPERTIES if ctx.email_bodies else [])
    meeting_props = MEETING_PROPERTIES + ([MEETING_INTERNAL_NOTES] if ctx.internal_notes else [])
    prop_sets = {"contacts": CONTACT_PROPERTIES, "companies": COMPANY_PROPERTIES, "calls": CALL_PROPERTIES,
                 "emails": email_props, "meetings": meeting_props, "notes": NOTE_PROPERTIES}
    objects: dict[str, dict[str, dict]] = {}
    fetched = 0
    from_cache = 0
    for kind, ids in (("contacts", contact_ids), ("companies", company_ids), *engagement_ids.items()):
        objects[kind] = {}
        need = []
        for oid in ids:
            cached = None if refresh_all else cache.read(kind, oid)
            if cached and _has_properties(cached, prop_sets[kind]):
                objects[kind][oid] = cached
                from_cache += 1
            else:
                need.append(oid)
        for raw in client.batch_read(kind, need, prop_sets[kind]):
            oid = str(raw.get("id"))
            cache.write(kind, oid, raw, prop_sets[kind])
            objects[kind][oid] = raw
            fetched += 1
    log(f"objects: {fetched} fetched, {from_cache} from cache")

    # 5b. engagement -> contacts (participants) and contacts -> companies
    eng_contacts: dict[str, dict[str, list[str]]] = {}
    for kind in ENGAGEMENT_TYPES:
        ids = list(objects[kind].keys())
        m = client.batch_associations(kind, "contacts", ids) if ids else {}
        eng_contacts[kind] = {k: [str(a.get("toObjectId")) for a in v] for k, v in m.items()}
    contact_company: dict[str, Optional[str]] = {}
    if objects["contacts"]:
        m = client.batch_associations("contacts", "companies", list(objects["contacts"].keys()))
        for cid, tos in m.items():
            primary = None
            for a in tos:
                if 1 in _type_ids(a):
                    primary = str(a.get("toObjectId"))
                    break
            if primary is None and tos:
                primary = str(tos[0].get("toObjectId"))
            contact_company[cid] = primary
    extra_company_ids = [c for c in set(contact_company.values()) if c and c not in objects["companies"]]
    if extra_company_ids:
        need = [c for c in extra_company_ids if refresh_all or not cache.has("companies", c)]
        for c in extra_company_ids:
            if c not in need:
                objects["companies"][c] = cache.read("companies", c) or {}
        for raw in client.batch_read("companies", need, COMPANY_PROPERTIES):
            cache.write("companies", str(raw.get("id")), raw, COMPANY_PROPERTIES)
            objects["companies"][str(raw.get("id"))] = raw

    # 6 to 9. owners, convert, validate, save (shared with the connector-cache import)
    owners = owners_early if owners_early is not None else client.owners(archived=False)
    built = assemble_and_save(store, cfg, ctx, deal_ids=deal_ids, deals_raw=deals_raw, assoc=assoc, objects=objects,
                              eng_contacts=eng_contacts, contact_company=contact_company, owners=owners,
                              warnings=warnings, log=log, cache=cache,
                              fetch_archived_owners=lambda: client.owners(archived=True))
    deals, reps, contacts, companies = built["deals"], built["reps"], built["contacts"], built["companies"]
    counts, links, validation, wrote = built["counts"], built["links"], built["validation"], built["wrote"]

    summary = {
        "ok": True,
        "source": "hubspot",
        "baseUrl": client.base_url,
        "window": {"from": cfg.window[0], "to": cfg.window[1]},
        "since": since,
        "owner": {"email": owner_rec.get("email"), "id": str(owner_rec.get("id"))} if owner_rec else None,
        "pipelines": [{"id": pid, "label": lbl} for pid, lbl in ctx.pipeline_label.items()],
        "counts": {"deals": len(deals), "contacts": len(contacts), "companies": len(companies), "reps": len(reps),
                   "interactions": counts, "links": len(links)},
        "cache": {"dealsFromCache": deals_from_cache, "objectsFromCache": from_cache, "objectsFetched": fetched},
        "unmappedStages": unmapped,
        "requests": client.request_count,
        "retries": client.retry_count,
        "warnings": warnings,
        "validation": validation,
        "wrote": wrote,
        "durationMs": int((time.time() - started) * 1000),
    }
    return summary


def _has_properties(raw: dict, wanted: list[str]) -> bool:
    """A cached object is usable when it was fetched with at least the properties we want now.

    HubSpot may omit null-valued properties, so the list of requested properties is stored with the raw object
    (`_flowsales.properties`); older cache files fall back to a key check.
    """
    requested = ((raw.get("_flowsales") or {}).get("properties")) or []
    if requested:
        return set(wanted) <= set(requested)
    props = raw.get("properties") or {}
    return all(k in props for k in wanted)


def _validate(collections: dict[str, list[dict]]) -> Optional[dict]:
    try:
        from ..schema.validate import validate_records  # type: ignore
    except Exception:  # noqa: BLE001 - module written separately; absent is fine
        return None
    report: dict[str, Any] = {}
    for kind, records in collections.items():
        try:
            report[kind] = validate_records(kind, records)
        except Exception as exc:  # noqa: BLE001
            report[kind] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return report
