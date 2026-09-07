"""The local store under .flow-sales/. Every module reads and writes through this class."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .config import Config
from .util import now_iso, safe_id


def resolve_home(explicit: Optional[str] = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("FLOW_SALES_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.cwd() / ".flow-sales").resolve()


class Store:
    def __init__(self, home: Path):
        self.home = Path(home)
        self.config_path = self.home / "config.json"
        self.runs_path = self.home / "runs.jsonl"
        self.cache_dir = self.home / "cache"
        self.data_dir = self.home / "data"
        self.interactions_dir = self.data_dir / "interactions"
        self.work_dir = self.home / "work"
        self.batches_dir = self.work_dir / "batches"
        self.assessments_dir = self.home / "assessments"
        self.analytics_dir = self.home / "analytics"
        self.reports_dir = self.home / "reports"
        self.briefings_dir = self.home / "briefings"
        self.retros_dir = self.home / "retros"
        self._config: Optional[Config] = None

    # ---------- lifecycle ----------
    def exists(self) -> bool:
        return self.config_path.exists()

    def ensure(self) -> None:
        for d in (self.home, self.cache_dir, self.data_dir, self.interactions_dir, self.batches_dir,
                  self.assessments_dir, self.analytics_dir, self.reports_dir, self.briefings_dir, self.retros_dir):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def config(self) -> Config:
        if self._config is None:
            self._config = Config.load(self.config_path)
        return self._config

    def save_config(self) -> None:
        self.config.save()

    # ---------- generic json ----------
    def read_json(self, relpath: str | Path, default: Any = None) -> Any:
        p = self.home / relpath if not Path(relpath).is_absolute() else Path(relpath)
        if not p.exists():
            return default
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def write_json(self, relpath: str | Path, obj: Any) -> Path:
        p = self.home / relpath if not Path(relpath).is_absolute() else Path(relpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        tmp.replace(p)
        return p

    # ---------- canonical collections ----------
    def load_deals(self) -> list[dict]:
        return self.read_json("data/deals.json", []) or []

    def save_deals(self, deals: list[dict]) -> None:
        self.write_json("data/deals.json", sorted(deals, key=lambda d: d.get("id", "")))

    def load_reps(self) -> list[dict]:
        return self.read_json("data/reps.json", []) or []

    def save_reps(self, reps: list[dict]) -> None:
        self.write_json("data/reps.json", sorted(reps, key=lambda d: d.get("id", "")))

    def load_contacts(self) -> list[dict]:
        return self.read_json("data/contacts.json", []) or []

    def save_contacts(self, contacts: list[dict]) -> None:
        self.write_json("data/contacts.json", sorted(contacts, key=lambda d: d.get("id", "")))

    def load_companies(self) -> list[dict]:
        return self.read_json("data/companies.json", []) or []

    def save_companies(self, companies: list[dict]) -> None:
        self.write_json("data/companies.json", sorted(companies, key=lambda d: d.get("id", "")))

    def interactions_path(self, deal_id: str) -> Path:
        return self.interactions_dir / f"{safe_id(deal_id)}.json"

    def load_interactions(self, deal_id: str) -> list[dict]:
        return self.read_json(self.interactions_path(deal_id), []) or []

    def save_interactions(self, deal_id: str, interactions: list[dict]) -> None:
        self.write_json(self.interactions_path(deal_id), sorted(interactions, key=lambda i: (i.get("at") or "", i.get("id", ""))))

    def load_unlinked(self) -> list[dict]:
        return self.read_json(self.interactions_dir / "_unlinked.json", []) or []

    def save_unlinked(self, interactions: list[dict]) -> None:
        self.write_json(self.interactions_dir / "_unlinked.json", sorted(interactions, key=lambda i: (i.get("at") or "", i.get("id", ""))))

    def iter_all_interactions(self) -> Iterator[tuple[Optional[str], dict]]:
        """Yield (dealId or None, interaction) for every stored interaction."""
        if not self.interactions_dir.exists():
            return
        for p in sorted(self.interactions_dir.glob("*.json")):
            items = self.read_json(p, []) or []
            for it in items:
                yield (None if p.name == "_unlinked.json" else it.get("dealId")), it

    def load_links(self) -> dict:
        return self.read_json("data/links.json", {"version": 1, "links": []}) or {"version": 1, "links": []}

    def save_links(self, links: dict) -> None:
        self.write_json("data/links.json", links)

    # ---------- assessments ----------
    def assessment_path(self, deal_id: str) -> Path:
        return self.assessments_dir / f"{safe_id(deal_id)}.json"

    def load_assessment(self, deal_id: str) -> Optional[dict]:
        return self.read_json(self.assessment_path(deal_id), None)

    def iter_assessments(self) -> Iterator[dict]:
        if not self.assessments_dir.exists():
            return
        for p in sorted(self.assessments_dir.glob("*.json")):
            obj = self.read_json(p, None)
            if obj:
                yield obj

    # ---------- merge helpers ----------
    @staticmethod
    def upsert(existing: list[dict], incoming: Iterable[dict], key: str = "id") -> list[dict]:
        index = {e.get(key): e for e in existing}
        for rec in incoming:
            k = rec.get(key)
            if k in index:
                index[k].update(rec)
            else:
                index[k] = rec
        return list(index.values())

    # ---------- runs log ----------
    def log_run(self, command: str, args: Any, ok: bool, started: float, read: Optional[list] = None,
                wrote: Optional[list] = None, notes: str = "") -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        entry = {
            "at": now_iso(),
            "command": command,
            "args": args if isinstance(args, (dict, list, str)) else str(args),
            "ok": bool(ok),
            "durationMs": int((time.time() - started) * 1000),
            "read": read or [],
            "wrote": wrote or [],
            "notes": notes,
        }
        with self.runs_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
