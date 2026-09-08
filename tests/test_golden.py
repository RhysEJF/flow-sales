"""Golden-set harness: build batches from the labelled snippets, compare a judge's output, record the run."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flowsales.evals import golden  # noqa: E402
from flowsales.store import Store  # noqa: E402


FRAMEWORK = json.loads((ROOT / "frameworks" / "meddpicc.json").read_text("utf-8"))
TAG_OWNER = {tag: el["code"] for el in FRAMEWORK["elements"] for tag in el.get("behaviourTags") or []}


def perfect_assessment(batch: dict, snippets: dict[str, dict]) -> dict:
    """An assessment that reproduces the labels exactly: quotes verbatim, each tag on the element that owns it
    (general tags on the first applicable element), as the validator's vocabulary check requires."""
    interactions = []
    for inter in batch["interactions"]:
        s = snippets[inter["interactionId"]]
        elements = {}
        codes = list(s["expected"].keys())
        tags_by_code: dict[str, list[str]] = {c: [] for c in codes}
        for tag in s.get("expectedBehaviourTags") or []:
            owner = TAG_OWNER.get(tag, codes[0])
            tags_by_code.setdefault(owner if owner in tags_by_code else codes[0], []).append(tag)
        for code, exp in s["expected"].items():
            tags = tags_by_code.get(code, [])
            elements[code] = {"evidence": exp["evidence"], "quote": exp.get("quote"), "speaker": exp.get("speaker"),
                              "whyNotHigher": "Label.", "nextQuestion": "Next?", "confidence": "high",
                              "behaviour": 1 if tags else 0, "behaviourTags": tags}
        interactions.append({
            "interactionId": inter["interactionId"], "at": inter["at"], "phaseAtTime": inter["phaseAtTime"],
            "applicable": list(s["expected"].keys()), "notApplicableReason": dict(s.get("notApplicable") or {}),
            "elements": elements,
            "hygiene": {"pitchBeforePain": bool((s.get("hygiene") or {}).get("pitchBeforePain")), "mutualNextStep": False, "repTalkRatio": None},
            "summary": "Golden snippet.",
        })
    return {"dealId": batch["dealId"], "framework": batch["framework"], "rubricHash": batch["rubricHash"],
            "judgedAt": "2026-09-08T12:00:00Z", "model": "test-judge", "interactions": interactions, "dealNotes": "Golden."}


class GoldenTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        # an isolated plugin root so runs.jsonl and results/ never touch the repo
        self.plugin_root = tmp / "plugin"
        (self.plugin_root / "frameworks").mkdir(parents=True)
        (self.plugin_root / "evals" / "golden").mkdir(parents=True)
        shutil.copy(ROOT / "frameworks" / "meddpicc.json", self.plugin_root / "frameworks" / "meddpicc.json")
        shutil.copy(ROOT / "evals" / "golden" / "snippets.json", self.plugin_root / "evals" / "golden" / "snippets.json")
        self.home = tmp / "store" / ".flow-sales"
        self.store = Store(self.home)
        self.snippets = {s["id"]: s for s in json.loads((ROOT / "evals" / "golden" / "snippets.json").read_text("utf-8"))["snippets"]}

    def tearDown(self):
        self._tmp.cleanup()

    def ctx(self, as_json=True) -> dict:
        return {"store": self.store, "home": self.home, "plugin_root": self.plugin_root, "json": as_json,
                "started": time.time(), "now": "2026-09-08T12:00:00Z"}

    def run_cmd(self, **kw):
        base = {"action": "build", "parts": None, "model": None, "note": None, "strict": False}
        base.update(kw)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = golden.run(self.ctx(), SimpleNamespace(**base))
        out = buf.getvalue()
        return code, (json.loads(out) if out.strip().startswith("{") else out)

    def test_build_writes_one_batch_per_part_in_contract_shape(self):
        code, out = self.run_cmd(action="build", parts=4)
        self.assertEqual(code, 0)
        self.assertEqual(out["totals"], {"deals": 4, "batches": 4, "interactions": 40, "chars": out["totals"]["chars"], "estTokens": out["totals"]["estTokens"]})
        files = sorted(p.name for p in self.store.batches_dir.glob("*.json"))
        self.assertEqual(files, ["demo_golden-1.json", "demo_golden-2.json", "demo_golden-3.json", "demo_golden-4.json"])
        batch = self.store.read_json("work/batches/demo_golden-1.json")
        self.assertEqual(batch["dealId"], "demo:golden-1")
        self.assertTrue(batch["rubricHash"].startswith("sha256:"))
        self.assertEqual(len(batch["interactions"]), 10)
        first = batch["interactions"][0]
        self.assertEqual(first["interactionId"], "g01")
        self.assertEqual(first["phaseAtTime"], self.snippets["g01"]["phase"])
        self.assertEqual(first["body"], self.snippets["g01"]["body"])
        self.assertEqual({p["role"] for p in first["participants"]}, {"rep", "buyer"})
        self.assertEqual(batch["outputFile"], str(self.store.assessment_path("demo:golden-1")))
        plan = self.store.read_json("work/plan.json")
        self.assertTrue(plan["golden"])
        self.assertEqual(len(plan["batches"]), 4)

    def test_compare_perfect_judge_meets_every_target(self):
        self.run_cmd(action="build", parts=2)
        for path in self.store.batches_dir.glob("*.json"):
            batch = self.store.read_json(path)
            self.store.write_json(batch["outputFile"], perfect_assessment(batch, self.snippets))
        code, out = self.run_cmd(action="compare", note="perfect")
        self.assertEqual(code, 0, out)
        m = out["metrics"]
        self.assertEqual((m["snippets"], m["exactAgreement"], m["withinOneLevel"], m["behaviourTagAgreement"]), (40, 1.0, 1.0, 1.0))
        self.assertTrue(all(out["passed"].values()))
        self.assertEqual({k: v for k, v in out["checks"].items() if v}, {})
        self.assertEqual(out["model"], "test-judge")
        runs = (self.plugin_root / "evals" / "golden" / "runs.jsonl").read_text("utf-8").splitlines()
        self.assertEqual(len(runs), 1)
        self.assertEqual(json.loads(runs[0])["note"], "perfect")
        self.assertTrue(Path(out["detail"]).exists())
        self.assertTrue(all(v["ok"] for v in out["validations"]))

    def test_compare_catches_inflation_missing_snippets_and_bad_quotes(self):
        self.run_cmd(action="build", parts=1)
        batch = self.store.read_json("work/batches/demo_golden-1.json")
        assessment = perfect_assessment(batch, self.snippets)
        by_id = {it["interactionId"]: it for it in assessment["interactions"]}
        # rep-assertion note inflated to 2 with a quote that is not in the text: the validator caps it, the check reports it
        rep_note = next(s for s in self.snippets.values() if s["kind"] == "rep-assertion")
        code0 = next(iter(rep_note["expected"]))
        by_id[rep_note["id"]]["elements"][code0].update({"evidence": 2, "quote": "words nobody said on this call", "speaker": "buyer"})
        # a pitch monologue given a behaviour tag
        pitch = next(s for s in self.snippets.values() if s["kind"] == "pitch-monologue")
        pcode = next(iter(pitch["expected"]))
        by_id[pitch["id"]]["elements"][pcode]["behaviourTags"] = ["asked-metrics"]
        # one snippet dropped entirely
        assessment["interactions"] = [it for it in assessment["interactions"] if it["interactionId"] != "g40"]
        self.store.write_json(batch["outputFile"], assessment)
        code, out = self.run_cmd(action="compare", strict=True)
        self.assertEqual(code, 1, "strict mode exits 1 when a target is missed or a check fails")
        self.assertEqual(out["metrics"]["snippets"], 39)
        self.assertEqual(out["checkDetails"]["missingSnippets"], ["g40"])
        self.assertTrue(any(rep_note["id"] in q for q in out["checkDetails"]["quoteFailures"]))
        self.assertEqual(out["checkDetails"]["repAssertionAbove1"], [], "capped by the validator before comparison")
        self.assertTrue(any(pitch["id"] in p for p in out["checkDetails"]["pitchMonologueWithTags"]))
        self.assertLess(out["metrics"]["behaviourTagAgreement"], 1.0)

    def test_compare_without_assessments_fails_clearly(self):
        self.run_cmd(action="build")
        code, _ = self.run_cmd(action="compare")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
