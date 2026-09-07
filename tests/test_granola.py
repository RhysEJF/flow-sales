"""Tests for the Granola source: parsers, canonical conversion, export-folder import, the legacy cache guard,
the public API client (paging, 413 fallback, note cache, watermark) and the doctor checks.

No network access: a fake urlopen is injected through the module-level hook granola.URLOPEN.
Run: python3 -m unittest tests.test_granola -v
"""
from __future__ import annotations

import contextlib
import email.message
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowsales.config import Config  # noqa: E402
from flowsales.crm import granola  # noqa: E402
from flowsales.crm import granola_parse as gp  # noqa: E402
from flowsales.schema.validate import validate_records  # noqa: E402
from flowsales.store import Store  # noqa: E402
from flowsales.util import now_iso  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "granola"
ACME = "9f2c1a3e-1b2c-4d5e-8f90-a1b2c3d4e5f6"        # external, list + get + transcript files
INTERNAL = "5a6b7c8d-9e0f-4a1b-8c2d-3e4f5a6b7c8d"    # Northwind only
FJORD = "c3d4e5f6-a7b8-4c9d-8e0f-112233445566"       # external, transcript file without meeting_id
HELIOS = "0a1b2c3d-4e5f-4a6b-8c7d-9e8f7a6b5c4d"      # public API note
EXPORT_KEYS = set(gp.new_meeting().keys())


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def make_store(tmp: str, mode: str | None = None, **granola_cfg) -> Store:
    store = Store(Path(tmp) / ".flow-sales")
    store.ensure()
    cfg = store.config
    cfg.set("org.internalDomains", ["northwind.example"])
    cfg.set("window.from", "2026-08-01")
    cfg.set("window.to", "2026-08-31")
    if mode:
        cfg.set("sources.granola.mode", mode)
    for k, v in granola_cfg.items():
        cfg.set(f"sources.granola.{k}", v)
    cfg.save()
    store.save_reps([{"id": "rep:sam", "name": "Sam Rep", "email": "sam@northwind.example", "source": "granola"}])
    return store


def run_import(store: Store, json_out: bool = False, **kw) -> tuple[int, str, str]:
    ctx = {"store": store, "home": store.home, "plugin_root": ROOT, "json": json_out, "started": time.time(), "now": now_iso()}
    args = SimpleNamespace(source="granola", cache=kw.get("cache"), export_dir=kw.get("export_dir"),
                           seed=7, deals=None, interactions=None, folder=None, json=json_out)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = granola.run(ctx, args)
    return code, out.getvalue(), err.getvalue()


def unlinked_ids(store: Store) -> set[str]:
    return {it["id"] for it in store.load_unlinked()}


# ---------------------------------------------------------------------------
# parsers
# ---------------------------------------------------------------------------

