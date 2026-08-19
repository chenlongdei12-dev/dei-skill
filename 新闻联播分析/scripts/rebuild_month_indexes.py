#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild year/month indexes for transcripts and reports."""

import argparse
import os
import re
from collections import defaultdict


def collect(base_dir, pattern):
    grouped = defaultdict(list)
    if not os.path.isdir(base_dir):
        return grouped
    for directory, _, filenames in os.walk(base_dir):
        for filename in filenames:
            match = pattern.match(filename)
            if match:
                grouped[(match.group(1), match.group(2))].append((filename, os.path.join(directory, filename)))
    return grouped


def build(root, folder, title, pattern, label):
    base_dir = os.path.join(root, folder)
    for (year, month), files in collect(base_dir, pattern).items():
        month_dir = os.path.join(base_dir, year, month)
        os.makedirs(month_dir, exist_ok=True)
        files.sort(reverse=True)
        lines = [f"# {year}年{month}月{title}", "", f"> 共 {len(files)} 份", ""]
        for filename, filepath in files:
            relative = os.path.relpath(filepath, month_dir)
            lines.append(f"- [{label(filename)}]({relative})")
        lines.append("")
        with open(os.path.join(month_dir, "00-月份索引.md"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("NEWS_ANALYSIS_ROOT"))
    args = parser.parse_args()
    if not args.root:
        parser.error("set --root or NEWS_ANALYSIS_ROOT")
    build(args.root, "新闻联播原文", "新闻联播原文索引", re.compile(r"^(\d{4})(\d{2})\d{2}\.md$"), lambda name: name[:8])
    build(args.root, "每日分析报告", "每日分析报告索引", re.compile(r"^(\d{4})-(\d{2})-\d{2}_分析报告\.md$"), lambda name: name[:-3])


if __name__ == "__main__":
    main()
