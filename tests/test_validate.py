"""Tests for flowsales.assess.validate (validate-assessment, CONTRACTS 8.2)."""
from __future__ import annotations

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

from flowsales.assess import planner, validate  # noqa: E402
from flowsales.store import Store  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "assess"

BODY_1 = (
    "Priya: Month-end close takes us 11 days; we need it under 5 by the next audit.\n"
    "Sam: Who owns that number today?\n"
    "Priya: Our CFO, Dana, reports it to the board every quarter."
)
BODY_2 = "Sam: Who signs a purchase of this size?\nPriya: That would be Dana, she has the budget."


def make_deal(**overrides) -> dict:
    deal = {
        "id": "hs:1", "source": "hubspot", "name": "Acme expansion", "amount": 1000.0, "currency": "GBP",
        "pipeline": "default", "stage": "qualifiedtobuy", "stageLabel": "Qualified", "phase": "evaluation",
        "stageHistory": [{"stage": "appointmentscheduled", "label": "Appointment", "phase": "discovery", "at": "2026-03-01T10:00:00Z"}],
        "outcome": "open", "createdAt": "2026-03-01T10:00:00Z", "closedAt": None, "ownerId": "rep:1",
        "contactIds": ["c:1"], "companyId": "co:1", "companyDomain": "acme.com", "meta": {},
    }
    deal.update(overrides)
    return deal


def make_interaction(iid: str, at: str, body: str) -> dict:
    return {
        "id": iid, "source": "granola", "type": "meeting", "dealId": "hs:1", "direction": "outbound", "at": at,
        "durationSec": 1800, "title": "Acme call", "body": body, "transcript": None, "notes": None, "summary": None,
        "participants": [{"name": "Priya Shah", "email": "priya@acme.com", "role": "buyer"}], "repId": "rep:1",
        "recordingUrl": None, "meta": {},
    }


def element(evidence: int, quote, speaker="buyer", tags=None) -> dict:
    return {"evidence": evidence, "quote": quote, "speaker": speaker, "whyNotHigher": "One source.",
            "nextQuestion": "Who owns it?", "confidence": "high", "behaviour": 1 if tags else 0, "behaviourTags": tags or []}


def make_assessment(m_block: dict, e_block: dict | None = None, iid: str = "granola:1") -> dict:
    e_block = e_block or element(0, None, None)
    return {
        "dealId": "hs:1", "framework": "testfw", "judgedAt": "2026-09-07T11:00:00Z", "model": "sonnet",
        "interactions": [{
            "interactionId": iid, "at": "2026-03-04T14:00:00Z", "phaseAtTime": "discovery",
            "applicable": ["M", "E"], "notApplicableReason": {}, "elements": {"M": m_block, "E": e_block},
            "hygiene": {"pitchBeforePain": False, "mutualNextStep": True, "repTalkRatio": None},
            "summary": "Discovery call.",
        }],
        "dealNotes": "Fine.",
    }


class ValidateBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / ".flow-sales"
        self.store = Store(self.home)
        self.store.ensure()
        self.store.config.set("framework", "testfw")
        self.store.config.set("window", {"from": "2026-01-01", "to": "2026-12-31"})
        self.store.save_config()
        self.store.save_deals([make_deal()])
        self.store.save_interactions("hs:1", [
            make_interaction("granola:1", "2026-03-04T14:00:00Z", BODY_1),
            make_interaction("granola:2", "2026-03-20T14:00:00Z", BODY_2),
        ])
        self.plan()

    def tearDown(self):
        self._tmp.cleanup()

    def ctx(self, json_out: bool = True) -> dict:
        return {"store": self.store, "home": self.home, "plugin_root": FIXTURES, "json": json_out,
                "started": time.time(), "now": "2026-09-07T12:00:00Z"}

    def plan(self, **overrides) -> dict:
        buf = io.StringIO()
        base = {"force": True, "sample": None, "deal": None, "json": True, "home": None}
        base.update(overrides)
        with redirect_stdout(buf):
            planner.run(self.ctx(), SimpleNamespace(**base))
        return json.loads(buf.getvalue())

    def write_assessment(self, assessment: dict, name: str = "hs_1.json") -> Path:
        path = self.store.assessments_dir / name
        self.store.write_json(path, assessment)
        return path

    def validate(self, path: Path, json_out: bool = True) -> tuple[int, dict]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = validate.run(self.ctx(json_out), SimpleNamespace(file=str(path), json=json_out, home=None))
        return code, json.loads(buf.getvalue())

    def read(self, path: Path) -> dict:
        return json.loads(path.read_text("utf-8"))