class ParserTests(unittest.TestCase):
    def assert_export_shape(self, meetings: list[dict]) -> None:
        self.assertTrue(meetings)
        for m in meetings:
            self.assertTrue(EXPORT_KEYS <= set(m.keys()), f"missing keys: {EXPORT_KEYS - set(m.keys())}")
            self.assertIsInstance(m["participants"], list)
            self.assertIsInstance(m["transcript"], list)

    def test_mcp_list_envelope(self):
        meetings = gp.parse_mcp_text(read("list_meetings.txt"))
        self.assert_export_shape(meetings)
        self.assertEqual([m["uuid"] for m in meetings], [ACME, INTERNAL, FJORD])
        acme = meetings[0]
        self.assertEqual(acme["source"], gp.SOURCE_MCP)
        self.assertEqual(acme["title"], "Acme discovery")
        self.assertEqual(acme["at"], "2026-08-04T14:00:00Z")
        self.assertEqual(acme["date_text"], "Aug 4, 2026 2:00 PM")
        self.assertEqual(acme["web_url"], gp.WEB_URL_PREFIX + ACME)
        self.assertEqual(acme["participants"][0], {"name": "Sam Rep", "email": "sam@northwind.example", "company": "Northwind", "role": gp.ROLE_CREATOR})
        self.assertEqual(acme["participants"][1], {"name": "Priya Shah", "email": "priya@acme.example", "company": "Acme", "role": gp.ROLE_ATTENDEE})
        self.assertEqual(acme["owner"], {"name": "Sam Rep", "email": "sam@northwind.example"})
        self.assertEqual(acme["transcript"], [])

    def test_mcp_get_meetings_envelope_has_summary_and_private_notes(self):
        meetings = gp.parse_mcp_text(read(f"{ACME}.txt"))
        self.assert_export_shape(meetings)
        self.assertEqual(len(meetings), 1)
        self.assertIn("Acme is replacing its legacy CRM", meetings[0]["summary_markdown"])
        self.assertTrue(meetings[0]["summary_markdown"].startswith("## Acme discovery"))
        self.assertEqual(meetings[0]["private_notes_markdown"], "Ask about their procurement timeline.")

    def test_mcp_transcript_envelope(self):
        name = f"{ACME}-transcript.txt"
        meetings = gp.parse_mcp_text(read(name), fallback_id=gp.uuid_from_path(name))
        self.assert_export_shape(meetings)
        m = meetings[0]
        self.assertEqual(m["uuid"], ACME)
        self.assertEqual(m["transcript"][0], {"speaker": "Sam Rep", "t": 15.0, "text": "Thanks for making time today, Priya."})
        self.assertEqual(m["transcript"][1]["speaker"], "Priya Shah")
        self.assertEqual(m["transcript"][-1]["t"], 31 * 60 + 2)
        self.assertEqual(m["duration_sec"], 1862)

    def test_mcp_transcript_without_meeting_id_uses_file_name(self):
        name = f"{FJORD}-transcript.txt"
        meetings = gp.parse_mcp_text(read(name), fallback_id=gp.uuid_from_path(name))
        self.assertEqual(len(meetings), 1)
        self.assertEqual(meetings[0]["uuid"], FJORD)
        self.assertEqual([s["speaker"] for s in meetings[0]["transcript"]], ["Me", "Them", "Me"])

    def test_public_api_note(self):
        meetings = gp.parse_public_api_note(json.loads(read("public_api_note.json")))
        self.assert_export_shape(meetings)
        m = meetings[0]
        self.assertEqual(m["source"], gp.SOURCE_API)
        self.assertEqual(m["id"], "not_7Hj2kL9mNpQrSt")
        self.assertEqual(m["uuid"], HELIOS)
        self.assertEqual(m["at"], "2026-08-18T09:00:00Z")           # calendar start beats created_at
        self.assertEqual(m["duration_sec"], 45 * 60)
        self.assertEqual(m["calendar_event"]["calendar_event_id"], "2su99n6iiik37iiknmb5t4fkfh_20260818T090000Z")
        self.assertEqual(m["calendar_event"]["organiser"], "sam@northwind.example")
        self.assertEqual(m["folders"], ["Sales calls"])
        self.assertEqual(m["owner"], {"name": "Sam Rep", "email": "sam@northwind.example"})
        emails = {p["email"]: p["role"] for p in m["participants"]}
        self.assertEqual(emails["maya@helios.example"], gp.ROLE_ATTENDEE)
        self.assertEqual(emails["sam@northwind.example"], gp.ROLE_OWNER)
        self.assertEqual([s["speaker"] for s in m["transcript"]], ["Sam Rep", "Maya Chen", "Sam Rep"])
        self.assertEqual(m["transcript"][1]["t"], 8.0)
        self.assertEqual(m["transcript_started_at"], "2026-08-18T09:01:00Z")

    def test_public_api_transcript_items_override_inline(self):
        note = json.loads(read("public_api_note.json"))
        items = [{"speaker": {"attribution": "them", "name": "Maya Chen"}, "text": "Paged item.", "start_time": 3.0, "end_time": 5.0}]
        m = gp.parse_public_api_note(note, transcript_items=items)[0]
        self.assertEqual(m["transcript"], [{"speaker": "Maya Chen", "t": 3.0, "text": "Paged item.", "end": 5.0}])

    def test_csv_export(self):
        meetings = gp.parse_csv(read("export.csv"))
        self.assert_export_shape(meetings)
        self.assertEqual(len(meetings), 2)
        orbit = meetings[0]
        self.assertEqual(orbit["source"], gp.SOURCE_CSV)
        self.assertEqual(orbit["uuid"], "d1e2f3a4-b5c6-4d7e-8f90-0a1b2c3d4e5f")
        self.assertEqual(orbit["title"], "Orbit renewal call")
        self.assertEqual(orbit["at"], "2026-08-20T15:00:00Z")
        self.assertEqual({p["email"] for p in orbit["participants"]}, {"sam@northwind.example", "nia@orbit.example"})
        self.assertEqual(orbit["summary_markdown"], "Orbit wants to renew for two years if we hold the price.")
        self.assertEqual(orbit["private_notes_markdown"], "Check the discount policy with finance.")
        self.assertEqual(len(orbit["transcript"]), 3)
        self.assertEqual(orbit["transcript"][0]["speaker"], "Unknown")   # the CSV carries no speaker labels
        self.assertTrue(meetings[1]["id"].startswith("csv-"))
        self.assertIsNone(meetings[1]["uuid"])

    def test_markdown_export(self):
        meetings = gp.parse_markdown(read("export.md"), path=FIXTURES / "export.md")
        self.assert_export_shape(meetings)
        m = meetings[0]
        self.assertEqual(m["source"], gp.SOURCE_MARKDOWN)
        self.assertEqual(m["uuid"], "e5f6a7b8-c9d0-4e1f-8a2b-3c4d5e6f7a8b")
        self.assertEqual(m["title"], "Vela onboarding kickoff")
        self.assertEqual(m["at"], "2026-08-25T13:00:00Z")
        self.assertEqual(m["folders"], ["Sales calls"])
        self.assertEqual([(p["name"], p["company"], p["role"]) for p in m["participants"]],
                         [("Sam Rep", "Northwind", gp.ROLE_CREATOR), ("Tomas Reyes", "Vela", gp.ROLE_ATTENDEE)])
        self.assertIn("Vela wants to go live in October.", m["summary_markdown"])
        self.assertEqual(m["private_notes_markdown"], "Send the onboarding checklist.")
        self.assertEqual(m["transcript"][1], {"speaker": "Tomas Reyes", "t": 12.0, "text": "Happy to be here. October is our target."})
        self.assertEqual(m["duration_sec"], 760)

    def test_legacy_cache(self):
        obj = json.loads(read("cache_legacy.json"))
        self.assertEqual(gp.cache_document_count(obj), 1)
        meetings = gp.parse_cache_json(obj)
        self.assert_export_shape(meetings)
        m = meetings[0]
        self.assertEqual(m["source"], gp.SOURCE_CACHE)
        self.assertEqual(m["uuid"], "b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d0e")
        self.assertEqual(m["at"], "2026-04-10T14:00:00Z")
        self.assertEqual(m["folders"], ["Demos"])
        self.assertIn("Atlas cares about reporting.", m["summary_markdown"])
        self.assertEqual([s["speaker"] for s in m["transcript"]], ["Sam Rep", "Them"])
        self.assertEqual(gp.cache_document_count(json.loads(read("cache_stub.json"))), 0)

    def test_merge_transcript_into_meeting_by_uuid(self):
        name = f"{ACME}-transcript.txt"
        merged = gp.merge_meetings(gp.parse_mcp_text(read("list_meetings.txt")) + gp.parse_mcp_text(read(f"{ACME}.txt"))
                                   + gp.parse_mcp_text(read(name), fallback_id=gp.uuid_from_path(name)))
        self.assertEqual([m["uuid"] for m in merged], [ACME, INTERNAL, FJORD])
        acme = merged[0]
        self.assertEqual(len(acme["transcript"]), 4)
        self.assertIn("Acme is replacing", acme["summary_markdown"])
        self.assertEqual(acme["at"], "2026-08-04T14:00:00Z")
        self.assertEqual(len(acme["participants"]), 3)
        self.assertEqual(acme["duration_sec"], 1862)


