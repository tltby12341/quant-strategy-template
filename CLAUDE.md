# {{STRATEGY_NAME}}

> 用 `quant-strategy-template` 模板初始化后，请把 `{{STRATEGY_NAME}}` 替换为本项目的实际策略名（如 "股票动量策略"、"期权 Iron Condor" 等）。

## 知识中枢: llm-wiki

**所有分析工作从 `llm-wiki/index.md` 入口开始。** 这是项目的核心知识库，包含方法论、历史数据、决策链和已证伪方向。

分析前按 index.md 的场景表格读取必要文件，不需要用户手动唤起。

### llm-wiki 结构
- `index.md` — 入口导航
- `methodology.md` — 分析方法论（怎么分析）
- `performance-matrix.md` — 回测数据全表（数字在这里）
- `decisions-log.md` — 决策链（为什么这样做）
- `dead-ends.md` — 失败方向（不要重复）
- `history.md` — 策略演化史
- `phoenix-protocol.md` — 策略铁律
- `validation-plan.md` — 当前验证任务
- `live-deploy.md` — 实盘适配

## 策略优化 Harness: StrategyForge

本项目使用 **StrategyForge** 工作流进行策略优化。核心原则：

- **Claude 是分析师+工程师+策略顾问**
- 可以基于数据提出假说和建议方向，但必须说明依据
- 最终决策由用户拍板

### 启动方式
- 输入 `/forge` 启动完整工作流
- 或直接说"分析一下"、"开始优化"

### 关键文件
- Skill 文档: `strategy_research/skills/StrategyForge/SKILL.md`
- 工作流: `.agent/workflows/strategy-forge.md`
- 取证工具: `strategy_research/skills/StrategyForge/discover.py`
- 评估工具: `strategy_research/skills/StrategyForge/evaluate.py`
- 基准配置: `strategy_research/skills/StrategyForge/baseline.json`
- 批量扫描: `strategy_research/skills/BacktestMaster/batch_sweep.py`

### 铁律
1. 可以提假说，但必须基于数据，说明逻辑链
2. 所有数字来自数据，不估算
3. 一次只改一个变量
4. 表现差立即停止
5. 不放松验收标准
6. 回测检查从 0% 开始
7. 不刷新 QC 浏览器，API only
