# AkShare 策略框架 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按设计文档实现一个基于 AkShare CSV 的通用单标策略回测小框架（策略信号 + vectorbt 封装 + CLI 脚本），支持多种常见策略。

**Architecture:** 新增 `sharecode/strategies/common.py` 与 `sharecode/backtest/vectorbt_runner.py` 两个模块，将策略信号与回测逻辑与现有脚本解耦；增加 `scripts/vectorbt_run_strategy_from_csv.py` 作为统一入口，内部通过 argparse 分发到不同策略。

**Tech Stack:** Python, AkShare, pandas, vectorbt, argparse, pytest（如后续添加测试）

---

## Task 1: 创建基础目录与空模块

**Files:**
- Create: `sharecode/strategies/__init__.py`
- Create: `sharecode/strategies/common.py`
- Create: `sharecode/backtest/__init__.py`
- Create: `sharecode/backtest/vectorbt_runner.py`

**Steps:**
1. 确认 `sharecode` 目录存在。
2. 新建上述 4 个文件，先写入最小骨架（函数签名与简单 docstring），不实现具体逻辑。
3. 使用 `python -m compileall sharecode` 或直接运行一个简单 import 脚本，确保模块没有语法错误。

## Task 2: 在 `vectorbt_runner.py` 中封装回测逻辑

**Files:**
- Modify: `sharecode/backtest/vectorbt_runner.py`

**Steps:**
1. 引入 `pandas as pd` 与 `vectorbt as vbt`。
2. 实现函数：

```python
def run_signals_backtest(
    close: pd.Series,
    entries: pd.Series | pd.DataFrame,
    exits: pd.Series | pd.DataFrame,
    *,
    init_cash: float = 100_000.0,
    fees: float = 0.001,
    slippage: float = 0.0005,
    freq: str = "1D",
):
    ...
```

3. 在函数中调用 `vbt.Portfolio.from_signals`，返回 `(pf, stats)`，其中 `stats` 为 `pf.stats()`。
4. 增加一个帮助函数 `print_basic_stats(pf, stats)`，负责打印回测结果中的关键指标。

## Task 3: 在 `strategies/common.py` 中实现双均线策略信号

**Files:**
- Modify: `sharecode/strategies/common.py`

**Steps:**
1. 引入 `pandas as pd` 与 `vectorbt as vbt`。
2. 实现 `ma_cross_signals(df: pd.DataFrame, fast: int, slow: int)`：
   - 将 `df["日期"]` 解析为 datetime 并排序。
   - 提取 `close = df.set_index("日期")["收盘"].astype(float)`。
   - 使用 `vbt.MA.run` 计算 `fast_ma` 与 `slow_ma`。
   - 利用 `fast_ma.ma_crossed_above(slow_ma)` 作为 `entries`，`fast_ma.ma_crossed_below(slow_ma)` 作为 `exits`。
   - 返回 `(close, entries, exits)` 或仅 `(entries, exits)`（计划中 CLI 层负责构造 close，因此这里返回 `(entries, exits)`，并在 docstring 中说明）。

## Task 4: 实现布林带突破与回归策略信号

**Files:**
- Modify: `sharecode/strategies/common.py`

**Steps:**
1. 使用 `vbt.BBANDS.run(close, window=window, std=n_std)` 计算布林带。
2. 实现：
   - `bollinger_breakout_signals(df, window: int, n_std: float)`：
     - entries: 价格从下方突破上轨。
     - exits: 价格跌破中轨或上轨（根据实现选择其一，并在 docstring 中说明）。
   - `bollinger_reversion_signals(df, window: int, n_std: float)`：
     - entries: 价格跌破下轨（可用 shift 判断“刚刚跌破”）。
     - exits: 价格回到中轨或上轨。
3. 确保返回的 `entries` 和 `exits` 索引与 `close` 对齐。

## Task 5: 实现 RSI 均值回归策略信号

**Files:**
- Modify: `sharecode/strategies/common.py`

**Steps:**
1. 使用 `vbt.RSI.run(close, window=window)` 计算 RSI。
2. 实现 `rsi_reversion_signals(df, window: int, low: float, high: float)`：
   - entries: `RSI < low`。
   - exits: `RSI > high`。
3. 确保返回布尔类型 Series，并与 `close` 索引对齐。

## Task 6: 实现均线择时策略信号

**Files:**
- Modify: `sharecode/strategies/common.py`

**Steps:**
1. 基于 Task 3 的 MA 逻辑实现 `timing_ma_signals(df, fast: int, slow: int)`：
   - 与 `ma_cross_signals` 类似，但 docstring 中说明用于“指数/单标择时”。
   - 依然使用 `ma_crossed_above`/`ma_crossed_below` 作为 entries/exits。

## Task 7: 新建统一的 CLI 脚本

**Files:**
- Create: `scripts/vectorbt_run_strategy_from_csv.py`

**Steps:**
1. 使用 `argparse` 解析参数：
   - 必选：`--csv`, `--strategy`（如 `ma_cross`, `boll_breakout`, `boll_reversion`, `rsi_reversion`, `timing_ma`）。
   - 通用：`--init-cash`, `--fees`, `--slippage`。
   - 各策略特有参数（如 `--fast`, `--slow`, `--window`, `--n-std`, `--rsi-low`, `--rsi-high` 等）。
2. 读取 CSV 并构造 `df` 与 `close` 序列，与现有示例保持一致。
3. 根据 `--strategy` 分支调用 `strategies.common` 中对应的信号函数。
4. 使用 `vectorbt_runner.run_signals_backtest` 和 `print_basic_stats` 执行回测并打印结果。

## Task 8: 更新 README 文档

**Files:**
- Modify: `README.md`

**Steps:**
1. 在现有内容基础上增加一小节，说明：
   - 新的策略回测脚本 `scripts/vectorbt_run_strategy_from_csv.py`。
   - 支持的策略列表与示例命令。
2. 保持 README 简洁，指向设计文档获取更多细节。

