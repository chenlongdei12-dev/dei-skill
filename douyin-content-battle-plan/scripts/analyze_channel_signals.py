#!/usr/bin/env python3
"""Normalize non-Douyin feedback as separate weak signals.

Signals are never merged into Douyin performance metrics. The output can suggest
cross-channel hypotheses but cannot validate platform performance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from analyze_douyin import number, parse_date, read_table


ALIASES = {
    "content_id": ["内容ID", "朋友圈ID", "作品ID", "content_id"],
    "channel": ["渠道", "平台", "channel"],
    "published_at": ["发布时间", "发布日期", "published_at"],
    "text": ["内容", "文案", "正文", "text"],
    "topic": ["主题", "选题", "topic"],
    "content_world": ["内容世界", "栏目", "content_world"],
    "primary_task": ["主任务", "目的", "primary_task"],
    "likes": ["点赞", "点赞数", "likes"],
    "comments": ["评论", "评论数", "comments"],
    "private_messages": ["私聊", "私信", "私聊数", "private_messages"],
    "experience_replies": ["经历讲述", "主动讲述", "experience_replies"],
    "business_inquiries": ["业务咨询", "咨询数", "business_inquiries"],
    "source_path": ["来源", "来源路径", "source_path"],
}
NUMERIC = {"likes", "comments", "private_messages", "experience_replies", "business_inquiries"}


def choose_columns(headers: list[str]) -> dict[str, str]:
    normalized = {str(h).strip().lower(): h for h in headers}
    result = {}
    for standard, aliases in ALIASES.items():
        for alias in aliases:
            if alias.lower() in normalized:
                result[standard] = normalized[alias.lower()]
                break
    return result


def normalize(raw: list[dict[str, Any]], default_channel: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not raw:
        return [], {}
    mapping = choose_columns(list(raw[0]))
    rows = []
    for index, source in enumerate(raw, 1):
        row: dict[str, Any] = {"source_row": index + 1}
        for standard, original in mapping.items():
            value = source.get(original)
            if standard in NUMERIC:
                row[standard] = max(0, number(value) or 0)
            elif standard == "published_at":
                row[standard] = parse_date(value)
            else:
                row[standard] = "" if value is None else str(value).strip()
        row["channel"] = row.get("channel") or default_channel
        row["content_id"] = row.get("content_id") or f"{row['channel']}-{index:04d}"
        rows.append(row)
    return rows, mapping


def summarize(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "未标注")].append(row)
    output = []
    for label, items in groups.items():
        output.append({
            "label": label, "post_count": len(items),
            "likes": int(sum(x.get("likes", 0) for x in items)),
            "comments": int(sum(x.get("comments", 0) for x in items)),
            "private_messages": int(sum(x.get("private_messages", 0) for x in items)),
            "experience_replies": int(sum(x.get("experience_replies", 0) for x in items)),
            "business_inquiries": int(sum(x.get("business_inquiries", 0) for x in items)),
            "posts_with_deep_response": sum((x.get("private_messages", 0) + x.get("experience_replies", 0) + x.get("business_inquiries", 0)) > 0 for x in items),
            "content_ids": [x["content_id"] for x in items],
        })
    return sorted(output, key=lambda x: (x["posts_with_deep_response"], x["post_count"]), reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="分析朋友圈等跨渠道弱信号")
    parser.add_argument("data", type=Path)
    parser.add_argument("--channel", default="moments")
    parser.add_argument("--output-dir", type=Path, default=Path("channel_signal_output"))
    args = parser.parse_args()

    rows, mapping = normalize(read_table(args.data), args.channel)
    if not rows:
        raise SystemExit("没有读取到渠道反馈")
    topic_summaries = summarize(rows, "topic")
    world_summaries = summarize(rows, "content_world")
    hypotheses = []
    for index, group in enumerate(topic_summaries, 1):
        if group["post_count"] >= 3 and group["posts_with_deep_response"] >= 2:
            stable = hashlib.sha1(f"{args.channel}|{group['label']}".encode("utf-8")).hexdigest()[:8].upper()
            hypotheses.append({
                "hypothesis_id": f"XCH-{stable}",
                "statement": f"{group['label']}在{args.channel}出现重复深度反馈，值得在抖音做小样本内容测试",
                "source_channel": args.channel, "evidence_type": "cross_channel_weak_signal",
                "source_content_ids": group["content_ids"], "sample_size": group["post_count"],
                "status": "proposed", "confidence": "low",
                "result": None, "next_action": "生成不超过3条抖音测试内容；不得把朋友圈反馈当作抖音表现验证",
            })
    summary = {
        "post_count": len(rows), "channels": dict((channel, sum(r["channel"] == channel for r in rows)) for channel in sorted({r["channel"] for r in rows})),
        "signals_available": [field for field in NUMERIC if any(r.get(field, 0) > 0 for r in rows)],
        "deep_response_definition": "私聊、主动讲述经历或业务咨询；分别保存，不合并为平台表现分",
    }
    result = {
        "schema_version": "1.0", "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": str(args.data.resolve()), "column_mapping": mapping, "summary": summary,
        "topic_summaries": topic_summaries, "content_world_summaries": world_summaries,
        "hypotheses": hypotheses,
        "limitations": ["跨渠道反馈只能用于选题发现与人格/需求线索。", "不得与抖音播放、互动或留存合并计算。", "点赞和评论受到社交关系与触达范围影响，不能视为随机样本。"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "cross_channel_signals.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["content_id", "channel", "published_at", "topic", "content_world", "primary_task", "likes", "comments", "private_messages", "experience_replies", "business_inquiries", "source_path", "text"]
    with (args.output_dir / "normalized_channel_signals.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    with (args.output_dir / "topic_signal_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields2 = ["label", "post_count", "likes", "comments", "private_messages", "experience_replies", "business_inquiries", "posts_with_deep_response", "content_ids"]
        writer = csv.DictWriter(handle, fieldnames=fields2, extrasaction="ignore")
        writer.writeheader()
        for row in topic_summaries:
            item = dict(row); item["content_ids"] = "、".join(row["content_ids"]); writer.writerow(item)
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "posts": len(rows), "hypotheses": len(hypotheses)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
