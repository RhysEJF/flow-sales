"""Team folder: judged assessments shared between machines through a folder the team already syncs.

No hub, no server. Every machine keeps its own store and pulls its own data; the folder only saves a judging
step. One file per deal under ``<folder>/assessments/``, the same shape as the local assessment. A file is
reused when its deal id, input hash and rubric hash match what the planner is about to judge, so a stale or
missing folder never changes a number, it only costs a repeat judging.

``fs.py team init <path>`` creates one, ``join <path>`` points this store at an existing one, ``status``
compares, ``sync`` pulls matching assessments in and pushes new ones out (``--pull-only`` / ``--push-only``),
``leave`` forgets the folder without touching it. ``candidates()`` looks for a folder named FlowSales in the
usual synced drives so setup can suggest one.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any, Iterable, Optional

from .store import Store
from .util import now_iso, safe_id

FOLDER_NAME = "FlowSales"
ASSESSMENTS = "assessments"
MARKER = "team.json"
SYNC_ROOTS = [
    "~/Library/CloudStorage/*",       # Google Drive, OneDrive, Dropbox and Box on current macOS
    "~/Google Drive*",
    "~/My Drive",
    "~/Dropbox*",
    "~/OneDrive*",
    "~/Box*",
    "~/Nextcloud",
]
README_TEXT = """FlowSales team folder

This folder is shared by a sales team running FlowSales. It holds one judged assessment per deal
(assessments/<deal>.json): element levels, the buyer quotes behind them, the judge's reasons and next
questions. Every machine on the team reads from and writes to this folder so a deal is judged once.

It is not the record. Deals, calls and emails always come from each person's own HubSpot and Granola.
Deleting this folder loses nothing except the saved judging: the next run repopulates it.

The quotes in here are from real calls and emails. Share the folder with the sales team only.
"""


# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
def folder_of(cfg: Any) -> Optional[Path]:
    raw = cfg.get("team.folder") if cfg is not None else None
    return Path(str(raw)).expanduser() if raw else None


def assessments_dir(folder: Path) -> Path:
    return folder / ASSESSMENTS


def assessment_path(folder: Path, deal_id: str) -> Path:
    return assessments_dir(folder) / f"{safe_id(deal_id)}.json"


def is_team_folder(path: Path) -> bool:
    return path.is_dir() and (assessments_dir(path).is_dir() or (path / MARKER).exists())


def candidates(roots: Optional[Iterable[str]] = None, workspace: Optional[Path] = None) -> list[Path]:
    """Folders named FlowSales that already hold assessments, at most four deep under the usual synced drives
    (a shared drive mirrored to ~/Library/CloudStorage/GoogleDrive-<you>/Shared drives/Sales/Enablement/FlowSales
    still counts) and under the working folder, which is where a folder added to a Cowork session appears."""
    found: list[Path] = []
    patterns = list(roots or SYNC_ROOTS)
    if roots is None:
        ws = Path(workspace or os.getcwd())
        patterns = [str(ws), str(ws.parent)] + patterns
    for pattern in patterns:
        for root in glob.glob(os.path.expanduser(pattern)):
            root_path = Path(root)
            if not root_path.is_dir():
                continue
            for depth_pattern in ("", "*/", "*/*/", "*/*/*/"):
                for hit in glob.glob(str(root_path / f"{depth_pattern}{FOLDER_NAME}")):
                    p = Path(hit)
                    if is_team_folder(p) and p not in found:
                        found.append(p)
    return found


# ---------------------------------------------------------------------------
# create, join
# ---------------------------------------------------------------------------
def init(path: Path, created_by: Optional[str] = None) -> Path:
    path = Path(path).expanduser()
    assessments_dir(path).mkdir(parents=True, exist_ok=True)
    readme = path / "README.txt"
    if not readme.exists():
        readme.write_text(README_TEXT, encoding="utf-8")
    marker = path / MARKER
    if not marker.exists():
        marker.write_text(json.dumps({"version": 1, "createdAt": now_iso(), "createdBy": created_by}, indent=2) + "\n",
                          encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# matching and moving assessments
# ---------------------------------------------------------------------------
def _read(path: Path) -> Optional[dict]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            obj = json.load(fh)
        return obj if isinstance(obj, dict) else None
    except (OSError, ValueError):
        return None


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)


def matching(folder: Path, deal_id: str, input_hash: str, rubric_hash: str) -> Optional[dict]:
    """The team's assessment for this deal if it was judged on exactly these interactions with this rubric."""
    obj = _read(assessment_path(folder, deal_id))
    if not obj:
        return None
    if obj.get("dealId") not in (None, deal_id):
        return None
    if obj.get("inputHash") != input_hash or obj.get("rubricHash") != rubric_hash:
        return None
    return obj