# ---------------------------------------------------------------------------
# canonical conversion
# ---------------------------------------------------------------------------

class ToInteractionTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config({"org": {"internalDomains": ["northwind.example"]}}, Path("/nonexistent/config.json"))
        self.reps = [{"id": "rep:sam", "name": "Sam Rep", "email": "sam@northwind.example"}]

    def convert(self, meeting: dict) -> dict:
        return gp.to_interaction(meeting, self.cfg, internal_domains=self.cfg.internal_domains(self.reps), reps=self.reps)

    def test_roles_at_duration_body(self):
        name = f"{ACME}-transcript.txt"
        merged = gp.merge_meetings(gp.parse_mcp_text(read("list_meetings.txt")) + gp.parse_mcp_text(read(f"{ACME}.txt"))
                                   + gp.parse_mcp_text(read(name), fallback_id=gp.uuid_from_path(name)))
        it = self.convert(merged[0])
        self.assertEqual(it["id"], f"granola:{ACME}")
        self.assertEqual(it["source"], "granola")
        self.assertEqual(it["type"], "meeting")
        self.assertIsNone(it["dealId"])
        self.assertEqual(it["at"], "2026-08-04T14:00:00Z")
        self.assertEqual(it["durationSec"], 1862)
        self.assertEqual(it["title"], "Acme discovery")
        self.assertEqual([(p["name"], p["role"]) for p in it["participants"]],
                         [("Sam Rep", "rep"), ("Priya Shah", "buyer"), ("Dev Patel", "buyer")])
        self.assertEqual(it["repId"], "rep:sam")
        self.assertTrue(it["body"].startswith("Sam Rep: Thanks for making time today, Priya.\nPriya Shah: Of course."))
        self.assertEqual(len(it["transcript"]), 4)
        self.assertEqual(it["transcript"][0], {"speaker": "Sam Rep", "t": 15.0, "text": "Thanks for making time today, Priya."})
        self.assertIn("Acme is replacing", it["summary"])
        self.assertEqual(it["notes"], "Ask about their procurement timeline.")
        self.assertEqual(it["meta"]["uuid"], ACME)
        self.assertEqual(it["meta"]["web_url"], gp.WEB_URL_PREFIX + ACME)
        self.assertTrue(it["meta"]["hasTranscript"])
        self.assertEqual(it["meta"]["participantCompanies"]["priya@acme.example"], "Acme")
        self.assertEqual(it["meta"]["externalParticipants"], 2)
        self.assertEqual(validate_records("interaction", [it]), [])

    def test_me_and_them_speakers_use_owner_name(self):
        name = f"{FJORD}-transcript.txt"
        merged = gp.merge_meetings(gp.parse_mcp_text(read("list_meetings.txt"))
                                   + gp.parse_mcp_text(read(name), fallback_id=gp.uuid_from_path(name)))
        it = self.convert(merged[2])
        self.assertEqual(it["transcript"][0]["speaker"], "Sam Rep")
        self.assertEqual(it["transcript"][1]["speaker"], "Them")
        self.assertEqual(it["durationSec"], 1110)

    def test_body_without_transcript_uses_notes(self):
        it = self.convert(gp.parse_mcp_text(read(f"{ACME}.txt"))[0])
        self.assertTrue(it["body"].startswith("Notes:\n## Acme discovery"))
        self.assertIn("Private notes:\nAsk about their procurement timeline.", it["body"])
        self.assertEqual(it["transcript"], [])
        self.assertFalse(it["meta"]["hasTranscript"])
        self.assertIsNone(it["durationSec"])

    def test_public_api_note_maps_calendar_fields(self):
        it = self.convert(gp.parse_public_api_note(json.loads(read("public_api_note.json")))[0])
        self.assertEqual(it["id"], f"granola:{HELIOS}")
        self.assertEqual(it["at"], "2026-08-18T09:00:00Z")
        self.assertEqual(it["durationSec"], 2700)
        self.assertEqual({p["email"]: p["role"] for p in it["participants"]},
                         {"maya@helios.example": "buyer", "sam@northwind.example": "rep"})
        self.assertEqual(it["meta"]["calendar_event_id"], "2su99n6iiik37iiknmb5t4fkfh_20260818T090000Z")
        self.assertEqual(it["meta"]["scheduled_end_time"], "2026-08-18T09:45:00Z")
        self.assertEqual(it["meta"]["granola_id"], "not_7Hj2kL9mNpQrSt")
        self.assertEqual(validate_records("interaction", [it]), [])

    def test_internal_only_detection(self):
        meetings = gp.parse_mcp_text(read("list_meetings.txt"))
        self.assertFalse(granola.has_external_participant(self.convert(meetings[1])))
        self.assertTrue(granola.has_external_participant(self.convert(meetings[0])))
        self.assertFalse(granola.has_external_participant({"participants": []}))

    def test_every_fixture_validates(self):
        meetings = (gp.parse_mcp_text(read("list_meetings.txt")) + gp.parse_csv(read("export.csv"))
                    + gp.parse_markdown(read("export.md"), path="export.md")
                    + gp.parse_cache_json(json.loads(read("cache_legacy.json"))))
        records = [self.convert(m) for m in meetings]
        self.assertEqual(validate_records("interaction", records), [])