class QuoteVerificationTests(unittest.TestCase):
    def test_substring_ignores_case_and_whitespace(self):
        ok, ratio = validate.verify_quote("month-end CLOSE takes us   11 days;  we need it under 5", BODY_1)
        self.assertTrue(ok)
        self.assertEqual(ratio, 1.0)

    def test_surrounding_quotation_marks_and_ellipsis_are_ignored(self):
        ok, _ = validate.verify_quote("“We need it under 5 by the next audit...”", BODY_1)
        self.assertTrue(ok)

    def test_fuzzy_match_with_small_typo(self):
        ok, ratio = validate.verify_quote("Month-end close takes us 11 days; we need it under 5 by the next audti", BODY_1)
        self.assertTrue(ok)
        self.assertGreaterEqual(ratio, 0.85)
        self.assertLess(ratio, 1.0)

    def test_fuzzy_match_inside_long_body(self):
        filler = " ".join(f"Sam: filler sentence number {i} about nothing in particular." for i in range(400))
        body = filler + "\n" + BODY_1 + "\n" + filler
        ok, ratio = validate.verify_quote("we need it under five by the next audit", body)
        self.assertTrue(ok, ratio)

    def test_fabricated_quote_fails(self):
        ok, ratio = validate.verify_quote("We have already signed off on the budget for this project", BODY_1)
        self.assertFalse(ok)
        self.assertLess(ratio, 0.85)

    def test_empty_inputs(self):
        self.assertEqual(validate.verify_quote("", BODY_1), (False, 0.0))
        self.assertEqual(validate.verify_quote("hello", ""), (False, 0.0))


