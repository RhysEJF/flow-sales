"""Tests for flowsales.assess.planner (plan-assessment, CONTRACTS section 7)."""
from __future__ import annotations

import datetime as _dt
import io
import json
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from flowsales.assess import planner  # noqa: E402
from flowsales.store import Store  # noqa: E402
from flowsales.util import parse_iso  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "assess"
UTC = _dt.timezone.utc


def make_deal(deal_id: str = "hs:1", **overrides) -> dict:
    deal = {
        "id": deal_id, "source": "hubspot", "name": "Acme expansion", "amount": 1000.0, "currency": "GBP",
        "pipeline": "default", "stage": "qualifiedtobuy", "stageLabel": "Qualified To Buy", "phase": "evaluation",
        "stageHistory": [], "outcome": "open", "createdAt": "2026-03-01T10:00:00Z", "closedAt": None,
        "ownerId": "rep:1", "contactIds": ["c:1"], "companyId": "co:1", "companyDomain": "acme.com", "meta": {"raw": 1},
    }
    deal.update(overrides)
    return deal


def make_interaction(iid: str, at: str, body: str, **overrides) -> dict:
    inter = {
        "id": iid, "source": "granola", "type": "meeting", "dealId": "hs:1", "direction": "outbound", "at": at,
        "durationSec": 1800, "title": "Acme call", "body": body, "transcript": None, "notes": None, "summary": None,
        "participants": [{"name": "Priya Shah", "email": "priya@acme.com", "role": "buyer"}], "repId": "rep:1",
        "recordingUrl": None, "meta": {},
    }
    inter.update(overrides)
    return inter


def args(**overrides) -> SimpleNamespace:
    base = {"force": False, "sample": None, "deal": None, "json": True, "home": None}
    base.update(overrides)
    return SimpleNamespace(**base)


class PlannerBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / ".flow-sales"
        self.store = Store(self.home)
        self.store.ensure()
        self.store.config.set("framework", "testfw")
        self.store.config.set("window", {"from": "2026-01-01", "to": "2026-12-31"})
        self.store.save_config()

    def tearDown(self):
        self._tmp.cleanup()

    def ctx(self, json_out: bool = True) -> dict:
        return {"store": self.store, "home": self.home, "plugin_root": FIXTURES, "json": json_out,
                "started": time.time(), "now": "2026-09-07T12:00:00Z"}

    def plan(self, **overrides) -> tuple[int, dict | str]:
        buf = io.StringIO()
        json_out = overrides.pop("json_out", True)
        with redirect_stdout(buf):
            code = planner.run(self.ctx(json_out), args(**overrides))
        out = buf.getvalue()
        return code, (json.loads(out) if json_out else out)

    def seed_single_deal(self) -> None:
        self.store.save_deals([make_deal()])
        self.store.save_interactions("hs:1", [
            make_interaction("granola:1", "2026-03-04T14:00:00Z", "Priya: month-end close takes 11 days."),
            make_interaction("granola:2", "2026-03-20T14:00:00Z", "Sam: who signs a purchase of this size?"),
            make_interaction("granola:3", "2026-03-25T14:00:00Z", "   "),
        ])


