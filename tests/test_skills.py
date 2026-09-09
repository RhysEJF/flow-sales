"""The plugin's command set and the promises the skill texts make to each other."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def skill_text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


class SkillSetTests(unittest.TestCase):
    def test_the_command_set(self):
        names = sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists())
        self.assertEqual(names, ["audit", "coaching-voice", "daily-sync", "impact", "link", "methodology", "retro", "setup", "start", "status"])
        self.assertFalse((SKILLS / "standup").exists(), "standup was renamed to daily-sync on 2026-09-09")

    def test_frontmatter_names_match_folders(self):
        for p in SKILLS.iterdir():
            f = p / "SKILL.md"
            if not f.exists():
                continue
            m = re.search(r"^name:\s*(\S+)", f.read_text(encoding="utf-8"), re.M)
            self.assertIsNotNone(m, p.name)
            self.assertEqual(m.group(1), p.name)

    def test_no_text_still_points_at_the_old_command(self):
        for f in list(SKILLS.rglob("SKILL.md")) + [ROOT / "README.md", ROOT / "INSTALL.md", ROOT / "docs" / "CONTRACTS.md"]:
            self.assertNotIn("flow-sales:standup", f.read_text(encoding="utf-8"), str(f))

    def test_setup_asks_who_you_are_and_offers_the_team_folder_and_the_connector(self):
        s = skill_text("setup")
        for needle in ("me.role", "me.email", "fs.py team candidates", "fs.py team init", "fs.py team join",
                       "get_user_details", "search_crm_objects", "fs.py import hubspot-cache", "cache/hubspot-mcp", "consent.repsInformed"):
            self.assertIn(needle, s, needle)
        self.assertIn("Anyone can go first", s)

    def test_daily_sync_pulls_own_deals_and_syncs_the_team_folder(self):
        s = skill_text("daily-sync")
        for needle in ("--owner me", "me.repId", "fs.py team sync --pull-only", "fs.py team sync --push-only", "fs.py import hubspot-cache",
                       "fs.py log --command daily-sync"):
            self.assertIn(needle, s, needle)

    def test_audit_syncs_the_team_folder_around_judging(self):
        s = skill_text("audit")
        self.assertIn("fs.py team sync --pull-only", s)
        self.assertIn("fs.py team sync --push-only", s)
        self.assertIn("reusedFromTeam", s)

    def test_audit_prints_the_estimate_and_runs_without_asking(self):
        s = skill_text("audit")
        self.assertIn("Do not ask before running", s)
        self.assertIn("more than 40 deals", s, "the only gate left is size")
        self.assertNotIn("Plan and gate on volume", s)

    def test_judge_agent_pins_sonnet_and_docs_say_so(self):
        agent = (ROOT / "agents" / "deal-assessor.md").read_text(encoding="utf-8")
        self.assertIn("model: sonnet", agent.split("---")[1])
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("pinned to Sonnet", readme)
        self.assertIn("session itself on Opus", readme)

    def test_status_reports_the_team_folder(self):
        self.assertIn("fs.py team status --json", skill_text("status"))

    def test_start_and_status_may_be_invoked_from_plain_language(self):
        for name in ("start", "status"):
            self.assertNotIn("disable-model-invocation: true", skill_text(name), name)
        for name in ("setup", "audit", "daily-sync", "retro", "impact", "link"):
            self.assertIn("disable-model-invocation: true", skill_text(name), name + " spends money or writes files: slash command only")
        self.assertIn("skills/setup/SKILL.md", skill_text("start"), "start hands off to setup")

    def test_manifest_and_marketplace_parse(self):
        for name in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", ".mcp.json"):
            json.loads((ROOT / name).read_text(encoding="utf-8"))
        mcp = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
        self.assertIn("hubspot", mcp["mcpServers"], "the connector route depends on the shipped HubSpot server")


if __name__ == "__main__":
    unittest.main()
