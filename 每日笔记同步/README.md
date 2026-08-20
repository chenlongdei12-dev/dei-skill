# 每日笔记同步（daily-notes-sync）

在新 Mac 上一键配置「flomo + 得到大脑」每日笔记自动同步：每天早上自动拉取**前一天**的笔记，保存为 Markdown 到指定知识库目录。

## 功能

- 09:00 拉取昨天 flomo 笔记 → `FLOMO-YYYY-MM-DD.md`（走 `flomo-web-mcp`，需网页登录态 token）
- 09:05 拉取昨天得到大脑笔记 → `GETNOTE-YYYY-MM-DD.md`（走官方 `getnote` CLI，浏览器 OAuth）
- 文件含时间、标签、正文、原文链接；无记录写占位；同名文件跳过，可安全手动补跑
- 时间可配置，仅支持 macOS（LaunchAgent）

## 安装为 opencode skill

```bash
cd 每日笔记同步 && ./install.sh
# 或手动：把本目录整个复制/软链到 ~/.config/opencode/skills/daily-notes-sync
```

之后在 opencode 里说「配置笔记自动化」即可由 Agent 按流程引导配置。

## 手动配置（不用 Agent）

```bash
npm install -g flomo-web-mcp @getnote/cli@latest
getnote auth login          # 浏览器授权得到大脑
# 从 v.flomoapp.com DevTools 抓 Authorization: Bearer ...（详见 SKILL.md Step 2）

./setup.sh \
  --out-dir "~/Documents/01-知识库/xxx/日记" \
  --flomo-auth "Bearer 你的token"

# 验证
~/.local/bin/flomo-daily.sh && ~/.local/bin/getnote-daily.sh
launchctl list | grep com.dailynotes
```

## 文件

| 文件 | 说明 |
| --- | --- |
| `SKILL.md` | Agent 执行流程与排障手册 |
| `setup.sh` | 一键安装（写配置/装脚本/注册 LaunchAgent） |
| `uninstall.sh` | 卸载 |
| `flomo-daily.sh` / `getnote-daily.sh` | 每日拉取脚本 |
| `templates/*.plist` | LaunchAgent 模板 |

## 安全

本机凭据只存于 `~/.config/daily-notes/config.env`（权限 600，含 flomo token），本仓库不含任何真实凭据。flomo token 过期后重抓一次并更新该文件即可。
