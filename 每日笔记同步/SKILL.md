---
name: daily-notes-sync
description: |
  每日笔记自动同步（flomo + 得到大脑）。在新电脑上配置定时自动化：
  安装 flomo-web-mcp 与 getnote CLI、引导浏览器授权、注册 macOS LaunchAgent，
  每天早上自动拉取前一天的 flomo 和得到大脑笔记，保存为 Markdown 到指定知识库目录。
  触发方式：/daily-notes-sync、「配置笔记自动化」「同步 flomo 到知识库」「定时拉取得到笔记」
  「在新电脑配置这套自动化」「笔记定时同步」。
  Use when the user wants to set up or port the daily notes automation
  (flomo + 得到大脑/GetNote) on any Mac, or fix/maintain an existing installation.
metadata:
  version: "1.0.0"
  display_name: "每日笔记同步"
  language: "zh-CN"
  platform: "macOS"
---

# 每日笔记同步 Skill

## 一、目的

在新电脑上一键配置「flomo + 得到大脑」每日笔记自动同步：

```text
每天 09:00  拉取昨天 flomo 笔记      → FLOMO-YYYY-MM-DD.md
每天 09:05  拉取昨天得到大脑笔记     → GETNOTE-YYYY-MM-DD.md
```

保存目录由用户指定（如知识库的「日记」目录）。文件含时间、标签、正文、原文链接；当天无记录时写占位行；同名文件已存在则跳过（可随时手动补跑）。

技术链路：

- **flomo**：非官方 Web 接口（需登录态 token），通过社区包 `flomo-web-mcp`（stdio MCP）调用，已封装签名逻辑
- **得到大脑**：官方 CLI `getnote`，浏览器 OAuth 授权
- **定时**：macOS LaunchAgent（本 skill 仅支持 macOS）

## 二、产物清单

| 组件 | 位置 | 说明 |
| --- | --- | --- |
| 本机配置 | `~/.config/daily-notes/config.env` | 含 OUT_DIR、FLOMO_AUTH（敏感）、各二进制绝对路径；权限 600，**绝不提交仓库** |
| flomo 脚本 | `~/.local/bin/flomo-daily.sh` | 拉取昨天 flomo 笔记 |
| getnote 脚本 | `~/.local/bin/getnote-daily.sh` | 拉取昨天得到大脑笔记 |
| LaunchAgent | `~/Library/LaunchAgents/com.dailynotes.{flomo,getnote}.plist` | 定时调起 |
| 输出 | `$OUT_DIR/FLOMO-*.md`、`GETNOTE-*.md` | 每日笔记文件 |
| 日志 | `$OUT_DIR/.flomo-daily.log`、`.getnote-daily.log` | 排障用 |

## 三、新电脑配置流程（Agent 按此执行）

### Step 0：前置检查

- 确认 macOS（`uname -s` 为 Darwin）；LaunchAgent 仅 macOS 可用
- Node >= 20：`node -v`。若未安装，先提示用户安装 Node

### Step 1：收集配置项

用 question 工具向用户确认：

1. **OUT_DIR**（必填）：笔记保存目录
2. 需要哪些平台：仅 flomo / 仅得到大脑 / 两者（默认两者）
3. 定时时间（默认 flomo 09:00、得到大脑 09:05，错开避免并发）
4. 时区（默认 Asia/Shanghai）

### Step 2：flomo 部分（如需要）

1. 安装 MCP：

```bash
npm install -g flomo-web-mcp
```

2. 引导用户抓取 Authorization（发给用户照做）：

> 1. 浏览器打开 `https://v.flomoapp.com` 并登录（注意是 `v.` 开头的网页版）
> 2. `Cmd + Option + I` 打开开发者工具 → **Network（网络）** 标签
> 3. `Cmd + R` 刷新页面（必须先开 Network 再刷新，否则列表为空）
> 4. 点过滤栏 **Fetch/XHR**，点任意发往 `flomoapp.com/api/...` 的请求
> 5. 右侧 **Request Headers** 里找 `authorization: Bearer ...` 一行，右键 Copy value 发给 Agent

常见卡点：看到的是 Response Headers（Request 在下面）；该请求不带 Authorization（换一个 XHR 试试）。

3. 拿到 token 后可直接进入 Step 4（安装后手动跑一次脚本即为冒烟测试；失败看日志，多为 token 无效）。

### Step 3：得到大脑部分（如需要）

1. 安装 CLI：

```bash
npm install -g @getnote/cli@latest
```

