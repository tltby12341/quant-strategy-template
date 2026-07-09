# quant-strategy-template

量化策略项目脚手架：`llm-wiki` 知识中枢 + `StrategyForge` 优化工作流 + QuantConnect API 工具链。

每个策略一个独立项目（独立 history、记忆、wiki），从本模板初始化。

---

## 一行命令初始化新策略项目

```bash
git clone https://github.com/tltby12341/quant-strategy-template.git my-new-strategy
cd my-new-strategy
rm -rf .git && git init
cp .env.example .env # 填入 QuantConnect 凭证
```

---

## 初始化后必做

1. **替换 `CLAUDE.md` 顶部的 `{{STRATEGY_NAME}}`** 为本项目实际策略名
2. **替换 `llm-wiki/index.md` 的 `{{STRATEGY_NAME}}`**
3. **填入 `.env`** 的 QuantConnect 凭证（`QC_USER_ID` / `QC_API_TOKEN` / `QC_PROJECT_ID`）
4. 验证连接：`python3 strategy_research/skills/BacktestMaster/verify_connection.py`
5. 在 Claude Code 里输入 `/forge` 启动工作流

---

## 目录说明

```
.
├── CLAUDE.md                          # Claude Code 项目说明
├── .agent/workflows/strategy-forge.md # /forge 工作流定义
├── .env.example                       # QC 凭证模板
├── llm-wiki/                          # 知识中枢（9 个文件，骨架就绪）
└── strategy_research/skills/
    ├── BacktestMaster/                # QC API 回测提交/监控/取结果
    ├── DeepForensics/                 # 订单 CSV 取证
    ├── StrategyForge/                 # 评分/实验日志/RAG/取证整合
    └── TopPerformerScanner/           # QC 公开榜单扫描
```

---

## 知识中枢 (llm-wiki)

9 个文件，初始为骨架。开发过程中由 Claude 自动维护：

- `index.md` — 入口和场景导航
- `methodology.md` — 分析方法论（已就绪，含 Kill Criteria 模板和风险指标清单）
- `phoenix-protocol.md` — 策略铁律（空，按版本积累后回填）
- `performance-matrix.md` — 回测数据全表（空，每次回测追加）
- `decisions-log.md` — 决策链（空，按 Phase 追加）
- `dead-ends.md` — 失败方向（空，证伪后追加）
- `history.md` — 策略演化史
- `validation-plan.md` — 当前验证任务（已含 preflight checklist 模板）
- `live-deploy.md` — 实盘适配

---

## 铁律（写在 CLAUDE.md，由 Claude 持续遵守）

1. 可以提假说，但必须基于数据，说明逻辑链
2. 所有数字来自数据，不估算
3. 一次只改一个变量
4. 表现差立即停止
5. 不放松验收标准
6. 回测检查从 0% 开始
7. 不刷新 QC 浏览器，API only
