"""Tests for flowsales.link.linker (CONTRACTS section 6)."""
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

from flowsales.link import linker  # noqa: E402
from flowsales.store import Store  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "assess"
NOW = "2026-09-07T12:00:00Z"

PRIYA = {"name": "Priya Shah", "email": "priya@acme.com", "role": "buyer"}
WEI = {"name": "Wei Chen", "email": "wei@globex.io", "role": "buyer"}
SAM = {"name": "Sam Rep", "email": "sam@vendor.com", "role": "rep"}


def make_deal(deal_id: str, name: str, **overrides) -> dict:
    deal = {
        "id": deal_id, "source": "hubspot", "name": name, "amount": 1000.0, "currency": "GBP", "pipeline": "default",
        "stage": "qualifiedtobuy", "stageLabel": "Qualified", "phase": "evaluation", "stageHistory": [], "outcome": "open",
        "createdAt": "2026-03-01T10:00:00Z", "closedAt": None, "ownerId": "rep:1", "contactIds": [], "companyId": None,
        "companyDomain": None, "meta": {},
    }
    deal.update(overrides)
    return deal


def make_interaction(iid: str, at: str, participants: list[dict], **overrides) -> dict:
    inter = {
        "id": iid, "source": "granola", "type": "meeting", "dealId": None, "direction": "outbound", "at": at,
        "durationSec": 1800, "title": "Weekly sync", "body": "Priya: hello there, this is a transcript body.",
        "transcript": [{"speaker": "Priya", "t": 0.0, "text": "hello there, this is a transcript body."}],
        "notes": None, "summary": None, "participants": participants, "repId": None, "recordingUrl": None, "meta": {},
    }
    inter.update(overrides)
    return inter


def args(action: str = "run", iid: str | None = None, deal_id: str | None = None, dry_run: bool = False) -> SimpleNamespace:
    return SimpleNamespace(action=action, interaction_id=iid, deal_id=deal_id, dry_run=dry_run, json=True, home=None)


class LinkerBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / ".flow-sales"
        self.store = Store(self.home)
        self.store.ensure()
        self.store.config.set("window", {"from": "2026-01-01", "to": "2026-12-31"})
        self.store.save_config()
        self.store.save_reps([{"id": "rep:1", "name": "Sam Rep", "email": "sam@vendor.com", "source": "hubspot"}])
        self.store.save_contacts([
            {"id": "c:1", "name": "Priya Shah", "email": "priya@acme.com", "title": "CFO", "companyId": "co:1", "buyingRole": None},
            {"id": "c:2", "name": "Wei Chen", "email": "wei@globex.io", "title": "COO", "companyId": "co:2", "buyingRole": None},
        ])
        self.store.save_companies([
            {"id": "co:1", "name": "Acme", "domain": "acme.com"},
            {"id": "co:2", "name": "Globex", "domain": "globex.io"},
        ])
        self.store.save_deals([
            make_deal("hs:1", "Acme expansion", contactIds=["c:1"], companyId="co:1", companyDomain="acme.com"),
            make_deal("hs:2", "Globex renewal", contactIds=["c:2"], companyId="co:2", companyDomain="globex.io",
                      createdAt="2026-02-01T10:00:00Z", closedAt="2026-05-01T00:00:00Z", outcome="won", stage="closedwon", phase="won"),
        ])

    def tearDown(self):
        self._tmp.cleanup()

    def ctx(self) -> dict:
        return {"store": self.store, "home": self.home, "plugin_root": FIXTURES, "json": True, "started": time.time(), "now": NOW}

    def run_link(self, *a, **kw) -> tuple[int, dict]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = linker.run(self.ctx(), args(*a, **kw))
        return code, json.loads(buf.getvalue())

    def links(self) -> list[dict]:
        return self.store.load_links()["links"]

    def link_for(self, iid: str, status: str | None = None) -> dict | None:
        for link in self.links():
            if link["interactionId"] == iid and (status is None or link["status"] == status):
                return link
        return None

    def ids_in(self, deal_id: str) -> list[str]:
        return [i["id"] for i in self.store.load_interactions(deal_id)]