# ---------------------------------------------------------------------------
# export folder import
# ---------------------------------------------------------------------------

class ExportDirImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = make_store(self.tmp.name)
        self.export = Path(self.tmp.name) / "export"
        self.export.mkdir()
        for name in ("list_meetings.txt", f"{ACME}.txt", f"{ACME}-transcript.txt", f"{FJORD}-transcript.txt"):
            shutil.copy(FIXTURES / name, self.export / name)

    def test_parser_routing_by_extension_and_content(self):
        found, kind = granola.parse_export_file(FIXTURES / "list_meetings.txt")
        self.assertEqual((len(found), kind), (3, "mcp"))
        found, kind = granola.parse_export_file(FIXTURES / "public_api_note.json")
        self.assertEqual((found[0]["uuid"], kind), (HELIOS, "api"))
        found, kind = granola.parse_export_file(FIXTURES / "export.csv")
        self.assertEqual((len(found), kind), (2, "csv"))
        found, kind = granola.parse_export_file(FIXTURES / "export.md")
        self.assertEqual((found[0]["source"], kind), (gp.SOURCE_MARKDOWN, "markdown"))
        found, kind = granola.parse_export_file(FIXTURES / "cache_legacy.json")
        self.assertEqual((found[0]["source"], kind), (gp.SOURCE_CACHE, "cache"))
        # an export-shape dict passes through; a list of API notes and an MCP tool result saved as JSON also work
        shape = gp.new_meeting(id=ACME, uuid=ACME, source=gp.SOURCE_MCP, title="Passthrough", at="2026-08-04T14:00:00Z")
        p = self.export / "shape.json"
        p.write_text(json.dumps([shape]), encoding="utf-8")
        found, kind = granola.parse_export_file(p)
        self.assertEqual((found[0]["title"], kind), ("Passthrough", "export"))
        p = self.export / "tool-result.json"
        p.write_text(json.dumps({"content": [{"type": "text", "text": read("list_meetings.txt")}]}), encoding="utf-8")
        found, kind = granola.parse_export_file(p)
        self.assertEqual((len(found), kind), (3, "mcp"))
        p = self.export / "notes-page.json"
        p.write_text(json.dumps({"notes": [json.loads(read("public_api_note.json"))], "hasMore": False}), encoding="utf-8")
        found, kind = granola.parse_export_file(p)
        self.assertEqual((found[0]["uuid"], kind), (HELIOS, "api"))
        p = self.export / "meeting.xml"
        p.write_text(read(f"{ACME}.txt"), encoding="utf-8")
        found, kind = granola.parse_export_file(p)
        self.assertEqual((found[0]["uuid"], kind), (ACME, "mcp"))
        (self.export / "README.txt").write_text("Nothing to see here.\n", encoding="utf-8")
        self.assertEqual(granola.parse_export_file(self.export / "README.txt"), ([], "unrecognised"))
        (self.export / "_watermark.json").write_text("{}", encoding="utf-8")
        (self.export / ".hidden.txt").write_text(read("list_meetings.txt"), encoding="utf-8")
        names = [p.name for p in granola.export_files(self.export)]
        self.assertNotIn("_watermark.json", names)
        self.assertNotIn(".hidden.txt", names)
        self.assertIn("README.txt", names)

    def test_import_writes_unlinked_merges_dedupes_and_skips(self):
        # FJORD is already linked to a deal: it must be left alone
        self.store.save_interactions("hs:1", [{"id": f"granola:{FJORD}", "source": "granola", "type": "meeting", "dealId": "hs:1",
                                               "direction": "unknown", "at": "2026-08-12T15:00:00Z", "durationSec": None,
                                               "title": "Fjord pricing review", "body": "", "transcript": [], "notes": None,
                                               "summary": None, "participants": [], "repId": None, "recordingUrl": None, "meta": {}}])
        code, out, err = run_import(self.store, export_dir=str(self.export))
        self.assertEqual(code, 0, err)
        self.assertIn("files read: 4", out)
        self.assertIn("meetings parsed: 3", out)
        self.assertIn("transcripts present: 2", out)
        self.assertIn("skipped internal-only: 1", out)
        self.assertIn("already linked: 1", out)
        self.assertIn("written unlinked: 1", out)
        unlinked = self.store.load_unlinked()
        self.assertEqual([it["id"] for it in unlinked], [f"granola:{ACME}"])
        acme = unlinked[0]
        self.assertEqual(len(acme["transcript"]), 4)                     # transcript file merged in
        self.assertIn("Acme is replacing", acme["summary"])               # get_meetings envelope merged in
        self.assertEqual(acme["durationSec"], 1862)
        self.assertEqual(validate_records("interaction", unlinked), [])
        linked = self.store.load_interactions("hs:1")
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["body"], "")                           # untouched
        runs = [json.loads(line) for line in self.store.runs_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(runs[-1]["command"], "import granola")
        self.assertTrue(runs[-1]["ok"])
        self.assertIn("1 written unlinked", runs[-1]["notes"])
        self.assertEqual(runs[-1]["read"], [str(self.export)])

    def test_import_is_idempotent_and_updates_in_place(self):
        run_import(self.store, export_dir=str(self.export))
        self.store.save_unlinked([dict(it, title="edited by hand") if it["id"] == f"granola:{ACME}" else it for it in self.store.load_unlinked()])
        code, out, _ = run_import(self.store, json_out=True, export_dir=str(self.export))
        self.assertEqual(code, 0)
        summary = json.loads(out)
        self.assertEqual(summary["writtenUnlinked"], 2)                    # ACME and FJORD (nothing is linked here)
        self.assertEqual(summary["unlinkedTotal"], 2)
        self.assertEqual(summary["meetingsParsed"], 3)
        self.assertEqual(summary["filesRead"], 4)
        unlinked = self.store.load_unlinked()
        self.assertEqual(len(unlinked), 2)                                 # no duplicates on re-import
        acme = next(it for it in unlinked if it["id"] == f"granola:{ACME}")
        self.assertEqual(acme["title"], "Acme discovery")                  # re-import wins over the manual edit

    def test_all_formats_in_one_folder(self):
        for name in ("public_api_note.json", "export.csv", "export.md"):
            shutil.copy(FIXTURES / name, self.export / name)
        code, out, _ = run_import(self.store, json_out=True, export_dir=str(self.export))
        self.assertEqual(code, 0, out)
        summary = json.loads(out)
        self.assertEqual(summary["filesRead"], 7)
        self.assertEqual(summary["meetingsParsed"], 3 + 1 + 2 + 1)
        self.assertEqual(summary["skippedInternal"], 2)                    # pipeline sync and the CSV coffee chat
        ids = unlinked_ids(self.store)
        self.assertEqual(ids, {f"granola:{ACME}", f"granola:{FJORD}", f"granola:{HELIOS}",
                               "granola:d1e2f3a4-b5c6-4d7e-8f90-0a1b2c3d4e5f", "granola:e5f6a7b8-c9d0-4e1f-8a2b-3c4d5e6f7a8b"})
        self.assertEqual(validate_records("interaction", self.store.load_unlinked()), [])

    def test_default_export_dir_is_cache_granola(self):
        target = self.store.cache_dir / "granola"
        shutil.copytree(self.export, target)
        code, out, _ = run_import(self.store, json_out=True)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["source"], str(target))
        self.assertEqual(json.loads(out)["writtenUnlinked"], 2)

    def test_config_export_dir(self):
        self.store.config.set("sources.granola.exportDir", str(self.export))
        self.store.save_config()
        code, out, _ = run_import(self.store, json_out=True)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["source"], str(self.export))

    def test_missing_export_dir(self):
        code, out, err = run_import(self.store, export_dir=str(Path(self.tmp.name) / "nope"))
        self.assertEqual(code, 1)
        self.assertIn("No Granola export folder", err)

    def test_invalid_records_are_reported_not_written(self):
        (self.export / "undated.csv").write_text("title,attendees,summary\nNo date call,Zed Q <zed@zeta.example>,Hello\n", encoding="utf-8")
        code, out, _ = run_import(self.store, json_out=True, export_dir=str(self.export))
        self.assertEqual(code, 0)
        summary = json.loads(out)
        self.assertEqual(summary["invalid"], 1)
        self.assertTrue(any("'at'" in e for e in summary["validationErrors"]), summary["validationErrors"])
        self.assertEqual(summary["writtenUnlinked"], 2)


