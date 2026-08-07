#!/usr/bin/env python3
"""Validate v2 artifacts and cross-artifact invariants without third-party packages."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: JSON无法解析: {exc}") from exc


def require(obj: dict[str, Any], keys: tuple[str, ...], label: str, errors: list[str]) -> None:
    for key in keys:
        if key not in obj:
            errors.append(f"{label}: 缺少字段 {key}")


def validate_analysis(path: Path, errors: list[str]) -> None:
    data = load(path)
    require(data, ("schema_version", "snapshot", "sample_size", "capability", "data_audit", "evidence_ledger", "contradiction_ledger", "limitations"), str(path), errors)
    if data.get("schema_version") != "2.0":
        errors.append(f"{path}: schema_version 应为2.0")
    snapshot = data.get("snapshot", {})
    if snapshot.get("metric_window") not in {"fixed_window", "cumulative_as_of_snapshot"}:
        errors.append(f"{path}: metric_window 非法")
    for claim in data.get("evidence_ledger", []):
        require(claim, ("claim_id", "statement", "claim_type", "sample_size", "confidence", "limitations", "status"), "claim", errors)
    for conflict in data.get("contradiction_ledger", []):
        require(conflict, ("conflict_id", "issue", "claim_a", "claim_b", "resolution", "status"), "conflict", errors)


def validate_forecast(path: Path, errors: list[str]) -> None:
    data = load(path)
    require(data, ("prediction_kind", "metric", "metric_window", "backtest", "predictions", "global_limitations"), str(path), errors)
    backtest = data.get("backtest", {})
    if data.get("metric_window") == "cumulative" and backtest.get("status") == "usable":
        errors.append(f"{path}: 累计指标预测不得标记usable")
    if backtest.get("status") == "usable":
        if backtest.get("test_count", 0) < 20 or backtest.get("brier_improvement", 0) < .01 or backtest.get("balanced_accuracy", 0) < .55:
            errors.append(f"{path}: usable未达到回测门槛")
    for prediction in data.get("predictions", []):
        require(prediction, ("forecast_id", "candidate_id", "target", "metric", "metric_window", "probability_above_baseline", "confidence", "status"), "prediction", errors)
        probability = prediction.get("probability_above_baseline")
        if probability is None or not 0 <= probability <= 1:
            errors.append("prediction: 概率必须在0—1")
        if prediction.get("metric_window") == "cumulative" and prediction.get("confidence") != "low":
            errors.append("prediction: 累计指标置信度必须为low")


def validate_passport(path: Path, errors: list[str]) -> None:
    data = load(path)
    required = ("version", "analyses", "initial_baseline", "current_baseline", "evidence_ledger", "contradiction_ledger", "formula_library", "hypothesis_ledger", "forecast_ledger", "forecast_backtests", "execution_history", "cross_channel_signals", "data_gaps", "data_gap_history")
    require(data, required, str(path), errors)
    if data.get("version") != "2.0":
        errors.append(f"{path}: passport version 应为2.0")
    ids = [x.get("id") for x in data.get("analyses", [])]
    if len(ids) != len(set(ids)):
        errors.append(f"{path}: analysis id重复")


def validate_cross(path: Path, errors: list[str]) -> None:
    data = load(path)
    require(data, ("summary", "topic_summaries", "content_world_summaries", "hypotheses", "limitations"), str(path), errors)
    forbidden = {"combined_score", "douyin_equivalent_score", "performance_index"}
    if forbidden & set(data.get("summary", {})):
        errors.append(f"{path}: 跨渠道输出不得生成统一表现分")
    for hypothesis in data.get("hypotheses", []):
        if hypothesis.get("evidence_type") != "cross_channel_weak_signal" or hypothesis.get("confidence") != "low":
            errors.append(f"{path}: 跨渠道假设必须标记weak_signal与low")


def validate_csv(path: Path, errors: list[str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
    required = {"video_id", "published_at", "snapshot_at", "observation_age_days", "maturity_bucket", "semantic_endpoint_draft", "reality_mechanism_draft", "script_match_ambiguous"}
    missing = required - fields
    if missing:
        errors.append(f"{path}: content_dna缺少 {sorted(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="校验抖音内容系统v2产物")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    if not args.root.exists():
        raise SystemExit(f"路径不存在: {args.root}")
    errors: list[str] = []
    checked = []
    for path in args.root.rglob("*.json"):
        name = path.name
        if name == "analysis_result.json":
            validate_analysis(path, errors); checked.append(str(path))
        elif name == "forecast_result.json":
            validate_forecast(path, errors); checked.append(str(path))
        elif name == "cross_channel_signals.json":
            validate_cross(path, errors); checked.append(str(path))
        elif "passport" in name.lower():
            validate_passport(path, errors); checked.append(str(path))
    for path in args.root.rglob("content_dna.csv"):
        validate_csv(path, errors); checked.append(str(path))
    if not checked:
        errors.append("没有找到可识别的v2产物")
    result = {"root": str(args.root.resolve()), "checked": checked, "error_count": len(errors), "errors": errors, "status": "pass" if not errors else "fail"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
