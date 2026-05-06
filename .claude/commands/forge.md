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
- PHASE 4 (评估): 对比基准，更新RAG，新一轮取证

详细文档见 `strategy_research/skills/StrategyForge/SKILL.md`