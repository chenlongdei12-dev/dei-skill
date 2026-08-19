# 数据契约

## 目录契约

```text
NEWS_ANALYSIS_ROOT/
├── 新闻联播原文/YYYY/MM/YYYYMMDD.md
├── 每日分析报告/YYYY/MM/YYYY-MM-DD_分析报告.md
├── 02-结构化索引/
│   ├── 预览卡/YYYY/MM/YYYYMMDD.json
│   ├── 详情证据/YYYY/MM/YYYYMMDD-NN.json
│   ├── 月度统计/YYYY/YYYY-MM.json
│   └── 主题时间线/主题时间线.jsonl
└── 06-运行日志/
```

## 自动化输入

```json
{
  "run_at": "2026-08-20T09:00:00+08:00",
  "program_date": "2026-08-19",
  "source_url": "https://cn.govopendata.com/xinwenlianbo/20260819/",
  "today": {
    "date": "2026-08-19",
    "items": [
      {
        "order": 6,
        "title": "新闻标题",
        "text": "新闻正文"
      }
    ]
  },
  "history": [
    {
      "date": "2026-08-18",
      "items": []
    }
  ]
}
```

`program_date` 是新闻实际播出日期，不是任务运行日期。

## 预览卡JSON

```json
{
  "date": "2026-08-19",
  "items": [
    {
      "news_id": "20260819-06",
      "name": "我国首次实现火箭陆地回收",
      "description": "朱雀三号完成我国首次着陆腿方式陆地可控回收。",
      "triggers": ["商业航天", "重复使用火箭", "火箭回收"],
      "topic_id": "commercial-space-reusable-launch",
      "order": 6,
      "category": "科技创新",
      "policy_stage": "工程验证",
      "match_flags": ["near_30d_new", "stage_change"],
      "source_ref": {
        "file": "新闻联播原文/2026/08/20260819.md",
        "item": 6
      }
    }
  ]
}
```

## 详情证据包

```json
{
  "news_id": "20260819-06",
  "topic_id": "commercial-space-reusable-launch",
  "current": {
    "date": "2026-08-19",
    "quote": "原文引用",
    "source_ref": "新闻联播原文/2026/08/20260819.md#6"
  },
  "historical_matches": [],
  "comparison_window": "30d",
  "statistics": {
    "occurrence_days": 1,
    "first_seen": "2026-08-19",
    "last_seen": "2026-08-19"
  }
}
```
