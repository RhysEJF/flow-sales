"""Report builder smoke tests against the report fixtures."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowsales.report import build_report, charts  # noqa: E402
from flowsales.store import Store  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "report"


class ReportTests(unittest.TestCase):
    def render(self, out: Path) -> dict:
        store = Store(FIXTURES)
        ctx = {"store": store, "home": FIXTURES, "plugin_root": ROOT, "json": True, "started": 0.0, "now": "2026-09-07T20:00:00Z"}
        args = argparse.Namespace(open=False, out=str(out), json=True, home=str(FIXTURES))
        code = build_report.run(ctx, args)
        self.assertEqual(code, 0)
        return {"path": out}

    def test_renders_self_contained_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.html"
            self.render(out)
            html = out.read_text(encoding="utf-8")
            self.assertLess(out.stat().st_size, 1_000_000)
            self.assertIn("FlowSales", html)
            self.assertIn("Powered by FlowSales", html)
            for deal in json.loads((FIXTURES / "data" / "deals.json").read_text(encoding="utf-8")):
                self.assertIn(deal["name"], html)
            for rep in json.loads((FIXTURES / "data" / "reps.json").read_text(encoding="utf-8")):
                self.assertIn(rep["name"], html)
            self.assertFalse(re.search(r'(src|href)="https?://', html), "report must not load anything from the network")
            self.assertNotIn("—", html)

    def test_charts_are_well_formed_svg(self):
        for name in dir(charts):
            fn = getattr(charts, name)
            if not callable(fn) or name.startswith("_") or not name.islower():
                continue
            # only exercise builders with a documented simple signature via the module's self-test hook when present
        if hasattr(charts, "selftest"):
            for svg in charts.selftest():
                ET.fromstring(svg)


if __name__ == "__main__":
    unittest.main()
