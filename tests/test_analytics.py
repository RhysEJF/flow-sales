"""Tests for flowsales.analytics (rollup, impact, packs), CONTRACTS section 9.

Fixtures live in tests/fixtures/analytics: six deals, two reps, hand-built assessments that exercise
decay, gates, influenced yes and no, tertiles, coverage at phase end, before and after training,
timeseries and the briefing and retro packs. Run: python3 -m unittest tests.test_analytics -v
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
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

from flowsales.analytics import impact, packs, rollup  # noqa: E402
from flowsales.config import Config  # noqa: E402
from flowsales.store import Store  # noqa: E402
from flowsales.util import parse_iso  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "analytics"
NOW = "2026-09-07T12:00:00Z"
ANA, BEN = "rep:ana@vendor.example", "rep:ben@vendor.example"
CODES = ["M", "E", "DC", "DP", "PP", "I", "CH", "CO"]


def fresh_home(tmp: Path) -> Path:
    home = tmp / "store"
    shutil.copytree(FIXTURES, home)
    return home


def make_ctx(home: Path, plugin_root: Path, as_json: bool = False) -> dict:
    return {"store": Store(home), "home": home, "plugin_root": plugin_root, "json": as_json, "started": time.time(), "now": NOW}


def capture(func, ctx, args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = func(ctx, args)
    return code, buf.getvalue()


class AnalyticsBase(unittest.TestCase):
    """Computes everything once from the fixtures with the built-in framework (no frameworks/ under plugin_root)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        cls.home = fresh_home(tmp)
        cls.plugin_root = tmp / "plugin-without-frameworks"
        cls.plugin_root.mkdir()
        cls.store = Store(cls.home)
        cls.cfg = cls.store.config
        cls.framework, cls.source = rollup.load_framework(cls.plugin_root, cls.cfg.framework)
        cls.inputs = rollup.load_inputs(cls.store)
        cls.out = rollup.compute_all(cls.inputs, cls.framework, cls.cfg, parse_iso(NOW))
        cls.states = {s["dealId"]: s for s in cls.out["deal_states"]}
        cls.reps = {r["repId"]: r for r in cls.out["rep_metrics"]}
        cls.team = cls.out["team_metrics"]
        cls.ts = cls.out["timeseries"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def levels(self, deal_id: str) -> dict:
        return {c: v["level"] for c, v in self.states[deal_id]["elements"].items()}


class FrameworkTests(AnalyticsBase):
    def test_builtin_fallback_when_file_missing(self):
        self.assertEqual(self.source, "builtin")
        self.assertEqual(rollup.element_codes(self.framework), CODES)
        self.assertEqual(self.framework["scoring"]["commitGate"], {"all": 2, "E": 3, "CH": 3, "PP": 2})
        self.assertEqual(self.framework["scoring"]["qualifyOut"], {"maxTotal": 9, "minInteractions": 4})
        index = rollup.element_index(self.framework)
        self.assertEqual(index["PP"]["stageExpectations"], {"proposal": 1, "commit": 2})
        self.assertEqual(index["E"]["stageExpectations"]["commit"], 3)
        self.assertNotIn("discovery", index["E"]["stageExpectations"])

    def test_loads_framework_file_when_present(self):
        fw, source = rollup.load_framework(ROOT / "tests" / "fixtures" / "report", "meddpicc")
        self.assertTrue(source.endswith("meddpicc.json"))
        self.assertEqual(fw["version"], "0.1.0")
        self.assertEqual(rollup.element_codes(fw), CODES)


class DealStateTests(AnalyticsBase):
    def test_levels_with_decay_on_closed_deal(self):
        d1 = self.states["demo:1"]
        self.assertEqual(self.levels("demo:1"), {"M": 1, "E": 3, "DC": 2, "DP": 2, "PP": 2, "I": 2, "CH": 3, "CO": 2})
        m = d1["elements"]["M"]
        self.assertTrue(m["decayed"])  # last level-2 support on 2026-03-04, closed 2026-06-20: 108 days > 45
        self.assertEqual(m["interactionId"], "demo:i1-1")
        self.assertEqual(m["lastAt"], "2026-03-04T14:00:00Z")
        self.assertEqual(m["firstAt"], "2026-03-04T14:00:00Z")
        e = d1["elements"]["E"]
        self.assertFalse(e["decayed"])
        self.assertEqual(e["firstAt"], "2026-03-25T10:00:00Z")
        self.assertEqual(e["interactionId"], "demo:i1-5")
        self.assertEqual((d1["total"], d1["maxTotal"], d1["coverage2"], d1["coverage3"]), (17, 24, 7, 2))
        self.assertEqual(d1["cycleDays"], 110)
        self.assertEqual(d1["outcome"], "won")
        self.assertEqual(d1["ownerId"], ANA)

    def test_open_deal_decay_uses_window_end(self):
        d6 = self.states["demo:6"]
        self.assertEqual(d6["elements"]["I"]["level"], 1)
        self.assertTrue(d6["elements"]["I"]["decayed"])  # level 2 on 2026-05-08, window ends 2026-09-07
        self.assertEqual(d6["total"], 4)
        d5 = self.states["demo:5"]
        self.assertEqual(d5["elements"]["M"]["level"], 2)
        self.assertFalse(d5["elements"]["M"]["decayed"])  # supported on 2026-07-28, 41 days before the window end
        self.assertIsNone(d5["cycleDays"])

    def test_unverified_quotes_are_capped_at_one(self):
        d4 = self.states["demo:4"]
        self.assertEqual(d4["elements"]["DC"]["level"], 1)  # evidence 2 without verified, evidence 3 with verified false
        self.assertEqual(d4["total"], 8)
        self.assertEqual(d4["coverage2"], 2)

    def test_gates(self):
        self.assertEqual(self.states["demo:2"]["gate"], "commit-eligible")
        self.assertEqual(self.states["demo:4"]["gate"], "qualify-out")  # total 8 after 4 interactions
        self.assertEqual(self.states["demo:1"]["gate"], "upside")  # coverage2 7 but M decayed to 1
        self.assertEqual(self.states["demo:3"]["gate"], "upside")
        self.assertEqual(self.states["demo:5"]["gate"], "upside")
        self.assertEqual(self.states["demo:6"]["gate"], "pipeline")

    def test_qualify_out_when_eb_or_champion_zero_after_evaluation(self):
        deal = {"id": "x:1", "name": "Synthetic", "amount": 1.0, "currency": "GBP", "stage": "presentationscheduled", "phase": "proposal",
                "outcome": "open", "createdAt": "2026-07-01T00:00:00Z", "closedAt": None, "ownerId": ANA,
                "stageHistory": [{"stage": "appointmentscheduled", "phase": "discovery", "at": "2026-07-01T00:00:00Z"},
                                 {"stage": "presentationscheduled", "phase": "proposal", "at": "2026-08-01T00:00:00Z"}]}
        entry = {"interactionId": "x:i1", "at": "2026-08-10T10:00:00Z", "phaseAtTime": "proposal", "applicable": CODES,
                 "elements": {c: {"evidence": 2, "quote": "q", "speaker": "buyer", "verified": True, "behaviour": 1, "behaviourTags": ["asked-metrics"]}
                              for c in CODES}}
        entry["elements"]["E"] = {"evidence": 0, "quote": None, "speaker": None, "verified": False, "behaviour": 0, "behaviourTags": []}
        state = rollup.compute_deal_state(deal, {"dealId": "x:1", "interactions": [entry]}, [], self.framework, self.cfg, NOW)
        self.assertEqual(state["gate"], "qualify-out")
        self.assertEqual(state["interactions"], 1)
        # same deal still in evaluation is not qualified out
        deal["phase"], deal["stage"] = "evaluation", "qualifiedtobuy"
        state = rollup.compute_deal_state(deal, {"dealId": "x:1", "interactions": [entry]}, [], self.framework, self.cfg, NOW)
        self.assertEqual(state["gate"], "upside")

    def test_evidence_quality_index(self):
        self.assertAlmostEqual(self.states["demo:3"]["evidenceQualityIndex"], round(11 / 12, 3), places=3)
        self.assertEqual(self.states["demo:1"]["evidenceQualityIndex"], 1.0)

    def test_adoption_and_behaviours(self):
        d1 = self.states["demo:1"]
        self.assertEqual((d1["interactions"], d1["appliedInteractions"], d1["behaviours"]), (5, 4, 10))
        self.assertAlmostEqual(d1["dealAdoption"], 0.8, places=3)
        d5 = self.states["demo:5"]
        self.assertEqual(d5["interactions"], 3)  # assessed interactions
        self.assertEqual(d5["interactionsStored"], 4)  # one stored email never assessed
        self.assertEqual(d5["dealAdoption"], 1.0)

    def test_coverage_at_phase_end(self):
        self.assertEqual(self.states["demo:1"]["coverageAtPhaseEnd"], {"discovery": 2, "evaluation": 4, "proposal": 6, "commit": 8})
        self.assertEqual(self.states["demo:5"]["coverageAtPhaseEnd"], {"discovery": 2, "evaluation": 6})  # proposal still open
        self.assertEqual(self.states["demo:4"]["coverageAtPhaseEnd"], {"discovery": 2, "evaluation": 2})
        self.assertEqual(self.states["demo:6"]["coverageAtPhaseEnd"], {"discovery": 1})

    def test_stage_gaps(self):
        self.assertEqual(self.states["demo:1"]["stageGaps"], [{"phase": "commit", "element": "M", "expected": 2, "actual": 1}])
        self.assertEqual(self.states["demo:2"]["stageGaps"], [])
        self.assertEqual(self.states["demo:3"]["stageGaps"], [{"phase": "proposal", "element": "CO", "expected": 2, "actual": 1}])
        gaps5 = self.states["demo:5"]["stageGaps"]
        self.assertEqual([(g["element"], g["expected"], g["actual"]) for g in gaps5], [("DP", 2, 1), ("PP", 1, 0)])
        self.assertEqual(len(self.states["demo:4"]["stageGaps"]), 3)
        self.assertEqual(len(self.states["demo:6"]["stageGaps"]), 6)

    def test_influenced_yes(self):
        inf = self.states["demo:1"]["influenced"]
        self.assertTrue(inf["isInfluenced"])
        self.assertEqual((inf["behaviours"], inf["interactions"], inf["movedElements"]), (5, 2, ["E", "PP"]))
        self.assertIn("after 2026-06-01", inf["rule"])
        self.assertIn("E moved 1 to 3", inf["rule"])
        self.assertEqual(self.states["demo:2"]["influenced"]["movedElements"], ["E", "DP", "PP", "CO"])
        self.assertTrue(self.states["demo:2"]["influenced"]["isInfluenced"])

    def test_influenced_no(self):
        d3 = self.states["demo:3"]["influenced"]
        self.assertFalse(d3["isInfluenced"])
        self.assertEqual((d3["behaviours"], d3["interactions"], d3["movedElements"]), (0, 0, []))
        d4 = self.states["demo:4"]["influenced"]
        self.assertFalse(d4["isInfluenced"])
        self.assertIn("lost", d4["rule"])
        d5 = self.states["demo:5"]["influenced"]
        self.assertFalse(d5["isInfluenced"])  # open deal, even though elements moved
        self.assertEqual(d5["movedElements"], ["M", "E", "DC", "I", "CH", "CO"])

    def test_influenced_uses_window_when_no_training_date(self):
        data = json.loads(json.dumps(self.cfg.data))
        data["trainingDate"] = None
        cfg = Config(data, self.home / "config.json")
        deal = next(d for d in self.inputs["deals"] if d["id"] == "demo:1")
        state = rollup.compute_deal_state(deal, self.inputs["assessments"]["demo:1"], self.inputs["interactions"]["demo:1"], self.framework, cfg, NOW)
        self.assertTrue(state["influenced"]["isInfluenced"])
        self.assertEqual((state["influenced"]["behaviours"], state["influenced"]["interactions"]), (10, 4))
        self.assertIn("inside window 2026-03-01 to 2026-09-07", state["influenced"]["rule"])
        deal3 = next(d for d in self.inputs["deals"] if d["id"] == "demo:3")
        state3 = rollup.compute_deal_state(deal3, self.inputs["assessments"]["demo:3"], self.inputs["interactions"]["demo:3"], self.framework, cfg, NOW)
        self.assertFalse(state3["influenced"]["isInfluenced"])  # only one behaviour in the window

    def test_deal_without_assessment(self):
        deal = next(d for d in self.inputs["deals"] if d["id"] == "demo:6")
        state = rollup.compute_deal_state(deal, None, self.inputs["interactions"]["demo:6"], self.framework, self.cfg, NOW)
        self.assertFalse(state["assessed"])
        self.assertEqual(state["total"], 0)
        self.assertEqual(state["interactions"], 2)  # stored count when nothing was assessed
        self.assertIsNone(state["dealAdoption"])
        self.assertIsNone(state["evidenceQualityIndex"])
        self.assertEqual(state["gate"], "pipeline")


class RepMetricsTests(AnalyticsBase):
    def test_counts_and_rates(self):
        ana, ben = self.reps[ANA], self.reps[BEN]
        self.assertEqual(ana["name"], "Ana Ruiz")
        self.assertEqual((ana["interactions"], ana["appliedInteractions"]), (11, 8))
        self.assertAlmostEqual(ana["adoptionRate"], round(8 / 11, 3), places=3)
        self.assertEqual((ana["dealsWon"], ana["dealsLost"], ana["dealsOpen"], ana["winRate"]), (2, 0, 1, 1.0))
        self.assertEqual((ben["dealsWon"], ben["dealsLost"], ben["dealsOpen"], ben["winRate"]), (1, 1, 1, 0.5))

    def test_coverage_and_totals_at_close(self):
        ana, ben = self.reps[ANA], self.reps[BEN]
        self.assertEqual(ana["avgCoverageAtClose"], {"won": 6.5, "lost": None})
        self.assertEqual((ana["avgTotalWon"], ana["avgTotalLost"]), (15.5, None))  # totals 17 and 14
        self.assertEqual(ben["avgCoverageAtClose"], {"won": 8.0, "lost": 2.0})
        self.assertEqual((ben["avgTotalWon"], ben["avgTotalLost"]), (19.0, 8.0))

    def test_before_and_after_training(self):
        ana = self.reps[ANA]
        self.assertEqual(ana["beforeTraining"], {"adoptionRate": 0.5, "n": 6})
        self.assertEqual(ana["afterTraining"], {"adoptionRate": 1.0, "n": 5})
        self.assertAlmostEqual(ana["adoptionLift"], 0.5, places=3)
        ben = self.reps[BEN]
        self.assertEqual((ben["beforeTraining"]["n"], ben["afterTraining"]["n"]), (7, 4))
        self.assertAlmostEqual(ben["adoptionLift"], round(0.75 - round(5 / 7, 3), 3), places=3)

    def test_adoption_by_element_and_extremes(self):
        ana = self.reps[ANA]
        self.assertAlmostEqual(ana["adoptionByElement"]["PP"], 0.125, places=3)  # one applied of eight applicable
        self.assertEqual(set(ana["adoptionByElement"]), set(CODES))
        self.assertEqual(len(ana["weakestElements"]), 3)
        self.assertEqual(len(ana["strongestElements"]), 3)
        rates = ana["adoptionByElement"]
        self.assertEqual(rates[ana["weakestElements"][0]], min(rates.values()))
        self.assertEqual(rates[ana["strongestElements"][0]], max(rates.values()))
        self.assertTrue(set(ana["weakestElements"]).isdisjoint(ana["strongestElements"]))

    def test_behaviour_tags_and_evidence_quality(self):
        ana = self.reps[ANA]
        self.assertEqual(ana["behaviourTagCounts"]["asked-metrics"], 2)
        self.assertEqual(ana["behaviourTagCounts"]["identified-pain"], 2)  # demo:i1-1 and demo:i3-1
        self.assertAlmostEqual(ana["evidenceQualityIndex"], 0.98, places=3)
        self.assertEqual(self.reps[BEN]["evidenceQualityIndex"], 1.0)


class TeamMetricsTests(AnalyticsBase):
    def test_totals_and_win_rate(self):
        t = self.team["totals"]
        self.assertEqual((t["deals"], t["dealsAssessed"], t["dealsWon"], t["dealsLost"], t["dealsOpen"], t["reps"]), (6, 6, 3, 1, 2, 2))
        self.assertEqual((t["interactions"], t["appliedInteractions"], t["behaviours"]), (22, 16, 35))
        self.assertAlmostEqual(t["adoptionRate"], round(16 / 22, 3), places=3)
        self.assertEqual(t["amountWon"], 123000.0)
        self.assertEqual(self.team["winRate"], 0.75)

    def test_win_rate_by_adoption_tertile(self):
        tertiles = {row["tertile"]: row for row in self.team["winRateByAdoptionTertile"]}
        self.assertEqual([r["tertile"] for r in self.team["winRateByAdoptionTertile"]], ["low", "mid", "high"])
        self.assertEqual((tertiles["low"]["n"], tertiles["low"]["winRate"]), (1, 1.0))
        self.assertEqual((tertiles["mid"]["n"], tertiles["mid"]["winRate"]), (1, 0.0))
        self.assertEqual((tertiles["high"]["n"], tertiles["high"]["winRate"]), (2, 1.0))
        self.assertEqual(tertiles["high"]["medianCycleDays"], 120.0)
        self.assertEqual(tertiles["high"]["avgAmount"], 52500.0)
        self.assertEqual(tertiles["mid"]["adoptionRange"], [0.5, 0.5])

    def test_win_rate_by_coverage_at_phase_end(self):
        by = self.team["winRateByCoverageAtPhaseEnd"]
        disc = {r["coverageBand"]: r for r in by["discovery"]}
        self.assertEqual(list(disc), ["0-1", "2-3", "4-5", "6-8"])
        self.assertEqual((disc["2-3"]["n"], disc["2-3"]["winRate"]), (4, 0.75))
        self.assertEqual((disc["0-1"]["n"], disc["0-1"]["winRate"]), (0, None))
        ev = {r["coverageBand"]: r for r in by["evaluation"]}
        self.assertEqual((ev["4-5"]["n"], ev["4-5"]["winRate"]), (3, 1.0))
        self.assertEqual((ev["2-3"]["n"], ev["2-3"]["winRate"]), (1, 0.0))

    def test_element_weakness(self):
        weakness = {w["element"]: w for w in self.team["elementWeakness"]}
        self.assertEqual([w["element"] for w in self.team["elementWeakness"]], CODES)
        self.assertAlmostEqual(weakness["E"]["avgLevelWon"], round(8 / 3, 3), places=3)
        self.assertEqual(weakness["E"]["avgLevelLost"], 0.0)
        self.assertEqual(weakness["M"]["name"], "Metrics")
        self.assertIsNotNone(weakness["M"]["adoptionRate"])

    def test_before_after(self):
        ba = self.team["beforeAfter"]
        self.assertEqual(ba["trainingDate"], "2026-06-01")
        self.assertEqual(ba["before"], {"adoptionRate": round(8 / 13, 3), "n": 13, "dealsClosed": 1, "winRate": 1.0})
        self.assertEqual(ba["after"], {"adoptionRate": round(8 / 9, 3), "n": 9, "dealsClosed": 3, "winRate": round(2 / 3, 3)})

    def test_data_coverage(self):
        cov = self.team["dataCoverage"]
        self.assertEqual(cov["interactionsByType"], {"call": 9, "email": 3, "meeting": 11})
        self.assertEqual((cov["dealsWithTranscripts"], cov["dealsWithoutInteractions"], cov["unlinkedInteractions"]), (3, 0, 1))
        self.assertEqual((cov["interactionsAssessed"], cov["interactionsUnassessed"]), (22, 1))

    def test_zero_denominators(self):
        team = rollup.compute_team_metrics([], [], [], self.framework, self.cfg)
        self.assertIsNone(team["winRate"])
        self.assertIsNone(team["totals"]["adoptionRate"])
        self.assertEqual([(r["n"], r["winRate"], r["medianCycleDays"], r["avgAmount"]) for r in team["winRateByAdoptionTertile"]],
                         [(0, None, None, None)] * 3)
        self.assertTrue(all(r["winRate"] is None for rows in team["winRateByCoverageAtPhaseEnd"].values() for r in rows))
        self.assertTrue(all(w["avgLevelWon"] is None and w["adoptionRate"] is None for w in team["elementWeakness"]))
        self.assertIsNone(team["beforeAfter"]["before"]["adoptionRate"])
        reps = rollup.compute_rep_metrics([{"id": "rep:nobody", "name": "Nobody"}], [], [], self.framework, self.cfg)
        rep = reps[0]
        self.assertIsNone(rep["adoptionRate"])
        self.assertIsNone(rep["winRate"])
        self.assertIsNone(rep["adoptionLift"])
        self.assertEqual(rep["weakestElements"], [])
        self.assertEqual(rep["avgCoverageAtClose"], {"won": None, "lost": None})
        self.assertIsNone(rep["evidenceQualityIndex"])
        ts = rollup.compute_timeseries([], [], self.framework, self.cfg)
        self.assertEqual(ts["weeks"][0], "2026-W09")
        self.assertTrue(all(b["adoptionRate"] is None for b in ts["team"]))
        self.assertIsNone(rollup.ratio(3, 0))


class TimeseriesTests(AnalyticsBase):
    def test_weekly_buckets(self):
        weeks = self.ts["weeks"]
        self.assertEqual((weeks[0], weeks[-1]), ("2026-W09", "2026-W37"))
        self.assertEqual(len(weeks), 29)
        ana = {b["week"]: b for b in self.ts["reps"][ANA]}
        w10 = ana["2026-W10"]
        self.assertEqual((w10["interactions"], w10["applied"], w10["adoptionRate"]), (1, 1, 1.0))
        self.assertEqual(w10["byElement"], {"M": 1, "E": 0, "DC": 0, "DP": 0, "PP": 0, "I": 1, "CH": 0, "CO": 0})
        self.assertIsNone(ana["2026-W12"]["adoptionRate"])  # no Ana interaction that week
        team = {b["week"]: b for b in self.ts["team"]}
        self.assertEqual((team["2026-W24"]["interactions"], team["2026-W24"]["applied"]), (2, 2))
        self.assertEqual(sum(b["interactions"] for b in self.ts["team"]), 22)
        self.assertEqual(set(self.ts["reps"]), {ANA, BEN})


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.home = fresh_home(tmp)
        self.plugin_root = tmp / "plugin"
        self.plugin_root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_rollup_run_writes_files_and_logs(self):
        ctx = make_ctx(self.home, self.plugin_root, as_json=True)
        code, out = capture(rollup.run, ctx, SimpleNamespace(json=True))
        self.assertEqual(code, 0)
        summary = json.loads(out)
        self.assertTrue(summary["ok"])
        self.assertEqual((summary["deals"], summary["reps"], summary["interactions"]), (6, 2, 22))
        self.assertEqual(summary["framework"], "builtin")
        for name in ("deal_states", "rep_metrics", "team_metrics", "timeseries"):
            self.assertTrue((self.home / "analytics" / f"{name}.json").exists(), name)
        states = json.loads((self.home / "analytics" / "deal_states.json").read_text())
        self.assertEqual(len(states), 6)
        runs = [json.loads(line) for line in (self.home / "runs.jsonl").read_text().splitlines() if line.strip()]
        self.assertEqual(runs[-1]["command"], "rollup")
        self.assertTrue(runs[-1]["ok"])
        self.assertEqual(len(runs[-1]["wrote"]), 4)
        code, out = capture(rollup.run, make_ctx(self.home, self.plugin_root), SimpleNamespace(json=False))
        self.assertEqual(code, 0)
        self.assertIn("Rollup: 6 deals", out)

    def test_impact_quarter(self):
        ctx = make_ctx(self.home, self.plugin_root, as_json=True)
        capture(rollup.run, ctx, SimpleNamespace(json=True))
        code, out = capture(impact.run, make_ctx(self.home, self.plugin_root, as_json=True), SimpleNamespace(quarter="2026-q3", json=True))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(result["ok"])
        self.assertFalse(result["computedInMemory"])
        self.assertEqual((result["quarter"], result["wonCount"], result["influencedCount"]), ("2026-Q3", 1, 1))
        self.assertEqual((result["wonAmount"], result["influencedAmount"]), (65000.0, 65000.0))
        row = result["influencedDeals"][0]
        self.assertEqual((row["dealId"], row["name"], row["ownerName"], row["movedElements"]), ("demo:2", "Borealis platform", "Ben Cole", ["E", "DP", "PP", "CO"]))
        self.assertEqual((result["adoptionBefore"], result["adoptionAfter"]), (round(8 / 13, 3), round(8 / 9, 3)))
        self.assertEqual((result["adoptionBeforeN"], result["adoptionAfterN"]), (13, 9))
        self.assertEqual((result["winRateBefore"], result["winRateAfter"], result["closedBefore"], result["closedAfter"]), (1.0, round(2 / 3, 3), 1, 3))
        self.assertEqual(result["trainingDate"], "2026-06-01")
        self.assertIn("at least 3 framework behaviours across at least 2 interactions after 2026-06-01", result["rule"])
        caveats = " ".join(result["caveats"])
        self.assertIn("correlational", caveats)
        self.assertIn("younger", caveats)
        self.assertIn("Small numbers", caveats)
        self.assertIn("emails", caveats)
        md_path = self.home / "analytics" / "impact-2026-Q3.md"
        self.assertTrue(md_path.exists())
        md = md_path.read_text(encoding="utf-8")
        self.assertNotIn("\u2014", md)
        self.assertIn("| Borealis platform | Ben Cole | GBP 65,000 | E, DP, PP, CO | 7 across 3 interactions |", md)
        self.assertIn("## Caveats", md)
        self.assertIn("Win rate before and after", md)
        saved = json.loads((self.home / "analytics" / "impact.json").read_text())
        self.assertEqual(saved["influencedCount"], 1)
        # a quarter with two won deals, one influenced
        code, out = capture(impact.run, make_ctx(self.home, self.plugin_root, as_json=True), SimpleNamespace(quarter="2026-Q2", json=True))
        result = json.loads(out)
        self.assertEqual((result["wonCount"], result["influencedCount"], result["influencedDeals"][0]["dealId"]), (2, 1, "demo:1"))

    def test_impact_computes_in_memory_without_deal_states(self):
        code, out = capture(impact.run, make_ctx(self.home, self.plugin_root, as_json=True), SimpleNamespace(quarter="2026-Q3", json=True))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(result["computedInMemory"])
        self.assertEqual(result["influencedCount"], 1)
        self.assertFalse((self.home / "analytics" / "deal_states.json").exists())

    def test_impact_without_training_date_splits_at_quarter_start(self):
        store = Store(self.home)
        store.config.set("trainingDate", None)
        store.config.save()
        code, out = capture(impact.run, make_ctx(self.home, self.plugin_root, as_json=True), SimpleNamespace(quarter="2026-Q3", json=True))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertIsNone(result["trainingDate"])
        self.assertEqual(result["splitDate"], "2026-07-01T00:00:00Z")
        self.assertIn("No training date is configured", " ".join(result["caveats"]))
        self.assertIn("inside the config window", result["rule"])

    def test_impact_bad_quarter(self):
        code, _ = capture(impact.run, make_ctx(self.home, self.plugin_root, as_json=True), SimpleNamespace(quarter="2026-Q7", json=True))
        self.assertEqual(code, 1)


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.home = fresh_home(tmp)
        self.plugin_root = tmp / "plugin"
        self.plugin_root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_pack(self, func, **kw):
        defaults = {"rep": None, "date": None, "week": None}
        defaults.update(kw)
        code, out = capture(func, make_ctx(self.home, self.plugin_root), SimpleNamespace(**defaults))
        return code, json.loads(out)

    def test_briefing_pack(self):
        code, pack = self.run_pack(packs.briefing, rep="ANA@vendor.example", date="2026-09-07")
        self.assertEqual(code, 0)
        self.assertTrue(pack["ok"])
        self.assertTrue(pack["computedInMemory"])  # no analytics files yet
        self.assertEqual(pack["rep"]["id"], ANA)
        self.assertEqual(pack["date"], "2026-09-07")
        self.assertEqual([d["dealId"] for d in pack["deals"]], ["demo:5"])
        deal = pack["deals"][0]
        self.assertEqual((deal["company"], deal["phase"], deal["stageLabel"]), ("Echo Ltd", "proposal", "Presentation Scheduled"))
        self.assertEqual((deal["daysInStage"], deal["daysSinceLastInteraction"]), (44, 18))
        self.assertEqual(deal["gate"], "upside")
        m = deal["elements"]["M"]
        self.assertEqual((m["level"], m["interactionId"], m["speaker"]), (2, "demo:i5-3", "buyer"))
        self.assertTrue(m["quote"].startswith("Month-end close"))
        self.assertIsNone(deal["elements"]["PP"]["quote"])
        self.assertEqual([(g["element"], g["expected"], g["actual"]) for g in deal["stageGaps"]], [("DP", 2, 1), ("PP", 1, 0)])
        self.assertEqual([f["element"] for f in deal["focus"]], ["PP", "DP", "M"])
        self.assertTrue(all(f["nextQuestion"] for f in deal["focus"]))
        self.assertTrue(all(f["exampleQuote"] for f in deal["focus"]))
        self.assertEqual([i["id"] for i in deal["lastInteractions"]], ["demo:i5-4", "demo:i5-3", "demo:i5-2"])
        self.assertEqual(set(deal["lastInteractions"][0]), {"id", "at", "type", "title", "summary"})
        self.assertEqual((deal["unassessedInteractions"], pack["unassessedInteractions"]), (1, 1))
        self.assertEqual(len(pack["pendingLinks"]), 1)
        self.assertEqual((pack["pendingLinks"][0]["interactionId"], pack["pendingLinks"][0]["repDeals"]), ("granola:unl-1", ["demo:5"]))
        self.assertEqual([w["week"] for w in pack["adoptionLast4Weeks"]], ["2026-W34", "2026-W35", "2026-W36", "2026-W37"])
        self.assertAlmostEqual(pack["team"]["adoptionRate"], round(16 / 22, 3), places=3)
        self.assertEqual(len(pack["rep"]["weakestElements"]), 3)
        self.assertEqual(len(pack["rep"]["strongestElements"]), 3)

    def test_briefing_after_rollup_uses_files_and_resolves_by_name_and_id(self):
        capture(rollup.run, make_ctx(self.home, self.plugin_root, as_json=True), SimpleNamespace(json=True))
        code, pack = self.run_pack(packs.briefing, rep="ben cole")
        self.assertEqual(code, 0)
        self.assertFalse(pack["computedInMemory"])
        self.assertEqual(pack["rep"]["id"], BEN)
        self.assertEqual(pack["date"], "2026-09-07")  # ctx now
        self.assertEqual([d["dealId"] for d in pack["deals"]], ["demo:6"])
        code, pack = self.run_pack(packs.briefing, rep=BEN)
        self.assertEqual(pack["rep"]["name"], "Ben Cole")
        code, pack = self.run_pack(packs.briefing, rep="Ana")  # unique partial name
        self.assertEqual(pack["rep"]["id"], ANA)

    def test_briefing_unknown_rep(self):
        code, pack = self.run_pack(packs.briefing, rep="nobody@nowhere.example")
        self.assertEqual(code, 1)
        self.assertFalse(pack["ok"])
        self.assertIn("rep not found", pack["error"])

    def test_retro_pack(self):
        code, pack = self.run_pack(packs.retro, rep=ANA, week="2026-W25")
        self.assertEqual(code, 0)
        self.assertTrue(pack["ok"])
        self.assertEqual((pack["week"], pack["weekStart"], pack["previousWeek"]), ("2026-W25", "2026-06-15T00:00:00Z", "2026-W24"))
        self.assertEqual(pack["adoption"]["thisWeek"]["interactions"], 0)
        self.assertIsNone(pack["adoption"]["thisWeek"]["adoptionRate"])
        self.assertEqual((pack["adoption"]["lastWeek"]["interactions"], pack["adoption"]["lastWeek"]["adoptionRate"]), (2, 1.0))
        four = pack["adoption"]["fourWeekAverage"]
        self.assertEqual(four["weeks"], ["2026-W22", "2026-W23", "2026-W24", "2026-W25"])
        self.assertEqual((four["interactions"], four["applied"]), (3, 3))  # i1-4 in W23, i1-5 and i5-1 in W24
        self.assertEqual(pack["adoption"]["team"]["thisWeek"]["interactions"], 2)  # Ben: i2-3 and i4-4
        self.assertEqual(pack["interactionsByType"], {})
        self.assertEqual(pack["behaviourTags"], {})
        self.assertEqual(len(pack["dealsMoved"]), 1)
        moved = pack["dealsMoved"][0]
        self.assertEqual((moved["dealId"], moved["from"]["phase"], moved["to"]["phase"], moved["to"]["label"]), ("demo:1", "commit", "won", "Closed Won"))
        self.assertEqual(len(pack["dealsClosed"]), 1)
        closed = pack["dealsClosed"][0]
        self.assertEqual((closed["dealId"], closed["outcome"], closed["total"], closed["weakestElements"]), ("demo:1", "won", 17, ["M", "DC", "DP"]))
        self.assertEqual(closed["elements"]["E"], 3)
        self.assertEqual(pack["staleDeals"], [])  # Echo rollout had a meeting on 2026-06-12
        self.assertEqual(pack["previousRetroFocus"], "Ask for the economic buyer earlier")
        self.assertEqual(pack["comparison"]["weakestElements"]["rep"], pack["rep"]["weakestElements"])
        self.assertEqual(len(pack["comparison"]["weakestElements"]["team"]), 3)
        self.assertIsNotNone(pack["comparison"]["adoptionRate"]["delta"])

    def test_retro_week_with_activity(self):
        code, pack = self.run_pack(packs.retro, rep=ANA, week="2026-W24")
        self.assertEqual(code, 0)
        self.assertEqual(pack["interactionsByType"], {"call": 1, "meeting": 1})
        self.assertEqual(pack["behaviourTags"], {"asked-metrics": 1, "identified-eb": 1, "implicated-pain": 1, "positioned-differentiation": 1})
        self.assertEqual((pack["adoption"]["thisWeek"]["interactions"], pack["adoption"]["thisWeek"]["adoptionRate"]), (2, 1.0))
        self.assertEqual(pack["dealsMoved"], [])
        self.assertIsNone(pack["previousRetroFocus"])

    def test_retro_stale_deals_and_default_week(self):
        code, pack = self.run_pack(packs.retro, rep="ben@vendor.example", week="2026-W36")
        self.assertEqual(code, 0)
        self.assertEqual([s["dealId"] for s in pack["staleDeals"]], ["demo:6"])
        self.assertGreaterEqual(pack["staleDeals"][0]["daysSinceLastInteraction"], 14)
        self.assertEqual(pack["staleDeals"][0]["lastInteractionAt"], "2026-05-30T11:00:00Z")
        code, pack = self.run_pack(packs.retro, rep=BEN)
        self.assertEqual(pack["week"], "2026-W37")
        code, pack = self.run_pack(packs.retro, rep=BEN, week="2026-W33")
        self.assertEqual([c["dealId"] for c in pack["dealsClosed"]], ["demo:2"])  # won 2026-08-14
        self.assertEqual(pack["dealsClosed"][0]["gate"], "commit-eligible")

    def test_retro_bad_week(self):
        code, pack = self.run_pack(packs.retro, rep=ANA, week="2026-13")
        self.assertEqual(code, 1)
        self.assertFalse(pack["ok"])


class CliTests(unittest.TestCase):
    def test_dispatch_through_fs_py(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = fresh_home(Path(tmp))
            fs = ROOT / "scripts" / "fs.py"
            res = subprocess.run([sys.executable, str(fs), "rollup", "--home", str(home), "--json"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(json.loads(res.stdout)["ok"])
            res = subprocess.run([sys.executable, str(fs), "impact", "--quarter", "2026-Q3", "--home", str(home), "--json"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads(res.stdout)["wonCount"], 1)
            res = subprocess.run([sys.executable, str(fs), "briefing-data", "--rep", "ana@vendor.example", "--home", str(home)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads(res.stdout)["deals"][0]["dealId"], "demo:5")
            res = subprocess.run([sys.executable, str(fs), "retro-data", "--rep", BEN, "--week", "2026-W36", "--home", str(home)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(json.loads(res.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
