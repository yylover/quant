# AkShare 策略框架设计文档

**Goal:** 基于 AkShare 日线数据与 vectorbt，在现有示例脚本基础上，抽象出统一的策略信号与回测小框架，并实现多种常见单标策略（趋势、均值回归、择时），为后续多标选股与组合扩展打基础。

**Architecture:** 保留已有的 AkShare 拉取与 CSV 缓存脚本，将策略抽象为“从 DataFrame 生成 entries/exits 信号”的纯函数，由一个统一的 backtest 封装负责调用 vectorbt 并输出核心指标。通过 CLI 脚本选择策略类型与参数，实现从拉取数据到回测的一键流程。

**Tech Stack:** Python, AkShare, pandas, vectorbt, argparse

---

## 模块划分

- `scripts/akshare_fetch_cache.py`
  - 职责：从 AkShare 拉取 A 股日线数据，支持重试与 CSV 缓存。
  - 当前状态：已实现，保留现有接口。

- `sharecode/strategies/common.py`（新增）
  - 职责：提供一组通用策略信号函数，输入为标准化的日线 DataFrame（含 `日期`、`收盘` 等列），输出为 `(entries, exits)` 布尔序列或 DataFrame。
  - 计划实现的策略：
    - `ma_cross_signals`：双均线/多均线趋势跟踪。
    - `bollinger_breakout_signals`：布林带突破趋势策略。
    - `bollinger_reversion_signals`：布林带均值回归策略。
    - `rsi_reversion_signals`：RSI 超买超卖均值回归策略。
    - `timing_ma_signals`：基于指数的均线择时策略（控制仓位 0/1）。

- `sharecode/backtest/vectorbt_runner.py`（新增）
  - 职责：为单标策略封装 vectorbt 回测逻辑：
    - 统一构造 `Portfolio.from_signals`。
    - 提供 `run_signals_backtest(close, entries, exits, config) -> (pf, stats)`。
    - 统一输出核心统计指标。

- `scripts/vectorbt_run_strategy_from_csv.py`（新增）
  - 职责：作为 CLI 入口：
    - 参数：`--csv`、`--strategy`、策略参数（如 `--fast`、`--slow`、`--rsi-low`、`--rsi-high` 等）、资金与手续费配置。
    - 按策略名称分发到对应的 `strategies.*_signals`。
    - 调用 `vectorbt_runner.run_signals_backtest` 并打印结果。
  - 兼容现有示例：
    - 双均线策略可通过 `--strategy ma_cross --fast 10 --slow 30` 运行，实现与旧脚本类似的行为。

- 未来扩展（暂不实现，仅预留思路）
  - 多标选股与组合：
    - 设计 DataFrame 结构为多列 close（列为股票），信号函数返回多列 entries/exits。
    - 使用 vectorbt 的组合支持按截面权重构建组合。

## 数据约定

- CSV 列名沿用 AkShare 返回的中文列：
  - 日期列：`日期`，将被解析为 `datetime` 并排序。
  - 收盘价列：`收盘`，转换为 `float`，并作为 `close` 序列供策略与回测使用。
  - 其他列（`开盘`、`最高`、`最低`、`成交量` 等）在未来策略中可用，目前以 `close` 为主。

- 策略信号函数接口约定：

```python
def strategy_signals(df: pd.DataFrame, **params) -> tuple[pd.Series, pd.Series]:
    """返回 (entries, exits)，索引与 df['日期'] 对齐。"""
```

- 回测封装接口约定：

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
) -> tuple[vbt.Portfolio, pd.Series]:
    ...
```

## 策略设计概要

### 1. 趋势类：双均线策略（`ma_cross_signals`）

- 输入参数：
  - `fast: int`，短周期窗口（如 10）。
  - `slow: int`，长周期窗口（如 30）。
- 信号规则：
  - `fast_ma > slow_ma` 且刚刚上穿：`entries = True`。
  - `fast_ma < slow_ma` 且刚刚下穿：`exits = True`。
- 注意事项：
  - 需确保 `fast < slow`，否则给出友好报错或自动调整。

### 2. 趋势类：布林带突破（`bollinger_breakout_signals`）

- 参数：
  - `window: int`，均线窗口。
  - `n_std: float`，标准差倍数（如 2.0）。
- 信号：
  - 价格从下方突破上轨：买入。
  - 价格跌破中轨或上轨：卖出（可参数化为卖出条件）。

### 3. 均值回归：布林带回归（`bollinger_reversion_signals`）

- 参数同上。
- 信号：
  - 价格跌破下轨：买入。
  - 价格回到中轨或上轨：卖出。

### 4. 均值回归：RSI 超买超卖（`rsi_reversion_signals`）

- 参数：
  - `window: int`，RSI 计算窗口。
  - `low: float`，超卖阈值（如 30）。
  - `high: float`，超买阈值（如 70）。
- 信号：
  - `RSI < low`：买入。
  - `RSI > high`：卖出。

### 5. 指数/单标择时：均线择时（`timing_ma_signals`）

- 适用于指数或单一 ETF。
- 参数：
  - `fast: int`，短均线。
  - `slow: int`，长均线。
- 信号：
  - `fast` 上穿 `slow`：加仓到满仓。
  - `fast` 下穿 `slow`：减仓至空仓。
- 实现上与 `ma_cross_signals` 类似，但语义上用于“择时持有/空仓”。

## 回测统计输出

- 默认打印如下关键指标：
  - `Start Value`
  - `End Value`
  - `Total Return [%]`
  - `Max Drawdown [%]`
  - `Sharpe Ratio`
  - `Calmar Ratio`
  - `Win Rate [%]`
  - `Total Trades`

- CLI 输出格式：
  - 先打印：策略名称、参数配置、样本区间（起止日期与样本数量）。
  - 再按行打印上述统计指标。

## 计划的脚本使用示例

- 双均线趋势策略：

```bash
conda activate aquant
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy ma_cross \
  --fast 10 \
  --slow 30
```

- 布林带回归策略：

```bash
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy boll_reversion \
  --window 20 \
  --n-std 2.0
```

- RSI 均值回归策略：

```bash
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy rsi_reversion \
  --window 14 \
  --rsi-low 30 \
  --rsi-high 70
```

## 后续工作

1. 按本设计创建 `strategies/common.py` 与 `backtest/vectorbt_runner.py`。
2. 新增 `scripts/vectorbt_run_strategy_from_csv.py`，支持多策略与参数。
3. 在 README 中补充示例命令与策略说明。
4. 未来扩展到多标选股与组合回测时，复用当前信号与回测封装思路。

