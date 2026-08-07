#!/usr/bin/env python3
"""Append analysis, experiments, forecasts, and channel signals to a v2 passport."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def read_json(path: Path | None) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path else None


def new_passport(handle: str, nickname: str) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "version": "2.0", "platform": "douyin", "handle": handle, "nickname": nickname,
        "positioning": {}, "created_at": now, "last_analysis_date": None,
        "initial_baseline": {}, "current_baseline": {}, "analyses": [],
        "evidence_ledger": [], "contradiction_ledger": [], "formula_library": [],
        "hypothesis_ledger": [], "forecast_ledger": [], "forecast_backtests": [],
        "execution_history": [], "cross_channel_signals": [], "growth_milestones": [],
        "data_gaps": [], "data_gap_history": [], "notes": [],
    }


def migrate(passport: dict[str, Any]) -> dict[str, Any]:
    passport["version"] = "2.0"
    if "baseline" in passport and passport.get("baseline") and not passport.get("initial_baseline"):
        passport["initial_baseline"] = passport["baseline"]
    for key, default in {
        "initial_baseline": {}, "current_baseline": {}, "analyses": [], "evidence_ledger": [],
        "contradiction_ledger": [], "formula_library": [], "hypothesis_ledger": [],
        "forecast_ledger": [], "forecast_backtests": [], "execution_history": [],
        "cross_channel_signals": [], "growth_milestones": [], "data_gaps": [],
        "data_gap_history": [], "notes": [],
    }.items():
        passport.setdefault(key, default)
    return passport


def unique_id(items: list[dict[str, Any]], base: str, key: str = "id") -> str:
    ids = {item.get(key) for item in items}
    if base not in ids:
        return base
    index = 2
    while f"{base}-{index}" in ids:
        index += 1
    return f"{base}-{index}"


def detect_cadence(passport: dict[str, Any]) -> str:
    last = passport.get("last_analysis_date")
    if not last or not passport.get("analyses"):
        return "FIRST_TIME"
    try:
        days = (datetime.now() - datetime.fromisoformat(last)).days
    except ValueError:
        return "MONTHLY"
    return "WEEKLY" if days <= 14 else "MONTHLY" if days < 90 else "QUARTERLY"


def upsert(items: list[dict[str, Any]], incoming: list[dict[str, Any]], id_keys: tuple[str, ...]) -> None:
    for value in incoming:
        identity = next((value.get(key) for key in id_keys if value.get(key)), None)
        if not identity:
            continue
        existing = next((item for item in items if any(item.get(key) == identity for key in id_keys)), None)
        if existing:
            history = existing.setdefault("revision_history", [])
            history.append({"at": datetime.now().isoformat(timespec="seconds"), "previous_status": existing.get("status"), "previous_result": existing.get("result")})
            existing.update(value)
        else:
            items.append(value)


def resolve_forecasts(passport: dict[str, Any], execution: dict[str, Any] | None) -> None:
    if not execution:
        return
    actuals = execution.get("forecast_actuals", [])
    for actual in actuals:
        forecast_id = actual.get("forecast_id")
        forecast = next((x for x in passport["forecast_ledger"] if x.get("forecast_id") == forecast_id), None)
        if not forecast:
            continue
        forecast["actual"] = actual
        observed = actual.get("above_baseline")
        probability = forecast.get("probability_above_baseline")
        if observed is not None and probability is not None:
            forecast["brier"] = round((float(probability) - int(bool(observed))) ** 2, 6)
            forecast["status"] = "resolved"


def main() -> None:
    parser = argparse.ArgumentParser(description="创建或更新抖音内容决策护照 v2")
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--passport", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--execution", type=Path)
    parser.add_argument("--forecast", type=Path)
    parser.add_argument("--cross-channel", type=Path)
    parser.add_argument("--handle", default="")
    parser.add_argument("--nickname", default="")
    parser.add_argument("--intent", choices=["AUDIT", "DIAGNOSE", "FORECAST", "PLAN", "REVIEW", "CREATE"], default="DIAGNOSE")
    parser.add_argument("--cadence", choices=["FIRST_TIME", "WEEKLY", "MONTHLY", "QUARTERLY"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    analysis = read_json(args.analysis) or {}
    passport = migrate(read_json(args.passport) or new_passport(args.handle, args.nickname))
    plan, execution = read_json(args.plan), read_json(args.execution)
    forecast, cross = read_json(args.forecast), read_json(args.cross_channel)
    if args.handle:
        passport["handle"] = args.handle
    if args.nickname:
        passport["nickname"] = args.nickname

    now = datetime.now().isoformat(timespec="seconds")
    cadence = args.cadence or detect_cadence(passport)
    analysis_id = unique_id(passport["analyses"], now[:10])
    record = {
        "id": analysis_id, "created_at": now, "intent": args.intent, "cadence": cadence,
        "data_period": analysis.get("data_period"), "snapshot": analysis.get("snapshot"),
        "capability": analysis.get("capability", {"level": analysis.get("capability_level")}),
        "sample_size": analysis.get("sample_size"), "metrics": analysis.get("metric_distributions", {}),
        "top_items": analysis.get("top_items", []), "content_dna_summary": analysis.get("group_performance_draft", {}),
        "claim_ids": [x.get("claim_id") for x in analysis.get("evidence_ledger", [])],
        "conflict_ids": [x.get("conflict_id") for x in analysis.get("contradiction_ledger", [])],
        "plan": plan, "execution": execution,
        "source_files": [x for x in (analysis.get("source_file"), analysis.get("scripts_dir")) if x],
    }
    passport["analyses"].append(record)
    passport["last_analysis_date"] = now

    baseline = {"analysis_id": analysis_id, "date": now[:10], "snapshot": analysis.get("snapshot"), "capability": analysis.get("capability", {}), "sample_size": analysis.get("sample_size"), "metrics": analysis.get("metric_distributions", {})}
    if not passport.get("initial_baseline"):
        passport["initial_baseline"] = baseline
    passport["current_baseline"] = baseline

    upsert(passport["evidence_ledger"], analysis.get("evidence_ledger", []), ("claim_id",))
    upsert(passport["contradiction_ledger"], analysis.get("contradiction_ledger", []), ("conflict_id",))
    if plan:
        upsert(passport["hypothesis_ledger"], plan.get("hypotheses", []), ("hypothesis_id", "id"))
        upsert(passport["formula_library"], plan.get("formulas", []), ("formula_id", "id"))
    if execution:
        entry = dict(execution)
        entry.setdefault("id", unique_id(passport["execution_history"], f"EXEC-{now[:10]}"))
        entry.setdefault("recorded_at", now)
        passport["execution_history"].append(entry)
        upsert(passport["hypothesis_ledger"], execution.get("hypothesis_updates", []), ("hypothesis_id", "id"))
        upsert(passport["formula_library"], execution.get("formula_updates", []), ("formula_id", "id"))
    if forecast:
        for item in forecast.get("predictions", []):
            item.setdefault("created_at", now)
            item.setdefault("status", "pending")
        upsert(passport["forecast_ledger"], forecast.get("predictions", []), ("forecast_id",))
        if forecast.get("backtest"):
            passport["forecast_backtests"].append({"recorded_at": now, **forecast["backtest"]})
    if cross:
        passport["cross_channel_signals"].append({"recorded_at": now, "source": cross.get("source_file"), "summary": cross.get("summary"), "topic_summaries": cross.get("topic_summaries", [])})
        upsert(passport["hypothesis_ledger"], cross.get("hypotheses", []), ("hypothesis_id", "id"))

    resolve_forecasts(passport, execution)
    missing = analysis.get("missing_priority_metrics", [])
    passport["data_gaps"] = missing
    passport["data_gap_history"].append({"at": now, "analysis_id": analysis_id, "missing": missing})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(passport, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "intent": args.intent, "cadence": cadence, "analyses": len(passport["analyses"]), "claims": len(passport["evidence_ledger"]), "conflicts": len(passport["contradiction_ledger"]), "hypotheses": len(passport["hypothesis_ledger"]), "forecasts": len(passport["forecast_ledger"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