class RuleTests(LinkerBase):
    def test_crm_association_is_auto(self):
        self.store.save_unlinked([make_interaction("hs:call:1", "2026-03-05T10:00:00Z", [PRIYA], source="hubspot", type="call", dealId="hs:1")])
        code, out = self.run_link()
        self.assertEqual(code, 0)
        self.assertEqual(out["counts"], {"linked": 1, "merged": 0, "pending": 0, "unmatched": 0})
        self.assertEqual(self.ids_in("hs:1"), ["hs:call:1"])
        self.assertEqual(self.store.load_unlinked(), [])
        rec = self.store.load_interactions("hs:1")[0]
        self.assertEqual(rec["dealId"], "hs:1")
        self.assertEqual(rec["repId"], "rep:1", "repId falls back to the deal owner")
        link = self.link_for("hs:call:1")
        self.assertEqual((link["method"], link["confidence"], link["status"], link["by"]), ("crm-association", 1.0, "auto", "linker"))
        self.assertEqual(set(link["evidence"]), {"matchedEmails", "domain", "matchedHubspotMeeting", "titleHit"})

    def test_crm_association_to_unknown_deal_stays_unlinked(self):
        self.store.save_unlinked([make_interaction("hs:call:2", "2026-03-05T10:00:00Z", [PRIYA], source="hubspot", type="call", dealId="hs:404")])
        code, out = self.run_link()
        self.assertEqual(out["counts"]["unmatched"], 1)
        self.assertTrue(any("hs:404" in n for n in out["notes"]))
        self.assertEqual(self.store.load_unlinked()[0]["candidates"], [])

    def test_time_match_merges_into_hubspot_meeting(self):
        hs_meeting = make_interaction("hs:meeting:9", "2026-03-04T14:00:00Z", [PRIYA, SAM], source="hubspot", dealId="hs:1",
                                      title="Acme discovery", body="Discovery meeting", transcript=None, repId="rep:1")
        self.store.save_interactions("hs:1", [hs_meeting])
        granola = make_interaction("granola:abc", "2026-03-04T14:10:00Z", [PRIYA], title="Acme <> Vendor",
                                   body="Priya: " + "a long transcript " * 20, summary="AI summary")
        self.store.save_unlinked([granola])
        code, out = self.run_link()
        self.assertEqual(out["counts"]["linked"], 1)
        self.assertEqual(out["counts"]["merged"], 1)
        self.assertEqual(out["merged"][0], {"interactionId": "granola:abc", "into": "hs:meeting:9", "dealId": "hs:1"})
        records = self.store.load_interactions("hs:1")
        self.assertEqual([r["id"] for r in records], ["hs:meeting:9"], "one record survives")
        kept = records[0]
        self.assertTrue(kept["body"].startswith("Priya: a long transcript"))
        self.assertEqual(kept["transcript"], granola["transcript"])
        self.assertEqual(kept["summary"], "AI summary")
        self.assertEqual(kept["title"], "Acme discovery")
        self.assertEqual(kept["meta"]["mergedFrom"], "granola:abc")
        self.assertEqual([p["email"] for p in kept["participants"]], ["priya@acme.com", "sam@vendor.com"])
        self.assertEqual(self.store.load_unlinked(), [])
        link = self.link_for("granola:abc")
        self.assertEqual((link["method"], link["confidence"], link["status"]), ("time-match", 0.95, "auto"))
        self.assertEqual(link["evidence"]["matchedHubspotMeeting"], "hs:meeting:9")
        self.assertEqual(link["mergedInto"], "hs:meeting:9")

    def test_time_match_by_title_only(self):
        hs_meeting = make_interaction("hs:meeting:9", "2026-03-04T14:00:00Z", [SAM], source="hubspot", dealId="hs:1", title="Acme discovery", body="x")
        self.store.save_interactions("hs:1", [hs_meeting])
        self.store.save_unlinked([make_interaction("tx:1", "2026-03-04T13:50:00Z", [], type="transcript", title="ACME Discovery")])
        code, out = self.run_link()
        self.assertEqual(out["counts"]["merged"], 1)
        self.assertEqual(self.link_for("tx:1")["method"], "time-match")

    def test_time_match_needs_proximity_and_overlap(self):
        hs_meeting = make_interaction("hs:meeting:9", "2026-03-04T14:00:00Z", [PRIYA], source="hubspot", dealId="hs:1", title="Acme discovery", body="x")
        self.store.save_interactions("hs:1", [hs_meeting])
        self.store.save_unlinked([
            make_interaction("granola:far", "2026-03-04T15:00:00Z", [{"name": "Bob", "email": "bob@acme.com"}], title="Other"),
            make_interaction("granola:email", "2026-03-04T14:05:00Z", [PRIYA], type="email", title="Re: Acme discovery"),
        ])
        code, out = self.run_link()
        self.assertEqual(out["counts"]["merged"], 0)
        self.assertEqual(self.link_for("granola:far")["method"], "domain-match")
        self.assertEqual(self.link_for("granola:email")["method"], "email-match", "emails never time-match, they email-match")

    def test_email_match_is_auto_at_threshold(self):
        self.store.save_unlinked([make_interaction("granola:1", "2026-03-10T10:00:00Z", [PRIYA, SAM])])
        code, out = self.run_link()
        self.assertEqual(out["counts"]["linked"], 1)
        link = self.link_for("granola:1")
        self.assertEqual((link["method"], link["confidence"], link["status"]), ("email-match", 0.9, "auto"))
        self.assertEqual(link["evidence"]["matchedEmails"], ["priya@acme.com"])
        self.assertEqual(link["evidence"]["domain"], "acme.com", "evidence from lower rules is kept")
        self.assertEqual(self.ids_in("hs:1"), ["granola:1"])
        self.assertEqual(self.store.load_interactions("hs:1")[0]["repId"], "rep:1")

    def test_email_match_respects_deal_window(self):
        self.store.save_unlinked([
            make_interaction("granola:early", "2026-01-15T10:00:00Z", [PRIYA]),
            make_interaction("granola:grace", "2026-02-20T10:00:00Z", [PRIYA]),
            make_interaction("granola:late", "2026-06-01T10:00:00Z", [WEI]),
            make_interaction("granola:closegrace", "2026-05-10T10:00:00Z", [WEI]),
        ])
        code, out = self.run_link()
        self.assertEqual(sorted(out["unmatched"]), ["granola:early", "granola:late"])
        self.assertEqual(self.link_for("granola:grace")["dealId"], "hs:1")
        self.assertEqual(self.link_for("granola:closegrace")["dealId"], "hs:2")

    def test_domain_match_is_pending(self):
        self.store.save_unlinked([make_interaction("granola:d", "2026-03-10T10:00:00Z", [{"name": "Bob", "email": "bob@acme.com"}])])
        code, out = self.run_link()
        self.assertEqual(out["counts"], {"linked": 0, "merged": 0, "pending": 1, "unmatched": 0})
        unlinked = self.store.load_unlinked()
        self.assertEqual(len(unlinked), 1)
        self.assertEqual(unlinked[0]["candidates"], [{"dealId": "hs:1", "dealName": "Acme expansion", "method": "domain-match", "confidence": 0.7}])
        link = self.link_for("granola:d")
        self.assertEqual((link["status"], link["method"], link["confidence"]), ("pending", "domain-match", 0.7))
        self.assertEqual(link["evidence"]["domain"], "acme.com")
        self.assertEqual(link["candidates"][0]["dealId"], "hs:1")
        self.assertEqual(self.ids_in("hs:1"), [])
        self.assertEqual(out["pending"][0]["candidates"][0]["dealName"], "Acme expansion")

    def test_domain_tie_lists_all_candidates(self):
        deals = self.store.load_deals()
        deals.append(make_deal("hs:3", "Acme renewal", companyId="co:1", companyDomain="acme.com"))
        self.store.save_deals(deals)
        self.store.save_unlinked([make_interaction("granola:d", "2026-03-10T10:00:00Z", [{"name": "Bob", "email": "bob@acme.com"}])])
        code, out = self.run_link()
        self.assertEqual(out["counts"]["pending"], 1)
        self.assertEqual([c["dealId"] for c in self.store.load_unlinked()[0]["candidates"]], ["hs:1", "hs:3"])

    def test_single_top_candidate_wins_over_weaker_ones(self):
        deals = self.store.load_deals()
        deals.append(make_deal("hs:3", "Acme renewal", companyId="co:1", companyDomain="acme.com"))
        self.store.save_deals(deals)
        self.store.save_unlinked([make_interaction("granola:p", "2026-03-10T10:00:00Z", [PRIYA])])
        code, out = self.run_link()
        self.assertEqual(out["counts"]["linked"], 1)
        link = self.link_for("granola:p")
        self.assertEqual(link["dealId"], "hs:1")
        self.assertEqual([c["dealId"] for c in link["candidates"]], ["hs:3"], "alternatives are recorded")

    def test_tie_at_top_is_pending(self):
        deals = self.store.load_deals()
        deals.append(make_deal("hs:3", "Acme renewal", contactIds=["c:1"], companyId="co:1", companyDomain="acme.com"))
        self.store.save_deals(deals)
        self.store.save_unlinked([make_interaction("granola:p", "2026-03-10T10:00:00Z", [PRIYA])])
        code, out = self.run_link()
        self.assertEqual(out["counts"]["pending"], 1)
        self.assertEqual([c["confidence"] for c in self.store.load_unlinked()[0]["candidates"]], [0.9, 0.9])

    def test_title_match_whole_word(self):
        self.store.save_unlinked([
            make_interaction("granola:t1", "2026-03-01T10:00:00Z", [SAM], title="Kickoff with GLOBEX team"),
            make_interaction("granola:t2", "2026-03-01T10:00:00Z", [SAM], title="Globexx notes"),
        ])
        code, out = self.run_link()
        link = self.link_for("granola:t1")
        self.assertEqual((link["status"], link["method"], link["confidence"], link["dealId"]), ("pending", "title-match", 0.5, "hs:2"))
        self.assertEqual(link["evidence"]["titleHit"], "Globex")
        self.assertIn("granola:t2", out["unmatched"])

    def test_internal_domains_never_count(self):
        contacts = self.store.load_contacts()
        contacts.append({"id": "c:9", "name": "Tom Vendor", "email": "tom@vendor.com", "title": None, "companyId": "co:1", "buyingRole": None})
        contacts.append({"id": "c:10", "name": "Pat Partner", "email": "pat@partner.org", "title": None, "companyId": "co:1", "buyingRole": None})
        self.store.save_contacts(contacts)
        deals = self.store.load_deals()
        deals[0]["contactIds"] = ["c:1", "c:9", "c:10"]
        self.store.save_deals(deals)
        self.store.config.set("org.internalDomains", ["partner.org"])
        self.store.save_config()
        self.store.save_unlinked([
            make_interaction("granola:rep", "2026-03-10T10:00:00Z", [{"name": "Tom", "email": "tom@vendor.com"}]),
            make_interaction("granola:partner", "2026-03-10T10:00:00Z", [{"name": "Pat", "email": "pat@partner.org"}]),
        ])
        code, out = self.run_link()
        self.assertEqual(sorted(out["unmatched"]), ["granola:partner", "granola:rep"])

    def test_internal_company_domain_is_ignored(self):
        deals = self.store.load_deals()
        deals[0]["companyDomain"] = "vendor.com"
        self.store.save_deals(deals)
        self.store.save_unlinked([make_interaction("granola:x", "2026-03-10T10:00:00Z", [{"name": "Tom", "email": "tom@vendor.com"}])])
        code, out = self.run_link()
        self.assertEqual(out["unmatched"], ["granola:x"])

    def test_rejected_pairs_are_suppressed(self):
        self.store.save_links({"version": 1, "links": [
            {"interactionId": "granola:r1", "dealId": "hs:1", "method": "email-match", "confidence": 0.9, "status": "rejected",
             "evidence": {}, "candidates": [], "at": NOW, "by": "user"},
            {"interactionId": "granola:r2", "dealId": None, "method": "manual", "confidence": 1.0, "status": "rejected",
             "evidence": {}, "candidates": [], "at": NOW, "by": "user"},
        ]})
        self.store.save_unlinked([
            make_interaction("granola:r1", "2026-03-10T10:00:00Z", [PRIYA]),
            make_interaction("granola:r2", "2026-03-10T10:00:00Z", [PRIYA]),
        ])
        code, out = self.run_link()
        self.assertEqual(sorted(out["unmatched"]), ["granola:r1", "granola:r2"])
        self.assertEqual(len([l for l in self.links() if l["status"] == "rejected"]), 2, "rejected links are kept")

    def test_accepted_link_is_honoured_without_recompute(self):
        self.store.save_links({"version": 1, "links": [
            {"interactionId": "granola:c", "dealId": "hs:2", "method": "manual", "confidence": 1.0, "status": "confirmed",
             "evidence": {}, "candidates": [], "at": NOW, "by": "user"},
        ]})
        self.store.save_unlinked([make_interaction("granola:c", "2026-03-10T10:00:00Z", [PRIYA])])
        code, out = self.run_link()
        self.assertEqual(self.ids_in("hs:2"), ["granola:c"])
        self.assertEqual(self.link_for("granola:c")["status"], "confirmed")

    def test_already_linked_records_are_not_relinked(self):
        self.store.save_interactions("hs:2", [make_interaction("granola:z", "2026-03-10T10:00:00Z", [PRIYA], dealId="hs:2")])
        self.store.save_unlinked([make_interaction("granola:z", "2026-03-10T10:00:00Z", [PRIYA])])
        code, out = self.run_link()
        self.assertEqual(self.ids_in("hs:2"), ["granola:z"])
        self.assertEqual(self.ids_in("hs:1"), [])
        self.assertEqual(self.store.load_unlinked(), [])

    def test_dry_run_writes_nothing(self):
        self.store.save_unlinked([make_interaction("granola:1", "2026-03-10T10:00:00Z", [PRIYA])])
        before = {p: p.read_text("utf-8") for p in self.store.data_dir.rglob("*.json")}
        code, out = self.run_link(dry_run=True)
        self.assertEqual(code, 0)
        self.assertTrue(out["dryRun"])
        self.assertEqual(out["counts"]["linked"], 1)
        after = {p: p.read_text("utf-8") for p in self.store.data_dir.rglob("*.json")}
        self.assertEqual(before, after)
        self.assertEqual(self.ids_in("hs:1"), [])