# ---------------------------------------------------------------------------
# legacy cache
# ---------------------------------------------------------------------------

class CacheModeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = make_store(self.tmp.name)

    def assert_refused(self, path: str):
        code, out, err = run_import(self.store, cache=path)
        self.assertEqual(code, 1)
        self.assertEqual(out.strip(), granola.ENCRYPTED_CACHE_MESSAGE)
        code, out, _ = run_import(self.store, json_out=True, cache=path)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["error"], granola.ENCRYPTED_CACHE_MESSAGE)
        self.assertEqual(self.store.load_unlinked(), [])
        last = json.loads(self.store.runs_path.read_text(encoding="utf-8").splitlines()[-1])
        self.assertFalse(last["ok"])

    def test_encrypted_cache_is_refused(self):
        enc = Path(self.tmp.name) / "cache-v6.json.enc"
        enc.write_bytes(b"\x00\x01binary")
        self.assert_refused(str(enc))
        self.assertEqual(granola.inspect_cache_path(enc)[0], "encrypted")

    def test_missing_cache_is_refused(self):
        missing = Path(self.tmp.name) / "cache-v3.json"
        self.assert_refused(str(missing))
        self.assertEqual(granola.inspect_cache_path(missing)[0], "missing")
        (Path(self.tmp.name) / "cache-v3.json.enc").write_bytes(b"x")
        self.assertEqual(granola.inspect_cache_path(missing)[0], "encrypted")

    def test_stub_cache_without_documents_is_refused(self):
        self.assert_refused(str(FIXTURES / "cache_stub.json"))
        self.assertEqual(granola.inspect_cache_path(FIXTURES / "cache_stub.json")[0], "stub")
        bad = Path(self.tmp.name) / "cache-v3.json"
        bad.write_text("not json", encoding="utf-8")
        self.assert_refused(str(bad))

    def test_legacy_plaintext_cache_imports(self):
        code, out, _ = run_import(self.store, json_out=True, cache=str(FIXTURES / "cache_legacy.json"))
        self.assertEqual(code, 0, out)
        summary = json.loads(out)
        self.assertEqual(summary["mode"], "cache")
        self.assertEqual(summary["meetingsParsed"], 1)
        self.assertEqual(summary["transcriptsPresent"], 1)
        self.assertEqual(unlinked_ids(self.store), {"granola:b7c8d9e0-f1a2-4b3c-8d4e-5f6a7b8c9d0e"})

    def test_config_cache_path_selects_cache_mode(self):
        self.store.config.set("sources.granola.cachePath", str(Path(self.tmp.name) / "cache-v6.json.enc"))
        self.store.save_config()
        (Path(self.tmp.name) / "cache-v6.json.enc").write_bytes(b"x")
        code, out, _ = run_import(self.store)
        self.assertEqual(code, 1)
        self.assertEqual(out.strip(), granola.ENCRYPTED_CACHE_MESSAGE)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status: int, body: bytes, headers: dict | None = None):
        self.status = status
        self._body = body
        self.headers = headers or {"Content-Type": "application/json"}

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeGranolaApi:
    """Serves two notes: not_A (inline transcript) and not_B (413 on include=transcript, paged transcript)."""

    def __init__(self):
        self.calls: list[dict] = []
        self.queue: list[tuple[int, dict, dict]] = []    # forced responses, consumed first
        self.updated_notes: list[dict] = []               # what an updated_after listing returns
        base = json.loads(read("public_api_note.json"))
        self.note_a = dict(base, id="not_A00000000000001", title="Helios security review")
        self.note_b = dict(base, id="not_B00000000000002", title="Helios follow-up",
                           web_url="https://notes.granola.ai/d/1b2c3d4e-5f6a-4b7c-8d9e-0f1a2b3c4d5e",
                           created_at="2026-08-19T09:02:11Z")
        self.big_transcript = [
            {"speaker": {"attribution": "me"}, "text": f"Paged line {i}.", "start_time": float(i * 10), "end_time": float(i * 10 + 4)}
            for i in range(1, 4)
        ] + [{"speaker": {"attribution": "them", "name": "Maya Chen"}, "text": "We are ready to pilot.", "start_time": 40.0, "end_time": 43.0}]

    def summary(self, note: dict) -> dict:
        return {"id": note["id"], "object": "note", "title": note["title"], "owner": note["owner"],
                "created_at": note["created_at"], "updated_at": note["updated_at"]}

    def __call__(self, req, timeout=None):
        parsed = urlparse(req.full_url)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        self.calls.append({"path": parsed.path, "query": query, "auth": req.get_header("Authorization"),
                           "ua": req.get_header("User-agent")})
        if self.queue:
            status, hdrs, body = self.queue.pop(0)
            return self._respond(req.full_url, status, hdrs, body)
        status, body = self.route(parsed.path, query)
        return self._respond(req.full_url, status, {}, body)

    def _respond(self, url: str, status: int, hdrs: dict, body: dict):
        raw = json.dumps(body).encode("utf-8")
        if status >= 400:
            msg = email.message.Message()
            for k, v in hdrs.items():
                msg[k] = str(v)
            raise urllib.error.HTTPError(url, status, "error", msg, io.BytesIO(raw))
        return FakeResponse(status, raw, dict({"Content-Type": "application/json"}, **hdrs))

    def route(self, path: str, query: dict) -> tuple[int, dict]:
        if path == "/v1/notes":
            if "updated_after" in query:
                return 200, {"notes": [self.summary(n) for n in self.updated_notes], "hasMore": False, "cursor": None}
            if query.get("cursor") == "page2":
                return 200, {"notes": [self.summary(self.note_b)], "hasMore": False, "cursor": None}
            return 200, {"notes": [self.summary(self.note_a)], "hasMore": True, "cursor": "page2"}
        if path == "/v1/notes/not_A00000000000001":
            return 200, self.note_a
        if path == "/v1/notes/not_B00000000000002":
            if query.get("include") == "transcript":
                return 413, {"code": "TRANSCRIPT_TOO_LARGE", "message": "Transcript too large; use the transcript endpoint"}
            return 200, {k: v for k, v in self.note_b.items() if k != "transcript"}
        if path == "/v1/notes/not_B00000000000002/transcript":
            assert query.get("page_size") == "100", query
            if query.get("cursor") == "t2":
                return 200, {"transcript": self.big_transcript[3:], "hasMore": False, "cursor": None}
            return 200, {"transcript": self.big_transcript[:3], "hasMore": True, "cursor": "t2"}
        return 404, {"code": "NOT_FOUND", "message": path}


