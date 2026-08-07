#!/usr/bin/env python3
"""Audit Douyin exports and build traceable diagnostic artifacts.

The script is intentionally standard-library only. It produces descriptive evidence,
not causal claims. Semantic labels are drafts for agent review.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree as ET


BASE_ALIASES = {
    "video_id": ["视频ID", "作品ID", "video_id", "item_id"],
    "url": ["视频链接", "作品链接", "url", "share_url"],
    "description": ["视频描述", "作品标题", "标题", "文案", "description", "caption"],
    "published_at": ["发布时间", "发布日期", "published_at", "date", "create_time"],
    "snapshot_at": ["数据日期", "抓取时间", "统计时间", "snapshot_at", "observed_at"],
    "duration_sec": ["视频时长", "作品时长", "duration", "duration_sec"],
    "views": ["播放量", "播放次数", "观看次数", "views", "play_count"],
    "likes": ["点赞量", "点赞数", "likes", "digg_count"],
    "favorites": ["收藏量", "收藏数", "favorites", "collect_count"],
    "comments": ["评论量", "评论数", "comments", "comment_count"],
    "shares": ["分享量", "转发量", "shares", "share_count"],
    "recommendations": ["推荐量", "recommendations"],
    "avg_watch_sec": ["平均播放时长", "平均观看时长", "avg_watch_sec"],
    "completion_rate": ["完播率", "completion_rate", "finish_rate"],
    "retention_2s": ["2秒留存率", "2s留存", "retention_2s"],
    "retention_3s": ["3秒留存率", "3s留存", "retention_3s"],
    "retention_5s": ["5秒完播率", "5秒留存率", "retention_5s"],
    "profile_visits": ["主页访问", "主页访问量", "profile_visits"],
    "new_followers": ["新增粉丝", "涨粉量", "new_followers"],
    "leads": ["私信数", "线索数", "直播间引流人数", "leads"],
    "orders": ["订单数", "成交数", "orders"],
    "revenue": ["成交金额", "GMV", "revenue"],
    "tags": ["视频标签", "作品标签", "tags"],
    "search_terms": ["大家都在搜", "搜索词", "search_terms"],
}

WINDOWS = ("24h", "72h", "7d", "30d")
ENGAGEMENT_METRICS = ("likes", "favorites", "comments", "shares")
FUNNEL_METRICS = (
    "views", *ENGAGEMENT_METRICS, "recommendations", "avg_watch_sec", "completion_rate",
    "retention_2s", "retention_3s", "retention_5s", "profile_visits", "new_followers",
    "leads", "orders", "revenue",
)
ALIASES = dict(BASE_ALIASES)
for metric in ("views", *ENGAGEMENT_METRICS, "new_followers", "leads", "orders", "revenue"):
    for window in WINDOWS:
        zh = {"24h": "24小时", "72h": "72小时", "7d": "7天", "30d": "30天"}[window]
        label = {
            "views": "播放", "likes": "点赞", "favorites": "收藏", "comments": "评论",
            "shares": "分享", "new_followers": "涨粉", "leads": "线索", "orders": "订单",
            "revenue": "成交金额",
        }[metric]
        ALIASES[f"{metric}_{window}"] = [f"{zh}{label}", f"{label}_{window}", f"{metric}_{window}"]

NUMERIC_FIELDS = set(FUNNEL_METRICS) | {f"{m}_{w}" for m in ("views", *ENGAGEMENT_METRICS, "new_followers", "leads", "orders", "revenue") for w in WINDOWS}
PERCENT_FIELDS = {"completion_rate", "retention_2s", "retention_3s", "retention_5s"}

TOPIC_RULES = {
    "亲密关系": ["恋爱", "爱情", "伴侣", "男人", "男生", "关系", "爱人", "真爱", "择偶", "婚姻"],
    "女性现实": ["女性", "女生", "女人", "年龄", "生育", "照护", "家庭责任", "懂事"],
    "主体性": ["主体性", "自洽", "完整", "做自己", "内核", "边界"],
    "情绪心理": ["情绪", "焦虑", "内耗", "恐惧", "安全感", "稳定", "依恋"],
    "认知成长": ["认知", "思维", "逻辑", "成长", "觉醒", "智慧"],
    "哲学修行": ["道家", "佛家", "修行", "因果", "阴阳", "王阳明", "毛选", "臣服"],
    "原生家庭": ["原生家庭", "父母", "母亲", "父亲", "童年"],
    "事业财富": ["事业", "职场", "赚钱", "财富", "老板", "工作", "收入", "职业"],
    "选择代价": ["选择", "代价", "放弃", "承担", "后果", "退出成本"],
    "时代生活": ["算法", "平台", "消费", "标签", "社会评价", "时代"],
}

HOOK_RULES = [
    ("数字清单", re.compile(r"(?:[2-9]\d*|两|二|三|四|五|六|七|八|九|十)[个大步点条件阶段关卡逻辑真相]")),
    ("提问", re.compile(r"(?:为什么|怎么样|怎样|如何|到底|什么才|有没有|吗[？?]?$|[？?])")),
    ("反常识/否定", re.compile(r"(?:不是|并不|千万不要|真正的.+不是|你以为.+其实|反而|恰恰)")),
    ("极端断言", re.compile(r"(?:所有|任何|唯一|本质上|一定|绝对|99%|90%|最大的|顶级)")),
    ("身份点名", re.compile(r"(?:所有女生|女生|女人|事业型女性|30岁|缺爱的人|内核弱)")),
    ("故事/案例", re.compile(r"(?:我妈|我有一个|前几天|曾经|有个朋友|我认识|讲一个)")),
]

ENDPOINT_RULES = [
    ("主体性/向内", re.compile(r"主体性|向内求|做自己|内核|自洽")),
    ("爱自己/自我接纳", re.compile(r"爱自己|接纳自己|认可自己|相信自己")),
    ("认知提升", re.compile(r"提升认知|认知决定|思维决定|觉醒|看见自己")),
    ("关系行动", re.compile(r"离开|沟通|拒绝|设立边界|停止等待|结束关系")),
    ("现实选择与代价", re.compile(r"代价|承担后果|退出成本|资源|收入|职业|选择权")),
    ("开放问题", re.compile(r"你会怎么选|你怎么看|还没有答案|没有标准答案")),
]

REALITY_RULES = [
    ("金钱/资源", re.compile(r"钱|收入|财富|房|资源|经济")),
    ("权力/决定权", re.compile(r"权力|决定权|控制|话语权|谁说了算")),
    ("责任/照护", re.compile(r"责任|照顾|照护|修复|兜底|家务")),
    ("时间/注意力", re.compile(r"时间|注意力|等待|年龄|精力")),
    ("选择/代价", re.compile(r"选择|代价|放弃|承担|后果|成本")),
    ("信息/事实", re.compile(r"事实|证据|信息|承诺|行为一致")),
]

EVIDENCE_RULES = [
    ("数据", re.compile(r"\d+(?:\.\d+)?%|数据显示|统计|样本")),
    ("权威引用", re.compile(r"研究|书里|心理学|经济学|哲学家|孙子兵法|佛家|道家")),
    ("个人经历", re.compile(r"我曾经|我以前|我经历|我妈|我的朋友|我的学员")),
    ("人物案例", re.compile(r"有个|有一个|比如一个|前几天|曾经有")),
    ("行为观察", re.compile(r"他说|她说|做了|发生|长期|每次|后来")),
    ("类比", re.compile(r"就像|好比|仿佛|相当于")),
]


def col_index(ref: str) -> int:
    match = re.match(r"[A-Z]+", ref.upper())
    if not match:
        return 0
    value = 0
    for ch in match.group(0):
        value = value * 26 + ord(ch) - 64
    return value - 1


def read_xlsx(path: Path) -> list[dict[str, Any]]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships", "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iterfind(".//m:t", ns)) for si in root.findall("m:si", ns)]
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        first_sheet = workbook.find(".//m:sheets/m:sheet", ns)
        if first_sheet is None:
            return []
        rid = first_sheet.attrib[f"{{{ns['r']}}}id"]
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target = next((rel.attrib["Target"] for rel in rels.findall("p:Relationship", ns) if rel.attrib.get("Id") == rid), None)
        if not target:
            return []
        target = target.lstrip("/")
        root = ET.fromstring(zf.read(target if target.startswith("xl/") else f"xl/{target}"))
        matrix: list[list[Any]] = []
        for row in root.findall(".//m:sheetData/m:row", ns):
            values: dict[int, Any] = {}
            for cell in row.findall("m:c", ns):
                idx, kind = col_index(cell.attrib.get("r", "A1")), cell.attrib.get("t")
                if kind == "inlineStr":
                    value: Any = "".join(t.text or "" for t in cell.iterfind(".//m:t", ns))
                else:
                    vnode = cell.find("m:v", ns)
                    raw = vnode.text if vnode is not None else ""
                    if kind == "s" and raw != "":
                        value = shared[int(raw)]
                    elif kind in {"str", "e"}:
                        value = raw
                    else:
                        try:
                            value = float(raw)
                            value = int(value) if value.is_integer() else value
                        except (TypeError, ValueError):
                            value = raw
                values[idx] = value
            if values:
                matrix.append([values.get(i, "") for i in range(max(values) + 1)])
        if not matrix:
            return []
        headers = [str(x).strip() for x in matrix[0]]
        return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in matrix[1:]]


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, Any]]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle, delimiter=delimiter))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法识别 CSV 编码: {path}")


def read_table(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".xlsx":
        return read_xlsx(path)
    if path.suffix.lower() == ".csv":
        return read_csv(path)
    if path.suffix.lower() == ".tsv":
        return read_csv(path, "\t")
    raise ValueError("仅支持 .xlsx/.csv/.tsv")


def choose_columns(headers: list[str]) -> dict[str, str]:
    normalized = {str(h).strip().lower(): h for h in headers}
    mapping: dict[str, str] = {}
    for standard, aliases in ALIASES.items():
        for alias in aliases:
            if alias.lower() in normalized:
                mapping[standard] = normalized[alias.lower()]
                break
    return mapping


def number(value: Any, percent: bool = False) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        text = str(value).strip().replace(",", "").replace("，", "")
        is_percent = text.endswith("%")
        try:
            result = float(text.rstrip("%"))
        except ValueError:
            return None
        if is_percent:
            result /= 100
    if percent and 1 < result <= 100:
        result /= 100
    return result


def duration_seconds(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    h, m, s = re.search(r"(\d+(?:\.\d+)?)\s*(?:小时|时)", text), re.search(r"(\d+(?:\.\d+)?)\s*分", text), re.search(r"(\d+(?:\.\d+)?)\s*秒", text)
    if h or m or s:
        return (float(h.group(1)) * 3600 if h else 0) + (float(m.group(1)) * 60 if m else 0) + (float(s.group(1)) if s else 0)
    parts = text.split(":")
    if all(p.replace(".", "", 1).isdigit() for p in parts):
        nums = [float(p) for p in parts]
        return nums[-1] + (nums[-2] * 60 if len(nums) >= 2 else 0) + (nums[-3] * 3600 if len(nums) >= 3 else 0)
    return number(value)


def parse_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d+)?", value.strip())):
        serial = float(value)
        if 20000 < serial < 90000:
            return (datetime(1899, 12, 30) + timedelta(days=serial)).isoformat(sep=" ", timespec="seconds")
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).isoformat(sep=" ", timespec="seconds")
        except ValueError:
            pass
    return text


def dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def infer_snapshot(path: Path, explicit: str | None) -> tuple[str, str]:
    if explicit:
        parsed = parse_date(explicit)
        if not parsed:
            raise ValueError("无法解析 --snapshot-at")
        return parsed, "cli"
    matches = re.findall(r"20\d{6}", path.name)
    if matches:
        parsed = parse_date(matches[-1])
        if parsed:
            return parsed, "filename"
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(sep=" ", timespec="seconds"), "file_mtime"


def normalize_title(text: str) -> str:
    text = re.sub(r"#[^#\s]+", "", text or "")
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE).lower()


def split_caption(text: str) -> tuple[str, list[str]]:
    tags = re.findall(r"#([^#\s]+)", text or "")
    return re.sub(r"#[^#\s]+", "", text or "").strip(), tags


def clean_markdown(path: Path) -> tuple[str, str, dict[str, float]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    title_match = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_match.group(1).strip() if title_match else path.stem
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    body = re.sub(r"^>.*$|^#.*$|\*\*(?:标题|作者)：?\*\*.*$", "", body, flags=re.M)
    body = re.sub(r"#[^#\s]+", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    metrics: dict[str, float] = {}
    for key, label in (("likes", "点赞"), ("favorites", "收藏"), ("comments", "评论"), ("shares", "分享")):
        found = re.search(rf"\*\*([\d,]+)\*\*\s*{label}", text)
        if found:
            metrics[key] = float(found.group(1).replace(",", ""))
    return title, body, metrics


def build_script_index(directory: Path | None) -> list[dict[str, Any]]:
    if not directory or not directory.exists():
        return []
    index = []
    for path in directory.rglob("*.md"):
        if any(token in path.name for token in ("DNA", "解析报告", "README")):
            continue
        title, body, metrics = clean_markdown(path)
        index.append({"path": str(path), "title": title, "norm": normalize_title(title), "body": body, "metrics": metrics})
    return index


def match_script(row: dict[str, Any], scripts: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float, str, bool]:
    metric_matches = []
    for item in scripts:
        comparable = [key for key in ENGAGEMENT_METRICS if row.get(key) is not None and item["metrics"].get(key) is not None]
        if len(comparable) >= 3 and all(float(row[key]) == float(item["metrics"][key]) for key in comparable):
            metric_matches.append(item)
    if len(metric_matches) == 1:
        return metric_matches[0], 1.0, "metrics", False
    caption, _ = split_caption(row.get("description", ""))
    norm = normalize_title(caption.splitlines()[0] if caption else "")
    if not norm:
        return None, 0.0, "none", False
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in scripts:
        other = item["norm"]
        if not other:
            continue
        score = 0.95 if (norm in other or other in norm) and min(len(norm), len(other)) >= 6 else SequenceMatcher(None, norm, other).ratio()
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored or scored[0][0] < 0.68:
        return None, scored[0][0] if scored else 0.0, "none", False
    ambiguous = len(scored) > 1 and scored[0][0] - scored[1][0] < 0.04
    return (None if ambiguous else scored[0][1]), scored[0][0], "title", ambiguous


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    data = sorted(values)
    pos = (len(data) - 1) * q
    low, high = math.floor(pos), math.ceil(pos)
    return data[low] if low == high else data[low] * (high - pos) + data[high] * (pos - low)


def distribution(values: list[float | None]) -> dict[str, float | int | None]:
    data = [float(v) for v in values if v is not None]
    if not data:
        return {"count": 0, "mean": None, "median": None, "p75": None, "p90": None, "max": None, "sum": None}
    return {"count": len(data), "mean": round(statistics.fmean(data), 4), "median": round(statistics.median(data), 4), "p75": round(quantile(data, .75) or 0, 4), "p90": round(quantile(data, .9) or 0, 4), "max": round(max(data), 4), "sum": round(sum(data), 4)}


def percentile_ranks(values: list[float | None]) -> list[float | None]:
    valid = sorted(float(v) for v in values if v is not None)
    if not valid:
        return [None] * len(values)
    if len(valid) == 1:
        return [1.0 if v is not None else None for v in values]
    result = []
    for value in values:
        if value is None:
            result.append(None)
        else:
            below, equal = sum(v < value for v in valid), sum(v == value for v in valid)
            result.append((below + (equal - 1) / 2) / (len(valid) - 1))
    return result


def first_label(text: str, rules: list[tuple[str, re.Pattern[str]]], default: str) -> str:
    return next((label for label, pattern in rules if pattern.search(text or "")), default)


def hook_type(text: str) -> str:
    return first_label((text or "")[:180], HOOK_RULES, "观点陈述")


def topics(text: str) -> list[str]:
    scored = [(label, sum(text.count(word) for word in words)) for label, words in TOPIC_RULES.items()]
    return [label for label, score in sorted(scored, key=lambda x: x[1], reverse=True) if score > 0][:3] or ["其他"]


def structure_type(text: str) -> str:
    sample = (text or "")[:1800]
    if re.search(r"第一|首先", sample) and re.search(r"第二|其次", sample):
        return "步骤/模型"
    if re.search(r"你以为|不是.+而是|其实|反而", sample):
        return "反转重构"
    if re.search(r"比如|举个例子|我有一个|前几天|曾经", sample):
        return "案例升华"
    if re.search(r"什么叫|所谓|本质是|指的是", sample):
        return "定义澄清"
    if re.search(r"如果.+那么|一方面|另一方面|同时", sample):
        return "条件/双重真相"
    return "观点论证"


def evidence_types(text: str) -> list[str]:
    return [label for label, pattern in EVIDENCE_RULES if pattern.search(text or "")] or ["纯断言"]


def duration_bucket(seconds: float | None) -> str:
    if seconds is None:
        return "未知"
    if seconds <= 30:
        return "≤30秒"
    if seconds <= 60:
        return "31–60秒"
    if seconds <= 180:
        return "61–180秒"
    if seconds <= 360:
        return "181–360秒"
    return ">360秒"


def maturity_bucket(days: int | None) -> str:
    if days is None:
        return "未知"
    if days < 0:
        return "未来日期异常"
    if days < 1:
        return "<24h"
    if days < 3:
        return "24–72h"
    if days < 7:
        return "3–7d"
    if days < 30:
        return "7–30d"
    return "≥30d"


def normalize_rows(raw_rows: list[dict[str, Any]], default_snapshot: str) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    if not raw_rows:
        return [], {}, []
    mapping = choose_columns(list(raw_rows[0]))
    parsed: list[dict[str, Any]] = []
    for source_index, source in enumerate(raw_rows, 2):
        row: dict[str, Any] = {"source_row": source_index}
        for standard, original in mapping.items():
            value = source.get(original)
            if standard in NUMERIC_FIELDS:
                row[standard] = number(value, standard in PERCENT_FIELDS)
            elif standard == "duration_sec":
                row[standard] = duration_seconds(value)
            elif standard in {"published_at", "snapshot_at"}:
                row[standard] = parse_date(value)
            else:
                row[standard] = "" if value is None else str(value).strip()
        row["snapshot_at"] = row.get("snapshot_at") or default_snapshot
        if row.get("video_id") or row.get("description"):
            parsed.append(row)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    anonymous: list[dict[str, Any]] = []
    for row in parsed:
        key = str(row.get("video_id") or "").strip()
        (grouped[key] if key else anonymous).append(row)
    duplicates: list[dict[str, Any]] = []
    rows = list(anonymous)
    for video_id, items in grouped.items():
        chosen = max(items, key=lambda r: sum(r.get(k) not in (None, "") for k in (*FUNNEL_METRICS, "description", "published_at")))
        rows.append(chosen)
        if len(items) > 1:
            duplicates.append({"video_id": video_id, "source_rows": [x["source_row"] for x in items], "kept_source_row": chosen["source_row"], "rule": "保留字段最完整记录"})
    return rows, mapping, duplicates


def capability(rows: list[dict[str, Any]], mapped_fields: set[str] | None = None) -> dict[str, Any]:
    tracked = set(FUNNEL_METRICS) | {field for field in (mapped_fields or set()) if field in NUMERIC_FIELDS}
    coverage = {field: round(sum(r.get(field) is not None for r in rows) / len(rows), 4) for field in sorted(tracked)}
    available = sorted(field for field, rate in coverage.items() if rate > 0)
    substantially_available = {field for field, rate in coverage.items() if rate >= .8}
    axes = {
        "exposure": "views" in substantially_available,
        "retention": any(x in substantially_available for x in ("avg_watch_sec", "completion_rate", "retention_2s", "retention_3s", "retention_5s")),
        "engagement": sum(x in substantially_available for x in ENGAGEMENT_METRICS) >= 3,
        "conversion": any(x in substantially_available for x in ("profile_visits", "new_followers", "leads", "orders", "revenue")),
        "fixed_window": any(re.search(r"_(?:24h|72h|7d|30d)$", x) for x in substantially_available),
    }
    if axes["exposure"] and axes["retention"] and axes["conversion"]:
        level = "A"
    elif axes["engagement"]:
        level = "B"
    else:
        level = "C"
    missing = [x for x in ("views", "retention_3s", "avg_watch_sec", "completion_rate", "profile_visits", "new_followers", "leads") if x not in available]
    fixed_window_metrics = sorted(x for x in substantially_available if re.search(r"_(?:24h|72h|7d|30d)$", x))
    return {"level": level, "axes": axes, "coverage": coverage, "available_metrics": available, "fixed_window_metrics": fixed_window_metrics, "coverage_threshold": .8, "missing_priority_metrics": missing}


def audit_rows(rows: list[dict[str, Any]], duplicates: list[dict[str, Any]], snapshot_source: str) -> dict[str, Any]:
    anomalies: list[dict[str, Any]] = []
    for row in rows:
        vid = row.get("video_id") or f"row-{row.get('source_row')}"
        for field in NUMERIC_FIELDS:
            value = row.get(field)
            if value is not None and value < 0:
                anomalies.append({"video_id": vid, "field": field, "value": value, "reason": "negative"})
        for field in PERCENT_FIELDS:
            value = row.get(field)
            if value is not None and not 0 <= value <= 1:
                anomalies.append({"video_id": vid, "field": field, "value": value, "reason": "rate_out_of_range"})
        if row.get("avg_watch_sec") is not None and row.get("duration_sec") and row["avg_watch_sec"] > row["duration_sec"] * 1.5:
            anomalies.append({"video_id": vid, "field": "avg_watch_sec", "value": row["avg_watch_sec"], "reason": "watch_time_exceeds_duration_1_5x"})
        if row.get("observation_age_days") is not None and row["observation_age_days"] < 0:
            anomalies.append({"video_id": vid, "field": "published_at", "value": row.get("published_at"), "reason": "published_after_snapshot"})
    return {"row_count": len(rows), "duplicate_groups": duplicates, "duplicate_group_count": len(duplicates), "anomalies": anomalies, "anomaly_count": len(anomalies), "snapshot_source": snapshot_source, "maturity_counts": dict(Counter(r.get("maturity_bucket") for r in rows))}


def group_performance(rows: list[dict[str, Any]], labels: Callable[[dict[str, Any]], str | list[str]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row_labels = labels(row)
        for label in ([row_labels] if isinstance(row_labels, str) else row_labels):
            groups[label or "未知"].append(row)
    output = []
    for label, items in groups.items():
        output.append({
            "label": label, "count": len(items),
            "mean_likes": distribution([r.get("likes") for r in items])["mean"],
            "median_interaction_index": distribution([r.get("interaction_value_index") for r in items])["median"],
            "median_likes": distribution([r.get("likes") for r in items])["median"],
            "median_favorites": distribution([r.get("favorites") for r in items])["median"],
            "median_comments": distribution([r.get("comments") for r in items])["median"],
            "median_shares": distribution([r.get("shares") for r in items])["median"],
            "median_relative_likes": distribution([r.get("relative_likes_to_peer") for r in items])["median"],
        })
    return sorted(output, key=lambda x: (x["median_interaction_index"] is not None, x["median_interaction_index"] or -1), reverse=True)


def add_peer_baselines(rows: list[dict[str, Any]]) -> None:
    dated = sorted([r for r in rows if dt(r.get("published_at"))], key=lambda r: dt(r["published_at"]) or datetime.min)
    for row in dated:
        when = dt(row.get("published_at"))
        peers = [p for p in dated if dt(p.get("published_at")) and dt(p["published_at"]) < when and p.get("duration_bucket") == row.get("duration_bucket") and (when - dt(p["published_at"])).days <= 180]
        if len(peers) < 5:
            peers = [p for p in dated if dt(p.get("published_at")) and dt(p["published_at"]) < when][-30:]
        for metric in ENGAGEMENT_METRICS:
            values = [p.get(metric) for p in peers if p.get(metric) is not None]
            median = statistics.median(values) if len(values) >= 5 else None
            row[f"peer_median_{metric}"] = round(median, 4) if median is not None else None
            value = row.get(metric)
            row[f"relative_{metric}_to_peer"] = round((value + 1) / (median + 1), 4) if value is not None and median is not None else None
        row["peer_count"] = len(peers)


def evidence_ledger(rows: list[dict[str, Any]], group_tables: dict[str, list[dict[str, Any]]], level: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("published_at"):
            by_year[row["published_at"][:4]].append(row)
    years = sorted(y for y, items in by_year.items() if len(items) >= 5)
    if len(years) >= 2:
        old, new = years[-2], years[-1]
        old_med, new_med = distribution([r.get("likes") for r in by_year[old]])["median"], distribution([r.get("likes") for r in by_year[new]])["median"]
        if old_med is not None and new_med is not None:
            claims.append({"claim_id": "CLM-TREND-001", "statement": f"{new}年点赞中位数相对{old}年{'下降' if new_med < old_med else '上升'}", "claim_type": "descriptive_fact", "metric": "likes", "scope": "year", "sample_size": {old: len(by_year[old]), new: len(by_year[new])}, "data_period": {"start": old, "end": new}, "estimate": {old: old_med, new: new_med, "ratio": round((new_med + 1) / (old_med + 1), 4)}, "supporting_work_ids": [r.get("video_id") for r in by_year[new] if r.get("video_id")], "counterexample_work_ids": [], "confidence": "medium" if level == "B" else "high", "limitations": ["累计互动受作品成熟度与曝光影响；不能据此判断下滑原因", "最新年份可能尚未结束，年度样本量与发布时间结构不一致"], "status": "observed", "next_test": "补齐固定窗口播放与留存"})
    for dimension, table in group_tables.items():
        eligible = [g for g in table if g["count"] >= 10 and g["median_likes"] is not None]
        if eligible:
            leader = max(eligible, key=lambda g: g["median_likes"])
            members = [r for r in rows if leader["label"] in labels_for_dimension(r, dimension) and r.get("likes") is not None]
            members.sort(key=lambda r: r.get("likes") or 0, reverse=True)
            claims.append({"claim_id": f"CLM-GROUP-{dimension.upper()}", "statement": f"{dimension}维度中，{leader['label']}的历史点赞中位数最高", "claim_type": "observed_correlation", "metric": "likes", "scope": dimension, "sample_size": leader["count"], "estimate": leader["median_likes"], "supporting_work_ids": [str(r.get("video_id")) for r in members[:10] if r.get("video_id")], "counterexample_work_ids": [str(r.get("video_id")) for r in members[-5:] if r.get("video_id")], "confidence": "low" if leader["count"] < 30 else "medium", "limitations": ["自然发布样本存在年份、选题、时长和曝光混杂", "规则标签需语义复核"], "status": "observed", "next_test": "在同主题、同时长、同观察窗口下配对复验"})
    return claims


def labels_for_dimension(row: dict[str, Any], dimension: str) -> list[str]:
    mapping = {
        "hook": [row.get("hook_type_draft")], "topic": row.get("topics_draft", []),
        "structure": [row.get("structure_draft")], "duration": [row.get("duration_bucket")],
        "endpoint": [row.get("semantic_endpoint_draft")], "reality_mechanism": [row.get("reality_mechanism_draft")],
    }
    return [str(x) for x in mapping.get(dimension, []) if x]


def contradiction_ledger(group_tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    conflicts = []
    for dimension, table in group_tables.items():
        eligible = [g for g in table if g["count"] >= 5 and g["mean_likes"] is not None and g["median_likes"] is not None]
        if len(eligible) < 2:
            continue
        mean_leader = max(eligible, key=lambda g: g["mean_likes"])
        median_leader = max(eligible, key=lambda g: g["median_likes"])
        if mean_leader["label"] != median_leader["label"]:
            conflicts.append({"conflict_id": f"CNF-{dimension.upper()}-MEAN-MEDIAN", "issue": f"{dimension}分组的均值与中位数领先者不同", "claim_a": {"statement": f"按均值，{mean_leader['label']}领先", "evidence": mean_leader}, "claim_b": {"statement": f"按中位数，{median_leader['label']}领先", "evidence": median_leader}, "resolution": "保留冲突；检查极值贡献、样本规模和同期配对", "status": "unresolved"})
    return conflicts


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="审计抖音数据并生成可追溯内容诊断")
    parser.add_argument("data", type=Path)
    parser.add_argument("--scripts-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("douyin_analysis_output"))
    parser.add_argument("--snapshot-at", help="数据观察时间；缺省从文件名日期或文件mtime推断")
    args = parser.parse_args()

    snapshot_at, snapshot_source = infer_snapshot(args.data, args.snapshot_at)
    raw = read_table(args.data)
    rows, mapping, duplicates = normalize_rows(raw, snapshot_at)
    if not rows:
        raise SystemExit("没有读取到有效作品记录")
    scripts = build_script_index(args.scripts_dir)

    for row in rows:
        published, observed = dt(row.get("published_at")), dt(row.get("snapshot_at"))
        age = (observed - published).days if published and observed else None
        row["observation_age_days"] = age
        row["maturity_bucket"] = maturity_bucket(age)
        caption, hashtags = split_caption(row.get("description", ""))
        row["caption_clean"] = caption
        row["hashtags"] = "、".join(hashtags)
        matched, score, method, ambiguous = match_script(row, scripts)
        body = matched["body"] if matched else ""
        semantic_text = body or caption
        row["script_path"] = matched["path"] if matched else ""
        row["script_match_score"] = round(score, 3)
        row["script_match_method"] = method
        row["script_match_ambiguous"] = ambiguous
        row["hook_type_draft"] = hook_type(semantic_text)
        row["topics_draft"] = topics(f"{caption} {body[:4000]}")
        row["primary_topic_draft"] = row["topics_draft"][0]
        row["structure_draft"] = structure_type(semantic_text)
        row["evidence_types_draft"] = evidence_types(semantic_text)
        ending = semantic_text[-700:]
        row["semantic_endpoint_draft"] = first_label(ending, ENDPOINT_RULES, "未识别/无固定结论")
        row["reality_mechanism_draft"] = first_label(semantic_text, REALITY_RULES, "心理/抽象解释")
        row["duration_bucket"] = duration_bucket(row.get("duration_sec"))
        row["opening_preview"] = semantic_text[:180]

    for metric in ENGAGEMENT_METRICS:
        for row, rank in zip(rows, percentile_ranks([r.get(metric) for r in rows])):
            row[f"_{metric}_pct"] = rank
    for row in rows:
        weights = (("_likes_pct", .25), ("_favorites_pct", .25), ("_comments_pct", .20), ("_shares_pct", .30))
        usable = [(row.get(key), weight) for key, weight in weights if row.get(key) is not None]
        row["interaction_value_index"] = round(sum(value * weight for value, weight in usable) / sum(weight for _, weight in usable) * 100, 2) if usable else None

    add_peer_baselines(rows)
    cap = capability(rows, set(mapping))
    audit = audit_rows(rows, duplicates, snapshot_source)
    available = cap["available_metrics"]
    metrics = {metric: distribution([r.get(metric) for r in rows]) for metric in available}
    dates = sorted(r["published_at"] for r in rows if row_date_valid(r))
    matched_count = sum(bool(r.get("script_path")) for r in rows)
    ambiguous_count = sum(bool(r.get("script_match_ambiguous")) for r in rows)
    group_tables = {
        "hook": group_performance(rows, lambda r: r["hook_type_draft"]),
        "topic": group_performance(rows, lambda r: r["topics_draft"]),
        "structure": group_performance(rows, lambda r: r["structure_draft"]),
        "duration": group_performance(rows, lambda r: r["duration_bucket"]),
        "endpoint": group_performance(rows, lambda r: r["semantic_endpoint_draft"]),
        "reality_mechanism": group_performance(rows, lambda r: r["reality_mechanism_draft"]),
    }
    claims = evidence_ledger(rows, group_tables, cap["level"])
    conflicts = contradiction_ledger(group_tables)
    ranked = sorted(rows, key=lambda r: (r.get("interaction_value_index") is not None, r.get("interaction_value_index") or -1), reverse=True)
    top_fields = ("video_id", "description", "published_at", "observation_age_days", "duration_sec", "views", *ENGAGEMENT_METRICS, "interaction_value_index", "hook_type_draft", "primary_topic_draft", "structure_draft", "semantic_endpoint_draft", "reality_mechanism_draft", "script_path")
    limitations = ["自动标签是语义复核候选，不是最终分类。", "自然发布数据只能支持描述与相关性观察，不能直接证明因果。"]
    if not cap["axes"]["fixed_window"]:
        limitations.append("没有固定观察窗口字段；当前互动为抓取时累计值，不能当作7天或30天表现。")
    if not cap["axes"]["exposure"] or not cap["axes"]["retention"]:
        limitations.append("缺少完整曝光/留存，不能判断分发、开头留存和完播。")
    if matched_count / len(rows) < .8:
        limitations.append("逐字稿可靠匹配率低于80%，未匹配作品不得做深层文案归因。")
    if ambiguous_count:
        limitations.append(f"有{ambiguous_count}条逐字稿匹配存在近似候选冲突，已保留未匹配。")

    result = {
        "schema_version": "2.0", "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": str(args.data.resolve()), "scripts_dir": str(args.scripts_dir.resolve()) if args.scripts_dir else None,
        "snapshot": {"at": snapshot_at, "source": snapshot_source, "metric_window": "fixed_window" if cap["axes"]["fixed_window"] else "cumulative_as_of_snapshot"},
        "sample_size": len(rows), "data_period": {"start": dates[0] if dates else None, "end": dates[-1] if dates else None},
        "capability": cap, "capability_level": cap["level"], "available_metrics": available,
        "missing_priority_metrics": cap["missing_priority_metrics"], "column_mapping": mapping,
        "script_inventory_size": len(scripts), "script_match_count": matched_count,
        "script_match_rate": round(matched_count / len(rows), 4), "script_match_ambiguous_count": ambiguous_count,
        "metric_distributions": metrics, "group_performance_draft": group_tables,
        "top_items": [{key: row.get(key) for key in top_fields} for row in ranked[:15]],
        "evidence_ledger": claims, "contradiction_ledger": conflicts, "data_audit": audit, "limitations": limitations,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "analysis_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "data_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "evidence_ledger.json").write_text(json.dumps({"schema_version": "1.0", "claims": claims}, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "contradiction_ledger.json").write_text(json.dumps({"schema_version": "1.0", "conflicts": conflicts}, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["video_id", "description", "caption_clean", "hashtags", "published_at", "snapshot_at", "observation_age_days", "maturity_bucket", "duration_sec", "duration_bucket", *available, "interaction_value_index", "peer_count", *[f"peer_median_{m}" for m in ENGAGEMENT_METRICS], *[f"relative_{m}_to_peer" for m in ENGAGEMENT_METRICS], "hook_type_draft", "primary_topic_draft", "topics_draft", "structure_draft", "evidence_types_draft", "semantic_endpoint_draft", "reality_mechanism_draft", "script_path", "script_match_score", "script_match_method", "script_match_ambiguous", "opening_preview"]
    csv_rows = []
    for row in rows:
        out = dict(row)
        out["topics_draft"] = "、".join(row["topics_draft"])
        out["evidence_types_draft"] = "、".join(row["evidence_types_draft"])
        csv_rows.append(out)
    write_csv(args.output_dir / "content_dna.csv", csv_rows, fields)
    write_csv(args.output_dir / "script_matches.csv", rows, ["video_id", "description", "script_path", "script_match_score", "script_match_method", "script_match_ambiguous"])

    lines = ["# 抖音诊断摘要 v2", "", f"- 数据能力：**{cap['level']}**（曝光={cap['axes']['exposure']}，留存={cap['axes']['retention']}，互动={cap['axes']['engagement']}，转化={cap['axes']['conversion']}）", f"- 样本：**{len(rows)}** 条；逐字稿可靠匹配：**{matched_count}/{len(rows)}**", f"- 数据观察时间：{snapshot_at}（来源：{snapshot_source}）", f"- 指标窗口：{result['snapshot']['metric_window']}", "", "## 证据结论", ""]
    lines.extend([f"- [{claim['claim_type']}] {claim['statement']}（置信：{claim['confidence']}）" for claim in claims] or ["- 当前没有满足最小样本门槛的自动结论。"])
    lines.extend(["", "## 未解决矛盾", ""])
    lines.extend([f"- {conflict['issue']}：{conflict['resolution']}" for conflict in conflicts] or ["- 当前未检测到均值与中位数排序冲突；仍需人工语义审计。"])
    lines.extend(["", "## 限制", ""] + [f"- {item}" for item in limitations])
    (args.output_dir / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "sample_size": len(rows), "capability_level": cap["level"], "script_match_rate": result["script_match_rate"], "claims": len(claims), "conflicts": len(conflicts)}, ensure_ascii=False))


def row_date_valid(row: dict[str, Any]) -> bool:
    return dt(row.get("published_at")) is not None


if __name__ == "__main__":
    main()