class ResolveTests(LinkerBase):
    def seed_pending(self) -> None:
        deals = self.store.load_deals()
        deals.append(make_deal("hs:3", "Acme renewal", companyId="co:1", companyDomain="acme.com"))
        self.store.save_deals(deals)
        self.store.save_unlinked([make_interaction("granola:d", "2026-03-10T10:00:00Z", [{"name": "Bob", "email": "bob@acme.com"}])])
        self.run_link()

    def test_pending_command_lists_candidates(self):
        self.seed_pending()
        code, out = self.run_link("pending")
        self.assertEqual(code, 0)
        self.assertEqual(len(out["pending"]), 1)
        item = out["pending"][0]
        self.assertEqual(item["id"], "granola:d")
        self.assertEqual(item["participants"], [{"name": "Bob", "email": "bob@acme.com"}])
        self.assertEqual([c["dealName"] for c in item["candidates"]], ["Acme expansion", "Acme renewal"])
        self.assertEqual(out["unmatched"], 0)

    def test_confirm_moves_record_and_records_user(self):
        self.seed_pending()
        code, out = self.run_link("confirm", "granola:d", "hs:3")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ids_in("hs:3"), ["granola:d"])
        self.assertEqual(self.store.load_unlinked(), [])
        rec = self.store.load_interactions("hs:3")[0]
        self.assertEqual(rec["dealId"], "hs:3")
        self.assertNotIn("candidates", rec)
        link = self.link_for("granola:d")
        self.assertEqual((link["status"], link["by"], link["method"], link["confidence"]), ("confirmed", "user", "domain-match", 0.7))
        self.assertIsNone(self.link_for("granola:d", "pending"))
        code, out = self.run_link("pending")
        self.assertEqual(out["pending"], [])

    def test_confirm_non_candidate_is_manual(self):
        self.seed_pending()
        code, out = self.run_link("confirm", "granola:d", "hs:2")
        self.assertEqual(code, 0)
        link = self.link_for("granola:d")
        self.assertEqual((link["status"], link["method"], link["confidence"]), ("confirmed", "manual", 1.0))
        self.assertEqual(self.ids_in("hs:2"), ["granola:d"])

    def test_confirm_errors(self):
        self.seed_pending()
        self.assertEqual(self.run_link("confirm", "granola:d", "hs:404")[0], 1)
        self.assertEqual(self.run_link("confirm", "granola:nope", "hs:1")[0], 1)
        self.assertEqual(self.run_link("confirm", "granola:d", None)[0], 1)

    def test_confirm_moves_between_deals(self):
        self.store.save_unlinked([make_interaction("granola:1", "2026-03-10T10:00:00Z", [PRIYA])])
        self.run_link()
        self.assertEqual(self.ids_in("hs:1"), ["granola:1"])
        code, out = self.run_link("confirm", "granola:1", "hs:2")
        self.assertEqual(self.ids_in("hs:1"), [])
        self.assertEqual(self.ids_in("hs:2"), ["granola:1"])
        self.assertEqual(len([l for l in self.links() if l["interactionId"] == "granola:1"]), 1)

    def test_reject_one_candidate_keeps_the_other(self):
        self.seed_pending()
        code, out = self.run_link("reject", "granola:d", "hs:1")
        self.assertEqual(code, 0)
        self.assertEqual([c["dealId"] for c in out["remainingCandidates"]], ["hs:3"])
        unlinked = self.store.load_unlinked()
        self.assertEqual([c["dealId"] for c in unlinked[0]["candidates"]], ["hs:3"])
        rejected = self.link_for("granola:d", "rejected")
        self.assertEqual((rejected["dealId"], rejected["by"], rejected["method"]), ("hs:1", "user", "domain-match"))
        pending = self.link_for("granola:d", "pending")
        self.assertEqual(pending["dealId"], "hs:3")
        code, out = self.run_link()
        self.assertEqual(out["counts"]["pending"], 1)
        self.assertEqual([c["dealId"] for c in self.store.load_unlinked()[0]["candidates"]], ["hs:3"], "rejected deal is not proposed again")

    def test_reject_all_suppresses_interaction(self):
        self.seed_pending()
        code, out = self.run_link("reject", "granola:d")
        self.assertEqual(code, 0)
        self.assertEqual(self.store.load_unlinked()[0]["candidates"], [])
        self.assertIsNone(self.link_for("granola:d", "pending"))
        self.assertIsNotNone(self.link_for("granola:d", "rejected"))
        self.assertIsNone(self.link_for("granola:d", "rejected")["dealId"])
        code, out = self.run_link()
        self.assertEqual(out["unmatched"], ["granola:d"])

    def test_reject_auto_linked_moves_it_back(self):
        self.store.save_unlinked([make_interaction("granola:1", "2026-03-10T10:00:00Z", [PRIYA])])
        self.run_link()
        self.assertEqual(self.ids_in("hs:1"), ["granola:1"])
        code, out = self.run_link("reject", "granola:1", "hs:1")
        self.assertEqual(code, 0)
        self.assertEqual(out["unlinkedFrom"], "hs:1")
        self.assertEqual(self.ids_in("hs:1"), [])
        self.assertEqual([i["id"] for i in self.store.load_unlinked()], ["granola:1"])
        self.assertIsNone(self.link_for("granola:1", "auto"))
        self.assertEqual(self.link_for("granola:1", "rejected")["method"], "email-match")
        code, out = self.run_link()
        self.assertEqual(out["unmatched"], ["granola:1"])

    def test_reject_dry_run_and_unknown(self):
        self.seed_pending()
        before = self.store.load_links()
        code, out = self.run_link("reject", "granola:d", "hs:1", dry_run=True)
        self.assertEqual(code, 0)
        self.assertEqual(self.store.load_links(), before)
        self.assertEqual(self.run_link("reject", "granola:nope")[0], 1)

    def test_reject_merged_interaction_is_refused(self):
        self.store.save_interactions("hs:1", [make_interaction("hs:meeting:9", "2026-03-04T14:00:00Z", [PRIYA], source="hubspot", dealId="hs:1", body="x")])
        self.store.save_unlinked([make_interaction("granola:abc", "2026-03-04T14:05:00Z", [PRIYA])])
        self.run_link()
        code, out = self.run_link("reject", "granola:abc")
        self.assertEqual(code, 1)
        self.assertIn("merged into hs:meeting:9", out["error"])

    def test_runs_are_logged(self):
        self.seed_pending()
        self.run_link("confirm", "granola:d", "hs:1")
        runs = [json.loads(line) for line in self.store.runs_path.read_text("utf-8").splitlines()]
        self.assertEqual([r["command"] for r in runs[-2:]], ["link", "link"])
        self.assertEqual(runs[-1]["args"]["action"], "confirm")
        self.assertTrue(runs[-1]["wrote"])


if __name__ == "__main__":
    unittest.main()
