# Performance Matrix

> 回测数据全表。所有版本的 NP、Sharpe、DD、WR、Orders，标注初始资金和测试区间。

---

## 被动基准（Buy-and-Hold）

> 用于本项目所有策略对照。基准选取应反映策略的资产类、主题或风险敞口。
> 数据源建议：yfinance（auto_adjust=True）或 QC 内置数据。

| Ticker | 说明 | NP | CAR(年化) | MaxDD | Calmar |
|--------|------|-----|-----------|-------|--------|
|        |      |    |           |       |        |

---

## 策略回测表

> 每个大版本起一节。新回测完成后追加行，不删旧行。
> 初始资金、IS/OOS 区间、佣金/滑点模型必须显式标注。

### vX.0 系列 — 一句话主题（IS 窗口：YYYY-MM-DD ~ YYYY-MM-DD）

理论基础：

| Version | 关键参数 | NP | CAR | Sharpe | MaxDD | Calmar | WR | Orders | Top-1 ticker % | vs 基准超额 | Backtest ID |
|---------|---------|-----|-----|--------|-------|--------|-----|--------|----------------|------------|-------------|
|         |         |    |     |        |       |        |    |        |                |            |             |

---

## 报告字段约定

每行至少包含：
- **资金/区间/佣金/滑点** 必须可追溯（写在该节顶部或单列）
- **Top-1 / Top-3 / Top-5 ticker PnL 占比**（单票集中度门槛见 methodology.md §五）
- **vs 主题基准超额**（被动 buy-and-hold 跑赢与否）
- **Backtest ID**（QC 平台溯源）
