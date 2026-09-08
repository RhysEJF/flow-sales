"""Golden-set evaluation for the judge (evals/golden/README.md, CONTRACTS section 13).

`fs.py eval-golden build`   writes batch files for the 40 labelled snippets into a scratch store, ready for the
                            deal-assessor agent (one batch per part, so no single assessment file gets unwieldy).
`fs.py eval-golden compare` validates the judge's assessments in that store, compares them with the labels,
                            prints the three metrics, the secondary checks and a per-element confusion table,
                            and appends the run to evals/golden/runs.jsonl.
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any, Optional

from ..assess import planner, validate
from ..store import Store
from ..util import normalize_text, now_iso, safe_id

DEAL_PREFIX = "demo:golden"
DEFAULT_PARTS = 4


def _plugin_root(ctx: dict) -> Path:
    return Path(ctx["plugin_root"])


def golden_dir(plugin_root: Path | str) -> Path:
    return Path(plugin_root) / "evals" / "golden"


def load_snippets(plugin_root: Path | str) -> dict:
    with (golden_dir(plugin_root) / "snippets.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _participants(snippet: dict) -> list[dict]:
    out = []
    for label, role in (snippet.get("speakerRoles") or {}).items():
        out.append({"name": label, "email": None, "role": role})
    return out


def _fake_deal(deal_id: str, part_no: int, parts: int) -> dict:
    """A stand-in deal so the batch has the CONTRACTS section 7 shape. Every phase appears in the history so
    phaseAtTime values from the snippets are all legal for this deal."""
    base = _dt.datetime(2026, 1, 5, 9, 0, tzinfo=_dt.timezone.utc)
    phases = [("appointmentscheduled", "Appointment Scheduled", "discovery"), ("qualifiedtobuy", "Qualified To Buy", "evaluation"),
              ("presentationscheduled", "Presentation Scheduled", "proposal"), ("contractsent", "Contract Sent", "commit")]
    history = [{"stage": s, "label": lab, "phase": ph, "at": (base + _dt.timedelta(days=30 * i)).isoformat().replace("+00:00", "Z")}
               for i, (s, lab, ph) in enumerate(phases)]
    return {
        "id": deal_id, "source": "demo", "name": f"Golden set part {part_no} of {parts}", "amount": None, "currency": None,
        "pipeline": "default", "stage": "contractsent", "stageLabel": "Contract Sent", "phase": "commit",
        "stageHistory": history, "outcome": "open", "createdAt": history[0]["at"], "closedAt": None,
        "ownerId": "rep:golden", "contactIds": [], "companyId": None, "companyDomain": None,
    }


def build_batches(snippets_doc: dict, plugin_root: Path | str, store: Store, parts: int = DEFAULT_PARTS) -> dict:
    framework, framework_file = planner.load_framework(plugin_root, snippets_doc.get("framework") or "meddpicc")
    rubric_hash = planner.rubric_hash_of(framework)
    snippets = list(snippets_doc.get("snippets") or [])
    parts = max(1, min(int(parts or 1), len(snippets) or 1))
    size = -(-len(snippets) // parts)
    chunks = [snippets[i:i + size] for i in range(0, len(snippets), size)]
    codes = [e["code"] for e in framework.get("elements") or []]
    base = _dt.datetime(2026, 2, 2, 9, 0, tzinfo=_dt.timezone.utc)
    store.ensure()
    planner._clear_batches(store)
    meta = []
    for part_no, chunk in enumerate(chunks, start=1):
        deal_id = f"{DEAL_PREFIX}-{part_no}"
        interactions = []
        for k, s in enumerate(chunk):
            at = (base + _dt.timedelta(days=part_no * 100 + k)).isoformat().replace("+00:00", "Z")
            interactions.append({
                "interactionId": s["id"], "at": at, "type": s.get("type") or "call", "source": "demo",
                "direction": "unknown", "phaseAtTime": s.get("phase") or "discovery",
                "title": f"{s['id']} ({s.get('kind', 'standard')}, {s.get('phase', '')})",
                "participants": _participants(s), "body": s.get("body") or "",
            })
        path = store.batches_dir / planner.batch_file_name(deal_id)
        batch = {
            "batchId": part_no, "dealId": deal_id, "framework": framework.get("slug") or "meddpicc",
            "frameworkFile": str(framework_file), "rubricHash": rubric_hash, "inputHash": None, "batchFile": str(path),
            "part": 1, "parts": 1, "reason": "golden set", "deal": _fake_deal(deal_id, part_no, len(chunks)),
            "priorState": {c: 0 for c in codes}, "interactions": interactions,
            "outputFile": str(store.assessment_path(deal_id)),
        }
        store.write_json(path, batch)
        chars = sum(len(i["body"]) for i in interactions)
        meta.append({"batchId": part_no, "dealId": deal_id, "dealName": batch["deal"]["name"], "file": str(path),
                     "interactions": len(interactions), "chars": chars, "estTokens": planner.est_tokens(chars),
                     "part": 1, "parts": 1, "reason": "golden set"})
    plan_doc = {"plannedAt": now_iso(), "rubricHash": rubric_hash, "framework": framework.get("slug") or "meddpicc",
                "frameworkFile": str(framework_file), "maxInteractionChars": None, "considered": len(chunks), "batches": meta,
                "totals": {"deals": len(chunks), "batches": len(meta), "interactions": len(snippets),
                           "chars": sum(m["chars"] for m in meta), "estTokens": sum(m["estTokens"] for m in meta)},
                "skipped": {"unchanged": 0, "withoutInteractions": 0, "notFound": []}, "golden": True}
    store.write_json("work/plan.json", plan_doc)
    return plan_doc


# ---------- comparison ----------

def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def compare(snippets_doc: dict, assessments: list[dict], framework: dict) -> dict:
    codes = [e["code"] for e in framework.get("elements") or []]
    max_level = int(framework.get("maxLevel", 3) or 3)
    judged: dict[str, dict] = {}
    for a in assessments:
        for it in a.get("interactions") or []:
            if isinstance(it, dict) and it.get("interactionId"):
                judged[str(it["interactionId"])] = it
    pairs = exact = within = 0
    tag_scores: list[float] = []
    confusion = {c: [[0] * (max_level + 1) for _ in range(max_level + 1)] for c in codes}
    checks = {"applicabilityMismatches": [], "quoteFailures": [], "repAssertionAbove1": [], "reversalEarlierQuoteUsed": [],
              "pitchMonologueWithTags": [], "pitchBeforePainMissed": [], "missingSnippets": []}
    per_snippet = []
    for s in snippets_doc.get("snippets") or []:
        sid = s["id"]
        it = judged.get(sid)
        if it is None:
            checks["missingSnippets"].append(sid)
            continue
        elements = it.get("elements") or {}
        applicable = set(it.get("applicable") or elements.keys())
        row = {"id": sid, "kind": s.get("kind"), "elements": {}}
        for code, exp in (s.get("expected") or {}).items():
            want = int(exp.get("evidence", 0))
            block = elements.get(code)
            if block is None:
                checks["applicabilityMismatches"].append(f"{sid}: {code} expected but not scored")
                got = 0
            else:
                got = int(block.get("evidence", 0) or 0)
                if got > 1 and block.get("verified") is False:
                    checks["quoteFailures"].append(f"{sid}: {code} quote not verbatim")
                if "quote-unverified" in (block.get("flags") or []):
                    checks["quoteFailures"].append(f"{sid}: {code} quote capped by the validator")
            pairs += 1
            exact += int(got == want)
            within += int(abs(got - want) <= 1)
            if 0 <= want <= max_level and 0 <= got <= max_level:
                confusion[code][want][got] += 1
            row["elements"][code] = {"expected": want, "judged": got}
            if s.get("kind") == "rep-assertion" and got > 1:
                checks["repAssertionAbove1"].append(f"{sid}: {code} judged {got}")
        for code in (s.get("notApplicable") or {}):
            if code in applicable or code in elements:
                checks["applicabilityMismatches"].append(f"{sid}: {code} scored but labelled not applicable")
        got_tags = {t for b in elements.values() if isinstance(b, dict) for t in (b.get("behaviourTags") or [])}
        want_tags = set(s.get("expectedBehaviourTags") or [])
        score = _jaccard(got_tags, want_tags)
        tag_scores.append(score)
        row["tags"] = {"expected": sorted(want_tags), "judged": sorted(got_tags), "jaccard": round(score, 3)}
        if s.get("kind") == "pitch-monologue":
            if got_tags:
                checks["pitchMonologueWithTags"].append(f"{sid}: {sorted(got_tags)}")
            if (s.get("hygiene") or {}).get("pitchBeforePain") and not (it.get("hygiene") or {}).get("pitchBeforePain"):
                checks["pitchBeforePainMissed"].append(sid)
        rev = s.get("reversal")
        if rev and rev.get("element"):
            block = elements.get(rev["element"]) or {}
            q = normalize_text(str(block.get("quote") or ""))
            earlier = normalize_text(str(rev.get("earlierQuote") or ""))
            if q and earlier and (earlier in q or q in earlier):
                checks["reversalEarlierQuoteUsed"].append(f"{sid}: {rev['element']}")
        per_snippet.append(row)
    metrics = {
        "exactAgreement": round(exact / pairs, 3) if pairs else None,
        "withinOneLevel": round(within / pairs, 3) if pairs else None,
        "behaviourTagAgreement": round(sum(tag_scores) / len(tag_scores), 3) if tag_scores else None,
        "pairs": pairs, "snippets": len(per_snippet),
    }
    targets = snippets_doc.get("targets") or {}
    passed = {k: (metrics.get(k) is not None and metrics[k] >= float(v)) for k, v in targets.items()}
    return {"metrics": metrics, "targets": targets, "passed": passed, "allTargetsMet": all(passed.values()) if passed else False,
            "checks": checks, "confusion": confusion, "perSnippet": per_snippet}


def _confusion_text(confusion: dict, max_level: int) -> list[str]:
    lines = ["Confusion (rows: expected level, columns: judged level)"]
    for code, table in confusion.items():
        lines.append(f"  {code}:")
        lines.append("       " + "".join(f"{j:>5}" for j in range(max_level + 1)))
        for i, row in enumerate(table):
            lines.append(f"    {i:>2} " + "".join(f"{n:>5}" for n in row))
    return lines


def _report_text(result: dict, max_level: int) -> str:
    m, t = result["metrics"], result["targets"]
    lines = [f"Golden set: {m['snippets']} snippets, {m['pairs']} element pairs"]
    for key in ("exactAgreement", "withinOneLevel", "behaviourTagAgreement"):
        val = m.get(key)
        mark = "ok " if result["passed"].get(key) else "MISS"
        lines.append(f"  {mark} {key}: {'n/a' if val is None else f'{val:.3f}'} (target {t.get(key)})")
    lines.append("Secondary checks:")
    for key, items in result["checks"].items():
        lines.append(f"  {key}: {len(items)}" + (f" -> {', '.join(items[:6])}{' ...' if len(items) > 6 else ''}" if items else ""))
    lines += _confusion_text(result["confusion"], max_level)
    return "\n".join(lines)


# ---------- command ----------

def _prompt_lines(plan_doc: dict, plugin_root: Path) -> list[str]:
    lines = [f"Planned {plan_doc['totals']['batches']} golden batches, {plan_doc['totals']['interactions']} snippets, "
             f"~{plan_doc['totals']['estTokens']:,} tokens. Launch one flow-sales:deal-assessor agent per batch file:"]
    for b in plan_doc["batches"]:
        lines.append(f"  {b['file']}  ({b['interactions']} snippets)")
    lines.append(f"Then: python3 {plugin_root}/scripts/fs.py eval-golden compare --home <this store> --model <judge model>")
    return lines


def run(ctx: dict, args: Any) -> int:
    store: Store = ctx["store"]
    plugin_root = _plugin_root(ctx)
    action = getattr(args, "action", None) or "build"
    snippets_doc = load_snippets(plugin_root)
    framework, _ = planner.load_framework(plugin_root, snippets_doc.get("framework") or "meddpicc")
    if action == "build":
        store.ensure()
        if not store.exists():
            store.config.set("framework", snippets_doc.get("framework") or "meddpicc")
            store.config.save()
        plan_doc = build_batches(snippets_doc, plugin_root, store, parts=getattr(args, "parts", None) or DEFAULT_PARTS)
        store.log_run("eval-golden build", {"parts": plan_doc["totals"]["batches"]}, True, ctx["started"],
                      wrote=[b["file"] for b in plan_doc["batches"]], notes=f"{plan_doc['totals']['interactions']} snippets")
        if ctx.get("json"):
            print(json.dumps({"ok": True, **plan_doc}, indent=2, ensure_ascii=False))
        else:
            print("\n".join(_prompt_lines(plan_doc, plugin_root)))
        return 0
    if action != "compare":
        print(f"unknown action {action!r}; expected build or compare", file=sys.stderr)
        return 1
    files = sorted(store.assessments_dir.glob(f"{safe_id(DEAL_PREFIX)}*.json")) if store.assessments_dir.exists() else []
    if not files:
        msg = f"no golden assessments under {store.assessments_dir}; run the judge on the batch files first"
        print(json.dumps({"ok": False, "error": msg}) if ctx.get("json") else msg, file=sys.stderr)
        return 1
    validations = []
    assessments = []
    for f in files:
        rep = validate.validate_file(f, store, plugin_root)
        validations.append({"file": str(f), "ok": rep["ok"], "errors": rep["errors"][:5], "capped": rep["capped"]})
        assessments.append(store.read_json(f, {}) or {})
    result = compare(snippets_doc, assessments, framework)
    max_level = int(framework.get("maxLevel", 3) or 3)
    model = getattr(args, "model", None) or next((str(a.get("model")) for a in assessments if a.get("model")), None)
    record = {"at": now_iso(), "rubricHash": planner.rubric_hash_of(framework), "framework": framework.get("slug"),
              "frameworkVersion": framework.get("version"), "goldenVersion": snippets_doc.get("version"), "model": model,
              "note": getattr(args, "note", None) or "", "metrics": result["metrics"], "passed": result["passed"],
              "checks": {k: len(v) for k, v in result["checks"].items()}, "store": str(store.home)}
    runs_path = golden_dir(plugin_root) / "runs.jsonl"
    with runs_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    results_dir = golden_dir(plugin_root) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = record["at"].replace(":", "").replace("-", "")
    detail_path = results_dir / f"{stamp}-{safe_id(str(model or 'unknown'))}.json"
    with detail_path.open("w", encoding="utf-8") as fh:
        json.dump({**record, "validations": validations, "confusion": result["confusion"], "perSnippet": result["perSnippet"],
                   "checkDetails": result["checks"]}, fh, indent=2, ensure_ascii=False)
    store.log_run("eval-golden compare", {"model": model}, True, ctx["started"], read=[str(f) for f in files],
                  wrote=[str(runs_path), str(detail_path)], notes=json.dumps(result["metrics"]))
    if ctx.get("json"):
        print(json.dumps({"ok": True, **record, "validations": validations, "checkDetails": result["checks"],
                          "detail": str(detail_path)}, indent=2, ensure_ascii=False))
    else:
        print(_report_text(result, max_level))
        print(f"Recorded in {runs_path}; detail in {detail_path}")
    strict = bool(getattr(args, "strict", False))
    complete = not result["checks"]["missingSnippets"]
    return 0 if (not strict or (result["allTargetsMet"] and complete)) else 1
