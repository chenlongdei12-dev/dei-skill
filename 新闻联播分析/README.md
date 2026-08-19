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
