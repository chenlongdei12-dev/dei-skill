#!/usr/bin/env python3
"""Transparent relative-performance forecast with chronological backtesting.

Predicts the probability that a work will exceed its prior rolling median. It does
not predict exact views or claim causality. Uses categorical empirical-Bayes rates
and Python's standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


FEATURES = (
    "primary_topic_draft", "hook_type_draft", "structure_draft", "duration_bucket",
    "semantic_endpoint_draft", "reality_mechanism_draft", "evidence_types_draft",
)


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path | None) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path else None


def number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def parse_date(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float = .03, high: float = .97) -> float:
    return max(low, min(high, value))


def logit(p: float) -> float:
    p = clamp(p)
    return math.log(p / (1 - p))


def logistic(value: float) -> float:
    return 1 / (1 + math.exp(-max(-20, min(20, value))))


def choose_metric(headers: set[str], requested: str | None) -> tuple[str, str]:
    if requested:
        if requested not in headers:
            raise ValueError(f"指标不存在: {requested}")
        window = requested.rsplit("_", 1)[-1] if requested.endswith(("_24h", "_72h", "_7d", "_30d")) else "cumulative"
        return requested, window
    for metric in ("shares_7d", "favorites_7d", "likes_7d", "shares", "favorites", "likes"):
        if metric in headers:
            return metric, metric.rsplit("_", 1)[-1] if metric.endswith(("_24h", "_72h", "_7d", "_30d")) else "cumulative"
    raise ValueError("没有可用于预测的互动指标")


def build_labels(rows: list[dict[str, Any]], metric: str, baseline_window: int, min_history: int) -> list[dict[str, Any]]:
    sorted_rows = sorted([r for r in rows if parse_date(r.get("published_at", "")) and number(r.get(metric)) is not None], key=lambda r: parse_date(r["published_at"]) or datetime.min)
    labeled = []
    history: list[float] = []
    for row in sorted_rows:
        value = number(row.get(metric))
        if len(history) >= min_history:
            baseline = statistics.median(history[-baseline_window:])
            item = dict(row)
            item["_target_value"] = value
            item["_baseline"] = baseline
            item["_label"] = int(value > baseline)
            labeled.append(item)
        history.append(value)
    return labeled


def feature_values(row: dict[str, Any], features: tuple[str, ...]) -> list[tuple[str, str]]:
    values = []
    for feature in features:
        raw = str(row.get(feature) or "未知")
        # Evidence can be multi-label; keep the first to avoid pretending independence.
        value = raw.split("、", 1)[0].strip() or "未知"
        values.append((feature, value))
    return values


def fit(rows: list[dict[str, Any]], features: tuple[str, ...], alpha: float = 8.0) -> dict[str, Any]:
    if not rows:
        raise ValueError("训练样本为空")
    global_rate = sum(r["_label"] for r in rows) / len(rows)
    counts: dict[str, dict[str, list[int]]] = {feature: defaultdict(lambda: [0, 0]) for feature in features}
    for row in rows:
        for feature, value in feature_values(row, features):
            counts[feature][value][0] += int(row["_label"])
            counts[feature][value][1] += 1
    rates: dict[str, dict[str, dict[str, float | int]]] = {}
    for feature, groups in counts.items():
        rates[feature] = {}
        for value, (successes, total) in groups.items():
            probability = (successes + alpha * global_rate) / (total + alpha)
            rates[feature][value] = {"probability": probability, "support": total, "successes": successes}
    return {"global_rate": global_rate, "rates": rates, "features": features, "training_size": len(rows), "alpha": alpha}


def predict(model: dict[str, Any], row: dict[str, Any]) -> tuple[float, int]:
    base = model["global_rate"]
    adjustments, supports = [], []
    for feature, value in feature_values(row, tuple(model["features"])):
        cell = model["rates"].get(feature, {}).get(value)
        if cell:
            adjustments.append(logit(float(cell["probability"])) - logit(base))
            supports.append(int(cell["support"]))
    score = logit(base) + (sum(adjustments) / max(1, len(adjustments)))
    return clamp(logistic(score)), min(supports) if supports else 0


def metrics(scored: list[dict[str, Any]], baseline_probability: float) -> dict[str, Any]:
    if not scored:
        return {"count": 0}
    labels = [int(x["actual"]) for x in scored]
    probs = [float(x["probability"]) for x in scored]
    predictions = [int(p >= .5) for p in probs]
    accuracy = sum(a == b for a, b in zip(labels, predictions)) / len(labels)
    tp = sum(a == 1 and b == 1 for a, b in zip(labels, predictions))
    tn = sum(a == 0 and b == 0 for a, b in zip(labels, predictions))
    positives, negatives = sum(labels), len(labels) - sum(labels)
    balanced = ((tp / positives if positives else 0) + (tn / negatives if negatives else 0)) / 2
    brier = sum((p - y) ** 2 for p, y in zip(probs, labels)) / len(labels)
    baseline_brier = sum((baseline_probability - y) ** 2 for y in labels) / len(labels)
    bins = []
    for lower in (0, .2, .4, .6, .8):
        cells = [x for x in scored if lower <= x["probability"] < lower + .2 or (lower == .8 and x["probability"] == 1)]
        if cells:
            bins.append({"range": [lower, round(lower + .2, 1)], "count": len(cells), "mean_prediction": round(sum(x["probability"] for x in cells) / len(cells), 4), "observed_rate": round(sum(x["actual"] for x in cells) / len(cells), 4)})
    return {"count": len(labels), "positive_rate": round(sum(labels) / len(labels), 4), "accuracy": round(accuracy, 4), "balanced_accuracy": round(balanced, 4), "brier": round(brier, 6), "baseline_brier": round(baseline_brier, 6), "brier_improvement": round(baseline_brier - brier, 6), "calibration_bins": bins}


def confidence(support: int, backtest: dict[str, Any], metric_window: str) -> str:
    if metric_window == "cumulative" or backtest.get("count", 0) < 20 or backtest.get("brier_improvement", 0) <= 0:
        return "low"
    if support >= 30 and backtest.get("count", 0) >= 40 and backtest.get("brier_improvement", 0) >= .01:
        return "high"
    return "medium" if support >= 10 else "low"


def main() -> None:
    parser = argparse.ArgumentParser(description="对抖音内容做超过滚动基准的相对概率预测")
    parser.add_argument("content_dna", type=Path)
    parser.add_argument("--metric")
    parser.add_argument("--candidates", type=Path, help="JSON: {candidates:[...]}，字段使用内容DNA标签")
    parser.add_argument("--output-dir", type=Path, default=Path("douyin_forecast_output"))
    parser.add_argument("--train-ratio", type=float, default=.7)
    parser.add_argument("--baseline-window", type=int, default=30)
    parser.add_argument("--min-history", type=int, default=20)
    args = parser.parse_args()

    rows = read_csv(args.content_dna)
    if not rows:
        raise SystemExit("content_dna 为空")
    metric, metric_window = choose_metric(set(rows[0]), args.metric)
    labeled = build_labels(rows, metric, args.baseline_window, args.min_history)
    if len(labeled) < 30:
        raise SystemExit(f"可回测样本不足：{len(labeled)}；至少需要30条")
    cutoff = max(20, min(len(labeled) - 10, int(len(labeled) * args.train_ratio)))
    train, test = labeled[:cutoff], labeled[cutoff:]
    model = fit(train, FEATURES)
    scored = []
    for row in test:
        probability, support = predict(model, row)
        scored.append({"video_id": row.get("video_id"), "published_at": row.get("published_at"), "target_value": row["_target_value"], "baseline": row["_baseline"], "actual": row["_label"], "probability": round(probability, 6), "support": support})
    backtest = metrics(scored, model["global_rate"])
    is_usable = (
        metric_window != "cumulative"
        and backtest.get("count", 0) >= 20
        and backtest.get("brier_improvement", 0) >= .01
        and backtest.get("balanced_accuracy", 0) >= .55
    )
    backtest.update({"metric": metric, "metric_window": metric_window, "split": "chronological_holdout", "training_count": len(train), "test_count": len(test), "cutoff_published_at": test[0].get("published_at"), "status": "usable" if is_usable else "experimental"})

    final_model = fit(labeled, FEATURES)
    candidate_payload = read_json(args.candidates) or {"candidates": []}
    predictions = []
    current_baseline = labeled[-1]["_baseline"]
    for index, candidate in enumerate(candidate_payload.get("candidates", []), 1):
        probability, support = predict(final_model, candidate)
        forecast_id = candidate.get("forecast_id") or f"FC-{datetime.now():%Y%m%d%H%M%S}-{index:03d}"
        predictions.append({
            "forecast_id": forecast_id, "candidate_id": candidate.get("candidate_id") or candidate.get("title") or str(index),
            "target": f"{metric}_above_prior_rolling_median", "metric": metric, "metric_window": metric_window,
            "baseline_value": current_baseline, "probability_above_baseline": round(probability, 4),
            "confidence": confidence(support, backtest, metric_window), "category_support_floor": support,
            "features": {feature: candidate.get(feature) for feature in FEATURES},
            "limitations": (["累计指标受作品成熟度影响；只作为探索性排序"] if metric_window == "cumulative" else []) + (["时间留出回测未优于基准，预测只能作为实验假设"] if backtest["status"] != "usable" else []),
            "status": "pending",
        })

    result = {
        "schema_version": "1.0", "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": str(args.content_dna.resolve()), "target_definition": f"{metric} 是否超过发布前{args.baseline_window}条作品中位数",
        "prediction_kind": "relative_probability", "metric": metric, "metric_window": metric_window,
        "backtest": backtest, "predictions": predictions,
        "global_limitations": ["这是相关性排序模型，不证明内容特征导致表现。", "不输出精确播放或点赞预测。"] + (["当前使用累计指标，置信度强制为低；优先补充固定观察窗口数据。"] if metric_window == "cumulative" else []),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "forecast_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with (args.output_dir / "forecast_backtest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["video_id", "published_at", "target_value", "baseline", "actual", "probability", "support"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(scored)
    summary = ["# 相对预测回测", "", f"- 目标：{result['target_definition']}", f"- 时间留出：训练{len(train)}条，测试{len(test)}条", f"- Brier：{backtest['brier']}；基准Brier：{backtest['baseline_brier']}；改善：{backtest['brier_improvement']}", f"- 状态：**{backtest['status']}**", f"- 指标窗口：{metric_window}", "", "只有状态为 usable 且固定观察窗口存在时，才能把预测用于内容排序；否则只作为待验证假设。"]
    (args.output_dir / "forecast_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "metric": metric, "window": metric_window, "backtest_status": backtest["status"], "test_count": len(test), "predictions": len(predictions)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
