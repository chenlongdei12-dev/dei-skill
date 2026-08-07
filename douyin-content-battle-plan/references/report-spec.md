# 报告与机器产物

## AUDIT

输出数据快照、字段覆盖率、成熟度、重复、异常、匹配率和能力轴。

## DIAGNOSE

输出账号基准、滚动/分期趋势、内容DNA、支持样本、反例、证据账本、矛盾账本和限制。按“事实→相关→解释→假设→战略选择”分层。

## FORECAST

输出目标定义、指标窗口、时间切分、朴素基准、Brier、平衡准确率、校准、状态、候选概率和限制。

## PLAN

输出业务目标、主指标、观察窗口、保留/停止/测试、假设、对照、唯一变量、发布表、预测ID、回填字段和复盘日。同时保存机器可读JSON。

## REVIEW

输出执行分、计划与实际、预测误差、假设裁决、公式状态、反例、矛盾变化和下一轮计划。

## CREATE

输出脚本卡、来源、实验变量、对照、预测登记和回填字段。不得因预测概率高而牺牲真实素材或业务目标。

## 默认机器产物

- `data_audit.json`
- `content_dna.csv`
- `script_matches.csv`
- `evidence_ledger.json`
- `contradiction_ledger.json`
- `analysis_result.json`
- 可选 `forecast_result.json`
- 可选 `cross_channel_signals.json`
- `{handle}_douyin_passport.json`

每份人类报告必须链接或说明对应机器产物，不能只保留无法追溯的自然语言结论。
