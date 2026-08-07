#!/usr/bin/env python3
"""End-to-end deterministic self-test for all three optimization stages."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True, text=True, capture_output=True)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="douyin-skill-v2-") as temp:
        root = Path(temp)
        data = root / "synthetic-20260801.csv"
        fields = ["作品ID", "作品标题", "发布时间", "视频时长", "点赞数", "收藏数", "评论数", "分享量", "likes_7d"]
        start = datetime(2025, 1, 1, 20)
        rows = []
        for index in range(120):
            strong = index % 2 == 0
            base = 10000 + (index % 7) * 100
            if strong:
                title = "为什么女人做选择要看现实代价 第一看收入 第二看责任"
                likes7 = base * 2
                duration = 240
            else:
                title = "关于提升认知和内核稳定的一点想法"
                likes7 = base // 2
                duration = 90
            rows.append({"作品ID": str(700000 + index), "作品标题": title, "发布时间": (start + timedelta(days=index)).strftime("%Y-%m-%d %H:%M:%S"), "视频时长": duration, "点赞数": likes7 * 2, "收藏数": likes7, "评论数": likes7 // 30, "分享量": likes7 // 2, "likes_7d": likes7})
        rows.append(dict(rows[-1]))  # duplicate ID must be audited and deduplicated
        with data.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

        analysis_dir = root / "analysis"
        run(str(ROOT / "analyze_douyin.py"), str(data), "--snapshot-at", "2026-08-01", "--output-dir", str(analysis_dir))
        analysis = json.loads((analysis_dir / "analysis_result.json").read_text(encoding="utf-8"))
        assert analysis["sample_size"] == 120
        assert analysis["data_audit"]["duplicate_group_count"] == 1
        assert analysis["capability"]["axes"]["fixed_window"] is True
        assert analysis["evidence_ledger"]
        assert "observation_age_days" in next(csv.DictReader((analysis_dir / "content_dna.csv").open(encoding="utf-8-sig")))

        candidates = root / "candidates.json"
        write_json(candidates, {"candidates": [
            {"candidate_id": "HIGH", "primary_topic_draft": "女性现实", "hook_type_draft": "提问", "structure_draft": "步骤/模型", "duration_bucket": "181–360秒", "semantic_endpoint_draft": "现实选择与代价", "reality_mechanism_draft": "责任/照护", "evidence_types_draft": "数据"},
            {"candidate_id": "LOW", "primary_topic_draft": "认知成长", "hook_type_draft": "观点陈述", "structure_draft": "观点论证", "duration_bucket": "61–180秒", "semantic_endpoint_draft": "主体性/向内", "reality_mechanism_draft": "心理/抽象解释", "evidence_types_draft": "纯断言"},
        ]})
        forecast_dir = root / "forecast"
        run(str(ROOT / "forecast_content.py"), str(analysis_dir / "content_dna.csv"), "--metric", "likes_7d", "--candidates", str(candidates), "--output-dir", str(forecast_dir))
        forecast = json.loads((forecast_dir / "forecast_result.json").read_text(encoding="utf-8"))
        assert forecast["backtest"]["status"] == "usable", forecast["backtest"]
        assert forecast["predictions"][0]["probability_above_baseline"] > forecast["predictions"][1]["probability_above_baseline"]

        channel_data = root / "moments.csv"
        with channel_data.open("w", encoding="utf-8-sig", newline="") as handle:
            fields2 = ["内容ID", "渠道", "发布时间", "主题", "内容世界", "主任务", "点赞", "评论", "私聊", "经历讲述", "业务咨询"]
            writer = csv.DictWriter(handle, fieldnames=fields2); writer.writeheader()
            writer.writerows([
                {"内容ID": "M1", "渠道": "moments", "发布时间": "2026-07-01", "主题": "女性现实", "内容世界": "女性现实", "主任务": "讨论", "点赞": 20, "评论": 3, "私聊": 1, "经历讲述": 1, "业务咨询": 0},
                {"内容ID": "M2", "渠道": "moments", "发布时间": "2026-07-02", "主题": "女性现实", "内容世界": "女性现实", "主任务": "认识", "点赞": 15, "评论": 2, "私聊": 0, "经历讲述": 1, "业务咨询": 0},
                {"内容ID": "M3", "渠道": "moments", "发布时间": "2026-07-03", "主题": "女性现实", "内容世界": "女性现实", "主任务": "理解", "点赞": 18, "评论": 1, "私聊": 0, "经历讲述": 0, "业务咨询": 0},
            ])
        channel_dir = root / "cross_channel"
        run(str(ROOT / "analyze_channel_signals.py"), str(channel_data), "--output-dir", str(channel_dir))
        cross = json.loads((channel_dir / "cross_channel_signals.json").read_text(encoding="utf-8"))
        assert len(cross["hypotheses"]) == 1
        assert cross["hypotheses"][0]["confidence"] == "low"

        plan = root / "plan.json"
        write_json(plan, {"hypotheses": [{"hypothesis_id": "HYP-001", "statement": "现实代价终点优于抽象认知终点", "primary_metric": "likes_7d", "metric_window": "7d", "control": [], "variant": [], "status": "testing", "sample_size": 0, "result": None, "next_action": "各发3条"}], "formulas": [{"formula_id": "FOR-001", "statement": "现实选择+步骤模型", "status": "proposed"}]})
        passport = root / "synthetic_passport.json"
        run(str(ROOT / "update_passport.py"), "--analysis", str(analysis_dir / "analysis_result.json"), "--plan", str(plan), "--forecast", str(forecast_dir / "forecast_result.json"), "--cross-channel", str(channel_dir / "cross_channel_signals.json"), "--handle", "synthetic", "--output", str(passport))
        saved = json.loads(passport.read_text(encoding="utf-8"))
        assert saved["version"] == "2.0"
        assert len(saved["hypothesis_ledger"]) == 2
        assert len(saved["forecast_ledger"]) == 2
        assert saved["cross_channel_signals"]

        execution = root / "execution.json"
        write_json(execution, {
            "hypothesis_updates": [{"hypothesis_id": "HYP-001", "statement": "现实代价终点优于抽象认知终点", "primary_metric": "likes_7d", "metric_window": "7d", "control": ["LOW"], "variant": ["HIGH"], "status": "supported", "sample_size": 6, "result": {"direction": "positive"}, "next_action": "继续复验"}],
            "forecast_actuals": [{"forecast_id": forecast["predictions"][0]["forecast_id"], "above_baseline": True, "actual_value": 22000}],
        })
        passport2 = root / "synthetic_passport_v2.json"
        run(str(ROOT / "update_passport.py"), "--analysis", str(analysis_dir / "analysis_result.json"), "--passport", str(passport), "--execution", str(execution), "--intent", "REVIEW", "--output", str(passport2))
        saved2 = json.loads(passport2.read_text(encoding="utf-8"))
        updated = next(x for x in saved2["hypothesis_ledger"] if x.get("hypothesis_id") == "HYP-001")
        resolved = next(x for x in saved2["forecast_ledger"] if x.get("forecast_id") == forecast["predictions"][0]["forecast_id"])
        assert updated["status"] == "supported" and updated["revision_history"]
        assert resolved["status"] == "resolved" and "brier" in resolved

        run(str(ROOT / "validate_artifacts.py"), str(root))
        print(json.dumps({"status": "pass", "stages": {"diagnosis": True, "forecast": True, "cross_channel": True, "passport": True, "validation": True}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
