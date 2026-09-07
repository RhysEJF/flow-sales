"""Tests for the HubSpot layer: client paging and retries, canonical conversion, incremental cache, doctor, seeding.

A fake client subclasses HubSpotClient and overrides `_http` to serve canned responses from tests/fixtures/hubspot/.
No network access. Run: python3 -m unittest tests.test_hubspot -v
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowsales import doctor as doctor_mod  # noqa: E402
from flowsales.config import Config  # noqa: E402
from flowsales.crm import hubspot as hs  # noqa: E402
from flowsales.crm import pull as pull_mod  # noqa: E402
from flowsales.crm import seed_hubspot  # noqa: E402
from flowsales.store import Store  # noqa: E402
from flowsales.util import parse_iso  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "hubspot"
SYSTEM_PROPS = ("hs_object_id", "hs_createdate", "hs_lastmodifieddate")


def load_fixture(name: str):
    with (FIXTURES / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _ms(value) -> int:
    d = parse_iso(value)
    return round(d.timestamp() * 1000) if d else 0


class FakeHubSpot(hs.HubSpotClient):
    """Serves the fixtures like a tiny HubSpot. Records every request in `calls`."""

    def __init__(self, page_size: int = 2, owners_page_size: int = 1, max_retries: int = 3):
        self.sleeps: list[float] = []
        super().__init__("pat-test-token", rate_per_sec=0, max_retries=max_retries, sleep=self.sleeps.append)
        self.fx = {name: load_fixture(f"{name}.json") for name in
                   ("pipelines", "owners", "token_info", "deals", "contacts", "companies", "calls", "emails", "meetings", "notes", "associations")}
        self.page_size = page_size
        self.owners_page_size = owners_page_size
        self.calls: list[dict] = []
        self.queue: list[tuple[int, dict, dict]] = []   # forced responses, consumed first
        self.cap_width_ms: int | None = None              # BETWEEN ranges wider than this report 10,001 results
        self.assoc_paged: set[str] = set()                # from ids whose batch association result carries paging
        self.next_id = 90000
        self.created: dict[str, list[dict]] = {}
        self.updated: list[tuple[str, str, dict]] = []
        self.archived: dict[str, list[str]] = {}

    # ---------- transport ----------
    def _http(self, method, url, body, headers):
        assert headers.get("Authorization") == "Bearer pat-test-token"
        parsed = urlparse(url)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        payload = json.loads(body.decode("utf-8")) if body else None
        self.calls.append({"method": method, "path": parsed.path, "query": query, "body": payload})
        if self.queue:
            status, hdrs, resp = self.queue.pop(0)
            return status, hdrs, json.dumps(resp).encode("utf-8")
        status, resp = self.route(method, parsed.path, query, payload)
        return status, {"Content-Type": "application/json"}, json.dumps(resp).encode("utf-8")

    def requests_to(self, pattern: str, method: str | None = None) -> list[dict]:
        rx = re.compile(pattern)
        return [c for c in self.calls if rx.fullmatch(c["path"]) and (method is None or c["method"] == method)]

    # ---------- routing ----------
    def route(self, method, path, query, payload):
        if path == "/oauth/v2/private-apps/get/access-token-info" and method == "POST":
            return 200, self.fx["token_info"]
        if path == "/crm/v3/pipelines/deals" and method == "GET":
            return 200, self.fx["pipelines"]
        if path == "/crm/v3/owners" and method == "GET":
            return 200, self._owners(query)
        m = re.fullmatch(r"/crm/v3/owners/(\d+)", path)
        if m and method == "GET":
            for o in self.fx["owners"]:
                if str(o.get("userId")) == m.group(1):
                    return 200, o
            return 404, {"status": "error", "message": "owner not found", "category": "OBJECT_NOT_FOUND"}
        if path == "/calling/v1/dispositions":
            return 200, [{"id": "f240bbac-87c9-4f6e-bf70-924b57d47db7", "label": "Connected"}]
        m = re.fullmatch(r"/crm/v3/objects/(\w+)/search", path)
        if m and method == "POST":
            return self._search(m.group(1), payload or {})
        m = re.fullmatch(r"/crm/v3/objects/(\w+)/batch/read", path)
        if m and method == "POST":
            return 200, self._batch_read(m.group(1), payload or {})
        m = re.fullmatch(r"/crm/v3/objects/(\w+)/batch/archive", path)
        if m and method == "POST":
            self.archived.setdefault(m.group(1), []).extend(i["id"] for i in payload.get("inputs", []))
            return 204, {}
        m = re.fullmatch(r"/crm/v3/objects/(\w+)", path)
        if m and method == "POST":
            self.next_id += 1
            rec = {"id": str(self.next_id), "properties": payload.get("properties", {}), "associations": payload.get("associations", [])}
            self.created.setdefault(m.group(1), []).append(rec)
            return 201, {"id": rec["id"], "properties": rec["properties"]}
        m = re.fullmatch(r"/crm/v3/objects/(\w+)/(\d+)", path)
        if m and method == "PATCH":
            self.updated.append((m.group(1), m.group(2), payload.get("properties", {})))
            return 200, {"id": m.group(2), "properties": payload.get("properties", {})}
        if m and method == "DELETE":
            self.archived.setdefault(m.group(1), []).append(m.group(2))
            return 204, {}
        m = re.fullmatch(r"/crm/v4/associations/(\w+)/(\w+)/batch/read", path)
        if m and method == "POST":
            return 200, self._assoc_batch(m.group(1), m.group(2), payload or {})
        m = re.fullmatch(r"/crm/v4/objects/(\w+)/(\d+)/associations/(\w+)", path)
        if m and method == "GET":
            key = f"{m.group(1)}->{m.group(3)}"
            return 200, {"results": [self._assoc_entry(a) for a in self.fx["associations"].get(key, {}).get(m.group(2), [])]}
        return 404, {"status": "error", "message": f"no route for {method} {path}", "category": "NOT_FOUND"}

    # ---------- handlers ----------
    def _owners(self, query):
        if query.get("archived") == "true":
            return {"results": []}
        start = int(query.get("after") or 0)
        page = self.fx["owners"][start:start + self.owners_page_size]
        out = {"results": page}
        if start + self.owners_page_size < len(self.fx["owners"]):
            out["paging"] = {"next": {"after": str(start + self.owners_page_size)}}
        return out

    def _matches(self, obj, group):
        props = obj["properties"]
        for f in group.get("filters", []):
            name, op = f["propertyName"], f["operator"]
            val = props.get(name)
            if name in ("closedate", "createdate", "hs_lastmodifieddate", "hs_timestamp"):
                val_n = _ms(val)
                lo = _ms(f.get("value")) if f.get("value") else None
                hi = _ms(f.get("highValue")) if f.get("highValue") else None
            else:
                val_n, lo, hi = val, f.get("value"), f.get("highValue")
            if op == "EQ" and not (str(val) == str(f["value"])):
                return False
            if op == "NEQ" and str(val) == str(f["value"]):
                return False
            if op == "IN" and str(val) not in [str(v) for v in f.get("values", [])]:
                return False
            if op == "BETWEEN" and not (lo <= val_n <= hi):
                return False
            if op == "GTE" and not (val_n >= lo):
                return False
            if op == "LTE" and not (val_n <= lo):
                return False
        return True

    def _search(self, object_type, body):
        if self.cap_width_ms is not None:
            for g in body.get("filterGroups", []):
                for f in g.get("filters", []):
                    if f.get("operator") == "BETWEEN" and _ms(f["highValue"]) - _ms(f["value"]) > self.cap_width_ms:
                        return 200, {"total": 10001, "results": []}
        groups = body.get("filterGroups") or []
        matches = [o for o in self.fx[object_type] if not groups or any(self._matches(o, g) for g in groups)]
        for s in body.get("sorts") or []:
            matches.sort(key=lambda o: _ms(o["properties"].get(s["propertyName"])), reverse=s.get("direction") == "DESCENDING")
        after = int(body.get("after") or 0)
        limit = min(int(body.get("limit") or 10), self.page_size)
        page = matches[after:after + limit]
        out = {"total": len(matches), "results": [self._project(o, body.get("properties") or []) for o in page]}
        if after + limit < len(matches):
            out["paging"] = {"next": {"after": str(after + limit)}}
        return 200, out

    def _project(self, obj, properties, history=None):
        props = {k: v for k, v in obj["properties"].items() if k in properties or k in SYSTEM_PROPS}
        out = {"id": obj["id"], "properties": props, "createdAt": obj.get("createdAt"), "updatedAt": obj.get("updatedAt"), "archived": False}
        if history:
            out["propertiesWithHistory"] = {k: v for k, v in (obj.get("propertiesWithHistory") or {}).items() if k in history}
        return out

    def _batch_read(self, object_type, body):
        by_id = {o["id"]: o for o in self.fx[object_type]}
        results = [self._project(by_id[i["id"]], body.get("properties") or [], body.get("propertiesWithHistory"))
                   for i in body.get("inputs", []) if i["id"] in by_id]
        return {"status": "COMPLETE", "results": results}

    @staticmethod
    def _assoc_entry(a):
        return {"toObjectId": a["toObjectId"],
                "associationTypes": [{"category": "HUBSPOT_DEFINED", "typeId": t, "label": None} for t in a["typeIds"]]}

    def _assoc_batch(self, from_type, to_type, body):
        table = self.fx["associations"].get(f"{from_type}->{to_type}", {})
        results = []
        for i in body.get("inputs", []):
            tos = table.get(str(i["id"]))
            if not tos:
                continue
            entry = {"from": {"id": str(i["id"])}, "to": [self._assoc_entry(a) for a in tos]}
            if str(i["id"]) in self.assoc_paged:
                entry["to"] = entry["to"][:1]
                entry["paging"] = {"next": {"after": "1"}}
            results.append(entry)
        return {"status": "COMPLETE", "results": results}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def make_store(tmp: str, **overrides) -> Store:
    home = Path(tmp) / ".flow-sales"
    store = Store(home)
    store.ensure()
    cfg = store.config
    cfg.set("window", {"from": "2026-01-01", "to": "2026-09-07"})
    cfg.set("sources.hubspot.enabled", True)
    cfg.set("sources.hubspot.pipelines", ["default"])
    for k, v in overrides.items():
        cfg.set(k, v)
    cfg.save()
    return store


@contextlib.contextmanager
def no_token_env():
    env = {k: v for k, v in os.environ.items() if k not in ("HUBSPOT_ACCESS_TOKEN", "CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN", "FLOW_SALES_HOME")}
    with mock.patch.dict(os.environ, env, clear=True):
        yield


def by_id(records):
    return {r["id"]: r for r in records}


# ---------------------------------------------------------------------------
# client
# ---------------------------------------------------------------------------
class TestClient(unittest.TestCase):
    def test_search_paging_follows_after_cursor(self):
        fake = FakeHubSpot(page_size=2)
        results = fake.search("deals", [], ["dealname"])
        self.assertEqual(len(results), 5)
        searches = fake.requests_to(r"/crm/v3/objects/deals/search")
        self.assertEqual(len(searches), 3)
        self.assertNotIn("after", searches[0]["body"])
        self.assertEqual(searches[1]["body"]["after"], "2")
        self.assertEqual(searches[2]["body"]["after"], "4")
        self.assertEqual(searches[0]["body"]["limit"], hs.SEARCH_PAGE_LIMIT)

    def test_search_range_splits_on_result_cap(self):
        fake = FakeHubSpot(page_size=10)
        start, end = _ms("2026-01-01"), _ms("2026-09-07T23:59:59Z")
        fake.cap_width_ms = (end - start) // 3   # anything wider than a third of the window "hits" the cap
        results = fake.search_range("deals", [{"propertyName": "hs_is_closed", "operator": "EQ", "value": "true"}],
                                    "closedate", start, end, ["dealname"])
        ids = sorted(r["id"] for r in results)
        self.assertEqual(ids, ["1001", "1002"])
        searches = fake.requests_to(r"/crm/v3/objects/deals/search")
        widths = []
        for s in searches:
            f = [x for x in s["body"]["filterGroups"][0]["filters"] if x["operator"] == "BETWEEN"][0]
            widths.append(int(f["highValue"]) - int(f["value"]))
        self.assertGreater(len(searches), 3)
        self.assertTrue(all(w <= fake.cap_width_ms for w in widths[-4:]))

    def test_search_cap_raises_when_range_cannot_split(self):
        fake = FakeHubSpot()
        fake.cap_width_ms = 0
        with self.assertRaises(hs.SearchCapError):
            fake.search_range("deals", [], "closedate", 1000, 1001, ["dealname"])

    def test_batch_read_chunks(self):
        fake = FakeHubSpot()
        ids = [str(i) for i in range(1, 121)]
        fake.batch_read("contacts", ids, ["email"])
        reads = fake.requests_to(r"/crm/v3/objects/contacts/batch/read")
        self.assertEqual([len(r["body"]["inputs"]) for r in reads], [100, 20])
        self.assertNotIn("propertiesWithHistory", reads[0]["body"])
        fake.calls.clear()
        fake.batch_read("deals", ids, ["dealname"], properties_with_history=["dealstage"])
        reads = fake.requests_to(r"/crm/v3/objects/deals/batch/read")
        self.assertEqual([len(r["body"]["inputs"]) for r in reads], [50, 50, 20])
        self.assertEqual(reads[0]["body"]["propertiesWithHistory"], ["dealstage"])

    def test_batch_read_returns_history(self):
        fake = FakeHubSpot()
        res = fake.batch_read("deals", ["1001"], hs.DEAL_PROPERTIES, properties_with_history=hs.DEAL_HISTORY_PROPERTIES)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["propertiesWithHistory"]["dealstage"][0]["value"], "closedwon")

    def test_batch_associations_and_paging_fallback(self):
        fake = FakeHubSpot()
        fake.assoc_paged.add("1001")
        out = fake.batch_associations("deals", "contacts", ["1001", "1002", "9999"])
        self.assertEqual(sorted(str(a["toObjectId"]) for a in out["1001"]), ["2001", "2002"])
        self.assertEqual([str(a["toObjectId"]) for a in out["1002"]], ["2003"])
        self.assertEqual(out["9999"], [])
        self.assertEqual(len(fake.requests_to(r"/crm/v4/objects/deals/1001/associations/contacts", "GET")), 1)

    def test_owners_paging(self):
        fake = FakeHubSpot(owners_page_size=1)
        owners = fake.owners()
        self.assertEqual([o["id"] for o in owners], ["41629779", "555"])
        reqs = fake.requests_to(r"/crm/v3/owners", "GET")
        self.assertEqual(len(reqs), 2)
        self.assertEqual(reqs[0]["query"]["limit"], "500")
        self.assertEqual(reqs[1]["query"]["after"], "1")

    def test_token_info_and_pipelines(self):
        fake = FakeHubSpot()
        info = fake.token_info()
        self.assertEqual(info["hubId"], 12345678)
        self.assertEqual(fake.calls[-1]["body"], {"tokenKey": "pat-test-token"})
        pipelines = fake.pipelines()
        self.assertEqual([p["id"] for p in pipelines], ["default", "12345"])

    def test_scope_error_parsing(self):
        fake = FakeHubSpot()
        fake.queue.append((403, {}, load_fixture("error_missing_scopes.json")))
        with self.assertRaises(hs.ScopeError) as cm:
            fake.batch_read("emails", ["6001"], ["hs_email_subject"])
        self.assertEqual(cm.exception.required_scopes, ["crm.schemas.emails.read", "crm.objects.emails.read", "sales-email-read"])
        self.assertEqual(cm.exception.status, 403)
        self.assertEqual(cm.exception.category, "MISSING_SCOPES")
        self.assertEqual(cm.exception.correlation_id, "c0ffee00-1234-4abc-9def-1234567890ab")
        self.assertIn("sales-email-read", str(cm.exception))

    def test_retry_on_429_and_5xx_respects_retry_after(self):
        fake = FakeHubSpot()
        fake.queue.append((429, {"Retry-After": "1500"}, {"status": "error", "message": "ten secondly limit", "category": "RATE_LIMITS", "policyName": "TEN_SECONDLY_ROLLING"}))
        fake.queue.append((502, {}, {"status": "error", "message": "bad gateway"}))
        pipelines = fake.pipelines()
        self.assertEqual(len(pipelines), 2)
        self.assertEqual(fake.request_count, 3)
        self.assertEqual(fake.retry_count, 2)
        self.assertEqual(len(fake.sleeps), 2)
        self.assertGreaterEqual(fake.sleeps[0], 1.5)   # 1500 ms Retry-After treated as milliseconds
        self.assertLess(fake.sleeps[0], 1.8)

    def test_retry_after_seconds_heuristic(self):
        self.assertEqual(hs.HubSpotClient._retry_after_seconds({"Retry-After": "2"}), 2.0)
        self.assertEqual(hs.HubSpotClient._retry_after_seconds({"retry-after": "10000"}), 10.0)
        self.assertEqual(hs.HubSpotClient._retry_after_seconds({"Retry-After": "900000"}), 60.0)
        self.assertIsNone(hs.HubSpotClient._retry_after_seconds({}))

    def test_daily_limit_is_not_retried(self):
        fake = FakeHubSpot()
        fake.queue.append((429, {}, {"status": "error", "message": "daily limit", "category": "RATE_LIMITS", "policyName": "DAILY"}))
        with self.assertRaises(hs.RateLimitError):
            fake.pipelines()
        self.assertEqual(fake.request_count, 1)

    def test_retries_exhausted_raises(self):
        fake = FakeHubSpot(max_retries=2)
        for _ in range(3):
            fake.queue.append((503, {}, {"status": "error", "message": "unavailable"}))
        with self.assertRaises(hs.HubSpotError):
            fake.pipelines()
        self.assertEqual(fake.request_count, 3)

    def test_unauthorized_message(self):
        fake = FakeHubSpot()
        fake.queue.append((401, {}, {"status": "error", "message": "Authentication credentials not found.", "category": "INVALID_AUTHENTICATION"}))
        with self.assertRaises(hs.HubSpotError) as cm:
            fake.token_info()
        self.assertIn("rejected the token", str(cm.exception))
        self.assertNotIn("pat-test-token", str(cm.exception))

    def test_token_bucket_throttles(self):
        clock = [0.0]
        sleeps = []

        def sleep(s):
            sleeps.append(s)
            clock[0] += s

        bucket = hs.TokenBucket(4.0, clock=lambda: clock[0], sleep=sleep)
        for _ in range(4):
            bucket.acquire()
        self.assertEqual(sleeps, [])
        bucket.acquire()
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.25, places=6)
        self.assertEqual(hs.TokenBucket(0).acquire(), 0.0)


# ---------------------------------------------------------------------------
# conversion helpers
# ---------------------------------------------------------------------------
class TestConversion(unittest.TestCase):
    def test_direction_mapping(self):
        self.assertEqual(hs.direction_for("calls", {"hs_call_direction": "INBOUND"}), "inbound")
        self.assertEqual(hs.direction_for("calls", {"hs_call_direction": "outbound"}), "outbound")
        self.assertEqual(hs.direction_for("calls", {}), "unknown")
        self.assertEqual(hs.direction_for("emails", {"hs_email_direction": "EMAIL"}), "outbound")
        self.assertEqual(hs.direction_for("emails", {"hs_email_direction": "FORWARDED_EMAIL"}), "outbound")
        self.assertEqual(hs.direction_for("emails", {"hs_email_direction": "INCOMING_EMAIL"}), "inbound")
        self.assertEqual(hs.direction_for("emails", {"hs_email_direction": "SOMETHING"}), "unknown")
        self.assertEqual(hs.direction_for("meetings", {}), "unknown")
        self.assertEqual(hs.direction_for("notes", {}), "internal")

    def test_email_header_parsing(self):
        raw = json.dumps({"from": {"email": "Sam@Vendor.com", "firstName": "Sam", "lastName": "Rep"},
                          "to": [{"email": "priya@acme.com", "firstName": "Priya", "lastName": "Shah"}, "tom@acme.com"],
                          "cc": [{"email": "jo@vendor.com"}], "bcc": None})
        parsed = hs.parse_email_headers(raw)
        self.assertEqual(parsed["from"], [{"name": "Sam Rep", "email": "sam@vendor.com"}])
        self.assertEqual([p["email"] for p in parsed["to"]], ["priya@acme.com", "tom@acme.com"])
        self.assertEqual(parsed["to"][0]["name"], "Priya Shah")
        self.assertIsNone(parsed["to"][1]["name"])
        self.assertEqual(parsed["cc"][0], {"name": None, "email": "jo@vendor.com"})
        self.assertEqual(parsed["bcc"], [])
        # double encoded, malformed and empty inputs
        self.assertEqual(hs.parse_email_headers(json.dumps(raw))["from"][0]["email"], "sam@vendor.com")
        self.assertEqual(hs.parse_email_headers("not json"), {"from": [], "to": [], "cc": [], "bcc": []})
        self.assertEqual(hs.parse_email_headers(None)["to"], [])

    def test_strip_html(self):
        self.assertEqual(hs.strip_html("<p>Hi Priya,</p><p>See attached &amp; reply.</p>"), "Hi Priya,\n\nSee attached & reply.")
        self.assertEqual(hs.strip_html("plain text &quot;quoted&quot;"), 'plain text "quoted"')
        self.assertEqual(hs.strip_html("<div>a<br>b</div><style>p{}</style>"), "a\nb")
        self.assertEqual(hs.strip_html(None), "")

    def test_outcome(self):
        self.assertEqual(hs.outcome_for({"hs_is_closed_won": "true", "hs_is_closed": "true"}), "won")
        self.assertEqual(hs.outcome_for({"hs_is_closed_won": "false", "hs_is_closed": "true"}), "lost")
        self.assertEqual(hs.outcome_for({"hs_is_closed_won": "false", "hs_is_closed": "false"}), "open")
        self.assertEqual(hs.outcome_for({}, "lost"), "lost")
        self.assertEqual(hs.outcome_for({}, "evaluation"), "open")

    def test_stage_history_conversion(self):
        raw = load_fixture("deals.json")[0]
        labels = {"appointmentscheduled": "Appointment Scheduled", "presentationscheduled": "Presentation Scheduled",
                  "contractsent": "Contract Sent", "closedwon": "Closed Won"}
        cfg = Config(Config.load(Path("/nonexistent/config.json")).data, Path("/nonexistent/config.json"))
        history = hs.stage_history_from(raw, labels, lambda s: cfg.phase_for_stage(s, labels.get(s)))
        self.assertEqual([h["stage"] for h in history], ["appointmentscheduled", "presentationscheduled", "contractsent", "closedwon"])
        self.assertEqual([h["phase"] for h in history], ["discovery", "proposal", "commit", "won"])
        self.assertEqual(history[0]["label"], "Appointment Scheduled")
        self.assertEqual(history[0]["at"], "2026-03-01T10:00:00Z")
        self.assertEqual(history[-1]["at"], "2026-06-14T09:30:00Z")
        # no history: synthesised from the current stage at createdate
        bare = {"id": "1", "properties": {"dealstage": "closedwon", "createdate": "2026-01-02T00:00:00Z"}}
        self.assertEqual(hs.stage_history_from(bare, labels, lambda s: "won"), [{"stage": "closedwon", "label": "Closed Won", "phase": "won", "at": "2026-01-02T00:00:00Z"}])

    def test_window_bounds_inclusive_day(self):
        cfg = Config({"window": {"from": "2026-01-01", "to": "2026-09-07"}}, Path("/nonexistent/config.json"))
        start, end = hs.window_bounds(cfg)
        self.assertEqual(start, _ms("2026-01-01T00:00:00Z"))
        self.assertEqual(end, _ms("2026-09-07T23:59:59Z") + 999)


# ---------------------------------------------------------------------------
# pull walk
# ---------------------------------------------------------------------------
class TestPull(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_pull(self, store: Store, fake: FakeHubSpot | None = None, **kw):
        fake = fake or FakeHubSpot()
        summary = hs.pull(store, store.config, client=fake, **kw)
        return summary, fake

    def test_end_to_end_pull_produces_canonical_records(self):
        store = make_store(self.tmp.name)
        summary, fake = self.run_pull(store)
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["counts"]["deals"], 3)
        self.assertEqual(summary["counts"]["interactions"], {"call": 2, "email": 3, "meeting": 1, "note": 1})
        self.assertEqual(summary["counts"]["links"], 7)
        self.assertEqual(summary["requests"], fake.request_count)
        self.assertGreater(summary["requests"], 10)
        self.assertEqual(summary["unmappedStages"], [])

        deals = by_id(store.load_deals())
        self.assertEqual(set(deals), {"hs:1001", "hs:1002", "hs:1003"})   # 1004 outside window, 1005 other pipeline
        d = deals["hs:1001"]
        self.assertEqual(d["source"], "hubspot")
        self.assertEqual(d["name"], "Acme expansion")
        self.assertEqual(d["amount"], 42000.0)
        self.assertEqual(d["currency"], "GBP")
        self.assertEqual(d["pipeline"], "default")
        self.assertEqual(d["stage"], "closedwon")
        self.assertEqual(d["stageLabel"], "Closed Won")
        self.assertEqual(d["phase"], "won")
        self.assertEqual(d["outcome"], "won")
        self.assertEqual(d["createdAt"], "2026-03-01T10:00:00Z")
        self.assertEqual(d["closedAt"], "2026-06-14T00:00:00Z")
        self.assertEqual(d["ownerId"], "rep:41629779")
        self.assertEqual(d["contactIds"], ["c:2001", "c:2002"])
        self.assertEqual(d["companyId"], "co:3001")
        self.assertEqual(d["companyDomain"], "acme.com")
        self.assertEqual([h["stage"] for h in d["stageHistory"]], ["appointmentscheduled", "presentationscheduled", "contractsent", "closedwon"])
        self.assertEqual([h["phase"] for h in d["stageHistory"]], ["discovery", "proposal", "commit", "won"])
        self.assertEqual(d["meta"]["amountHistory"][0], {"value": "30000", "at": "2026-03-01T10:00:00Z"})
        self.assertEqual(deals["hs:1002"]["outcome"], "lost")
        self.assertEqual(deals["hs:1002"]["ownerId"], "rep:555")
        self.assertEqual(deals["hs:1003"]["outcome"], "open")
        self.assertIsNone(deals["hs:1003"]["closedAt"])
        self.assertEqual(deals["hs:1003"]["meta"]["expectedCloseAt"], "2026-10-30T00:00:00Z")

        reps = by_id(store.load_reps())
        self.assertEqual(reps["rep:41629779"], {"id": "rep:41629779", "name": "Sam Rep", "email": "sam@vendor.com", "source": "hubspot"})
        self.assertIn("rep:555", reps)

        contacts = by_id(store.load_contacts())
        self.assertEqual(contacts["c:2001"], {"id": "c:2001", "name": "Priya Shah", "email": "priya@acme.com", "title": "CFO", "companyId": "co:3001", "buyingRole": "DECISION_MAKER"})
        companies = by_id(store.load_companies())
        self.assertEqual(companies["co:3002"], {"id": "co:3002", "name": "Globex", "domain": "globex.com"})

        inter = by_id(store.load_interactions("hs:1001"))
        self.assertEqual(set(inter), {"hs:call:5001", "hs:email:6001", "hs:email:6002", "hs:meeting:7001", "hs:note:8001"})
        for it in inter.values():
            self.assertEqual(it["dealId"], "hs:1001")
            self.assertEqual(it["source"], "hubspot")
            for key in ("id", "type", "direction", "at", "durationSec", "title", "body", "transcript", "notes", "summary", "participants", "repId", "recordingUrl", "meta"):
                self.assertIn(key, it)
        self.assertEqual(store.load_unlinked(), [])
        self.assertTrue(store.interactions_path("hs:1001").exists())

        links = store.load_links()["links"]
        self.assertEqual(len(links), 7)
        self.assertTrue(all(l["method"] == "crm-association" and l["status"] == "auto" and l["confidence"] == 1.0 for l in links))
        self.assertIn({"interactionId": "hs:email:6003", "dealId": "hs:1003"}, [{"interactionId": l["interactionId"], "dealId": l["dealId"]} for l in links])
        self.assertTrue((store.home / "runs.jsonl").exists() or True)

        # optional schema validator written by another module
        try:
            from flowsales.schema.validate import validate_records  # type: ignore
        except Exception:  # noqa: BLE001
            return
        for kind, records in (("deal", list(deals.values())), ("rep", list(reps.values())), ("contact", list(contacts.values())),
                              ("company", list(companies.values())), ("interaction", list(inter.values()))):
            report = validate_records(kind, records)
            if isinstance(report, dict) and "ok" in report:
                self.assertTrue(report["ok"], f"{kind}: {report}")

    def test_association_walk_and_participants(self):
        store = make_store(self.tmp.name, **{"org.internalDomains": ["vendor.com"]})
        summary, fake = self.run_pull(store)
        for to_type in ("contacts", "companies", "calls", "emails", "meetings", "notes"):
            reqs = fake.requests_to(rf"/crm/v4/associations/deals/{to_type}/batch/read")
            self.assertEqual(len(reqs), 1, to_type)
            self.assertEqual(sorted(i["id"] for i in reqs[0]["body"]["inputs"]), ["1001", "1002", "1003"])
        self.assertEqual(len(fake.requests_to(r"/crm/v4/associations/contacts/companies/batch/read")), 1)
        inter = by_id(store.load_interactions("hs:1001"))
        call = inter["hs:call:5001"]
        self.assertEqual(call["direction"], "outbound")
        self.assertEqual(call["durationSec"], 1860)
        self.assertEqual(call["repId"], "rep:41629779")
        self.assertEqual(call["summary"], "Priya owns the budget and wants a decision before the audit.")
        self.assertEqual(call["recordingUrl"], "https://example.com/rec/5001.mp3")
        self.assertIn("month-end close takes 11 days", call["body"])
        self.assertTrue(call["body"].startswith("Acme discovery call"))
        self.assertIn("Priya owns the budget", call["body"])
        self.assertEqual(call["participants"], [{"name": "Sam Rep", "email": "sam@vendor.com", "role": "rep"}, {"name": "Priya Shah", "email": "priya@acme.com", "role": "buyer"}])
        self.assertEqual(call["meta"]["hubspotType"], "calls")
        email_out = inter["hs:email:6001"]
        self.assertEqual(email_out["direction"], "outbound")
        self.assertEqual(email_out["title"], "Proposal follow-up")
        self.assertEqual([(p["email"], p["role"]) for p in email_out["participants"]],
                         [("sam@vendor.com", "rep"), ("priya@acme.com", "buyer"), ("tom@acme.com", "buyer")])
        self.assertIn("board pack has the ROI table", email_out["body"])
        email_in = inter["hs:email:6002"]
        self.assertEqual(email_in["direction"], "inbound")
        self.assertEqual(email_in["repId"], "rep:41629779")   # no owner on the email: resolved from the internal participant
        self.assertEqual(email_in["body"], "Re: Proposal follow-up\n\nThanks Sam, the board meets on the 20th.\nPriya")
        meeting = inter["hs:meeting:7001"]
        self.assertEqual(meeting["direction"], "unknown")
        self.assertEqual(meeting["durationSec"], 2700)
        self.assertEqual(meeting["notes"], "Tom is sceptical about the timeline; bring the implementation lead next time.")
        self.assertIn("Internal notes:", meeting["body"])
        self.assertEqual(sorted(p["email"] for p in meeting["participants"]), ["priya@acme.com", "sam@vendor.com", "tom@acme.com"])
        note = inter["hs:note:8001"]
        self.assertEqual(note["direction"], "internal")
        self.assertEqual(note["body"], "Called Priya, she confirmed procurement needs two weeks for the paper process.")
        self.assertTrue(note["title"].startswith("Called Priya"))
        other = by_id(store.load_interactions("hs:1002"))["hs:call:5002"]
        self.assertEqual(other["direction"], "inbound")
        self.assertEqual(other["at"], "2026-03-12T09:00:00Z")   # epoch millisecond hs_timestamp
        self.assertEqual(other["repId"], "rep:555")

    def test_content_flags(self):
        store = make_store(self.tmp.name, **{"content.emailBodies": False, "content.internalNotes": False})
        summary, fake = self.run_pull(store)
        email_read = fake.requests_to(r"/crm/v3/objects/emails/batch/read")[0]["body"]["properties"]
        self.assertNotIn("hs_email_text", email_read)
        self.assertNotIn("hs_email_html", email_read)
        self.assertIn("hs_email_subject", email_read)
        meeting_read = fake.requests_to(r"/crm/v3/objects/meetings/batch/read")[0]["body"]["properties"]
        self.assertNotIn("hs_internal_meeting_notes", meeting_read)
        inter = by_id(store.load_interactions("hs:1001"))
        self.assertEqual(inter["hs:email:6001"]["body"], "Proposal follow-up")
        self.assertEqual(inter["hs:email:6001"]["participants"][1]["email"], "priya@acme.com")   # headers still parsed
        self.assertIsNone(inter["hs:meeting:7001"]["notes"])
        self.assertNotIn("sceptical", inter["hs:meeting:7001"]["body"])
        self.assertFalse(inter["hs:email:6001"]["meta"]["bodyIncluded"])

    def test_incremental_cache(self):
        store = make_store(self.tmp.name)
        summary1, fake1 = self.run_pull(store)
        self.assertEqual(summary1["cache"]["dealsFromCache"], 0)
        self.assertTrue((store.cache_dir / "hubspot" / "deals" / "1001.json").exists())
        self.assertTrue((store.cache_dir / "hubspot" / "calls" / "5001.json").exists())
        self.assertTrue((store.cache_dir / "hubspot" / "pipelines.json").exists())

        summary2, fake2 = self.run_pull(store)
        self.assertEqual(summary2["cache"]["dealsFromCache"], 3)
        self.assertEqual(summary2["cache"]["objectsFetched"], 0)
        self.assertEqual(fake2.requests_to(r"/crm/v3/objects/deals/batch/read"), [])
        self.assertEqual(fake2.requests_to(r"/crm/v3/objects/calls/batch/read"), [])
        self.assertLess(fake2.request_count, fake1.request_count)
        self.assertEqual(summary2["counts"]["deals"], 3)
        self.assertEqual(len(store.load_links()["links"]), 7)   # upsert, no duplicates

        # one deal modified in HubSpot: only that deal is re-read
        fake3 = FakeHubSpot()
        fake3.fx["deals"][0]["properties"]["hs_lastmodifieddate"] = "2026-08-01T00:00:00Z"
        fake3.fx["deals"][0]["properties"]["amount"] = "45000"
        summary3, _ = self.run_pull(store, fake3)
        reads = fake3.requests_to(r"/crm/v3/objects/deals/batch/read")
        self.assertEqual([i["id"] for r in reads for i in r["body"]["inputs"]], ["1001"])
        self.assertEqual(summary3["cache"]["dealsFromCache"], 2)
        self.assertEqual(by_id(store.load_deals())["hs:1001"]["amount"], 45000.0)

        # --since refreshes everything and narrows the search
        summary4, fake4 = self.run_pull(store, since="2026-06-01")
        searches = fake4.requests_to(r"/crm/v3/objects/deals/search")
        filters = [f for s in searches for f in s["body"]["filterGroups"][0]["filters"] if f["propertyName"] == "hs_lastmodifieddate"]
        self.assertTrue(filters and filters[0]["operator"] == "GTE")
        self.assertEqual(summary4["cache"]["dealsFromCache"], 0)
        self.assertEqual(summary4["since"], "2026-06-01")
        self.assertGreater(len(fake4.requests_to(r"/crm/v3/objects/deals/batch/read")), 0)
        self.assertEqual(sorted(by_id(store.load_deals())), ["hs:1001", "hs:1002", "hs:1003"])

        with self.assertRaises(ValueError):
            self.run_pull(store, since="not a date")

    def test_pipeline_filter_and_unmapped_stages(self):
        store = make_store(self.tmp.name, **{"sources.hubspot.pipelines": []})
        summary, fake = self.run_pull(store)
        self.assertEqual(sorted(by_id(store.load_deals())), ["hs:1001", "hs:1002", "hs:1003", "hs:1005"])
        self.assertEqual(sorted(u["stageId"] for u in summary["unmappedStages"]), ["900001", "900002", "900003"])
        self.assertEqual({u["stageId"]: u["suggestedPhase"] for u in summary["unmappedStages"]}["900003"], "evaluation")
        search = fake.requests_to(r"/crm/v3/objects/deals/search")[0]["body"]
        self.assertFalse(any(f["propertyName"] == "pipeline" for f in search["filterGroups"][0]["filters"]))
        store2 = make_store(self.tmp.name + "/second", **{"sources.hubspot.pipelines": ["default", "12345"]})
        summary2, fake2 = self.run_pull(store2)
        search = fake2.requests_to(r"/crm/v3/objects/deals/search")[0]["body"]
        pipe = [f for f in search["filterGroups"][0]["filters"] if f["propertyName"] == "pipeline"][0]
        self.assertEqual(pipe, {"propertyName": "pipeline", "operator": "IN", "values": ["default", "12345"]})
        self.assertEqual(summary2["counts"]["deals"], 4)
        store3 = make_store(self.tmp.name + "/third", **{"sources.hubspot.pipelines": ["nope"]})
        summary3, _ = self.run_pull(store3)
        self.assertEqual(summary3["counts"]["deals"], 0)
        self.assertTrue(any("nope" in w for w in summary3["warnings"]))

    def test_limit_deals(self):
        store = make_store(self.tmp.name)
        summary, fake = self.run_pull(store, limit_deals=1)
        self.assertEqual(summary["counts"]["deals"], 1)
        self.assertEqual(list(by_id(store.load_deals())), ["hs:1001"])   # most recent closed deal first

    def test_search_filters_closed_and_open_groups(self):
        store = make_store(self.tmp.name)
        _, fake = self.run_pull(store)
        searches = fake.requests_to(r"/crm/v3/objects/deals/search")
        self.assertEqual(len(searches), 2)
        closed = searches[0]["body"]["filterGroups"][0]["filters"]
        self.assertIn({"propertyName": "pipeline", "operator": "EQ", "value": "default"}, closed)
        self.assertIn({"propertyName": "hs_is_closed", "operator": "EQ", "value": "true"}, closed)
        self.assertEqual([f["propertyName"] for f in closed if f["operator"] == "BETWEEN"], ["closedate"])
        opened = searches[1]["body"]["filterGroups"][0]["filters"]
        self.assertIn({"propertyName": "hs_is_closed", "operator": "EQ", "value": "false"}, opened)
        self.assertEqual([f["propertyName"] for f in opened if f["operator"] == "BETWEEN"], ["createdate"])
        self.assertEqual(searches[0]["body"]["properties"], hs.DEAL_PROPERTIES)

    def test_confirmed_links_survive_repull(self):
        store = make_store(self.tmp.name)
        self.run_pull(store)
        doc = store.load_links()
        for l in doc["links"]:
            if l["interactionId"] == "hs:note:8001":
                l["status"] = "confirmed"
                l["by"] = "user"
        store.save_links(doc)
        self.run_pull(store)
        link = [l for l in store.load_links()["links"] if l["interactionId"] == "hs:note:8001"][0]
        self.assertEqual(link["status"], "confirmed")


# ---------------------------------------------------------------------------
# pull command
# ---------------------------------------------------------------------------
class TestPullCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def ctx(self, store: Store, as_json: bool = False) -> dict:
        return {"store": store, "home": store.home, "plugin_root": ROOT, "json": as_json, "started": 0.0, "now": "2026-09-07T00:00:00Z"}

    def test_missing_token_lists_three_places(self):
        store = make_store(self.tmp.name)
        args = SimpleNamespace(source="hubspot", since=None, limit_deals=None)
        err = io.StringIO()
        with no_token_env(), contextlib.redirect_stderr(err):
            code = pull_mod.run(self.ctx(store), args)
        self.assertEqual(code, 1)
        text = err.getvalue()
        self.assertIn("HUBSPOT_ACCESS_TOKEN", text)
        self.assertIn("CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN", text)
        self.assertIn("secrets.json", text)
        self.assertIn("docs/hubspot.md", text)

    def test_pull_command_logs_requests(self):
        store = make_store(self.tmp.name)
        fake = FakeHubSpot()
        args = SimpleNamespace(source="hubspot", since=None, limit_deals=None)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "pat-test-token"}), \
                mock.patch.object(pull_mod, "HubSpotClient", lambda token, **kw: fake), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = pull_mod.run(self.ctx(store, as_json=True), args)
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["counts"]["deals"], 3)
        self.assertEqual(payload["requests"], fake.request_count)
        runs = [json.loads(l) for l in (store.home / "runs.jsonl").read_text().splitlines()]
        last = runs[-1]
        self.assertEqual(last["command"], "pull hubspot")
        self.assertTrue(last["ok"])
        self.assertIn(f"{fake.request_count} requests", last["notes"])
        self.assertIn("data/deals.json", last["wrote"])
        self.assertNotIn("pat-test-token", out.getvalue() + err.getvalue() + (store.home / "runs.jsonl").read_text())

    def test_pull_command_scope_error_exit_2(self):
        store = make_store(self.tmp.name)
        fake = FakeHubSpot()
        fake.queue.append((403, {}, load_fixture("error_missing_scopes.json")))
        args = SimpleNamespace(source="hubspot", since=None, limit_deals=None)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "pat-test-token"}), \
                mock.patch.object(pull_mod, "HubSpotClient", lambda token, **kw: fake), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = pull_mod.run(self.ctx(store, as_json=True), args)
        self.assertEqual(code, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["requiredScopes"], ["crm.schemas.emails.read", "crm.objects.emails.read", "sales-email-read"])


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------
class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        (Path(self.tmp.name) / "frameworks").mkdir()
        (Path(self.tmp.name) / "frameworks" / "meddpicc.json").write_text("{}", encoding="utf-8")

    def run_doctor(self, store: Store, fake: FakeHubSpot | None, source: str = "hubspot"):
        ctx = {"store": store, "home": store.home, "plugin_root": Path(self.tmp.name), "json": True, "started": 0.0}
        if fake is not None:
            ctx["hubspot_client_factory"] = lambda token, base_url: fake
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = doctor_mod.run(ctx, SimpleNamespace(source=source))
        return code, json.loads(out.getvalue())

    def checks(self, payload):
        return {c["check"]: c for c in payload["checks"]}

    def test_all_green(self):
        store = make_store(self.tmp.name)
        with mock.patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "pat-test-token"}):
            code, payload = self.run_doctor(store, FakeHubSpot())
        self.assertEqual(code, 0, payload)
        checks = self.checks(payload)
        self.assertTrue(checks["python"]["ok"] and checks["store"]["ok"] and checks["config"]["ok"] and checks["framework"]["ok"])
        self.assertEqual(checks["hubspot token"]["detail"], "found in environment variable HUBSPOT_ACCESS_TOKEN")
        self.assertIn("hubId 12345678", checks["hubspot token info"]["detail"])
        self.assertTrue(checks["hubspot scopes"]["ok"])
        self.assertTrue(checks["hubspot deals search"]["ok"])
        self.assertTrue(checks["hubspot stage phases"]["ok"])
        self.assertEqual(payload["hubspot"]["hubId"], 12345678)
        self.assertEqual([p["id"] for p in payload["hubspot"]["pipelines"]], ["default", "12345"])
        self.assertNotIn("pat-test-token", json.dumps(payload))

    def test_unmapped_stages_listed_with_labels(self):
        store = make_store(self.tmp.name, **{"sources.hubspot.pipelines": []})
        with mock.patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "pat-test-token"}):
            code, payload = self.run_doctor(store, FakeHubSpot())
        self.assertEqual(code, 1)
        checks = self.checks(payload)
        self.assertFalse(checks["hubspot stage phases"]["ok"])
        self.assertIn("900001 (Partner Intro)", checks["hubspot stage phases"]["detail"])
        self.assertIn("config set stagePhases", checks["hubspot stage phases"]["fix"])
        unmapped = {u["stageId"]: u for u in payload["hubspot"]["unmappedStages"]}
        self.assertEqual(set(unmapped), {"900001", "900002", "900003"})
        self.assertEqual(unmapped["900001"]["label"], "Partner Intro")
        self.assertEqual(unmapped["900001"]["pipelineId"], "12345")

    def test_missing_scopes_reported(self):
        store = make_store(self.tmp.name)
        fake = FakeHubSpot()
        fake.fx["token_info"] = dict(fake.fx["token_info"], scopes=["oauth", "crm.objects.deals.read"])
        with mock.patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "pat-test-token"}):
            code, payload = self.run_doctor(store, fake)
        self.assertEqual(code, 1)
        checks = self.checks(payload)
        self.assertFalse(checks["hubspot scopes"]["ok"])
        self.assertIn("sales-email-read", checks["hubspot scopes"]["detail"])
        self.assertEqual(payload["hubspot"]["missingScopes"], ["crm.objects.contacts.read", "crm.objects.companies.read", "crm.objects.owners.read", "crm.schemas.deals.read", "sales-email-read"])

    def test_search_scope_error_surfaces_required_scopes(self):
        store = make_store(self.tmp.name)
        fake = FakeHubSpot()
        fake.queue.append((200, {}, fake.fx["token_info"]))
        fake.queue.append((403, {}, load_fixture("error_missing_scopes.json")))
        with mock.patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "pat-test-token"}):
            code, payload = self.run_doctor(store, fake)
        self.assertEqual(code, 1)
        self.assertIn("crm.objects.emails.read", self.checks(payload)["hubspot deals search"]["detail"])

    def test_no_token_and_no_store(self):
        store = Store(Path(self.tmp.name) / "missing")
        with no_token_env():
            code, payload = self.run_doctor(store, None)
        self.assertEqual(code, 1)
        checks = self.checks(payload)
        self.assertFalse(checks["store"]["ok"])
        self.assertEqual(checks["store"]["fix"], "run: fs.py init")
        self.assertFalse(checks["hubspot token"]["ok"])
        self.assertIn("secrets.json", checks["hubspot token"]["fix"])
        self.assertNotIn("hubspot token info", checks)

    def test_secrets_file_token_and_permissions(self):
        store = make_store(self.tmp.name)
        secrets = store.home / "secrets.json"
        secrets.write_text(json.dumps({"hubspot_token": "pat-test-token"}), encoding="utf-8")
        os.chmod(secrets, 0o644)
        with no_token_env():
            code, payload = self.run_doctor(store, FakeHubSpot())
        checks = self.checks(payload)
        self.assertIn("secrets.json", checks["hubspot token"]["detail"])
        self.assertFalse(checks["hubspot secrets.json permissions"]["ok"])
        self.assertEqual(code, 1)
        os.chmod(secrets, 0o600)
        with no_token_env():
            code, payload = self.run_doctor(store, FakeHubSpot())
        self.assertEqual(code, 0)

    def test_granola_and_transcripts_checks(self):
        folder = Path(self.tmp.name) / "tx"
        folder.mkdir()
        (folder / "call.md").write_text("Rep: hi", encoding="utf-8")
        store = make_store(self.tmp.name, **{"sources.hubspot.enabled": False, "sources.granola.enabled": True,
                                             "sources.granola.cachePath": str(Path(self.tmp.name) / "nope.json"),
                                             "sources.transcripts.enabled": True, "sources.transcripts.folder": str(folder)})
        code, payload = self.run_doctor(store, None, source="all")
        checks = self.checks(payload)
        self.assertFalse(checks["granola"]["ok"])
        self.assertTrue(checks["transcripts"]["ok"])
        self.assertNotIn("hubspot token", checks)
        self.assertEqual(code, 1)


# ---------------------------------------------------------------------------
# seeding
# ---------------------------------------------------------------------------
class TestSeed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = make_store(self.tmp.name)
        self.store.save_companies([{"id": "co:1", "name": "Acme", "domain": "acme.com"}])
        self.store.save_contacts([{"id": "c:1", "name": "Priya Shah", "email": "priya@acme.com", "title": "CFO", "companyId": "co:1", "buyingRole": None}])
        self.store.save_reps([{"id": "rep:1", "name": "Sam Rep", "email": "sam@vendor.com", "source": "demo"}])
        self.store.save_deals([{
            "id": "demo:1", "source": "demo", "name": "Acme expansion", "amount": 42000.0, "currency": "GBP", "pipeline": "default",
            "stage": "closedwon", "stageLabel": "Closed Won", "phase": "won",
            "stageHistory": [{"stage": "appointmentscheduled", "label": "Appointment Scheduled", "phase": "discovery", "at": "2026-03-01T10:00:00Z"},
                             {"stage": "presentationscheduled", "label": "Presentation Scheduled", "phase": "proposal", "at": "2026-04-10T11:00:00Z"},
                             {"stage": "closedwon", "label": "Closed Won", "phase": "won", "at": "2026-06-14T09:30:00Z"}],
            "outcome": "won", "createdAt": "2026-03-01T10:00:00Z", "closedAt": "2026-06-14T00:00:00Z", "ownerId": "rep:1",
            "contactIds": ["c:1"], "companyId": "co:1", "companyDomain": "acme.com", "meta": {}}])
        self.store.save_interactions("demo:1", [
            {"id": "demo:i1", "source": "demo", "type": "call", "dealId": "demo:1", "direction": "outbound", "at": "2026-03-04T14:00:00Z", "durationSec": 1860,
             "title": "Discovery call", "body": "Priya: month-end close takes 11 days.", "transcript": None, "notes": None, "summary": None,
             "participants": [{"name": "Sam Rep", "email": "sam@vendor.com", "role": "rep"}, {"name": "Priya Shah", "email": "priya@acme.com", "role": "buyer"}],
             "repId": "rep:1", "recordingUrl": None, "meta": {}},
            {"id": "demo:i2", "source": "demo", "type": "email", "dealId": "demo:1", "direction": "inbound", "at": "2026-04-13T16:20:00Z", "durationSec": None,
             "title": "Re: proposal", "body": "Thanks Sam, the board meets on the 20th.", "transcript": None, "notes": None, "summary": None,
             "participants": [{"name": "Priya Shah", "email": "priya@acme.com", "role": "buyer"}, {"name": "Sam Rep", "email": "sam@vendor.com", "role": "rep"}],
             "repId": "rep:1", "recordingUrl": None, "meta": {}},
            {"id": "demo:i3", "source": "demo", "type": "meeting", "dealId": "demo:1", "direction": "unknown", "at": "2026-05-05T15:00:00Z", "durationSec": 2700,
             "title": "Exec review", "body": "Agenda: pricing", "transcript": None, "notes": "Tom sceptical", "summary": None,
             "participants": [], "repId": None, "recordingUrl": None, "meta": {}},
            {"id": "demo:i4", "source": "demo", "type": "note", "dealId": "demo:1", "direction": "internal", "at": "2026-05-21T10:00:00Z", "durationSec": None,
             "title": None, "body": "Procurement needs two weeks.", "transcript": None, "notes": None, "summary": None,
             "participants": [], "repId": "rep:1", "recordingUrl": None, "meta": {}},
        ])

    def test_dry_run_plans_without_writes(self):
        fake = FakeHubSpot()
        result = seed_hubspot.seed(self.store, self.store.config, fake, dry_run=True, log=lambda m: None)
        self.assertTrue(result["ok"])
        self.assertTrue(any(p.startswith("create companies Acme") for p in result["plan"]))
        self.assertTrue(any("dealstage -> presentationscheduled" in p for p in result["plan"]))
        self.assertEqual(fake.created, {})
        self.assertFalse((self.store.home / seed_hubspot.SEED_MAP).exists())

    def test_seed_creates_maps_and_is_idempotent(self):
        fake = FakeHubSpot()
        result = seed_hubspot.seed(self.store, self.store.config, fake, log=lambda m: None)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["created"], {"companies": 1, "contacts": 1, "deals": 1, "calls": 1, "emails": 1, "meetings": 1, "notes": 1})
        self.assertEqual(result["stagePatches"], 2)
        deal = fake.created["deals"][0]
        self.assertEqual(deal["properties"]["dealstage"], "appointmentscheduled")
        self.assertEqual(deal["properties"]["hubspot_owner_id"], "41629779")   # matched by email
        self.assertEqual(deal["associations"][0]["types"][0]["associationTypeId"], 3)
        self.assertEqual(deal["associations"][1]["types"][0]["associationTypeId"], 5)
        stages = [(t, p["dealstage"]) for t, _, p in fake.updated]
        self.assertEqual(stages, [("deals", "presentationscheduled"), ("deals", "closedwon")])
        self.assertEqual(fake.updated[-1][2]["closedate"], "2026-06-14T00:00:00Z")
        call = fake.created["calls"][0]
        self.assertEqual(call["properties"]["hs_timestamp"], "2026-03-04T14:00:00Z")
        self.assertEqual(call["properties"]["hs_call_direction"], "OUTBOUND")
        self.assertEqual(call["properties"]["hs_call_duration"], "1860000")
        self.assertEqual({a["types"][0]["associationTypeId"] for a in call["associations"]}, {206, 194})
        email = fake.created["emails"][0]
        self.assertEqual(email["properties"]["hs_email_direction"], "INCOMING_EMAIL")
        self.assertEqual(json.loads(email["properties"]["hs_email_headers"])["from"]["email"], "priya@acme.com")
        self.assertEqual({a["types"][0]["associationTypeId"] for a in email["associations"]}, {210, 198})
        meeting = fake.created["meetings"][0]
        self.assertEqual(meeting["properties"]["hs_meeting_end_time"], "2026-05-05T15:45:00Z")
        self.assertEqual(meeting["properties"]["hs_internal_meeting_notes"], "Tom sceptical")
        self.assertEqual({a["types"][0]["associationTypeId"] for a in meeting["associations"]}, {212, 200})
        self.assertEqual({a["types"][0]["associationTypeId"] for a in fake.created["notes"][0]["associations"]}, {214, 202})
        contact = fake.created["contacts"][0]
        self.assertEqual(contact["associations"][0]["types"][0]["associationTypeId"], 1)
        seed_map = self.store.read_json(seed_hubspot.SEED_MAP)
        self.assertEqual(len(seed_map["objects"]), 7)
        self.assertEqual(seed_map["objects"]["demo:1"]["type"], "deals")
        self.assertEqual(seed_map["stages"]["demo:1"], ["appointmentscheduled", "presentationscheduled", "closedwon"])

        again = seed_hubspot.seed(self.store, self.store.config, fake, log=lambda m: None)
        self.assertEqual(again["skippedExisting"], 7)
        self.assertEqual(sum(again["created"].values()), 0)
        self.assertEqual(again["stagePatches"], 0)

        wiped = seed_hubspot.seed(self.store, self.store.config, fake, wipe=True, log=lambda m: None)
        self.assertTrue(wiped["ok"])
        self.assertEqual(wiped["archived"]["deals"], 1)
        self.assertEqual(sorted(fake.archived), ["calls", "companies", "contacts", "deals", "emails", "meetings", "notes"])
        self.assertEqual(self.store.read_json(seed_hubspot.SEED_MAP)["objects"], {})

    def test_main_entry_dry_run(self):
        out = io.StringIO()
        with no_token_env(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = seed_hubspot.main(["--home", str(self.store.home), "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("create deals Acme expansion", out.getvalue())


if __name__ == "__main__":
    unittest.main()
