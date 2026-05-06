# {{STRATEGY_NAME}} — 知识中枢

> **这是所有分析工作的入口。** 分析前先读本文件确定需要查阅哪些模块。

---

## 核心结构

```
llm-wiki/
├── index.md              ← 你在这里。入口和导航
├── methodology.md        ← 分析方法论（怎么分析）
├── performance-matrix.md ← 回测数据全表（数字在这里）
├── decisions-log.md      ← 决策链（为什么这样做）
├── dead-ends.md          ← 失败方向（不要重复）
├── history.md            ← 策略演化史
├── phoenix-protocol.md   ← 策略铁律（红线）
├── validation-plan.md    ← 当前验证任务
└── live-deploy.md        ← 实盘适配要点
```

---

## 分析前读什么

| 场景 | 必读 | 按需读 |
|------|------|--------|
| **开始新一轮分析** | methodology.md, decisions-log.md | dead-ends.md |
| **回测结果出来了** | methodology.md §二(Results要点) | performance-matrix.md(对比基准) |
| **Trades 取证分析** | methodology.md §三(Trades方法论) | history.md(历史法医对照) |
| **提出新方向前** | dead-ends.md, decisions-log.md | phoenix-protocol.md(红线检查) |
| **参数 sweep** | validation-plan.md | performance-matrix.md |
| **准备实盘** | live-deploy.md | phoenix-protocol.md |

---

## 各文件定位

### methodology.md — 怎么分析
纯方法论。不含具体数据，只讲流程、维度优先级、陷阱、结论分层。具体案例引用其他 wiki 文件。

### performance-matrix.md — 数字在这里
**唯一的回测数据源。** 所有版本的 NP、Sharpe、DD、WR、Orders，标注初始资金和测试区间。新回测完成后自动追加。

### decisions-log.md — 为什么这样做
按时间顺序的重大决策链。每个 Phase 记录关键转折点和结论。理解"当前在哪里"的最快方式。

### dead-ends.md — 不要重复
已证伪/失败的方向。每个条目区分**方向性证伪**和**实现性缺陷**。实现性失败的方向改进实现后可重试。

### history.md — 从哪里来
策略演化史。理解策略的根本逻辑。

### phoenix-protocol.md — 红线
从历史回测中提炼的铁律(DON'Ts/DOs)。所有结论标注验证条件和环境依赖。

### validation-plan.md — 当前任务
活跃的验证计划。sweep 状态、待填结果表格、后续步骤。

### live-deploy.md — 实盘适配
回测→实盘的已知差异和必要改动。

---

## 维护规则

1. **新回测完成** → 更新 performance-matrix.md + decisions-log.md（如有新结论）+ dead-ends.md（如证伪了方向）
2. **方法论更新** → 只改 methodology.md，不在其他文件重复写方法论
3. **数据和案例** → 只存在 wiki 文件中，methodology.md 通过引用获取
4. **所有数据标注条件** → 初始资金 + 测试区间 + 样本量
