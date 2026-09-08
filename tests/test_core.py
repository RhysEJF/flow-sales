"""Tests for the shared core: util, config, store, CLI init/config/status."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from flowsales import util  # noqa: E402
from flowsales.config import Config, default_config, resolve_hubspot_token  # noqa: E402
from flowsales.store import Store  # noqa: E402


class UtilTests(unittest.TestCase):
    def test_parse_iso_variants(self):
        self.assertEqual(util.to_iso(util.parse_iso("2026-03-04")), "2026-03-04T00:00:00Z")
        self.assertEqual(util.to_iso(util.parse_iso("2026-03-04T14:00:00Z")), "2026-03-04T14:00:00Z")
        self.assertEqual(util.to_iso(util.parse_iso("2026-03-04T15:00:00+01:00")), "2026-03-04T14:00:00Z")
        self.assertEqual(util.to_iso(util.parse_iso("1772632800000")), "2026-03-04T14:00:00Z")
        self.assertIsNone(util.parse_iso(None))
        self.assertIsNone(util.parse_iso("not a date"))

    def test_quarter_bounds(self):
        start, end = util.quarter_bounds("2026-Q3")
        self.assertEqual(util.to_iso(start), "2026-07-01T00:00:00Z")
        self.assertEqual(util.to_iso(end), "2026-10-01T00:00:00Z")
        start, end = util.quarter_bounds("2026-q4")
        self.assertEqual(util.to_iso(end), "2027-01-01T00:00:00Z")
        with self.assertRaises(ValueError):
            util.quarter_bounds("2026-Q5")

    def test_hash_and_ids(self):
        self.assertEqual(util.sha256_of({"b": 1, "a": 2}), util.sha256_of({"a": 2, "b": 1}))
        self.assertEqual(util.safe_id("hs:call:12"), "hs_call_12")
        self.assertEqual(util.email_domain("Priya@Acme.com"), "acme.com")
        self.assertIsNone(util.email_domain("nope"))

    def test_normalize_and_transcript(self):
        self.assertEqual(util.normalize_text("  It’s  “Fine” —ok "), "it's \"fine\" -ok")
        body = util.transcript_to_body([{"speaker": "Priya", "t": 1, "text": "Hello"}, {"speaker": "", "text": "  "}, {"text": "x"}])
        self.assertEqual(body, "Priya: Hello\nUnknown: x")

    def test_dotted(self):
        obj: dict = {}
        util.set_dotted(obj, "a.b.c", 1)
        self.assertEqual(util.get_dotted(obj, "a.b.c"), 1)
        self.assertEqual(util.get_dotted(obj, "a.x", "d"), "d")


class ConfigTests(unittest.TestCase):
    def test_defaults_and_merge(self):
        cfg = Config({"framework": "meddic"}, Path("/tmp/x.json"))
        self.assertEqual(cfg.framework, "meddic")
        self.assertEqual(cfg.get("judge.parallel"), 5)
        self.assertIn("appointmentscheduled", cfg.data["stagePhases"])
        self.assertEqual(cfg.get("consent"), {"repsInformed": None, "audience": None}, "setup records who was told and who sees the report")
        self.assertEqual(cfg.get("attribution.decayDays"), 45)

    def test_phase_for_stage(self):
        cfg = Config(default_config(), Path("/tmp/x.json"))
        self.assertEqual(cfg.phase_for_stage("closedwon"), "won")
        self.assertEqual(cfg.phase_for_stage("custom1", "Contract Sent"), "commit")
        self.assertEqual(cfg.phase_for_stage("custom2", "Discovery Call"), "discovery")
        self.assertEqual(cfg.phase_for_stage("custom3", "Weird"), "evaluation")
        self.assertEqual(cfg.phase_for_stage(None), "evaluation")

    def test_internal_domains(self):
        cfg = Config({"org": {"internalDomains": ["Vendor.com"]}}, Path("/tmp/x.json"))
        doms = cfg.internal_domains([{"email": "sam@northwind.example"}])
        self.assertEqual(doms, {"vendor.com", "northwind.example"})

    def test_token_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cfg = Config(default_config(), home / "config.json")
            old = os.environ.pop("HUBSPOT_ACCESS_TOKEN", None)
            try:
                self.assertIsNone(resolve_hubspot_token(cfg, home))
                (home / "secrets.json").write_text(json.dumps({"hubspot_token": "pat-x"}), encoding="utf-8")
                self.assertEqual(resolve_hubspot_token(cfg, home), "pat-x")
                os.environ["HUBSPOT_ACCESS_TOKEN"] = "pat-env"
                self.assertEqual(resolve_hubspot_token(cfg, home), "pat-env")
            finally:
                os.environ.pop("HUBSPOT_ACCESS_TOKEN", None)
                if old:
                    os.environ["HUBSPOT_ACCESS_TOKEN"] = old


class StoreTests(unittest.TestCase):
    def test_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / ".flow-sales")
            store.ensure()
            store.save_deals([{"id": "demo:2"}, {"id": "demo:1"}])
            self.assertEqual([d["id"] for d in store.load_deals()], ["demo:1", "demo:2"])
            store.save_interactions("demo:1", [{"id": "b", "at": "2026-02-01T00:00:00Z"}, {"id": "a", "at": "2026-01-01T00:00:00Z"}])
            self.assertEqual([i["id"] for i in store.load_interactions("demo:1")], ["a", "b"])
            store.save_unlinked([{"id": "u", "at": "2026-01-01T00:00:00Z"}])
            got = list(store.iter_all_interactions())
            self.assertEqual(len(got), 3)
            self.assertIn((None, {"id": "u", "at": "2026-01-01T00:00:00Z"}), got)
            merged = Store.upsert([{"id": "x", "a": 1}], [{"id": "x", "b": 2}, {"id": "y"}])
            self.assertEqual(len(merged), 2)
            self.assertEqual(merged[0], {"id": "x", "a": 1, "b": 2})
            store.log_run("test", {"k": 1}, True, 0.0, read=["r"], wrote=["w"])
            line = json.loads(store.runs_path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(line["command"], "test")
            self.assertTrue(line["ok"])


class CliTests(unittest.TestCase):
    def run_fs(self, home: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPTS / "fs.py"), "--home", str(home), *args], capture_output=True, text=True)

    def test_init_config_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".flow-sales"
            r = self.run_fs(home, "init")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((home / "config.json").exists())
            r = self.run_fs(home, "config", "set", "trainingDate", '"2026-05-01"')
            self.assertEqual(r.returncode, 0, r.stderr)
            r = self.run_fs(home, "config", "get", "trainingDate", "--json")
            self.assertEqual(json.loads(r.stdout)["value"], "2026-05-01")
            r = self.run_fs(home, "status", "--json")
            self.assertEqual(r.returncode, 0, r.stderr)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["deals"], 0)
            self.assertEqual(payload["framework"], "meddpicc")

    def test_log_records_the_named_command(self):
        # Skills log with `fs.py log --command standup`; the option must not collide with the subcommand slot.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".flow-sales"
            self.assertEqual(self.run_fs(home, "init").returncode, 0)
            r = self.run_fs(home, "log", "--command", "standup", "--note", "Tom Ellis 2026-09-08")
            self.assertEqual(r.returncode, 0, r.stderr)
            last = json.loads((home / "runs.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual((last["command"], last["notes"], last["ok"]), ("standup", "Tom Ellis 2026-09-08", True))

    def test_status_reports_last_run_per_command(self):
        # The status skill prints "last audit ..." from runs.jsonl; skills log themselves with `fs.py log --command`.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".flow-sales"
            self.assertEqual(self.run_fs(home, "init").returncode, 0)
            self.assertEqual(self.run_fs(home, "log", "--command", "audit", "--note", "benchmark").returncode, 0)
            r = self.run_fs(home, "status", "--json")
            payload = json.loads(r.stdout)
            self.assertIn("audit", payload["lastRun"])
            self.assertNotIn("report", payload["lastRun"])
            self.assertIsNone(payload["latestReport"])

    def test_missing_store_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_fs(Path(tmp) / "nope", "status")
            self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
