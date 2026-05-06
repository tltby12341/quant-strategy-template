---
name: BacktestMaster
description: QuantConnect 自动化回测管理工具集，支持本地代码同步、云端编译、回测监控及结果下载。
---

# BacktestMaster 技能说明

`BacktestMaster` 是一个专门用于与 QuantConnect API 交互的功能模块，旨在自动化量化策略的开发与测试流程。它允许开发者在本地编辑代码，并无缝地将其部署到 QuantConnect 云端进行回测。

## 核心功能

1. **连接验证** (`verify_connection.py`): 检查 API 密钥和项目 ID 的配置是否正确，确保能够成功访问 QuantConnect 服务。
2. **代码同步与提交** (`submit_backtest.py`): 将指定的本地 `.py` 文件同步至云端，触发编译与回测。编译失败时打印具体行号和错误信息。
3. **状态监控** (`monitor_backtest.py`): 实时监控回测进度，显示进度条。支持：
   - **早停（Early Stop）**：通过 `--max-dd` 设定回撤阈值，若中途指标超出则自动调用 API 删除该回测，以退出码 `3` 终止，不下载结果。
   - Runtime Error 时打印完整错误栈，以退出码 `1` 终止。
   - 超时保护（默认 1 小时），以退出码 `2` 终止。
4. **结果导出** (`get_results.py`): 回测完成后下载统计指标（JSON）和订单明细（CSV）。
5. **历史回测列表** (`list_backtests.py`): 查看项目的历史回测记录及状态。
6. **自动化工作流** (`run_workflow.py`): 一键执行全流程：同步 → 编译 → 启动回测 → 监控（含早停）→ 下载结果。根据监控退出码决定后续动作。
7. **批量扫描调度** (`batch_sweep.py`): 事件驱动的多节点批量回测调度器。自动扫描目录、构建队列、双节点并行提交、轮询完成状态、自动下载结果。支持嵌套(`variant/year/file.py`)和扁平(`varname_year/file.py`)两种目录结构。

## 目录结构

```
BacktestMaster/
├── qc_api/
│   ├── client.py          # QuantConnect REST API 封装
│   └── config.py          # API 凭据与项目 ID 配置
├── verify_connection.py   # 连接测试
├── submit_backtest.py     # 代码上传 + 编译 + 启动回测
├── monitor_backtest.py    # 实时进度监控
├── get_results.py         # 指标与订单下载
├── list_backtests.py      # 历史回测列表
├── run_workflow.py        # 全流程编排（单个回测）
└── batch_sweep.py         # 批量扫描调度（多回测并行）
```

## 使用方法

### 1. 验证配置
```bash
python strategy_research/skills/BacktestMaster/verify_connection.py
```

### 2. 运行完整回测流水线
```bash
# 基础用法
python strategy_research/skills/BacktestMaster/run_workflow.py \
  --main-file <path_to_strategy.py> \
  --name "MyStrategy_V1"

# 带早停阈值：回撤超过 40% 时自动删除并终止
python strategy_research/skills/BacktestMaster/run_workflow.py \
  --main-file <path_to_strategy.py> \
  --name "MyStrategy_V1" \
  --max-dd 40

# 带 Net Profit 检查点：50% 进度后若利润 < 500% 则停止
python strategy_research/skills/BacktestMaster/run_workflow.py \
  --main-file <path_to_strategy.py> \
  --name "MyStrategy_V1" \
  --max-dd 75 --min-profit 500 --profit-check-after 0.50

# 带 peak-drop 检查：equity 从峰值下跌超过 60% 则停止
python strategy_research/skills/BacktestMaster/run_workflow.py \
  --main-file <path_to_strategy.py> \
  --name "MyStrategy_V1" \
  --max-dd 75 --max-peak-drop 60
```

### 3. 单独提交回测（不监控）
```bash
python strategy_research/skills/BacktestMaster/submit_backtest.py \
  --main-file <path_to_strategy.py> \
  --name "MyStrategy_V1"
```

### 4. 监控指定回测（支持早停）
```bash
# 基础监控
python strategy_research/skills/BacktestMaster/monitor_backtest.py <backtest_id>

# 带早停阈值：回撤超过 40% 时自动删除回测并退出
python strategy_research/skills/BacktestMaster/monitor_backtest.py <backtest_id> \
  --max-dd 40 \
  --check-after-progress 0.07
```

**早停退出码说明**：

| 退出码 | 含义 |
|--------|------|
| `0` | 回测正常完成 |
| `1` | 回测运行时错误 |
| `2` | 监控超时 |
| `3` | **早停**：指标超阈值，已通过 API 删除回测 |

### 5. 获取回测结果
```bash
python strategy_research/skills/BacktestMaster/get_results.py <backtest_id> \
  --output-dir ./results
```

### 6. 查看历史回测列表
```bash
python strategy_research/skills/BacktestMaster/list_backtests.py --limit 10
```

## 回测数据保存说明

`get_results.py` 会在 `--output-dir`（默认为当前目录）下生成以下文件：

| 文件 | 内容 |
|------|------|
| `<backtest_id>_result.json` | 完整回测结果，含所有统计指标、图表数据、runtimeStatistics |
| `<backtest_id>_orders.csv` | 订单明细，含 symbol、方向、数量、成交价、手续费、时间等 |

> **Logs（策略 `self.log()` 输出）**：QC REST API v2 不提供日志下载接口。请到 QuantConnect 网页端 → 对应回测 → "Logs" 标签页手动下载。

## 注意事项

- **入口文件**: 本地策略文件会以 `main.py` 的名称上传到云端。上传前会自动删除云端旧的 `Main.py`，防止旧代码残留。
- **项目 ID**: 默认项目 ID 在 `qc_api/config.py` 中配置，可通过 `--project-id` 参数覆盖。
- **超时**: `monitor_backtest.py` 默认超时为 1 小时，可通过 `--timeout <秒>` 调整。
- **早停阈值**：`--max-dd` 同时接受分数（`0.40`）和百分比（`40`）两种写法，含义相同。
- **早停检查窗口**：默认从 7% 进度开始检查（`--check-after-progress 0.07`），尽早捕捉灾难。
- **利润检查点**：`--min-profit 500` 表示 Net Profit 低于 500% 时停止，`--profit-check-after 0.50` 表示从 50% 进度开始检查（默认 50%）。
- **峰值回撤检查**：`--max-peak-drop 60` 表示 equity 从峰值下跌超过 60% 时停止。适合捕捉"先涨后崩"的情况。
- **QC 无"暂停"接口**：只有删除操作（`backtests/delete`）。早停会彻底删除该回测记录，不可恢复，但 **不影响 Project 本身**。

### 7. 批量扫描调度
```bash
# 嵌套结构 (variant/year/file.py), 如 v4.1/R03/2025/v4.1_R03_2025.py
python strategy_research/skills/BacktestMaster/batch_sweep.py \
  /path/to/sweep_dir --prefix v4.1_

# 扁平结构 (varname_year/file.py), 如 zscore_sweep/Z08_2020/v4.0_Z08_2020.py
python strategy_research/skills/BacktestMaster/batch_sweep.py \
  /path/to/sweep_dir --flat --prefix v4.0_

# 自定义节点数
python strategy_research/skills/BacktestMaster/batch_sweep.py \
  /path/to/sweep_dir --flat --nodes 2 --poll 60
```

**功能**：
- 自动扫描目录发现待测回测，跳过已有有效结果的
- 事件驱动双节点并行提交（可配置节点数）
- 自动接管已在QC运行的回测、下载已完成的回测
- 完成后自动下载结果到策略文件所在目录