已知的坑（依次排查）：

- **安装超时**：检查代理环境变量（`http_proxy`/`https_proxy`/`all_proxy` 可能指向失效的本地代理），`unset` 后重试
- **`permission denied: getnote`**：npm 全局 bin 下的文件缺执行权限，修复：

```bash
chmod +x "$(npm root -g)/@getnote/cli/bin/getnote" "$(npm root -g)/@getnote/cli/bin/getnote.js"
```

2. 浏览器授权（会打印授权 URL 和确认码，等用户在浏览器完成后自动继续）：

```bash
getnote auth login
```

3. 健康检查，确认 `"ready": true`、`issues` 为空；若提示 Skills missing，运行 `getnote setup`：

```bash
getnote doctor -o json
```

4. 验证查询能力（只读，不得创建/修改笔记）：

```bash
getnote notes --limit 1 -o json
```

### Step 4：安装

在本 skill 目录执行（把示例值替换为 Step 1-3 收集到的真实值）：

```bash
./setup.sh \
  --out-dir "/Users/xxx/Documents/01-知识库/xxx/日记" \
  --flomo-auth "Bearer xxx..." \
  --flomo-time 09:00 \
  --getnote-time 09:05 \
  --tz Asia/Shanghai
```

不需要的平台加 `--skip-flomo` 或 `--skip-getnote`。setup.sh 会：写 `config.env`（解析并固化 node / flomo-web-mcp / getnote 的**绝对路径**，保证 launchd 最小 PATH 环境下可运行）→ 安装脚本到 `~/.local/bin/` → 生成并加载 LaunchAgent。

### Step 5：验证

1. 手动跑两个脚本（会生成「昨天」的文件）：

```bash
~/.local/bin/flomo-daily.sh && ~/.local/bin/getnote-daily.sh
```

2. 检查输出文件内容与日志：

```bash
ls "$OUT_DIR"/FLOMO-*.md "$OUT_DIR"/GETNOTE-*.md
cat "$OUT_DIR/.flomo-daily.log" "$OUT_DIR/.getnote-daily.log"
```

正常日志为 `OK: ... (N 条)`；`SKIP` 表示文件已存在；`ERROR` 见下表。

3. 确认定时任务已加载：

```bash
launchctl list | grep com.dailynotes
```

4. 向用户报告：安装位置、定时时间、输出目录、验证结果。

## 四、日常维护

- **手动补跑**：直接执行对应脚本；想重新生成某天文件，先删该文件再跑（脚本按「昨天」取数，改日期需临时改脚本第一处 `date -v-1d`）
- **改时间/改目录**：重跑 `setup.sh`（同名文件已存在会跳过，不影响数据）
- **flomo token 过期**（日志出现 `登录态失效` 或持续 `ERROR: 拉取失败`）：按 Step 2 重新抓 Authorization，然后只需更新配置：

```bash
# 编辑 ~/.config/daily-notes/config.env 中的 FLOMO_AUTH=... 后验证：
~/.local/bin/flomo-daily.sh && cat "$OUT_DIR/.flomo-daily.log" | tail -2
```

- **getnote 授权过期**：`getnote auth login` 重新授权即可，无需重装

## 五、故障排查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| npm 安装超时 | 代理指向失效节点 | `unset http_proxy https_proxy all_proxy` 重试 |
| `permission denied: getnote` | bin 缺执行权限 | 见 Step 3 的 chmod 命令 |
| flomo 日志 `登录态失效` | token 过期 | 重抓 Authorization，更新 config.env |
| flomo 拉取返回 HTML | 请求走了错误的端点/签名缺失 | 确认使用的是本 skill 脚本（内含签名逻辑），不要直接 curl |
| 定时没跑 | LaunchAgent 未加载 | `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dailynotes.*.plist`，看 `/tmp/dailynotes-*.err` |
| launchd 下失败但手动 OK | PATH 问题 | 重跑 setup.sh 重新固化绝对路径 |

## 六、卸载

```bash
./uninstall.sh   # 移除 LaunchAgent、脚本、配置；已生成的笔记文件保留
```

## 七、安全红线

- `config.env` 含 flomo 登录态 token：权限 600，**绝不提交仓库、绝不粘贴到任何外部场合**
- 本仓库脚本与模板只含占位符，不含任何真实凭据
- flomo 读取依赖非官方 Web 接口（`flomo-web-mcp`），接口可能变化；得到大脑为官方 CLI
- 日志与本 skill 输出不含凭据，但笔记内容属用户隐私，勿外传
