"""The connector route: `import hubspot-cache` must build the same store as the REST pull from the same objects."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flowsales.crm import hubspot as hs  # noqa: E402
from flowsales.crm import hubspot_cache as hc  # noqa: E402
from flowsales.crm import import_cmd  # noqa: E402
from test_hubspot import FakeHubSpot, load_fixture, make_store  # noqa: E402


def write_cache(folder: Path, *, wrap_deals_in_mcp_envelope: bool = False, omit: tuple = ()) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for kind in ("deals", "contacts", "companies", "calls", "emails", "meetings", "notes", "owners"):
        if kind in omit:
            continue
        data = load_fixture(f"{kind}.json")
        if kind == "deals" and wrap_deals_in_mcp_envelope:
            data = {"content": [{"type": "text", "text": "Here are the deals:\n" + json.dumps({"results": data})}]}
        (folder / f"{kind}-1.json").write_text(json.dumps(data), encoding="utf-8")
    if "pipelines" not in omit:
        (folder / "pipelines-1.json").write_text(json.dumps(load_fixture("pipelines.json")), encoding="utf-8")
    if "associations" not in omit:
        for key, table in load_fixture("associations.json").items():
            frm, to = key.split("->")
            results = [{"from": {"id": fid}, "to": [{"toObjectId": a["toObjectId"], "associationTypes": [{"typeId": t} for t in a["typeIds"]]} for a in tos]}
                       for fid, tos in table.items()]
            (folder / f"associations-{frm}-{to}.json").write_text(json.dumps({"results": results}), encoding="utf-8")


def snapshot(store) -> dict:
    deals = store.load_deals()
    inter = {}
    for d in deals:
        inter[d["id"]] = sorted(i["id"] for i in store.load_interactions(d["id"]))
    return {"deals": sorted(d["id"] for d in deals),
            "stages": {d["id"]: (d.get("stage"), d.get("phase")) for d in deals},
            "contacts": sorted(c["id"] for c in store.load_contacts()),
            "companies": sorted(c["id"] for c in store.load_companies()),
            "reps": sorted((r["id"], r.get("name")) for r in store.load_reps()),
            "interactions": inter,
            "links": len(store.load_links().get("links", []))}


class ConnectorCacheTests(unittest.TestCase if False else __import__("unittest").TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_import(self, store, folder: Path, as_json=True):
        ctx = {"store": store, "home": store.home, "plugin_root": ROOT, "json": as_json, "started": 0.0}
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = import_cmd.run(ctx, SimpleNamespace(source="hubspot-cache", dir=str(folder), json=as_json, home=None))
        return code, (json.loads(out.getvalue()) if as_json and out.getvalue().strip().startswith("{") else out.getvalue()), err.getvalue()

    def test_cache_import_matches_the_rest_pull(self):
        rest = make_store(str(self.root / "rest"))
        hs.pull(rest, rest.config, client=FakeHubSpot())
        cache = make_store(str(self.root / "cache"))
        folder = self.root / "hubspot-mcp"
        write_cache(folder)
        code, payload, err = self.run_import(cache, folder)
        self.assertEqual(code, 0, err)
        self.assertTrue(payload["ok"])
        self.assertEqual(snapshot(cache), snapshot(rest), "same objects in, same store out, whichever route")
        self.assertEqual(payload["counts"]["deals"], 3)
        self.assertEqual(cache.config.get("sources.hubspot.enabled"), True)
        self.assertEqual(cache.config.get("sources.hubspot.route"), "connector")
        runs = [json.loads(l) for l in (cache.home / "runs.jsonl").read_text().splitlines()]
        self.assertEqual(runs[-1]["command"], "import hubspot-cache")

    def test_mcp_envelope_and_prose_are_unwrapped(self):
        cache = make_store(str(self.root / "cache"))
        folder = self.root / "hubspot-mcp"
        write_cache(folder, wrap_deals_in_mcp_envelope=True)
        code, payload, err = self.run_import(cache, folder)
        self.assertEqual(code, 0, err)
        self.assertEqual(payload["counts"]["deals"], 3)

    def test_kind_is_sniffed_when_the_file_name_says_nothing(self):
        folder = self.root / "hubspot-mcp"
        folder.mkdir()
        (folder / "reply 1.json").write_text(json.dumps(load_fixture("calls.json")), encoding="utf-8")
        (folder / "reply 2.json").write_text(json.dumps({"results": load_fixture("deals.json")}), encoding="utf-8")
        loaded = hc.load_dir(folder)
        self.assertEqual(len(loaded["objects"]["calls"]), 2)
        self.assertEqual(len(loaded["objects"]["deals"]), 5)
        self.assertEqual(loaded["unknown"], 0)

    def test_embedded_v3_associations_are_used(self):
        cache = make_store(str(self.root / "cache"))
        folder = self.root / "hubspot-mcp"
        write_cache(folder, omit=("associations",))
        deals = load_fixture("deals.json")
        table = load_fixture("associations.json")
        for d in deals:
            did = str(d["id"])
            d["associations"] = {}
            for key, tos in table.items():
                frm, to = key.split("->")
                if frm == "deals" and tos.get(did):
                    d["associations"][to] = {"results": [{"id": str(a["toObjectId"]), "type": f"deal_to_{to[:-1]}"} for a in tos[did]]}
        (folder / "deals-1.json").write_text(json.dumps(deals), encoding="utf-8")
        code, payload, err = self.run_import(cache, folder)
        self.assertEqual(code, 0, err)
        self.assertGreater(sum(payload["counts"]["interactions"].values()), 0, "interactions attached through embedded associations")
        self.assertNotIn("no deal-to-engagement associations", " ".join(payload["warnings"]))

    def test_missing_owners_and_pipelines_degrade_with_a_warning(self):
        cache = make_store(str(self.root / "cache"))
        folder = self.root / "hubspot-mcp"
        write_cache(folder, omit=("owners", "pipelines"))
        code, payload, err = self.run_import(cache, folder)
        self.assertEqual(code, 0, err)
        text = " ".join(payload["warnings"])
        self.assertIn("owners were not saved", text)
        self.assertIn("pipelines were not saved", text)
        self.assertEqual(payload["counts"]["deals"], 3)

    def test_empty_folder_fails_clearly(self):
        cache = make_store(str(self.root / "cache"))
        folder = self.root / "hubspot-mcp"
        folder.mkdir()
        code, payload, err = self.run_import(cache, folder)
        self.assertEqual(code, 1)
        self.assertIn("no HubSpot deals found", payload["error"])

    def test_per_deal_engagement_files_and_dealstage_options(self):
        cache = make_store(str(self.root / "cache"))
        folder = self.root / "hubspot-mcp"
        write_cache(folder, omit=("associations", "pipelines", "calls", "emails", "meetings", "notes"))
        table = load_fixture("associations.json")
        for kind in ("calls", "emails", "meetings", "notes"):
            objs = {str(o["id"]): o for o in load_fixture(f"{kind}.json")}
            for did, tos in table[f"deals->{kind}"].items():
                picked = [objs[str(a["toObjectId"])] for a in tos if str(a["toObjectId"]) in objs]
                if picked:
                    (folder / f"{kind}-deal-{did}-1.json").write_text(json.dumps({"results": picked}), encoding="utf-8")
        (folder / "properties-dealstage.json").write_text(json.dumps({"name": "dealstage", "options": [
            {"label": "Closed Won", "value": "closedwon"}, {"label": "Closed Lost", "value": "closedlost"},
            {"label": "Appointment", "value": "appointmentscheduled"}]}), encoding="utf-8")
        code, payload, err = self.run_import(cache, folder)
        self.assertEqual(code, 0, err)
        self.assertGreater(sum(payload["counts"]["interactions"].values()), 0, "per-deal reply files attach their objects to the deal")
        self.assertNotIn("pipelines were not saved", " ".join(payload["warnings"]))
        stages = {d["id"]: d.get("stageLabel") or d.get("stage") for d in cache.load_deals()}
        self.assertTrue(any("Closed" in str(v) for v in stages.values()), stages)

