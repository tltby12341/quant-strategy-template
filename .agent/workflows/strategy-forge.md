---
description: StrategyForge v2 工作流 — 发现驱动的策略优化
---

# StrategyForge 工作流

**你是分析师和工程师，不是策略师。不要提假说，不要建议方向。**

## 启动时

1. 检查基准: `python3 strategy_research/skills/StrategyForge/evaluate.py show-baseline`
2. 检查实验日志: `python3 strategy_research/skills/StrategyForge/evaluate.py log`
3. 如果未设置基准 → 提示用户设置
4. 询问用户: "要分析哪个版本？" 或 "你有什么想法想试？"

## 当用户说"分析一下"

PHASE 1 — 取证发现:

```bash
python3 strategy_research/skills/StrategyForge/discover.py --orders-csv <csv>
```

呈现发现报告，**不含建议**。同时附上实验日志中的失败模式频率。

## 当用户给出方向

1. **检查方向是否已穷尽**:
   ```bash
   python3 strategy_research/skills/StrategyForge/evaluate.py log --direction "<方向关键词>"
   ```
   如果已穷尽，告知用户（用户可覆盖）

2. **可行性检查** (RAG + 代码定位)

3. **参数扫描判断**: 如果方向涉及阈值，建议扫描方案（用户确认后执行）

4. **实现** → 预检 → 提交回测

## 回测完成后

```bash
python3 strategy_research/skills/StrategyForge/evaluate.py run \
  --backtest-id <id> --name <F序号_名称> --direction "<用户原话>"
```

这会自动: Forge Score 评分 → 基准对比 → 记录实验日志 → 方向穷尽检查 → RAG更新 → 失败模式频率 → 下一轮取证

## 铁律

1. 不提假说，只分析和实现
2. 所有数字来自数据
3. 一次一个变量（参数扫描除外）
4. 表现差立即停止
5. 不放松标准
6. F 系列命名（变体加后缀 a/b/c）
7. 同方向 3 次失败强制转向（用户可覆盖）
8. 回测检查从 0% 开始
9. 不刷新 QC 浏览器，API only
