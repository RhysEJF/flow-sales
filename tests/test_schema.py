"""Tests for flowsales.schema.validate (CONTRACTS sections 5 and 8)."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from flowsales.schema.validate import (  # noqa: E402
    assessment_warnings,
    element_codes,
    tag_vocabulary,
    validate_assessment_shape,
    validate_records,
)

FRAMEWORK = json.loads((ROOT / "tests" / "fixtures" / "assess" / "frameworks" / "testfw.json").read_text("utf-8"))

DEAL = {
    "id": "hs:12345", "source": "hubspot", "name": "Acme expansion", "amount": 42000.0, "currency": "GBP",
    "pipeline": "default", "stage": "closedwon", "stageLabel": "Closed Won", "phase": "won",
    "stageHistory": [{"stage": "appointmentscheduled", "label": "Appointment Scheduled", "phase": "discovery", "at": "2026-03-01T10:00:00Z"}],
    "outcome": "won", "createdAt": "2026-03-01T10:00:00Z", "closedAt": "2026-06-14T00:00:00Z",
    "ownerId": "rep:41629779", "contactIds": ["c:1", "c:2"], "companyId": "co:7", "companyDomain": "acme.com", "meta": {},
}
INTERACTION = {
    "id": "granola:9f2c", "source": "granola", "type": "meeting", "dealId": "hs:12345", "direction": "outbound",
    "at": "2026-03-04T14:00:00Z", "durationSec": 1860, "title": "Acme discovery", "body": "Priya: hello",
    "transcript": [{"speaker": "Priya", "t": 12.5, "text": "hello"}], "notes": None, "summary": None,
    "participants": [{"name": "Priya Shah", "email": "priya@acme.com", "role": "buyer"}],
    "repId": "rep:41629779", "recordingUrl": None, "meta": {"hubspotType": "meetings"},
}
REP = {"id": "rep:41629779", "name": "Sam Rep", "email": "sam@vendor.com", "source": "hubspot"}
CONTACT = {"id": "c:1", "name": "Priya Shah", "email": "priya@acme.com", "title": "CFO", "companyId": "co:7", "buyingRole": None}
COMPANY = {"id": "co:7", "name": "Acme", "domain": "acme.com"}

BATCH = {"dealId": "hs:12345", "interactions": [{"interactionId": "granola:9f2c", "body": "Priya: hello"}]}


def good_assessment() -> dict:
    return {
        "dealId": "hs:12345", "framework": "testfw", "judgedAt": "2026-09-07T11:00:00Z", "model": "sonnet",
        "interactions": [{
            "interactionId": "granola:9f2c", "at": "2026-03-04T14:00:00Z", "phaseAtTime": "discovery",
            "applicable": ["M"], "notApplicableReason": {"E": "discovery call"},
            "elements": {"M": {"evidence": 2, "quote": "hello", "speaker": "buyer", "whyNotHigher": "One source.",
                               "nextQuestion": "Who owns it?", "confidence": "high", "behaviour": 1,
                               "behaviourTags": ["asked-metrics", "secured-next-step"]}},
            "hygiene": {"pitchBeforePain": False, "mutualNextStep": True, "repTalkRatio": None},
            "summary": "Discovery call.",
        }],
        "dealNotes": "Fine.",
    }


class RecordValidationTests(unittest.TestCase):
    def test_valid_records_pass(self):
        for kind, rec in (("deal", DEAL), ("interaction", INTERACTION), ("rep", REP), ("contact", CONTACT), ("company", COMPANY)):
            self.assertEqual(validate_records(kind, [rec]), [], kind)

    def test_deal_errors(self):
        bad = copy.deepcopy(DEAL)
        bad.pop("name")
        bad["phase"] = "closing"
        bad["outcome"] = "maybe"
        bad["createdAt"] = "yesterday"
        bad["stageHistory"][0]["at"] = "not-a-date"
        bad["contactIds"] = ["c:1", 7]
        errors = validate_records("deal", [bad])
        joined = "\n".join(errors)
        self.assertIn("missing required key 'name'", joined)
        self.assertIn("'phase' must be one of", joined)
        self.assertIn("'outcome' must be one of", joined)
        self.assertIn("'createdAt' is not an ISO 8601", joined)
        self.assertIn("stageHistory[0]", joined)
        self.assertIn("'contactIds' items", joined)

    def test_deal_id_prefix_and_duplicates(self):
        wrong = dict(DEAL, id="deal-1")
        self.assertTrue(any("id must start with" in e for e in validate_records("deal", [wrong])))
        dupes = validate_records("deal", [DEAL, copy.deepcopy(DEAL)])
        self.assertTrue(any("duplicate id" in e for e in dupes))

    def test_open_deal_without_close_is_valid(self):
        rec = dict(DEAL, outcome="open", closedAt=None, stage="qualifiedtobuy", phase="evaluation", stageHistory=[])
        self.assertEqual(validate_records("deal", [rec]), [])

    def test_interaction_errors(self):
        bad = copy.deepcopy(INTERACTION)
        bad["type"] = "sms"
        bad["direction"] = "sideways"
        bad.pop("at")
        bad["body"] = None
        bad["participants"] = ["priya@acme.com"]
        errors = validate_records("interaction", [bad])
        joined = "\n".join(errors)
        self.assertIn("'type' must be one of", joined)
        self.assertIn("'direction' must be one of", joined)
        self.assertIn("missing required timestamp 'at'", joined)
        self.assertIn("'body' must be a string", joined)
        self.assertIn("'participants' items", joined)

    def test_interaction_empty_body_allowed(self):
        rec = dict(INTERACTION, body="", transcript=None, dealId=None, repId=None)
        self.assertEqual(validate_records("interaction", [rec]), [])

    def test_interaction_id_prefix(self):
        rec = dict(INTERACTION, id="meeting-1")
        self.assertTrue(any("id must start with" in e for e in validate_records("interaction", [rec])))

    def test_rep_contact_company_errors(self):
        self.assertTrue(any("missing required key 'name'" in e for e in validate_records("rep", [{"id": "rep:1", "email": "a@b.c"}])))
        self.assertTrue(any("id must start with" in e for e in validate_records("contact", [{"id": "person:1", "name": "x"}])))
        self.assertTrue(any("id must start with" in e for e in validate_records("company", [{"id": "c:7", "name": "Acme"}])))
        self.assertTrue(any("'email' must be a string" in e for e in validate_records("contact", [{"id": "c:1", "email": 5}])))
        self.assertEqual(validate_records("contact", [{"id": "c:2", "name": None, "email": None}]), [])

    def test_unknown_kind_and_non_list(self):
        with self.assertRaises(ValueError):
            validate_records("widget", [])
        self.assertTrue(validate_records("deal", {"id": "hs:1"}))
        self.assertTrue(any("must be an object" in e for e in validate_records("deal", ["hs:1"])))


class AssessmentShapeTests(unittest.TestCase):
    def test_framework_helpers(self):
        self.assertEqual(element_codes(FRAMEWORK), ["M", "E"])
        vocab = tag_vocabulary(FRAMEWORK)
        self.assertIn("asked-metrics", vocab["M"])
        self.assertIn("secured-next-step", vocab["M"])
        self.assertNotIn("identified-eb", vocab["M"])

    def test_good_assessment_has_no_errors(self):
        self.assertEqual(validate_assessment_shape(good_assessment(), BATCH, FRAMEWORK), [])

    def test_unknown_interaction_and_deal_mismatch(self):
        a = good_assessment()
        a["interactions"][0]["interactionId"] = "granola:nope"
        a["dealId"] = "hs:999"
        errors = validate_assessment_shape(a, BATCH, FRAMEWORK)
        self.assertTrue(any("not in the batch" in e for e in errors))
        self.assertTrue(any("does not match the batch dealId" in e for e in errors))

    def test_missing_applicable_entry(self):
        a = good_assessment()
        a["interactions"][0]["applicable"] = ["M", "E"]
        errors = validate_assessment_shape(a, BATCH, FRAMEWORK)
        self.assertTrue(any("applicable element E has no entry" in e for e in errors))

    def test_element_value_errors(self):
        a = good_assessment()
        block = a["interactions"][0]["elements"]["M"]
        block["evidence"] = 4
        block["behaviour"] = 2
        block["behaviourTags"] = ["asked-metrics", "made-up-tag"]
        block["confidence"] = "certain"
        block["speaker"] = "champion"
        block["quote"] = 12
        errors = validate_assessment_shape(a, BATCH, FRAMEWORK)
        joined = "\n".join(errors)
        self.assertIn("out of range 0..3", joined)
        self.assertIn("behaviour must be 0 or 1", joined)
        self.assertIn("outside vocabulary: ['made-up-tag']", joined)
        self.assertIn("confidence must be one of", joined)
        self.assertIn("speaker must be buyer, rep or null", joined)
        self.assertIn("quote must be a string or null", joined)

    def test_unknown_element_and_bad_shapes(self):
        a = good_assessment()
        a["interactions"][0]["elements"]["X"] = {"evidence": 1}
        a["interactions"][0]["applicable"] = "M"
        errors = validate_assessment_shape(a, BATCH, FRAMEWORK)
        self.assertTrue(any("unknown element 'X'" in e for e in errors))
        self.assertTrue(any("applicable must be a list" in e for e in errors))
        self.assertEqual(validate_assessment_shape({"dealId": "hs:12345", "interactions": {}}, BATCH, FRAMEWORK), ["interactions must be a list"])
        self.assertEqual(validate_assessment_shape([], BATCH, FRAMEWORK), ["assessment must be a JSON object"])

    def test_missing_evidence_is_error(self):
        a = good_assessment()
        del a["interactions"][0]["elements"]["M"]["evidence"]
        self.assertTrue(any("evidence must be an integer" in e for e in validate_assessment_shape(a, BATCH, FRAMEWORK)))

    def test_warnings_for_optional_fields(self):
        a = good_assessment()
        entry = a["interactions"][0]
        entry["elements"]["E"] = {"evidence": 0}
        del entry["notApplicableReason"]
        del entry["summary"]
        del a["dealNotes"]
        entry["elements"]["M"]["speaker"] = None
        warnings = assessment_warnings(a, BATCH, FRAMEWORK)
        joined = "\n".join(warnings)
        self.assertIn("scored but not in applicable", joined)
        self.assertIn("missing optional fields", joined)
        self.assertIn("missing optional field 'summary'", joined)
        self.assertIn("missing optional field 'dealNotes'", joined)
        self.assertIn("evidence 2 without a speaker", joined)
        self.assertEqual(validate_assessment_shape(a, BATCH, FRAMEWORK), [])


if __name__ == "__main__":
    unittest.main()
