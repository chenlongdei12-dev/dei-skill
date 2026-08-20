# AIHOT 新闻分析 Skill

这个 Skill 用于从 AIHOT 获取 AI 热点，保存原始数据，生成事实优先的日报、周报和月报，并追踪跨事件关联、AI 能力边界和成熟度变化。

## 安装

将整个 `aihot-news-analysis/` 目录复制到以下任一位置：

```text
.opencode/skills/aihot-news-analysis/
~/.config/opencode/skills/aihot-news-analysis/
```

安装后重启 OpenCode，使 Skill 被重新加载。

## 数据目录

默认使用当前项目的 `aihot/` 目录。也可以设置：

```bash
export AIHOT_ANALYSIS_ROOT="/path/to/aihot"
```

Skill 会在数据目录下保存：

- `raw/daily/`：每日精选 API 原文
- `raw/hot-topics/`：当前热点榜原文
- `reports/daily/`：日报
- `reports/weekly/`：周报
- `reports/monthly/`：月报
- `methodology/`：可持续修订的方法论

日报默认只陈述事实、具体变化、当前状态、证据和限制。个人价值、企业需求和落地性作为后台筛选标准，不默认写成新闻结论。
