---
name: douyin-content-battle-plan
description: 审计抖音数据与逐字稿，生成可追溯的内容诊断、矛盾账本、相对表现预测、时间回测、内容实验、脚本卡和周期复盘，并把朋友圈等跨渠道反馈作为独立弱信号回流账号护照。用户要求分析抖音账号/作品数据、判断内容下滑或爆款规律、预测候选内容、制定7天/30天计划、创作数据驱动逐字稿、复盘实验、更新账号护照，或讨论抖音与朋友圈协同内容系统时使用。支持CSV/XLSX、Markdown逐字稿和JSON护照；数据字段或固定观察窗口不足时必须降级，不得虚构播放、留存、涨粉、成交或预测可靠性。
---

# 抖音内容决策与作战系统

把内容运营做成可回溯的决策循环：先审计数据，再分层诊断；发布前登记预测和实验，发布后接受回测；保留反例与矛盾，不用事后叙事覆盖错误。

## 不可违反

1. 原始数据和逐字稿只读；输出写入独立目录。
2. 先声明数据快照、成熟度、能力轴和指标窗口，再下结论。
3. 累计互动不得称为7天表现；互动不得替代播放、留存或商业转化。
4. 将结论分为事实、相关、机制解释、假设、预测和战略选择；语言强度不得超过证据。
5. 矛盾结论进入账本，不得通过总结删除。
6. 自动内容标签只作初标；关键结论必须阅读逐字稿复核。
7. 预测只输出“超过发布前滚动基准的概率”；没有合格时间回测时标记实验性。
8. 跨渠道信号与抖音指标分开保存，只能生成低置信测试假设。
9. 创作回指真实素材；不得伪造个人经历、案例或数据。
10. 区分没有执行、实验不确定和策略失败。

## 选择任务意图与周期

任务意图只选当前需要的能力：

| 意图 | 主要输出 |
|---|---|
| `AUDIT` | 数据质量、快照、成熟度、匹配与能力轴 |
| `DIAGNOSE` | 内容DNA、趋势、证据和矛盾账本 |
| `FORECAST` | 相对概率预测与时间留出回测 |
| `PLAN` | 可裁决的7天/30天实验计划 |
| `REVIEW` | 执行、预测误差、假设与公式状态 |
| `CREATE` | 有来源、实验和回填字段的脚本卡 |

复盘周期另行记录为 `FIRST_TIME / WEEKLY / MONTHLY / QUARTERLY`，不要用周期代替任务意图。

## 第一步：审计输入

1. 向上查找并完整阅读项目 `AGENTS.md`、`SOURCE_OF_TRUTH.md` 和输入边界。
2. 枚举数据、逐字稿、内容单元、历史报告、反馈和账号护照。
3. 读取 [data-schema.md](references/data-schema.md)。确认抓取时间、作品数、字段覆盖、固定窗口、重复、异常和匹配率。
4. 运行：

```bash
python3 scripts/analyze_douyin.py DATA.xlsx \
  --scripts-dir SCRIPTS_DIR \
  --snapshot-at "YYYY-MM-DD HH:MM:SS" \
  --output-dir OUTPUT/analysis
```

只有文件名能可靠表示导出日期时才省略 `--snapshot-at`。检查 `data_audit.json`；异常未解释时不得进入预测。

## 第二步：诊断与语义复核

读取：

- [content-dna.md](references/content-dna.md)：复核主题、矛盾、证据、语义终点和现实机制；
- [evidence-policy.md](references/evidence-policy.md)：登记事实、相关、推断、假设、预测和战略选择；
- [report-spec.md](references/report-spec.md)：按任务意图组织交付。

优先做：

1. 相同观察窗口与邻近时期比较；
2. 中位数、分位数、极值贡献和滚动/同期基准；
3. 同主题不同结构的支持样本与反例；
4. 历史总体与近期表现分开；
5. “入口有效”和“品牌边界受限”等可并存结论分层保存。