class PhaseAtTimeTests(PlannerBase):
    def test_phase_from_stage_history(self):
        deal = make_deal(stageHistory=[
            {"stage": "presentationscheduled", "label": "Presentation", "phase": "proposal", "at": "2026-04-01T00:00:00Z"},
            {"stage": "appointmentscheduled", "label": "Appointment", "phase": "discovery", "at": "2026-03-01T10:00:00Z"},
            {"stage": "qualifiedtobuy", "label": "Qualified", "phase": "evaluation", "at": "2026-03-10T10:00:00Z"},
        ])
        cfg = self.store.config
        cases = {
            "2026-02-20T09:00:00Z": "discovery",
            "2026-03-05T09:00:00Z": "discovery",
            "2026-03-10T10:00:00Z": "evaluation",
            "2026-03-20T09:00:00Z": "evaluation",
            "2026-05-01T09:00:00Z": "proposal",
        }
        for at, expected in cases.items():
            self.assertEqual(planner.phase_at_time(deal, parse_iso(at), cfg), expected, at)
        self.assertEqual(planner.phase_at_time(deal, None, cfg), "proposal")

    def test_phase_without_history_uses_stage_mapping(self):
        cfg = self.store.config
        self.assertEqual(planner.phase_at_time(make_deal(stage="contractsent"), parse_iso("2026-03-05T00:00:00Z"), cfg), "commit")
        self.assertEqual(planner.phase_at_time(make_deal(stage="custom1", stageLabel="Negotiation"), parse_iso("2026-03-05T00:00:00Z"), cfg), "commit")
        self.assertEqual(planner.phase_at_time(make_deal(stage=None, stageLabel=None, phase="proposal"), None, cfg), "proposal")

    def test_history_entry_without_phase_is_mapped(self):
        deal = make_deal(stageHistory=[{"stage": "closedwon", "label": "Closed Won", "at": "2026-06-01T00:00:00Z"}])
        self.assertEqual(planner.phase_at_time(deal, parse_iso("2026-07-01T00:00:00Z"), self.store.config), "won")