class ValidateFileTests(ValidateBase):
    def test_verified_quote_keeps_score(self):
        path = self.write_assessment(make_assessment(element(2, "month-end close takes us 11 days; we need it under 5", tags=["asked-metrics"])))
        code, report = self.validate(path)
        self.assertEqual(code, 0, report)
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])
        self.assertEqual((report["capped"], report["verified"], report["unverified"]), (0, 1, 0))
        saved = self.read(path)
        block = saved["interactions"][0]["elements"]["M"]
        self.assertEqual(block["evidence"], 2)
        self.assertTrue(block["verified"])
        self.assertEqual(block["flags"], [])
        self.assertEqual(block["quoteMatch"], 1.0)

    def test_fuzzy_quote_is_verified(self):
        path = self.write_assessment(make_assessment(element(3, "Month-end close takes us 11 days; we need it under 5 by the next audti")))
        code, report = self.validate(path)
        self.assertEqual(code, 0)
        self.assertEqual(report["verified"], 1)
        self.assertEqual(self.read(path)["interactions"][0]["elements"]["M"]["evidence"], 3)

    def test_unverified_quote_is_capped_and_flagged(self):
        path = self.write_assessment(make_assessment(element(3, "We have already signed off on the budget for this project")))
        code, report = self.validate(path)
        self.assertEqual(code, 0, "capping is a correction, not a schema error")
        self.assertEqual((report["capped"], report["verified"], report["unverified"]), (1, 0, 1))
        block = self.read(path)["interactions"][0]["elements"]["M"]
        self.assertEqual(block["evidence"], 1)
        self.assertEqual(block["cappedFrom"], 3)
        self.assertFalse(block["verified"])
        self.assertEqual(block["flags"], ["quote-unverified"])

    def test_missing_quote_above_threshold_is_capped(self):
        path = self.write_assessment(make_assessment(element(2, None)))
        code, report = self.validate(path)
        self.assertEqual(report["capped"], 1)
        block = self.read(path)["interactions"][0]["elements"]["M"]
        self.assertEqual(block["evidence"], 1)
        self.assertEqual(block["flags"], ["quote-missing"])
        self.assertFalse(block["verified"])

    def test_level_one_without_quote_is_untouched(self):
        path = self.write_assessment(make_assessment(element(1, None)))
        code, report = self.validate(path)
        self.assertEqual(code, 0)
        self.assertEqual(report["capped"], 0)
        block = self.read(path)["interactions"][0]["elements"]["M"]
        self.assertEqual(block["evidence"], 1)
        self.assertEqual(block["flags"], [])
        self.assertNotIn("verified", block)

    def test_unverified_quote_at_level_one_is_flagged_not_capped(self):
        path = self.write_assessment(make_assessment(element(1, "nothing like this was said")))
        code, report = self.validate(path)
        self.assertEqual(report["capped"], 0)
        self.assertEqual(report["unverified"], 1)
        block = self.read(path)["interactions"][0]["elements"]["M"]
        self.assertEqual(block["evidence"], 1)
        self.assertEqual(block["flags"], ["quote-unverified"])

    def test_stamps_from_batch(self):
        assessment = make_assessment(element(1, None))
        del assessment["judgedAt"]
        path = self.write_assessment(assessment)
        code, report = self.validate(path)
        self.assertEqual(code, 0)
        batch = self.store.read_json("work/batches/1.json")
        saved = self.read(path)
        self.assertEqual(saved["rubricHash"], batch["rubricHash"])
        self.assertEqual(saved["inputHash"], batch["inputHash"])
        self.assertEqual(saved["batchId"], 1)
        self.assertEqual(saved["batchFile"], batch["batchFile"])
        self.assertTrue(saved["judgedAt"])
        self.assertTrue(saved["validatedAt"])
        self.assertEqual(saved["validation"]["capped"], 0)
        self.assertEqual(report["batchId"], 1)
        self.assertEqual(report["dealId"], "hs:1")
        self.assertTrue(any("judgedAt was missing" in w for w in report["warnings"]))
        runs = [json.loads(line) for line in self.store.runs_path.read_text("utf-8").splitlines()]
        self.assertEqual(runs[-1]["command"], "validate-assessment")
        self.assertIn(str(path), runs[-1]["wrote"])

    def test_schema_errors_exit_1(self):
        assessment = make_assessment(element(2, "month-end close takes us 11 days", tags=["made-up"]))
        assessment["interactions"].append({
            "interactionId": "granola:nope", "applicable": ["M"], "elements": {"M": element(1, None)},
        })
        path = self.write_assessment(assessment)
        code, report = self.validate(path)
        self.assertEqual(code, 1)
        self.assertFalse(report["ok"])
        self.assertTrue(any("not in the batch" in e for e in report["errors"]))
        self.assertTrue(any("outside vocabulary" in e for e in report["errors"]))
        self.assertTrue(report["wrote"], "corrections and stamps are still written so the judge sees them")
        self.assertTrue(any("could not be checked" in w for w in report["warnings"]))

    def test_batch_located_via_batch_file_when_plan_is_gone(self):
        batch = self.store.read_json("work/batches/1.json")
        (self.store.work_dir / "plan.json").unlink()
        assessment = make_assessment(element(1, None))
        assessment["batchFile"] = batch["batchFile"]
        path = self.write_assessment(assessment, "elsewhere.json")
        code, report = self.validate(path)
        self.assertEqual(code, 0, report)
        self.assertEqual(report["batchId"], 1)

    def test_batches_dir_scan_fallback(self):
        (self.store.work_dir / "plan.json").unlink()
        path = self.write_assessment(make_assessment(element(1, None)))
        code, report = self.validate(path)
        self.assertEqual(code, 0, report)

    def test_no_batch_is_an_error(self):
        for p in self.store.batches_dir.glob("*.json"):
            p.unlink()
        (self.store.work_dir / "plan.json").unlink()
        path = self.write_assessment(make_assessment(element(1, None)))
        code, report = self.validate(path)
        self.assertEqual(code, 1)
        self.assertTrue(any("no batch found" in e for e in report["errors"]))
        self.assertFalse(report["wrote"])

    def test_idempotent_then_restored_after_quote_fix(self):
        path = self.write_assessment(make_assessment(element(3, "nothing like this was said")))
        self.validate(path)
        code, report = self.validate(path)
        self.assertEqual(report["capped"], 0, "second run does not cap again")
        block = self.read(path)["interactions"][0]["elements"]["M"]
        self.assertEqual(block["flags"], ["quote-unverified"], "flags are not duplicated")
        self.assertEqual(block["evidence"], 1)
        saved = self.read(path)
        saved["interactions"][0]["elements"]["M"]["quote"] = "Our CFO, Dana, reports it to the board every quarter."
        self.store.write_json(path, saved)
        code, report = self.validate(path)
        self.assertEqual(report["restored"], 1)
        block = self.read(path)["interactions"][0]["elements"]["M"]
        self.assertEqual(block["evidence"], 3)
        self.assertNotIn("cappedFrom", block)
        self.assertEqual(block["flags"], [])
        self.assertTrue(block["verified"])

    def test_split_deal_validates_against_union_of_batches(self):
        self.store.config.set("judge.maxInteractionChars", 120)
        self.store.save_config()
        plan = self.plan()
        self.assertEqual(plan["totals"]["batches"], 2)
        assessment = make_assessment(element(2, "month-end close takes us 11 days"))
        assessment["interactions"].append({
            "interactionId": "granola:2", "at": "2026-03-20T14:00:00Z", "phaseAtTime": "discovery",
            "applicable": ["M", "E"], "notApplicableReason": {},
            "elements": {"M": element(0, None, None), "E": element(2, "That would be Dana, she has the budget", tags=["identified-eb"])},
            "hygiene": {}, "summary": "EB named.",
        })
        path = self.write_assessment(assessment)
        code, report = self.validate(path)
        self.assertEqual(code, 0, report)
        self.assertEqual(report["verified"], 2)
        saved = self.read(path)
        self.assertEqual(saved["batchIds"], [1, 2])
        self.assertEqual(saved["batchId"], 1)

    def test_missing_optional_fields_are_warnings(self):
        assessment = make_assessment({"evidence": 1})
        del assessment["interactions"][0]["summary"]
        del assessment["interactions"][0]["at"]
        path = self.write_assessment(assessment)
        code, report = self.validate(path)
        self.assertEqual(code, 0)
        self.assertTrue(any("missing optional fields" in w for w in report["warnings"]))
        block = self.read(path)["interactions"][0]["elements"]["M"]
        self.assertEqual(block["behaviour"], 0)
        self.assertEqual(block["behaviourTags"], [])
        self.assertEqual(self.read(path)["interactions"][0]["at"], "2026-03-04T14:00:00Z", "at is filled from the batch")

    def test_unreadable_file(self):
        path = self.store.assessments_dir / "missing.json"
        code, report = self.validate(path)
        self.assertEqual(code, 1)
        self.assertTrue(any("cannot read" in e for e in report["errors"]))
        bad = self.store.assessments_dir / "bad.json"
        bad.write_text("[1, 2]", encoding="utf-8")
        code, report = self.validate(bad)
        self.assertEqual(code, 1)
        self.assertIn("assessment must be a JSON object", report["errors"])

    def test_text_mode_prints_json_report(self):
        path = self.write_assessment(make_assessment(element(1, None)))
        code, report = self.validate(path, json_out=False)
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])


if __name__ == "__main__":
    unittest.main()