不要仅凭规则标签生成战略。人工复核后的标签用 `_reviewed` 保存；不覆盖 `_draft`。

## 第三步：相对预测

用户要求预测、候选排序或计划需要风险排序时，读取 [forecast-policy.md](references/forecast-policy.md)，运行：

```bash
python3 scripts/forecast_content.py OUTPUT/analysis/content_dna.csv \
  --metric shares_7d \
  --candidates candidates.json \
  --output-dir OUTPUT/forecast
```

`candidates.json` 结构：

```json
{
  "candidates": [{
    "candidate_id": "TOPIC-001",
    "primary_topic_draft": "女性现实",
    "hook_type_draft": "反常识/否定",
    "structure_draft": "条件/双重真相",
    "duration_bucket": "181–360秒",
    "semantic_endpoint_draft": "现实选择与代价",
    "reality_mechanism_draft": "选择/代价",
    "evidence_types_draft": "行为观察"
  }]
}
```

只有 `backtest.status=usable` 才能把概率用于候选排序。`experimental` 只能转成实验假设；累计指标预测置信度必须为低。发布前保存预测ID，发布后回填实际结果。

## 第四步：计划、创作与复盘

读取 [experiment-policy.md](references/experiment-policy.md) 和 [creation-workflow.md](references/creation-workflow.md)。

计划必须指定：业务目标、主指标、指标窗口、假设、对照、主要变量、控制维度、最小样本、发布日、复盘日和裁决规则。使用 [plan_template.json](assets/plan_template.json) 保存机器版。

脚本卡必须包含真实来源、语义终点、现实条件、实验ID、预测ID/限制及24h/72h/7d/30d回填。单条爆款只进入复验，不自动升级公式。

复盘时：

1. 先算执行分；不足60%不裁决策略。
2. 回填预测实际，报告Brier和错误预测。
3. 更新假设与公式为 `supported / rejected / inconclusive / fatigued`。
4. 检查矛盾是否新增证据；不够则保持未解决。

## 第五步：跨渠道弱信号

用户提供朋友圈或其他渠道反馈时，读取 [cross-channel-policy.md](references/cross-channel-policy.md)，运行：

```bash
python3 scripts/analyze_channel_signals.py FEEDBACK.xlsx \
  --channel moments \
  --output-dir OUTPUT/cross_channel
```

没有现成表格时，复制 [channel_feedback_template.csv](assets/channel_feedback_template.csv) 填写，不得从聊天印象虚构反馈数。

只有同主题至少3条且至少2条出现私聊、主动讲述或业务咨询，才登记低置信跨渠道假设。之后仍需抖音独立验证。

## 第六步：更新护照

读取 [passport-schema.md](references/passport-schema.md)，运行：

```bash
python3 scripts/update_passport.py \
  --analysis OUTPUT/analysis/analysis_result.json \
  --passport EXISTING.json \
  --plan plan.json \
  --execution execution.json \
  --forecast OUTPUT/forecast/forecast_result.json \
  --cross-channel OUTPUT/cross_channel/cross_channel_signals.json \
  --intent REVIEW \
  --output UPDATED.json
```

只传当前存在且相关的可选参数。v1护照自动迁移到v2；分析历史不覆盖，稳定ID账本保留修订记录。

## 验证与交付

完成后运行：

```bash
python3 scripts/validate_artifacts.py OUTPUT
```

默认交付机器产物、对应人类报告和更新后的护照。报告最后只保留三项行动：继续什么、停止什么、下一轮验证什么；同时列出数据缺口和仍未解决的矛盾。

主动降级：

- 无固定窗口：预测强制低置信；
- 时间回测未过门槛：预测标记实验性；
- 匹配率低于80%：未匹配内容不做文案归因；
- 样本少于10：只称观察；
- 极值贡献过高：同时给中位数和去极值观察；
- 跨渠道信号：不得并入抖音表现分；
- 商业目标存在但无转化字段：补齐回填是最高优先级。
