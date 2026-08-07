# 内容决策护照 v2

护照保存可回溯的学习状态，不复制完整逐字稿。

## 核心账本

- `analyses`：每次分析快照，区分任务意图与复盘周期；
- `initial_baseline/current_baseline`：初始与最近基准；
- `evidence_ledger`：事实、相关、解释和战略陈述；
- `contradiction_ledger`：未解决矛盾；
- `formula_library`：支持样本、反例和状态；
- `hypothesis_ledger`：实验假设；
- `forecast_ledger`：发布前预测与发布后实际；
- `forecast_backtests`：时间留出回测；
- `execution_history`：计划执行和假设更新；
- `cross_channel_signals`：不与抖音表现混合的弱信号；
- `data_gaps/data_gap_history`：当前缺口与历史变化。

## 更新规则

1. 分析快照只追加，不覆盖。
2. 证据、矛盾、公式和假设按稳定ID更新，并保存修订历史。
3. 新数据补齐字段后，当前 `data_gaps` 可以移除；历史缺口保留。
4. 预测发布前登记，回填后改为 `resolved` 并计算Brier。
5. 状态只允许规范枚举；没有足够样本时使用 `inconclusive`。
6. v1护照迁移时保留旧 `baseline` 为 `initial_baseline`。
