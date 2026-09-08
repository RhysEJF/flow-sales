"""Fixes that the first full demo run exposed: mixed currencies, unreadable weekly adoption, future judgedAt."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from flowsales.analytics import impact, rollup  # noqa: E402
from flowsales.report import build_report, charts  # noqa: E402
from test_validate import ValidateBase, element, make_assessment  # noqa: E402


class CurrencyTests(unittest.TestCase):
    STATES = [{"amount": 10.0, "currency": "GBP"}, {"amount": 5.5, "currency": "EUR"}, {"amount": 4.5, "currency": "EUR"}, {"amount": 1.0}]

    def test_amount_by_currency_never_adds_across_currencies(self):
        self.assertEqual(rollup.amount_by_currency(self.STATES), {"EUR": 10.0, "GBP": 10.0, "unknown": 1.0})

    def test_fmt_money_total_shows_each_currency(self):
        self.assertEqual(charts.fmt_money_total(20.0, {"GBP": 10.0, "EUR": 10.0}, "GBP"), "€10 + £10")
        self.assertEqual(charts.fmt_money_total(20.0, {"EUR": 20.0}, "GBP"), "€20")
        self.assertEqual(charts.fmt_money_total(20.0, None, "GBP"), "£20")

    def test_impact_markdown_does_not_sum_currencies(self):
        doc = {"quarter": "2026-Q3", "generatedAt": "x", "trainingDate": None, "quarterStart": "2026-07-01T00:00:00Z",
               "wonCount": 2, "wonAmount": 20.0, "wonAmountByCurrency": {"GBP": 10.0, "EUR": 10.0},
               "influencedCount": 1, "influencedAmount": 10.0, "influencedAmountByCurrency": {"GBP": 10.0},
               "influencedDeals": [], "adoptionBefore": None, "adoptionAfter": None, "adoptionBeforeN": 0, "adoptionAfterN": 0,
               "winRateBefore": None, "winRateAfter": None, "closedBefore": 0, "closedAfter": 0, "caveats": [], "rule": "r"}
        md = impact.render_markdown(doc)
        self.assertIn("EUR 10 + GBP 10", md)
        self.assertIn("share not computed across currencies", md)
        self.assertNotIn("GBP 20", md)


class RollingAdoptionTests(unittest.TestCase):
    def test_rolling_rate_pools_the_trailing_window(self):
        weeks = ["w1", "w2", "w3", "w4", "w5"]
        b = {"w1": {"interactions": 1, "applied": 1}, "w2": {"interactions": 1, "applied": 0},
             "w4": {"interactions": 2, "applied": 2}}
        got = build_report._rolling_rate(b, weeks, window=2)
        self.assertEqual(got, [1.0, 0.5, 0.0, 1.0, 1.0])

    def test_rolling_rate_is_none_when_the_window_is_empty(self):
        self.assertEqual(build_report._rolling_rate({}, ["w1", "w2"]), [None, None])


class FutureJudgedAtTests(ValidateBase):
    def test_future_judged_at_is_replaced(self):
        assessment = make_assessment(element(1, None))
        assessment["judgedAt"] = "2999-01-01T12:00:00Z"
        path = self.write_assessment(assessment)
        code, report = self.validate(path)
        self.assertEqual(code, 0, report)
        self.assertTrue(any("later than now" in w for w in report["warnings"]))
        saved = self.read(path)
        self.assertEqual(saved["judgedAt"], saved["validatedAt"])


if __name__ == "__main__":
    unittest.main()
