#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily AI analysis for Xinwenlianbo transcripts (OpenAI-compatible API).

Reads the latest transcript (or --date), builds a context-controlled prompt
(today's full text + 30-day title digest), calls a chat-completion API, and
writes 每日分析报告/YYYY/MM/YYYY-MM-DD_分析报告.md.

Environment:
  LLM_BASE_URL  API base, default https://api.openai.com/v1
  LLM_API_KEY   required to run; script exits 0 with a notice when missing
  LLM_MODEL     default gpt-4o-mini
Gracious skip: no key -> exit 0 (so CI stays green).
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta

try:
    from lxml import html as lxml_html
except ImportError:  # markdown parsing fallback: regex
    lxml_html = None

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
API_KEY = os.environ.get("LLM_API_KEY", "")

PROMPT_TEMPLATE = """你是一名《新闻联播》内容分析师。请基于以下材料生成当天的分析报告。

# 分析规则（必须遵守）
- 严格区分：原文事实 / 与历史相比的可观察变化 / 基于证据的解释 / 尚待验证的推测。
- "近30天首次出现"不等于历史上首次出现；当天未出现不等于政策取消。
- 单次表态或单个关键词只能作为弱信号。
- 外交新闻中各方说法分别标注，不把单方表述当作已证实事实。
- 每个重要判断标注对应新闻条目序号；证据不足时明确写"无法判断"。
- 不输出投资建议、商机推荐或个人行动建议。
- 频次统计以我提供的30天标题摘要为准，不凭记忆估算。

# 输出格式（Markdown，按此结构）
## 一、今日总览
（3-5句概括当天主线）
## 二、各新闻精炼摘要
（每条1-2句，标注条目序号）
## 三、近30天新增主题
（对照30天标题摘要，指出今天哪些主题是新出现的；没有则明确说明）
## 四、主题频率与报道重点变化
（哪些主题连续出现、篇幅或顺序变化）
## 五、关键词与措辞变化
（新提法、新表述，引用原文）
## 六、政策阶段变化
（方向提出/部署/文件/试点/工程验证/执行，只对有证据的主题判断）
## 七、需进一步核验的事项
## 八、分析限制

# 今日逐字稿（{date}）
{today_text}

# 近30天标题摘要（供对比，非全文）
{history_digest}
"""


def find_root(args_root):
    root = args_root or os.environ.get("NEWS_ANALYSIS_ROOT")
    if not root:
        sys.exit("set --root or NEWS_ANALYSIS_ROOT")
    return root


def list_transcripts(root):
    base = os.path.join(root, "新闻联播原文")
    days = []
    if os.path.isdir(base):
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                if re.match(r"^\d{8}\.md$", fn):
                    days.append(fn[:-3])
    return sorted(set(days), reverse=True)


def load_day(root, day):
    path = os.path.join(root, "新闻联播原文", day[:4], day[4:6], day + ".md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def extract_titles(text):
    return [line.lstrip("# ").strip() for line in text.splitlines()
            if line.startswith("## ")]


def build_history_digest(root, today_day, window=30):
    start = datetime.strptime(today_day, "%Y%m%d").date()
    digest_lines = []
    for offset in range(1, window + 1):
        d = (start - timedelta(days=offset)).strftime("%Y%m%d")
        text = load_day(root, d)
        if text:
            titles = extract_titles(text)
            digest_lines.append(f"{d}：" + "；".join(titles))
    return "\n".join(digest_lines) if digest_lines else "（暂无历史数据，本次为首次分析）"


def call_llm(prompt):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("NEWS_ANALYSIS_ROOT"))
    parser.add_argument("--date", help="分析日期 YYYYMMDD，默认最新一期")
    parser.add_argument("--backfill", type=int, default=0,
                        help="回填最近 N 天中缺报告的日期（默认 0 关闭）")
    args = parser.parse_args()

    if not API_KEY:
        print("[skip] LLM_API_KEY 未配置，跳过 AI 分析（仅抓取模式）。")
        return

    root = find_root(args.root)
    days = list_transcripts(root)
    if not days:
        print("[skip] 数据目录中没有逐字稿，跳过。")
        return

    if args.backfill > 0:
        targets = days[: args.backfill]
        done = 0
        for day in targets:
            report = os.path.join(root, "每日分析报告", day[:4], day[4:6],
                                  f"{day[:4]}-{day[4:6]}-{day[6:]}_分析报告.md")
            if os.path.isfile(report):
                continue
            generate_report(root, day)
            done += 1
        print(f"[done] 回填完成，新生成 {done} 份报告。")
        return

    day = args.date if args.date else days[0]
    today_text = load_day(root, day)
    if not today_text:
        sys.exit(f"未找到 {day} 的逐字稿")

    # 已生成则跳过（幂等）
    report_path = os.path.join(root, "每日分析报告", day[:4], day[4:6],
                               f"{day[:4]}-{day[4:6]}-{day[6:]}_分析报告.md")
    if os.path.isfile(report_path) and not args.date:
        print(f"[skip] {report_path} 已存在，跳过。")
        return
    generate_report(root, day)


def generate_report(root, day):
    today_text = load_day(root, day)
    if not today_text:
        print(f"[warn] 未找到 {day} 的逐字稿，跳过。")
        return
    history = build_history_digest(root, day)
    prompt = PROMPT_TEMPLATE.format(
        date=f"{day[:4]}-{day[4:6]}-{day[6:]}",
        today_text=today_text,
        history_digest=history,
    )
    print(f"[info] 调用模型 {MODEL} @ {BASE_URL}（{day}，prompt {len(prompt)} 字符）")
    report = call_llm(prompt)

    report_dir = os.path.join(root, "每日分析报告", day[:4], day[4:6])
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"{day[:4]}-{day[4:6]}-{day[6:]}_分析报告.md")
    header = (f"# 新闻联播每日分析报告 {day[:4]}-{day[4:6]}-{day[6:]}\n\n"
              f"> 模型：{MODEL} · 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
              f" · 数据源：cn.govopendata.com\n\n")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(header + report + "\n")
    print(f"[done] 已生成 {report_path}")


if __name__ == "__main__":
    main()