def pull_matching(store: Store, folder: Path, plans: Iterable[tuple[str, str, str]]) -> list[str]:
    """Copy in every team assessment that matches (deal id, input hash, rubric hash) and differs from the local one."""
    copied: list[str] = []
    for deal_id, input_hash, rubric_hash in plans:
        shared = matching(folder, deal_id, input_hash, rubric_hash)
        if not shared:
            continue
        local = store.load_assessment(deal_id)
        if local and local.get("inputHash") == input_hash and local.get("rubricHash") == rubric_hash:
            continue
        _write(store.assessment_path(deal_id), shared)
        copied.append(deal_id)
    return copied


def _newer(a: Optional[dict], b: Optional[dict]) -> bool:
    """True when assessment a was judged after b (missing b counts as older)."""
    if not b:
        return True
    return str(a.get("judgedAt") or "") > str(b.get("judgedAt") or "")


def push(store: Store, folder: Path) -> list[str]:
    """Copy local assessments to the folder when the folder has none for the deal or ours is newer."""
    copied: list[str] = []
    for local in store.iter_assessments():
        deal_id = local.get("dealId")
        if not deal_id:
            continue
        target = assessment_path(folder, deal_id)
        shared = _read(target)
        if shared and not _newer(local, shared):
            continue
        if shared and shared.get("inputHash") == local.get("inputHash") and shared.get("rubricHash") == local.get("rubricHash"):
            continue  # same judging already there
        _write(target, local)
        copied.append(deal_id)
    return copied


def pull_all(store: Store, folder: Path) -> list[str]:
    """Copy in team assessments for deals this store has no assessment for, or where the team's is newer.
    Used by sync; the planner's own reuse is hash-exact and happens at plan time."""
    copied: list[str] = []
    adir = assessments_dir(folder)
    if not adir.is_dir():
        return copied
    for p in sorted(adir.glob("*.json")):
        shared = _read(p)
        if not shared or not shared.get("dealId"):
            continue
        deal_id = shared["dealId"]
        if not any(d.get("id") == deal_id for d in store.load_deals()):
            continue  # not a deal this machine knows about
        local = store.load_assessment(deal_id)
        if local and not _newer(shared, local):
            continue
        _write(store.assessment_path(deal_id), shared)
        copied.append(deal_id)
    return copied