class ApiModeTests(unittest.TestCase):
    KEY = "grn_test_secret_key_123456"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = make_store(self.tmp.name, mode="api")
        self.fake = FakeGranolaApi()
        self.sleeps: list[float] = []
        patches = [mock.patch.object(granola, "URLOPEN", self.fake), mock.patch.object(granola, "SLEEP", self.sleeps.append),
                   mock.patch.dict(os.environ, {"GRANOLA_API_KEY": self.KEY})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.cache_dir = self.store.cache_dir / "granola"

    def test_first_run_pages_falls_back_on_413_caches_and_writes_watermark(self):
        code, out, err = run_import(self.store, json_out=True)
        self.assertEqual(code, 0, out + err)
        summary = json.loads(out)
        self.assertEqual(summary["mode"], "api")
        self.assertEqual(summary["api"]["notesListed"], 2)
        self.assertEqual(summary["api"]["notesFetched"], 2)
        self.assertEqual(summary["api"]["transcriptsPaged"], 1)
        self.assertEqual(summary["writtenUnlinked"], 2)
        self.assertEqual(summary["filesRead"], 2)
        paths = [c["path"] for c in self.fake.calls]
        self.assertEqual(paths, ["/v1/notes", "/v1/notes/not_A00000000000001", "/v1/notes", "/v1/notes/not_B00000000000002",
                                 "/v1/notes/not_B00000000000002", "/v1/notes/not_B00000000000002/transcript",
                                 "/v1/notes/not_B00000000000002/transcript"])
        first = self.fake.calls[0]
        self.assertEqual(first["query"]["created_after"], "2026-08-01")
        self.assertEqual(first["query"]["created_before"], "2026-08-31T23:59:59Z")
        self.assertEqual(first["query"]["page_size"], "30")
        self.assertNotIn("updated_after", first["query"])
        self.assertNotIn("cursor", first["query"])
        self.assertEqual(self.fake.calls[2]["query"]["cursor"], "page2")
        self.assertEqual(self.fake.calls[3]["query"], {"include": "transcript"})
        self.assertEqual(self.fake.calls[4]["query"], {})
        self.assertEqual(self.fake.calls[6]["query"]["cursor"], "t2")
        for c in self.fake.calls:
            self.assertEqual(c["auth"], f"Bearer {self.KEY}")
        # cached notes are named by the document uuid from web_url
        self.assertTrue((self.cache_dir / f"{HELIOS}.json").exists())
        cached_b = json.loads((self.cache_dir / "1b2c3d4e-5f6a-4b7c-8d9e-0f1a2b3c4d5e.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cached_b["transcript"]), 4)
        self.assertEqual(cached_b["title"], "Helios follow-up")
        wm = json.loads((self.cache_dir / "_watermark.json").read_text(encoding="utf-8"))
        self.assertTrue(wm["updated_after"].endswith("Z"))
        self.assertEqual(wm["notesListed"], 2)
        self.assertEqual(summary["api"]["watermark"], wm["updated_after"])
        # interactions
        ids = unlinked_ids(self.store)
        self.assertEqual(ids, {f"granola:{HELIOS}", "granola:1b2c3d4e-5f6a-4b7c-8d9e-0f1a2b3c4d5e"})
        b = next(it for it in self.store.load_unlinked() if it["id"].endswith("0f1a2b3c4d5e"))
        self.assertEqual(len(b["transcript"]), 4)
        self.assertEqual(b["transcript"][-1]["speaker"], "Maya Chen")
        self.assertEqual(validate_records("interaction", self.store.load_unlinked()), [])
        # the key never leaks
        for text in (out, err, self.store.runs_path.read_text(encoding="utf-8"), (self.cache_dir / "_watermark.json").read_text(encoding="utf-8")):
            self.assertNotIn(self.KEY, text)

    def test_second_run_is_incremental(self):
        run_import(self.store, json_out=True)
        wm = json.loads((self.cache_dir / "_watermark.json").read_text(encoding="utf-8"))["updated_after"]
        self.fake.calls.clear()
        code, out, _ = run_import(self.store, json_out=True)
        self.assertEqual(code, 0)
        summary = json.loads(out)
        self.assertEqual([c["path"] for c in self.fake.calls], ["/v1/notes"])
        self.assertEqual(self.fake.calls[0]["query"]["updated_after"], wm)
        self.assertEqual(summary["api"]["updatedAfter"], wm)
        self.assertEqual(summary["api"]["notesFetched"], 0)
        self.assertEqual(summary["writtenUnlinked"], 0)
        self.assertEqual(summary["unlinkedTotal"], 2)
        # a note updated since the watermark is fetched again and upserted in place
        self.fake.note_a["title"] = "Helios security review (renamed)"
        self.fake.updated_notes = [self.fake.note_a]
        self.fake.calls.clear()
        code, out, _ = run_import(self.store, json_out=True)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["writtenUnlinked"], 1)
        self.assertEqual(len(self.store.load_unlinked()), 2)
        self.assertEqual(next(it["title"] for it in self.store.load_unlinked() if it["id"] == f"granola:{HELIOS}"), "Helios security review (renamed)")

    def test_429_honours_retry_after_and_throttle_spaces_requests(self):
        self.fake.queue.append((429, {"Retry-After": "3"}, {"code": "RATE_LIMITED", "message": "slow down"}))
        code, out, _ = run_import(self.store, json_out=True)
        self.assertEqual(code, 0, out)
        summary = json.loads(out)
        self.assertEqual(summary["api"]["retries"], 1)
        self.assertEqual(summary["api"]["requests"], 8)
        self.assertIn(3.0, self.sleeps)
        self.assertEqual([c["path"] for c in self.fake.calls][:2], ["/v1/notes", "/v1/notes"])

    def test_server_error_exhausts_retries_and_exits_2(self):
        for _ in range(6):
            self.fake.queue.append((500, {}, {"message": "boom"}))
        code, out, err = run_import(self.store)
        self.assertEqual(code, 2)
        self.assertIn("HTTP 500", err)
        self.assertNotIn(self.KEY, err)
        self.assertFalse((self.cache_dir / "_watermark.json").exists())
        self.assertFalse(json.loads(self.store.runs_path.read_text(encoding="utf-8").splitlines()[-1])["ok"])

    def test_missing_key_exits_1_without_calling(self):
        with mock.patch.dict(os.environ, {"GRANOLA_API_KEY": ""}):
            code, out, err = run_import(self.store)
        self.assertEqual(code, 1)
        self.assertIn("GRANOLA_API_KEY", err)
        self.assertIn("secrets.json", err)
        self.assertEqual(self.fake.calls, [])

    def test_key_from_secrets_json(self):
        (self.store.home / "secrets.json").write_text(json.dumps({"granola_api_key": "grn_from_secrets"}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"GRANOLA_API_KEY": ""}):
            key, where = granola.resolve_granola_key(self.store.config, self.store.home)
            self.assertEqual(key, "grn_from_secrets")
            self.assertIn("secrets.json", where)
            self.assertNotIn("grn_from_secrets", where)
            code, out, _ = run_import(self.store, json_out=True)
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.calls[0]["auth"], "Bearer grn_from_secrets")

    def test_client_throttle_and_paging_directly(self):
        clock = [1000.0]
        sleeps: list[float] = []

        def fake_sleep(s: float) -> None:
            sleeps.append(s)
            clock[0] += s

        client = granola.GranolaClient("grn_x", rate_per_sec=5.0, urlopen=self.fake, sleep=fake_sleep, clock=lambda: clock[0])
        notes = list(client.list_notes(created_after="2026-08-01", page_size=30))
        self.assertEqual([n["id"] for n in notes], ["not_A00000000000001", "not_B00000000000002"])
        self.assertEqual(client.request_count, 2)
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.2, places=6)
        note, paged = client.get_note("not_B00000000000002")
        self.assertTrue(paged)
        self.assertEqual(len(note["transcript"]), 4)
        note, paged = client.get_note("not_A00000000000001")
        self.assertFalse(paged)
        self.assertEqual(len(note["transcript"]), 3)
        self.assertNotIn("grn_x", repr(client))
        with self.assertRaises(GranolaApiErrorAlias) as cm:
            client.get("/nowhere")
        self.assertEqual(cm.exception.status, 404)


