"""Tests for the team folder (flowsales.team): create, detect, reuse at plan time, push and pull."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flowsales import team  # noqa: E402
from flowsales.assess import planner  # noqa: E402
from flowsales.store import Store  # noqa: E402
from test_planner import PlannerBase, make_deal, make_interaction, FIXTURES  # noqa: E402


class TeamFolderTests(PlannerBase):
    def setUp(self):
        super().setUp()
        self.folder = Path(self._tmp.name) / "Drive" / "Sales" / "FlowSales"

    def team_cmd(self, *argv, json_out=True):
        action = argv[0] if argv else "status"
        path = argv[1] if len(argv) > 1 else None
        args = SimpleNamespace(action=action, path=path, pull_only=False, push_only=False, json=json_out, home=None)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = team.run(self.ctx(json_out), args)
        out = buf.getvalue()
        return code, (json.loads(out) if json_out else out)

    def judged(self, deal_id: str, inters: list[dict], judged_at: str) -> dict:
        framework, _ = planner.load_framework(FIXTURES, "testfw")
        return {"dealId": deal_id, "inputHash": planner.input_hash(planner.judgeable(inters)),
                "rubricHash": planner.rubric_hash_of(framework), "judgedAt": judged_at, "model": "test",
                "interactions": [], "elements": {}}

    def test_init_creates_folder_readme_and_marker(self):
        self.seed_single_deal()
        code, out = self.team_cmd("init", str(self.folder))
        self.assertEqual(code, 0, out)
        self.assertTrue((self.folder / "assessments").is_dir())
        self.assertIn("real calls and emails", (self.folder / "README.txt").read_text(encoding="utf-8"))
        self.assertTrue((self.folder / "team.json").exists())
        self.assertEqual(self.store.config.get("team.folder"), str(self.folder))
        self.assertTrue(team.is_team_folder(self.folder))

    def test_join_refuses_a_plain_folder(self):
        self.seed_single_deal()
        plain = Path(self._tmp.name) / "Downloads"
        plain.mkdir()
        code, out = self.team_cmd("join", str(plain))
        self.assertEqual(code, 1)
        self.assertIsNone(self.store.config.get("team.folder"))

    def test_candidates_finds_flowsales_folder_in_a_synced_root(self):
        team.init(self.folder)
        found = team.candidates(roots=[str(Path(self._tmp.name) / "Drive")])
        self.assertEqual(found, [self.folder])
        self.assertEqual(team.candidates(roots=[str(Path(self._tmp.name) / "Nowhere")]), [])

    def test_candidates_looks_under_the_working_folder_too(self):
        # A folder added to a Cowork session lands under the session workspace, not under ~/Library/CloudStorage.
        ws = Path(self._tmp.name) / "session"
        added = ws / "Sales" / "FlowSales"
        team.init(added)
        found = team.candidates(workspace=ws)
        self.assertIn(added, found)

    def test_planner_reuses_a_matching_team_assessment(self):
        self.seed_single_deal()
        team.init(self.folder)
        self.store.config.set("team.folder", str(self.folder)); self.store.save_config()
        inters = self.store.load_interactions("hs:1")
        team._write(team.assessment_path(self.folder, "hs:1"), self.judged("hs:1", inters, "2026-09-08T10:00:00Z"))
        code, out = self.plan()
        self.assertEqual(code, 0)
        self.assertEqual(out["totals"]["batches"], 0, "the team's assessment covers exactly these interactions")
        self.assertEqual(out["reusedFromTeam"], ["hs:1"])
        self.assertEqual(out["skipped"]["reusedFromTeam"], 1)
        self.assertIsNotNone(self.store.load_assessment("hs:1"), "copied into the local store")
        self.store.assessment_path("hs:1").unlink()
        code, text = self.plan(json_out=False)
        self.assertIn("Reused 1 assessments from the team folder", text)

    def test_planner_ignores_a_team_assessment_on_other_interactions(self):
        self.seed_single_deal()
        team.init(self.folder)
        self.store.config.set("team.folder", str(self.folder)); self.store.save_config()
        stale = self.judged("hs:1", [make_interaction("granola:9", "2026-02-01T10:00:00Z", "old body")], "2026-09-08T10:00:00Z")
        team._write(team.assessment_path(self.folder, "hs:1"), stale)
        code, out = self.plan()
        self.assertEqual(out["totals"]["batches"], 1, "different input hash: judge it here")
        self.assertEqual(out["reusedFromTeam"], [])
        self.assertIsNone(self.store.load_assessment("hs:1"))

    def test_estimate_only_reports_reuse_without_copying(self):
        self.seed_single_deal()
        team.init(self.folder)
        self.store.config.set("team.folder", str(self.folder)); self.store.save_config()
        inters = self.store.load_interactions("hs:1")
        team._write(team.assessment_path(self.folder, "hs:1"), self.judged("hs:1", inters, "2026-09-08T10:00:00Z"))
        code, out = self.plan(estimate_only=True)
        self.assertEqual(out["reusedFromTeam"], ["hs:1"])
        self.assertIsNone(self.store.load_assessment("hs:1"), "an estimate writes nothing")

    def test_push_and_pull_round_trip(self):
        self.seed_single_deal()
        inters = self.store.load_interactions("hs:1")
        mine = self.judged("hs:1", inters, "2026-09-08T10:00:00Z")
        self.store.write_json(self.store.assessment_path("hs:1"), mine)
        team.init(self.folder)
        pushed = team.push(self.store, self.folder)
        self.assertEqual(pushed, ["hs:1"])
        self.assertEqual(team.push(self.store, self.folder), [], "second push copies nothing")
        # a teammate judges the same deal later on new interactions; their file is newer
        theirs = dict(mine, inputHash="sha256:other", judgedAt="2026-09-09T10:00:00Z")
        team._write(team.assessment_path(self.folder, "hs:1"), theirs)
        pulled = team.pull_all(self.store, self.folder)
        self.assertEqual(pulled, ["hs:1"])
        self.assertEqual(self.store.load_assessment("hs:1")["judgedAt"], "2026-09-09T10:00:00Z")
        self.assertEqual(team.push(self.store, self.folder), [], "nothing newer here to push back")

    def test_status_and_sync_commands(self):
        self.seed_single_deal()
        code, out = self.team_cmd("status")
        self.assertEqual(out["folder"], None)
        self.team_cmd("init", str(self.folder))
        inters = self.store.load_interactions("hs:1")
        self.store.write_json(self.store.assessment_path("hs:1"), self.judged("hs:1", inters, "2026-09-08T10:00:00Z"))
        code, out = self.team_cmd("status")
        self.assertEqual((out["exists"], out["toShare"], out["teamAssessments"]), (True, 1, 0))
        code, out = self.team_cmd("sync")
        self.assertEqual(out["pushed"], ["hs:1"])
        code, out = self.team_cmd("status")
        self.assertEqual((out["teamAssessments"], out["toShare"], out["reusable"]), (1, 0, 0))
        code, out = self.team_cmd("leave")
        self.assertIsNone(self.store.config.get("team.folder"))
        self.assertTrue(team.assessment_path(self.folder, "hs:1").exists(), "leaving never touches the folder")

    def test_fs_status_carries_the_team_line(self):
        self.seed_single_deal()
        self.team_cmd("init", str(self.folder))
        from flowsales import core_cmds
        buf = io.StringIO()
        with redirect_stdout(buf):
            core_cmds.cmd_status(self.ctx(True), SimpleNamespace(json=True))
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["team"]["folder"], str(self.folder))
        self.assertTrue(payload["team"]["exists"])
        self.assertIn("me", payload)
