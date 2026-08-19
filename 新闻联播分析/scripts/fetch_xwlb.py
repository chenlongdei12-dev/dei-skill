#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch CCTV News Broadcast transcripts into a portable year/month layout."""

import argparse
import os
import re
import sys
import time
import urllib.request
from datetime import datetime


BASE_URL = "https://cn.govopendata.com/xinwenlianbo"

try:
    from lxml import html as lxml_html
except ImportError:
    sys.exit("Missing dependency: lxml")

try:
    from scrapling.fetchers import Fetcher
except ImportError:
    Fetcher = None


def fetch_html(url):
    if Fetcher is not None:
        page = Fetcher.get(url)
        if page.status == 200 and "Just a moment" not in page.html_content:
            return page.html_content
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (NewsBroadcastAnalysisSkill)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def parse_dates(content):
    document = lxml_html.fromstring(content)
    dates = set()
    for anchor in document.xpath('//a[@href]'):
        href = anchor.get("href") or ""
        match = re.match(r"/xinwenlianbo/(\d{8})/$", href)
        if match:
            dates.add(match.group(1))
    return dates


def parse_day(content):
    document = lxml_html.fromstring(content)
    items = []
    articles = document.xpath('//article[contains(@class,"content-section")]')
    for article in articles:
        titles = article.xpath(".//h2/text() | .//h3/text() | .//h4/text()")
        title = next((text.strip() for text in titles if text.strip()), "")
        parts = []
        for body in article.xpath('.//div[contains(@class,"content-body")]'):
            text = (body.text_content() or "").strip()
            if text:
                parts.append(text)
        content_text = "\n".join(parts)
        if content_text:
            items.append({"title": title, "content": content_text})
    return items


def log(root, message):
    log_dir = os.path.join(root, "06-运行日志")
    os.makedirs(log_dir, exist_ok=True)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    with open(os.path.join(log_dir, "fetch.log"), "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def existing_days(root):
    directory = os.path.join(root, "新闻联播原文")
    result = set()
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if re.match(r"^\d{8}\.md$", filename):
                result.add(filename[:-3])
    return result


def save_day(root, day, items):
    if not items:
        return False
    output_dir = os.path.join(root, "新闻联播原文", day[:4], day[4:6])
    os.makedirs(output_dir, exist_ok=True)
    date_text = f"{day[:4]}-{day[4:6]}-{day[6:]}"
    lines = [f"# 新闻联播 {date_text} 逐字稿", ""]
    for order, item in enumerate(items, 1):
        title = item["title"] or f"条目{order}"
        lines.extend([f"## {order}. {title}", "", item["content"], ""])
    with open(os.path.join(output_dir, f"{day}.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return True


def available_dates(required):
    dates = set()
    for page_number in range(1, 100):
        url = f"{BASE_URL}/" if page_number == 1 else f"{BASE_URL}/?page={page_number}"
        content = fetch_html(url)
        found = parse_dates(content)
        if not found:
            break
        dates.update(found)
        if len(dates) >= required:
            break
        time.sleep(1)
    return sorted(dates, reverse=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("NEWS_ANALYSIS_ROOT"))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--date", help="指定日期，例如 20260819")
    parser.add_argument("--incremental", action="store_true")
    args = parser.parse_args()
    if not args.root:
        parser.error("set --root or NEWS_ANALYSIS_ROOT")

    os.makedirs(args.root, exist_ok=True)
    dates = available_dates(max(args.days, 1))
    if args.date:
        targets = [args.date]
    elif args.incremental:
        targets = dates[:1]
    else:
        targets = dates[: args.days]

    existing = existing_days(args.root)
    todo = [day for day in targets if day not in existing]
    log(args.root, f"可用日期 {len(dates)} 个，待抓取 {len(todo)} 个")
    for day in sorted(todo):
        content = fetch_html(f"{BASE_URL}/{day}/")
        items = parse_day(content)
        if save_day(args.root, day, items):
            log(args.root, f"已保存 {day}.md ({len(items)}条)")
        else:
            log(args.root, f"{day}: 无内容")
        time.sleep(1.5)
    log(args.root, "抓取完成")


if __name__ == "__main__":
    main()