GranolaApiErrorAlias = granola.GranolaApiError


# ---------------------------------------------------------------------------
# doctor checks
# ---------------------------------------------------------------------------

class DoctorChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def names(self, checks: list[dict]) -> dict[str, dict]:
        for c in checks:
            self.assertEqual(set(c.keys()), {"check", "ok", "detail", "fix"})
            if c["ok"]:
                self.assertIsNone(c["fix"])
        return {c["check"]: c for c in checks}

    def test_export_mode_with_files(self):
        store = make_store(self.tmp.name, mode="mcp")
        target = store.cache_dir / "granola"
        target.mkdir(parents=True)
        for name in ("list_meetings.txt", f"{ACME}-transcript.txt"):
            shutil.copy(FIXTURES / name, target / name)
        checks = self.names(granola.granola_checks(store, store.config))
        self.assertTrue(checks["granola-export"]["ok"])
        self.assertIn("2 export files (1 transcripts)", checks["granola-export"]["detail"])
        self.assertTrue(checks["granola"]["ok"])
        self.assertNotIn("granola-cache", checks)

    def test_default_mode_with_export_files_does_not_flag_the_cache(self):
        store = make_store(self.tmp.name, cachePath=str(Path(self.tmp.name) / "absent-cache-v3.json"))
        store.config.set("sources.granola.cachePath", None)
        store.save_config()
        checks = self.names(granola.granola_checks(store, store.config))
        self.assertFalse(checks["granola-cache"]["ok"])                    # nothing usable yet
        self.assertFalse(checks["granola"]["ok"])
        target = store.cache_dir / "granola"
        target.mkdir(parents=True)
        shutil.copy(FIXTURES / "list_meetings.txt", target / "list_meetings.txt")
        checks = self.names(granola.granola_checks(store, store.config))
        self.assertTrue(checks["granola-cache"]["ok"])                     # unconfigured cache, export folder in use
        self.assertIn("export folder is used instead", checks["granola-cache"]["detail"])
        self.assertTrue(checks["granola"]["ok"])

    def test_local_cache_mode_reports_encrypted_cache(self):
        enc = Path(self.tmp.name) / "cache-v6.json.enc"
        enc.write_bytes(b"x")
        store = make_store(self.tmp.name, cachePath=str(enc))
        checks = self.names(granola.granola_checks(store, store.config))
        self.assertFalse(checks["granola-cache"]["ok"])
        self.assertIn(granola.ENCRYPTED_CACHE_MESSAGE, checks["granola-cache"]["fix"])
        self.assertFalse(checks["granola"]["ok"])
        self.assertFalse(checks["granola-export"]["ok"])

    def test_api_mode_never_prints_the_key(self):
        store = make_store(self.tmp.name, mode="api")
        with mock.patch.dict(os.environ, {"GRANOLA_API_KEY": "grn_doctor_secret"}):
            checks = self.names(granola.granola_checks(store, store.config))
        self.assertTrue(checks["granola-api-key"]["ok"])
        self.assertIn("GRANOLA_API_KEY", checks["granola-api-key"]["detail"])
        self.assertNotIn("grn_doctor_secret", json.dumps(checks))
        self.assertTrue(checks["granola"]["ok"])
        self.assertIn("no watermark", checks["granola-api-watermark"]["detail"])
        with mock.patch.dict(os.environ, {"GRANOLA_API_KEY": "", "CLAUDE_PLUGIN_OPTION_GRANOLA_API_KEY": ""}):
            checks = self.names(granola.granola_checks(store, store.config))
        self.assertFalse(checks["granola-api-key"]["ok"])
        self.assertIn("grn_", checks["granola-api-key"]["fix"])


if __name__ == "__main__":
    unittest.main()
