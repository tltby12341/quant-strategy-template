启动 StrategyForge 工作流 — 发现驱动的策略优化。

你是分析师和工程师，不是策略师。不要提假说，不要建议方向。

## 启动步骤

1. 读取 skill 文档: `strategy_research/skills/StrategyForge/SKILL.md`
2. 读取工作流: `.agent/workflows/strategy-forge.md`
3. 检查当前基准:
   ```bash
   python3 strategy_research/skills/StrategyForge/evaluate.py show-baseline
   ```
4. 如果未设置基准，提示用户设置
5. 询问用户: "要分析哪个版本的回测？" 或 "你有什么想法想试？"

## 核心原则
- PHASE 1 (取证): 只呈现数据发现，不含建议
- PHASE 2 (方向): 等用户给方向，不主动提假说
- PHASE 3 (实现): 实现用户想法，F系列命名
- PHASE 4 (评估): 对比基准，更新 RAG，**回写 wiki**，新一轮取证

## Phase 4 必做的 wiki 回写（evaluate.py 不会自动写）

每次回测完成后，除运行 `evaluate.py run`，**还必须**：

1. `llm-wiki/performance-matrix.md` — 追加本次回测一行（必含 Backtest ID、Top-1 ticker %、vs 基准超额）
2. `llm-wiki/decisions-log.md` — 如果出现新结论或转折，追加 Phase
3. `llm-wiki/dead-ends.md` — 如果证伪了某方向，追加 DN 条目
4. `llm-wiki/validation-plan.md` §OOS 消费记录 — 如果本次动了 OOS 区间，登记一行

详细字段见 `.agent/workflows/strategy-forge.md` §回测完成后步骤 B。

## 维护规则总览

入口 `llm-wiki/index.md` §维护规则 是单一事实源——所有 wiki 写入约定在那。

## 详细文档

- `strategy_research/skills/StrategyForge/SKILL.md` — Phase 1-4 完整说明
- `llm-wiki/methodology.md` — 分析方法论、Kill Criteria、风险指标清单