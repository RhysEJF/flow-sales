"""Tests for the file-based sources: demo, csv, transcripts folder, and the import dispatcher."""
from __future__ import annotations

import contextlib
import datetime as _dt
import importlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fs  # noqa: E402
from flowsales.crm import demo, demo_content, import_cmd, transcripts_folder  # noqa: E402
from flowsales.schema.validate import validate_records  # noqa: E402
from flowsales.store import Store  # noqa: E402
from flowsales.util import transcript_to_body  # noqa: E402

TODAY = _dt.datetime.now(_dt.timezone.utc).date()  # the demo import anchors its story on the run date


def run_cli(home: str, *argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = fs.main(["--home", home, *argv])
    return code, out.getvalue()


def words(text: str) -> int:
    return len(text.split())


class DemoImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = os.path.join(cls.tmp.name, "store")
        code, _ = run_cli(cls.home, "init")
        assert code == 0
        started = time.time()
        code, cls.output = run_cli(cls.home, "import", "demo", "--seed", "7")
        cls.elapsed = time.time() - started
        assert code == 0, cls.output
        cls.store = Store(Path(cls.home))
        cls.deals = cls.store.load_deals()
        cls.linked = [it for deal_id, it in cls.store.iter_all_interactions() if deal_id]
        cls.unlinked = cls.store.load_unlinked()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_runs_fast_and_prints_summary(self):
        self.assertLess(self.elapsed, 5.0)
        self.assertIn("deals: 32", self.output)
        self.assertIn("Tom Ellis", self.output)

    def test_records_are_valid(self):
        self.assertEqual(validate_records("deal", self.deals), [])
        self.assertEqual(validate_records("rep", self.store.load_reps()), [])
        self.assertEqual(validate_records("contact", self.store.load_contacts()), [])
        self.assertEqual(validate_records("company", self.store.load_companies()), [])
        self.assertEqual(validate_records("interaction", self.linked + self.unlinked), [])

    def test_counts_in_range(self):
        self.assertEqual(len(self.deals), 32)
        self.assertEqual(len(self.store.load_reps()), 4)
        self.assertTrue(130 <= len(self.linked) <= 190, len(self.linked))
        self.assertEqual(len(self.unlinked), 6)
        outcomes = {d["outcome"] for d in self.deals}
        self.assertEqual(outcomes, {"won", "lost", "open"})
        for deal in self.deals:
            self.assertTrue(4 <= len(deal["stageHistory"]) <= 6, deal["id"])
            self.assertTrue(1 <= len(deal["contactIds"]) <= 3, deal["id"])
            self.assertTrue(8000 <= deal["amount"] <= 120000, deal["id"])
            self.assertIn(deal["currency"], ("GBP", "EUR"))
            self.assertEqual(deal["stage"], deal["stageHistory"][-1]["stage"])
            ats = [h["at"] for h in deal["stageHistory"]]
            self.assertEqual(ats, sorted(ats))
            n = len(self.store.load_interactions(deal["id"]))
            self.assertTrue(4 <= n <= 7, f"{deal['id']} has {n} interactions")
        by_type = {}
        for it in self.linked:
            by_type[it["type"]] = by_type.get(it["type"], 0) + 1
        for t in ("call", "meeting", "email", "note"):
            self.assertGreater(by_type.get(t, 0), 5, by_type)
        links = self.store.load_links()["links"]
        self.assertEqual(len(links), len(self.linked))
        self.assertTrue(all(l["method"] == "crm-association" and l["confidence"] == 1.0 and l["status"] == "auto" for l in links))

    def test_transcripts_have_speakers_and_length(self):
        calls = [it for it in self.linked if it["type"] == "call"]
        self.assertGreater(len(calls), 20)
        for it in calls + [m for m in self.linked if m["type"] == "meeting" and m["transcript"]] + self.unlinked:
            self.assertTrue(it["transcript"], it["id"])
            speakers = {seg["speaker"] for seg in it["transcript"]}
            self.assertGreaterEqual(len(speakers), 2, it["id"])
            self.assertEqual(it["body"], transcript_to_body(it["transcript"]))
            n = sum(words(seg["text"]) for seg in it["transcript"])
            self.assertTrue(350 <= n <= 900, f"{it['id']} has {n} words")
            self.assertGreater(it["durationSec"], 0)
            # no fragment repeats inside one conversation
            texts = [seg["text"] for seg in it["transcript"] if words(seg["text"]) > 8]
            self.assertEqual(len(texts), len(set(texts)), it["id"])
        for it in self.linked:
            if it["type"] == "email":
                self.assertTrue(80 <= words(it["body"]) <= 200, f"{it['id']} has {words(it['body'])} words")
                self.assertIn(it["direction"], ("inbound", "outbound"))
            elif it["type"] == "note":
                self.assertTrue(40 <= words(it["body"]) <= 120, f"{it['id']} has {words(it['body'])} words")
            self.assertIn("demo", it["meta"])
            self.assertTrue(any(p["role"] == "rep" for p in it["participants"]), it["id"])

    def test_story_before_and_after_training(self):
        cfg = self.store.config
        self.assertEqual(cfg.get("trainingDate"), demo.shift_months(TODAY, -4).isoformat())
        self.assertEqual(cfg.get("window.from"), demo.shift_months(TODAY, -9).isoformat())
        self.assertEqual(cfg.get("window.to"), TODAY.isoformat())
        self.assertIn(demo_content.VENDOR["domain"], cfg.get("org.internalDomains"))
        self.assertTrue(cfg.get("sources.demo.enabled"))
        training = cfg.get("trainingDate")

        def rate(rep_key: str, after: bool) -> float:
            mine = [it for it in self.linked if rep_key in it["repId"] and it["direction"] != "inbound"
                    and (it["at"][:10] >= training) == after]
            return sum(1 for it in mine if it["meta"]["demo"]["behaviourTags"]) / len(mine)

        self.assertGreater(rate("tom.ellis", True), rate("tom.ellis", False) + 0.3)
        self.assertLess(rate("jonas.weber", True), 0.35)
        self.assertGreater(rate("amira.khan", False), 0.6)
        sofia = [it for it in self.linked if "sofia.marin" in it["repId"]]
        self.assertFalse(any("PP" in it["meta"]["demo"]["elementsAsked"] for it in sofia))
        self.assertFalse(any("asked-paper-process" in it["meta"]["demo"]["behaviourTags"] for it in sofia))
        self.assertFalse(any("paperwork look like" in it["body"] for it in sofia))
        self.assertLessEqual(sum(1 for it in sofia if "CH" in it["meta"]["demo"]["elementsAsked"]), 4)
        high = [it for it in self.linked if it["type"] == "call" and it["meta"]["demo"]["adoption"] == "high"]
        self.assertTrue(all(3 <= len(it["meta"]["demo"]["elementsAsked"]) <= 5 for it in high))
        lumen = sum(1 for it in self.linked if "Lumen BI" in it["body"])
        self.assertGreater(lumen, 20)
        self.assertTrue(any("spreadsheet works fine" in it["body"] for it in self.linked))

    def test_unlinked_meetings(self):
        contacts = {c["email"]: c for c in self.store.load_contacts()}
        deals_by_contact: dict[str, list[str]] = {}
        for deal in self.deals:
            for cid in deal["contactIds"]:
                deals_by_contact.setdefault(cid, []).append(deal["id"])
        domains = {d["companyDomain"] for d in self.deals}
        matched, domain_only, ambiguous = 0, 0, 0
        for it in self.unlinked:
            self.assertIsNone(it["dealId"])
            self.assertEqual(it["type"], "meeting")
            self.assertEqual(it["source"], "demo")
            buyers = [p["email"] for p in it["participants"] if p["role"] == "buyer"]
            self.assertTrue(buyers)
            hits = [deals_by_contact.get(contacts[e]["id"], []) for e in buyers if e in contacts]
            if not hits:
                self.assertTrue(all(e.split("@")[1] in domains for e in buyers))
                domain_only += 1
            elif any(len(h) > 1 for h in hits):
                ambiguous += 1
            else:
                matched += 1
        self.assertEqual((matched, domain_only, ambiguous), (4, 1, 1))

    def test_deterministic(self):
        a = demo.generate(7, TODAY)
        b = demo.generate(7, TODAY)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        c = demo.generate(8, TODAY)
        self.assertNotEqual(json.dumps(a["deals"], sort_keys=True), json.dumps(c["deals"], sort_keys=True))
        # a second import into the same store replaces rather than duplicates
        code, _ = run_cli(self.home, "import", "demo", "--seed", "7")
        self.assertEqual(code, 0)
        self.assertEqual(len(Store(Path(self.home)).load_deals()), 32)
        self.assertEqual(len(Store(Path(self.home)).load_unlinked()), 6)


class CsvAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "store")
        run_cli(self.home, "init")

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip_of_samples(self):
        code, out = run_cli(self.home, "import", "csv", "--deals", str(ROOT / "docs/examples/deals.csv"),
                            "--interactions", str(ROOT / "docs/examples/interactions.csv"))
        self.assertEqual(code, 0, out)
        store = Store(Path(self.home))
        deals = {d["id"]: d for d in store.load_deals()}
        self.assertEqual(set(deals), {"csv:D-1042", "csv:D-1043", "csv:D-1044"})
        won = deals["csv:D-1042"]
        self.assertEqual((won["phase"], won["outcome"], won["amount"], won["currency"]), ("won", "won", 42000.0, "GBP"))
        self.assertEqual(won["ownerId"], "rep:sam@vendor.example")
        self.assertEqual(won["contactIds"], ["c:priya@acme.example", "c:dev@acme.example"])
        self.assertEqual(won["companyId"], "co:acme.example")
        self.assertEqual(len(won["stageHistory"]), 5)
        self.assertEqual(won["stageHistory"][0]["phase"], "discovery")
        self.assertEqual(deals["csv:D-1043"]["phase"], "evaluation")
        self.assertEqual(deals["csv:D-1044"]["phase"], "lost")
        self.assertEqual(len(deals["csv:D-1044"]["stageHistory"]), 2)
        self.assertEqual({r["id"] for r in store.load_reps()}, {"rep:sam@vendor.example", "rep:jo@vendor.example"})
        self.assertEqual(validate_records("deal", list(deals.values())), [])
        linked = [it for deal_id, it in store.iter_all_interactions() if deal_id]
        unlinked = store.load_unlinked()
        self.assertEqual(len(linked), 5)
        self.assertEqual({it["id"] for it in unlinked}, {"csv:I-6", "csv:I-7"})
        self.assertEqual(validate_records("interaction", linked + unlinked), [])
        call = next(it for it in linked if it["id"] == "csv:I-1")
        self.assertEqual(call["dealId"], "csv:D-1042")
        self.assertEqual(len(call["transcript"]), 12)
        self.assertEqual(call["transcript"][1]["speaker"], "Priya Shah")
        self.assertEqual(call["body"], transcript_to_body(call["transcript"]))
        roles = {p["email"]: p["role"] for p in call["participants"]}
        self.assertEqual(roles, {"priya@acme.example": "buyer", "sam@vendor.example": "rep"})
        note = next(it for it in linked if it["id"] == "csv:I-4")
        self.assertEqual((note["direction"], note["transcript"]), ("internal", []))
        email = next(it for it in linked if it["id"] == "csv:I-5")
        self.assertEqual((email["direction"], email["repId"]), ("inbound", "rep:jo@vendor.example"))
        links = store.load_links()["links"]
        self.assertEqual(len(links), 5)
        self.assertTrue(all(l["method"] == "crm-association" for l in links))
        cfg = store.config
        self.assertTrue(cfg.get("sources.csv.enabled"))
        self.assertTrue(cfg.get("sources.csv.dealsFile").endswith("deals.csv"))
        runs = (Path(self.home) / "runs.jsonl").read_text().strip().splitlines()
        self.assertEqual(json.loads(runs[-1])["command"], "import csv")
        # importing again replaces, never duplicates
        code, _ = run_cli(self.home, "import", "csv", "--interactions", str(ROOT / "docs/examples/interactions.csv"))
        self.assertEqual(code, 0)
        self.assertEqual(len(store.load_unlinked()), 2)
        self.assertEqual(len(store.load_interactions("csv:D-1042")), 3)

    def test_bad_rows_stop_the_import(self):
        bad = Path(self.tmp.name) / "bad.csv"
        bad.write_text("id,deal_id,type,direction,at,duration_sec,title,body,participants,rep_email\nX-1,,fax,,not-a-date,,t,,,\n", encoding="utf-8")
        code, out = run_cli(self.home, "import", "csv", "--interactions", str(bad))
        self.assertEqual(code, 1)
        self.assertIn("type must be one of", out)
        self.assertFalse((Path(self.home) / "data" / "interactions" / "_unlinked.json").exists())


class TranscriptsFolderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "store")
        run_cli(self.home, "init")
        store = Store(Path(self.home))
        store.ensure()
        store.save_reps([{"id": "rep:sam@vendor.example", "name": "Sam Rep", "email": "sam@vendor.example", "source": "csv"}])
        store.save_deals([{"id": "csv:D-1042", "source": "csv", "name": "Acme", "amount": 1.0, "currency": "GBP", "pipeline": "default",
                           "stage": "closedwon", "stageLabel": "Closed Won", "phase": "won", "stageHistory": [], "outcome": "won",
                           "createdAt": "2026-03-01T00:00:00Z", "closedAt": "2026-06-01T00:00:00Z", "ownerId": "rep:sam@vendor.example",
                           "contactIds": [], "companyId": None, "companyDomain": "acme.example", "meta": {}}])
        self.folder = Path(self.tmp.name) / "transcripts"
        (self.folder / "march").mkdir(parents=True)
        (self.folder / "march" / "acme-discovery.md").write_text(
            "---\ntitle: Acme discovery\ndate: 2026-03-04 14:00\nparticipants:\n  - Priya Shah <priya@acme.example>\n  - Sam Rep <sam@vendor.example>\n"
            "deal_id: csv:D-1042\n---\n\nSam Rep: Thanks for the time, Priya.\nPriya Shah: Month-end close takes us 11 days.\n"
            "We need it under 5 by the audit.\n[00:03:10] Sam Rep: Who owns that number?\n", encoding="utf-8")
        (self.folder / "2026-03-12-1000-anita-review.vtt").write_text(
            "WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\n<v Sam Rep>Anita, thanks for joining.</v>\n\n2\n00:00:05.500 --> 00:00:09.000\n"
            "Anita Rao: Two conditions. No consultancy on the connector.\n\n3\n00:00:09.000 --> 00:00:12.000\nAnd a payback I can show the board.\n", encoding="utf-8")
        (self.folder / "beacon-demo.json").write_text(json.dumps({
            "title": "Beacon Foods demo", "date": "2026-07-22T13:00:00Z", "participants": [{"name": "Lotte de Vries", "email": "lotte@beaconfoods.example"}, "sam@vendor.example"],
            "segments": [{"speaker": "Sam Rep", "text": "Lotte, thanks for bringing Bram along.", "t": 0},
                         {"speaker": "Lotte de Vries", "text": "About 30 hours across three people.", "t": 14.5}]}), encoding="utf-8")
        (self.folder / "2026-04-02 dev patel call.txt").write_text(
            "Attendees: Dev Patel <dev@acme.example>, Sam Rep <sam@vendor.example>\n\nSam Rep: Dev, quick one about the service account.\n"
            "Dev Patel: Send the firewall rule and we are fine.\n", encoding="utf-8")
        (self.folder / "notes-only.txt").write_text("Just some prose about the meeting, no speakers at all.\n", encoding="utf-8")
        (self.folder / "ignored.pdf").write_bytes(b"%PDF-1.4")

    def tearDown(self):
        self.tmp.cleanup()

    def test_parses_three_formats(self):
        code, out = run_cli(self.home, "import", "transcripts", "--folder", str(self.folder))
        self.assertEqual(code, 0, out)
        store = Store(Path(self.home))
        linked = store.load_interactions("csv:D-1042")
        unlinked = store.load_unlinked()
        self.assertEqual(len(linked), 1)
        self.assertEqual(len(unlinked), 4)
        every = linked + unlinked
        self.assertEqual(validate_records("interaction", every), [])
        self.assertTrue(all(it["id"].startswith("tx:") and it["source"] == "transcripts" and it["type"] == "transcript" for it in every))
        by_title = {it["title"]: it for it in every}
        md = by_title["Acme discovery"]
        self.assertEqual(md["at"], "2026-03-04T14:00:00Z")
        self.assertEqual(md["dealId"], "csv:D-1042")
        self.assertEqual([s["speaker"] for s in md["transcript"]], ["Sam Rep", "Priya Shah", "Sam Rep"])
        self.assertEqual(md["transcript"][1]["text"], "Month-end close takes us 11 days. We need it under 5 by the audit.")
        self.assertEqual(md["transcript"][2]["t"], 190.0)
        self.assertEqual(md["repId"], "rep:sam@vendor.example")
        self.assertEqual({p["email"]: p["role"] for p in md["participants"]}, {"priya@acme.example": "buyer", "sam@vendor.example": "rep"})
        vtt = by_title["anita review"]
        self.assertEqual(vtt["at"], "2026-03-12T10:00:00Z")
        self.assertEqual([s["speaker"] for s in vtt["transcript"]], ["Sam Rep", "Anita Rao", "Unknown"])
        self.assertEqual(vtt["transcript"][0]["text"], "Anita, thanks for joining.")
        self.assertEqual(vtt["transcript"][1]["t"], 5.5)
        js = by_title["Beacon Foods demo"]
        self.assertEqual(js["at"], "2026-07-22T13:00:00Z")
        self.assertEqual(len(js["transcript"]), 2)
        self.assertEqual(js["repId"], "rep:sam@vendor.example")
        self.assertEqual(js["participants"][0]["name"], "Lotte de Vries")
        txt = by_title["dev patel call"]
        self.assertEqual(txt["at"], "2026-04-02T00:00:00Z")
        self.assertEqual(len(txt["transcript"]), 2)
        self.assertEqual({p["email"] for p in txt["participants"]}, {"dev@acme.example", "sam@vendor.example"})
        prose = by_title["notes only"]
        self.assertEqual(prose["transcript"], [])
        self.assertIn("no speakers", prose["body"])
        self.assertEqual(prose["meta"]["transcripts"]["timeFrom"], "mtime")
        self.assertEqual(len(list((Path(self.home) / "cache" / "transcripts").glob("*.json"))), 5)
        links = store.load_links()["links"]
        self.assertEqual([(l["interactionId"], l["dealId"]) for l in links], [(md["id"], "csv:D-1042")])
        self.assertTrue(store.config.get("sources.transcripts.enabled"))
        # idempotent
        code, _ = run_cli(self.home, "import", "transcripts", "--folder", str(self.folder))
        self.assertEqual(code, 0)
        self.assertEqual(len(store.load_unlinked()), 4)
        self.assertEqual(len(store.load_interactions("csv:D-1042")), 1)

    def test_helpers(self):
        self.assertEqual(transcripts_folder.timestamp_to_seconds("01:02:03.500"), 3723.5)
        self.assertEqual(transcripts_folder.parse_person("Priya Shah <Priya@Acme.example>"), {"name": "Priya Shah", "email": "priya@acme.example"})
        self.assertEqual(transcripts_folder.parse_person("dev@acme.example"), {"name": "dev", "email": "dev@acme.example"})
        self.assertEqual(transcripts_folder.title_from_filename("2026-03-04-1400_acme-discovery.md"), "acme discovery")
        fields, rest = transcripts_folder.parse_front_matter("---\ntitle: X\nparticipants: [a <a@b.c>, b <b@b.c>]\n---\nbody")
        self.assertEqual((fields["title"], len(fields["participants"]), rest), ("X", 2, "body"))


class ImportCommandTests(unittest.TestCase):
    def test_missing_adapter_message(self):
        tmp = tempfile.TemporaryDirectory()
        home = os.path.join(tmp.name, "store")
        run_cli(home, "init")
        original = dict(import_cmd.ADAPTERS)
        import_cmd.ADAPTERS["granola"] = "flowsales.crm.granola_missing_for_test"
        try:
            code, out = run_cli(home, "import", "granola")
        finally:
            import_cmd.ADAPTERS.clear()
            import_cmd.ADAPTERS.update(original)
        self.assertEqual(code, 1)
        self.assertIn("granola adapter not available yet", out)
        self.assertFalse(Store(Path(home)).config.get("sources.granola.enabled"))
        tmp.cleanup()

    def test_granola_module_import_when_present(self):
        try:
            importlib.import_module("flowsales.crm.granola")
        except ModuleNotFoundError:
            self.skipTest("granola adapter not written yet")


if __name__ == "__main__":
    unittest.main()
