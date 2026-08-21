# 新闻联播分析 Skill

这是一个可移植的 OpenCode Skill 包，用于处理《新闻联播》逐字稿、每日摘要、主题匹配、原文回查和长期趋势分析。

## 安装

在本目录执行：

```bash
bash install.sh
```

默认安装到：

```text
~/.config/opencode/skills/news-broadcast-analysis/
```

也可以将整个 `新闻联播分析/` 文件夹复制到项目的 `.opencode/skills/`、全局的 `~/.config/opencode/skills/` 或兼容的 `~/.claude/skills/` 目录。

安装后重启 OpenCode，使 Skill 被重新加载。

如果需要使用包内抓取脚本，额外安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 数据目录

Skill 不绑定任何个人电脑路径。设置：

```bash
export NEWS_ANALYSIS_ROOT="/path/to/新闻联播分析数据"
```

数据目录至少需要包含：

```text
新闻联播原文/YYYY/MM/
每日分析报告/YYYY/MM/
02-结构化索引/
```

## 能力范围

- 读取当天逐字稿并生成新闻预览卡；
- 通过预览卡的 `description`、`triggers` 和 `metadata` 匹配主题；
- 命中后回读同一条新闻的原文；
- 对比近7天、30天、90天或一年内的相关材料；
- 生成带来源引用的每日和长期趋势分析；
- 控制上下文，不把整年的原文一次性交给模型。

## 自动化说明

定时任务、具体模型API、网页抓取依赖和运行日志属于宿主环境。Skill提供通用流程、数据契约、模板和可选脚本，宿主只需要把当天原文和历史索引传入即可。

本包同时提供可选的逐字稿抓取和月份索引脚本。安装依赖后，可直接将它们接入Cron、LaunchAgent、Hermes或其他自动化工具。

## GitHub Actions 自动化（本仓库已配置）

仓库根目录 `.github/workflows/` 下有两个 workflow：

### 1. fetch-transcripts.yml — 定时抓取逐字稿

- 每天北京时间 **21:40** 和 **09:40** 各运行一次（晚间节目播出后 + 次日早上补漏）；
- 首次运行自动回填最近 **30 天**逐字稿，之后每天增量抓取；
- 抓取结果提交到仓库 `新闻联播分析数据/新闻联播原文/` 目录，并自动重建月份索引；
- 支持 Actions 页面手动触发（`workflow_dispatch`），可指定 `days`（回填天数）或 `date`（指定日期）。

### 2. daily-analysis.yml — AI 每日分析

- 抓取 workflow 成功后自动触发；另有每天北京时间 **22:20** 的定时兜底；
- 调用 OpenAI 兼容接口（`scripts/analyze_daily.py`）生成每日分析报告；
- **未配置 API Key 时优雅跳过**（workflow 保持绿色，不影响抓取）；
- 报告写入 `新闻联播分析数据/每日分析报告/YYYY/MM/`，支持 `--backfill N` 回填最近 N 天。

### 启用 AI 分析（可选）

仓库默认只开抓取。要启用 AI 分析，在仓库 **Settings → Secrets and variables → Actions → New repository secret** 添加：

| Secret | 说明 |
|---|---|
| `LLM_API_KEY` | **必填**，模型服务 API Key |
| `LLM_BASE_URL` | 可选，默认 `https://api.openai.com/v1`。智谱填 `https://open.bigmodel.cn/api/paas/v4`，DeepSeek 填 `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 可选，默认 `gpt-4o-mini`。智谱如 `glm-4.7`，DeepSeek 如 `deepseek-chat` |

添加后无需任何其他操作，下一次抓取完成即自动生成分析报告。