def status(store: Store, folder: Optional[Path]) -> dict:
    out: dict[str, Any] = {"folder": str(folder) if folder else None, "exists": bool(folder and is_team_folder(folder)),
                           "teamAssessments": 0, "localAssessments": sum(1 for _ in store.iter_assessments()),
                           "reusable": 0, "toShare": 0}
    if not out["exists"]:
        return out
    adir = assessments_dir(folder)
    shared_by_deal: dict[str, dict] = {}
    for p in adir.glob("*.json"):
        obj = _read(p)
        if obj and obj.get("dealId"):
            shared_by_deal[obj["dealId"]] = obj
    out["teamAssessments"] = len(shared_by_deal)
    known = {d.get("id") for d in store.load_deals()}
    local_by_deal = {a.get("dealId"): a for a in store.iter_assessments() if a.get("dealId")}
    for deal_id, shared in shared_by_deal.items():
        if deal_id in known and (deal_id not in local_by_deal or _newer(shared, local_by_deal[deal_id])):
            out["reusable"] += 1
    for deal_id, local in local_by_deal.items():
        shared = shared_by_deal.get(deal_id)
        if not shared or (_newer(local, shared) and shared.get("inputHash") != local.get("inputHash")):
            out["toShare"] += 1
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _out(ctx: dict, payload: dict, text: str) -> None:
    if ctx.get("json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text)


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    action = getattr(args, "action", "status")
    if not store.exists():
        _out(ctx, {"ok": False, "error": "no store; run init"}, "No FlowSales store here. Run: fs.py init")
        return 1
    cfg = store.config
    me = (cfg.get("me") or {}).get("email")
    path_arg = getattr(args, "path", None)

    if action in ("init", "join"):
        if not path_arg:
            _out(ctx, {"ok": False, "error": "path required"}, f"fs.py team {action} <folder path>")
            return 1
        path = Path(path_arg).expanduser()
        if action == "join" and not is_team_folder(path):
            _out(ctx, {"ok": False, "error": "not a team folder", "path": str(path)},
                 f"{path} is not a FlowSales team folder (no assessments/ inside). Ask whoever created it for the exact path, or run: fs.py team init {path}")
            return 1
        if action == "init":
            init(path, created_by=me)
        cfg.set("team.folder", str(path))
        store.save_config()
        pulled = pull_all(store, path)
        pushed = push(store, path)
        st = status(store, path)
        store.log_run(f"team {action}", {"path": str(path)}, True, ctx["started"], wrote=[str(store.config_path)],
                      notes=f"{st['teamAssessments']} team assessments, pulled {len(pulled)}, pushed {len(pushed)}")
        _out(ctx, {"ok": True, "action": action, **st, "pulled": pulled, "pushed": pushed},
             f"Team folder {'created' if action == 'init' else 'joined'}: {path}\n  {st['teamAssessments']} assessments there, "
             f"{len(pulled)} copied in, {len(pushed)} copied out.")
        return 0

    folder = folder_of(cfg)
    if action == "leave":
        cfg.set("team.folder", None)
        store.save_config()
        store.log_run("team leave", {}, True, ctx["started"], wrote=[str(store.config_path)])
        _out(ctx, {"ok": True, "action": "leave", "folder": str(folder) if folder else None},
             "This store no longer uses a team folder. Nothing in the folder was touched.")
        return 0

    if action == "candidates":
        found = [str(p) for p in candidates()]
        _out(ctx, {"ok": True, "candidates": found},
             ("Team folders found:\n  " + "\n  ".join(found)) if found else "No FlowSales team folder found in the synced drives.")
        return 0

    if not folder:
        found = [str(p) for p in candidates()]
        _out(ctx, {"ok": True, "folder": None, "candidates": found},
             "No team folder set. " + (("Found: " + ", ".join(found) + ". Join one with: fs.py team join <path>") if found
                                      else "Create one with: fs.py team init <path in a folder your team syncs>"))
        return 0

    if action == "sync":
        pull_only = bool(getattr(args, "pull_only", False))
        push_only = bool(getattr(args, "push_only", False))
        pulled = [] if push_only else pull_all(store, folder)
        pushed = [] if pull_only else push(store, folder)
        st = status(store, folder)
        store.log_run("team sync", {"pullOnly": pull_only, "pushOnly": push_only}, True, ctx["started"],
                      read=[str(assessments_dir(folder))], wrote=[str(store.assessments_dir)] if pulled else [],
                      notes=f"pulled {len(pulled)}, pushed {len(pushed)}")
        _out(ctx, {"ok": True, "action": "sync", **st, "pulled": pulled, "pushed": pushed},
             f"Team folder {folder}: {len(pulled)} assessments copied in, {len(pushed)} copied out. "
             f"{st['teamAssessments']} there, {st['localAssessments']} here.")
        return 0

    st = status(store, folder)
    _out(ctx, {"ok": True, "action": "status", **st},
         f"Team folder: {folder}" + ("" if st["exists"] else " (missing: not synced yet, or moved)") +
         f"\n  {st['teamAssessments']} assessments there, {st['localAssessments']} here; "
         f"{st['reusable']} reusable here, {st['toShare']} to share.")
    return 0
