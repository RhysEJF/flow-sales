"""Configuration: defaults, load/save, dotted access, token resolution. Standard library only."""
from __future__ import annotations

import copy
import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Optional

from .util import get_dotted, now_iso, set_dotted

DEFAULT_STAGE_PHASES = {
    "appointmentscheduled": "discovery",
    "qualifiedtobuy": "evaluation",
    "presentationscheduled": "proposal",
    "decisionmakerboughtin": "commit",
    "contractsent": "commit",
    "closedwon": "won",
    "closedlost": "lost",
}

PHASES = ["discovery", "evaluation", "proposal", "commit", "won", "lost"]


def default_config() -> dict:
    today = _dt.date.today()
    start = today.replace(year=today.year - 1)
    return {
        "version": 1,
        "framework": "meddpicc",
        "window": {"from": start.isoformat(), "to": today.isoformat()},
        "sources": {
            "hubspot": {"enabled": False, "baseUrl": "https://api.hubapi.com", "tokenEnv": "HUBSPOT_ACCESS_TOKEN", "pipelines": ["default"], "portalTimezone": "UTC"},
            "granola": {"enabled": False, "mode": "local-cache", "cachePath": None, "exportDir": None},
            "transcripts": {"enabled": False, "folder": None},
            "csv": {"enabled": False, "dealsFile": None, "interactionsFile": None},
            "demo": {"enabled": False},
        },
        "stagePhases": dict(DEFAULT_STAGE_PHASES),
        "org": {"name": None, "internalDomains": []},
        "reps": "all",
        "trainingDate": None,
        "content": {"emailBodies": True, "callTranscripts": True, "internalNotes": True},
        "anonymize": False,
        "attribution": {"influencedMinBehaviours": 3, "influencedMinInteractions": 2, "decayDays": 45},
        "judge": {"model": "sonnet", "parallel": 5, "maxInteractionChars": 60000},
        "linking": {"autoAcceptConfidence": 0.9, "timeGraceDays": 14},
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }


def merge_defaults(cfg: dict) -> dict:
    """Fill missing keys from the defaults without overwriting user values."""
    base = default_config()

    def merge(dst: dict, src: dict) -> dict:
        for k, v in src.items():
            if k not in dst:
                dst[k] = copy.deepcopy(v)
            elif isinstance(dst[k], dict) and isinstance(v, dict):
                merge(dst[k], v)
        return dst

    return merge(cfg, base)


class Config:
    def __init__(self, data: dict, path: Path):
        self.data = merge_defaults(data)
        self.path = path

    @classmethod
    def load(cls, path: Path) -> "Config":
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = default_config()
        return cls(data, path)

    def save(self) -> None:
        self.data["updatedAt"] = now_iso()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        tmp.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return get_dotted(self.data, key, default)

    def set(self, key: str, value: Any) -> None:
        set_dotted(self.data, key, value)

    # convenience
    @property
    def framework(self) -> str:
        return self.data.get("framework", "meddpicc")

    @property
    def window(self) -> tuple[str, str]:
        w = self.data.get("window", {})
        return w.get("from"), w.get("to")

    def phase_for_stage(self, stage_id: Optional[str], stage_label: Optional[str] = None) -> str:
        """Map a CRM stage id to a canonical phase; falls back to label keywords, then 'evaluation'."""
        if not stage_id and not stage_label:
            return "evaluation"
        mapping = self.data.get("stagePhases", {})
        if stage_id and stage_id in mapping:
            return mapping[stage_id]
        label = (stage_label or stage_id or "").lower()
        if "won" in label:
            return "won"
        if "lost" in label:
            return "lost"
        for phase, words in (
            ("discovery", ("appointment", "discovery", "qualif", "lead", "new", "prospect")),
            ("evaluation", ("evaluat", "demo", "poc", "pilot", "trial", "needs")),
            ("proposal", ("proposal", "presentation", "quote", "pricing", "solution")),
            ("commit", ("contract", "negotiat", "commit", "decision", "legal", "procurement", "verbal")),
        ):
            if any(w in label for w in words):
                return phase
        return "evaluation"

    def internal_domains(self, reps: Optional[list[dict]] = None) -> set[str]:
        domains = {d.lower() for d in (self.get("org.internalDomains") or []) if d}
        for rep in reps or []:
            email = rep.get("email") or ""
            if "@" in email:
                domains.add(email.rsplit("@", 1)[1].lower())
        return domains


def resolve_hubspot_token(cfg: Config, home: Path) -> Optional[str]:
    env_name = cfg.get("sources.hubspot.tokenEnv") or "HUBSPOT_ACCESS_TOKEN"
    for name in (env_name, "HUBSPOT_ACCESS_TOKEN", "CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN"):
        val = os.environ.get(name)
        if val:
            return val.strip()
    secrets = home / "secrets.json"
    if secrets.exists():
        try:
            with secrets.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            tok = data.get("hubspot_token")
            if tok:
                return str(tok).strip()
        except (OSError, ValueError):
            return None
    return None