class PlanRunTests(PlannerBase):
    def test_writes_batch_and_plan(self):
        self.seed_single_deal()
        deal = make_deal(stageHistory=[
            {"stage": "appointmentscheduled", "label": "Appointment", "phase": "discovery", "at": "2026-03-01T10:00:00Z"},
            {"stage": "qualifiedtobuy", "label": "Qualified", "phase": "evaluation", "at": "2026-03-10T10:00:00Z"},
        ])
        self.store.save_deals([deal])
        code, out = self.plan()
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])
        self.assertEqual(out["totals"]["deals"], 1)
        self.assertEqual(out["totals"]["batches"], 1)
        self.assertEqual(out["totals"]["interactions"], 2, "the empty-body interaction is skipped")
        batch_path = Path(out["batches"][0]["file"])
        self.assertEqual(batch_path, self.store.batches_dir / "hs_1.json")
        batch = json.loads(batch_path.read_text("utf-8"))
        self.assertEqual(batch["batchId"], 1)
        self.assertEqual(batch["dealId"], "hs:1")
        self.assertEqual(batch["framework"], "testfw")
        self.assertEqual(batch["frameworkFile"], str(FIXTURES / "frameworks" / "testfw.json"))
        self.assertTrue(batch["rubricHash"].startswith("sha256:"))
        self.assertTrue(batch["inputHash"].startswith("sha256:"))
        self.assertEqual(batch["batchFile"], str(batch_path))
        self.assertNotIn("meta", batch["deal"])
        self.assertEqual(batch["deal"]["name"], "Acme expansion")
        self.assertEqual(batch["priorState"], {"M": 0, "E": 0})
        self.assertEqual(batch["outputFile"], str(self.store.assessment_path("hs:1")))
        self.assertEqual([i["interactionId"] for i in batch["interactions"]], ["granola:1", "granola:2"])
        self.assertEqual([i["phaseAtTime"] for i in batch["interactions"]], ["discovery", "evaluation"])
        for key in ("interactionId", "at", "type", "phaseAtTime", "title", "participants", "body"):
            self.assertIn(key, batch["interactions"][0])
        chars = sum(len(i["body"]) for i in batch["interactions"])
        self.assertEqual(out["batches"][0]["chars"], chars)
        self.assertEqual(out["batches"][0]["estTokens"], chars // 4 + 1500)
        plan = self.store.read_json("work/plan.json")
        self.assertEqual(plan["rubricHash"], batch["rubricHash"])
        self.assertEqual(plan["framework"], "testfw")
        self.assertEqual(plan["plannedAt"], "2026-09-07T12:00:00Z")
        self.assertEqual(plan["totals"], out["totals"])
        self.assertEqual({"batchId", "dealId", "file", "interactions", "chars", "estTokens"} - set(plan["batches"][0]), set())
        runs = [json.loads(line) for line in self.store.runs_path.read_text("utf-8").splitlines()]
        self.assertEqual(runs[-1]["command"], "plan-assessment")
        self.assertTrue(runs[-1]["ok"])
        self.assertIn(str(batch_path), runs[-1]["wrote"])

    def test_text_output_lists_batches(self):
        self.seed_single_deal()
        code, out = self.plan(json_out=False)
        self.assertEqual(code, 0)
        self.assertIn("Planned 1 batches for 1 deals", out)
        self.assertIn(str(self.store.batches_dir / "hs_1.json"), out)
        self.assertIn("tokens", out)

    def test_split_batches_with_prior_state(self):
        self.store.config.set("judge.maxInteractionChars", 100)
        self.store.save_config()
        self.store.save_deals([make_deal()])
        body = "x" * 60
        self.store.save_interactions("hs:1", [
            make_interaction("granola:3", "2026-03-25T14:00:00Z", body + "3"),
            make_interaction("granola:1", "2026-03-04T14:00:00Z", body + "1"),
            make_interaction("granola:2", "2026-03-20T14:00:00Z", body + "2"),
        ])
        self.store.write_json(self.store.assessment_path("hs:1"), {
            "dealId": "hs:1", "rubricHash": "sha256:stale", "inputHash": "sha256:stale",
            "interactions": [
                {"interactionId": "granola:1", "elements": {"M": {"evidence": 2}, "E": {"evidence": 0}}},
                {"interactionId": "granola:2", "elements": {"M": {"evidence": 1}, "E": {"evidence": 1}}},
                {"interactionId": "granola:3", "elements": {"M": {"evidence": 3}, "E": {"evidence": 3}}},
            ],
        })
        code, out = self.plan()
        self.assertEqual(code, 0)
        self.assertEqual(out["totals"]["batches"], 3)
        self.assertEqual(out["totals"]["deals"], 1)
        batches = [json.loads(Path(b["file"]).read_text("utf-8")) for b in out["batches"]]
        self.assertEqual([b["interactions"][0]["interactionId"] for b in batches], ["granola:1", "granola:2", "granola:3"])
        self.assertEqual([(b["part"], b["parts"]) for b in batches], [(1, 3), (2, 3), (3, 3)])
        self.assertEqual(batches[0]["priorState"], {"M": 0, "E": 0})
        self.assertEqual(batches[1]["priorState"], {"M": 2, "E": 0})
        self.assertEqual(batches[2]["priorState"], {"M": 2, "E": 1})
        self.assertEqual(out["batches"][0]["reason"], "interactions changed")

    def test_split_helper_keeps_oversized_single_interaction(self):
        parts = planner.split_batches([{"body": "a" * 500}, {"body": "b" * 10}], 100)
        self.assertEqual([len(p) for p in parts], [1, 1])

    def test_input_hash_change_detection(self):
        self.seed_single_deal()
        code, out = self.plan()
        self.assertEqual(out["totals"]["batches"], 1)
        batch = json.loads(Path(out["batches"][0]["file"]).read_text("utf-8"))
        self.store.write_json(self.store.assessment_path("hs:1"), {
            "dealId": "hs:1", "rubricHash": batch["rubricHash"], "inputHash": batch["inputHash"], "interactions": [],
        })
        code, out = self.plan()
        self.assertEqual(code, 0)
        self.assertEqual(out["totals"]["batches"], 0)
        self.assertEqual(out["skipped"]["unchanged"], 1)
        self.assertFalse((self.store.batches_dir / "hs_1.json").exists(), "old batches are cleared even when nothing is planned")
        inters = self.store.load_interactions("hs:1")
        inters[0]["body"] = inters[0]["body"] + " Sam: and who reports it?"
        self.store.save_interactions("hs:1", inters)
        code, out = self.plan()
        self.assertEqual(out["totals"]["batches"], 1)
        self.assertEqual(out["batches"][0]["reason"], "interactions changed")
        new_batch = json.loads(Path(out["batches"][0]["file"]).read_text("utf-8"))
        self.assertNotEqual(new_batch["inputHash"], batch["inputHash"])
        assessment = self.store.load_assessment("hs:1")
        assessment["inputHash"] = new_batch["inputHash"]
        assessment["rubricHash"] = "sha256:different"
        self.store.write_json(self.store.assessment_path("hs:1"), assessment)
        code, out = self.plan()
        self.assertEqual(out["batches"][0]["reason"], "rubric changed")
        assessment["rubricHash"] = new_batch["rubricHash"]
        self.store.write_json(self.store.assessment_path("hs:1"), assessment)
        code, out = self.plan()
        self.assertEqual(out["totals"]["batches"], 0)
        code, out = self.plan(force=True)
        self.assertEqual(out["batches"][0]["reason"], "forced")

    def test_adding_empty_interaction_does_not_change_hash(self):
        inters = [make_interaction("granola:1", "2026-03-04T14:00:00Z", "hello")]
        before = planner.input_hash(planner.judgeable(inters))
        inters.append(make_interaction("granola:9", "2026-03-05T14:00:00Z", ""))
        self.assertEqual(planner.input_hash(planner.judgeable(inters)), before)

    def test_window_reps_deal_and_sample_filters(self):
        deals = [
            make_deal("hs:a"),
            make_deal("hs:b", createdAt="2025-06-01T00:00:00Z", closedAt="2025-08-01T00:00:00Z", outcome="lost"),
            make_deal("hs:c", ownerId="rep:2", createdAt="2026-04-01T00:00:00Z"),
        ]
        self.store.save_deals(deals)
        for d in deals:
            self.store.save_interactions(d["id"], [make_interaction(f"granola:{d['id']}", "2026-03-04T14:00:00Z", "body text", dealId=d["id"])])
        code, out = self.plan()
        self.assertEqual(sorted(b["dealId"] for b in out["batches"]), ["hs:a", "hs:c"])
        self.assertEqual(out["considered"], 2)
        self.store.config.set("reps", ["rep:1"])
        self.store.save_config()
        code, out = self.plan()
        self.assertEqual([b["dealId"] for b in out["batches"]], ["hs:a"])
        code, out = self.plan(deal=["hs:b", "hs:zzz"])
        self.assertEqual([b["dealId"] for b in out["batches"]], ["hs:b"], "explicit --deal bypasses the window")
        self.assertEqual(out["skipped"]["notFound"], ["hs:zzz"])
        self.store.config.set("reps", "all")
        self.store.save_config()
        code, out = self.plan(sample=1)
        self.assertEqual(out["totals"]["batches"], 1)
        first = out["batches"][0]["dealId"]
        code, out = self.plan(sample=1)
        self.assertEqual(out["batches"][0]["dealId"], first, "sampling is seeded and stable")

    def test_deal_without_judgeable_interactions_is_skipped(self):
        self.store.save_deals([make_deal()])
        self.store.save_interactions("hs:1", [make_interaction("granola:1", "2026-03-04T14:00:00Z", "")])
        code, out = self.plan()
        self.assertEqual(code, 0)
        self.assertEqual(out["totals"]["batches"], 0)
        self.assertEqual(out["skipped"]["withoutInteractions"], 1)

    def test_missing_framework_fails_clearly(self):
        self.seed_single_deal()
        self.store.config.set("framework", "nope")
        self.store.save_config()
        code, out = self.plan()
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertIn("framework file not found", out["error"])
        self.assertIn("nope", out["error"])
        runs = [json.loads(line) for line in self.store.runs_path.read_text("utf-8").splitlines()]
        self.assertFalse(runs[-1]["ok"])

    def test_old_batches_are_cleared(self):
        self.seed_single_deal()
        stale = self.store.batches_dir / "99.json"
        self.store.write_json(stale, {"batchId": 99})
        code, out = self.plan()
        self.assertFalse(stale.exists())
        self.assertEqual(sorted(p.name for p in self.store.batches_dir.glob("*.json")), ["hs_1.json"])

    def test_no_store_returns_1(self):
        empty = Store(Path(self._tmp.name) / "nowhere")
        buf = io.StringIO()
        ctx = self.ctx()
        ctx["store"] = empty
        with redirect_stdout(buf):
            code = planner.run(ctx, args())
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
