## A 股量化环境示例（akshare + pandas + backtrader / vectorbt）

### 环境
- Conda 环境名：`aquant`

### 运行方式
```bash
conda activate aquant
python quant/scripts/vectorbt_ma_cross_synth.py
python quant/scripts/backtrader_ma_cross_synth.py
```

### AkShare 数据拉取与缓存（网络不稳定时可复用本地 CSV）
```bash
conda activate aquant
python quant/scripts/akshare_fetch_cache.py --symbol 000001 --start 20240101 --end 20241231 --adjust qfq
python quant/scripts/vectorbt_ma_cross_from_csv.py --csv quant/data/000001_daily_qfq.csv
```

### 通用策略回测（基于 CSV + vectorbt）

在已有 CSV 的基础上，可以使用统一脚本运行多种常见策略：

```bash
# 双均线趋势策略
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy ma_cross \
  --fast 10 \
  --slow 30

# 布林带突破趋势策略
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy boll_breakout \
  --window 20 \
  --n-std 2.0

# 布林带均值回归策略
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy boll_reversion \
  --window 20 \
  --n-std 2.0

# RSI 均值回归策略
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy rsi_reversion \
  --rsi-window 14 \
  --rsi-low 30 \
  --rsi-high 70

# 指数/单标均线择时策略
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy timing_ma \
  --fast 20 \
  --slow 60

# MACD 趋势策略 + 止盈止损
python quant/scripts/vectorbt_run_strategy_from_csv.py \
  --csv quant/data/000001_daily_qfq.csv \
  --strategy macd \
  --macd-fast 12 \
  --macd-slow 26 \
  --macd-signal 9 \
  --sl-pct 0.05 \
  --tp-pct 0.1
```


## 补充特定的股票数据


```sh
python sharecode/scripts/fetch_and_load_all.py \
    --symbols 512800,159915,159949,515000,512000

# 验证
SELECT raw_symbol, name, COUNT(*) AS bars, MIN(ts) AS first_date, MAX(ts) AS last_date   FROM instrument i JOIN bar b ON b.instrument_id = i.id AND b.interval = '1d'   WHERE i.raw_symbol IN ('512800','159915','159949','515000','512000')   GROUP BY i.id, i.raw_symbol, i.name;
```

## 回测
```sh
python scripts/vectorbt_multi_momentum_from_dir.py \
    --lookback 120 --top-n 3 --rebalance-days 20 \
    --weight-scheme inv_vol --max-weight 0.33 \
    --start 2015-01-01
/opt/homebrew/Caskroom/miniforge/base/envs/aquant/lib/python3.11/site-packages/apscheduler/__init__.py:1: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  from pkg_resources import get_distribution, DistributionNotFound
loaded_symbols ['510300', '510500', '510050', '159915', '159949', '512100', '512010', '515000', '512000', '512800', '159208', '515880', '513120', '562500', '515220', '159755', '588460', '588050', '515400', '512480', '159819', '512690', '159869', '512660', '159928', '512170', '513500', '513100', '515790', '515030', '159892', '510880', '515080', '518880', '159934', '560010', '513050']
dates 2015-01-05 → 2026-03-17 rows 2720 symbols 37

multi_momentum_portfolio_ok
Start Value              100000.0
End Value           262285.303602
Total Return [%]       162.285304
Max Drawdown [%]        55.658672
Sharpe Ratio             0.444674
```
## 其他回测

使用 scripts/backtest_from_mysql.py 脚本，通过 --strategy 参数指定策略。目前支持的策略：

  MA 均线交叉
  python scripts/backtest_from_mysql.py \
      --symbol 510300 --exchange SSE --strategy ma_cross \
      --fast 10 --slow 60 \
      --start 2015-01-01

  布林带突破
  python scripts/backtest_from_mysql.py \
      --symbol 510300 --exchange SSE --strategy boll_breakout \
      --window 20 --n-std 2.0 \
      --start 2015-01-01

  布林带均值回归
  python scripts/backtest_from_mysql.py \
      --symbol 510300 --exchange SSE --strategy boll_reversion \
      --window 20 --n-std 2.0 \
      --start 2015-01-01

  RSI 均值回归
  python scripts/backtest_from_mysql.py \
      --symbol 510300 --exchange SSE --strategy rsi_reversion \
      --rsi-window 14 --rsi-low 30 --rsi-high 70 \
      --start 2015-01-01

  MACD 趋势
  python scripts/backtest_from_mysql.py \
      --symbol 510300 --exchange SSE --strategy macd \
      --macd-fast 12 --macd-slow 26 --macd-signal 9 \
      --start 2015-01-01

  加止损/止盈（任何策略都可以加）
  python scripts/backtest_from_mysql.py \
      --symbol 510300 --exchange SSE --strategy ma_cross \
      --fast 10 --slow 60 \
      --sl-pct 0.05 --tp-pct 0.15 \
      --start 2015-01-01

  换标的，例如银行ETF、创业板ETF：
  # 银行ETF (SSE)
  python scripts/backtest_from_mysql.py --symbol 512800 --exchange SSE --strategy ma_cross

  # 创业板ETF (SZSE)
  python scripts/backtest_from_mysql.py --symbol 159915 --exchange SZSE --strategy macd

  所有可用参数：

  ┌─────────────────┬────────┬──────────┐
  │      参数       │ 默认值 │   说明   │
  ├─────────────────┼────────┼──────────┤
  │ --init-cash     │ 100000 │ 初始资金 │
  ├─────────────────┼────────┼──────────┤
  │ --fees          │ 0.001  │ 手续费   │
  ├─────────────────┼────────┼──────────┤
  │ --slippage      │ 0.0005 │ 滑点     │
  ├─────────────────┼────────┼──────────┤
  │ --start / --end │ 无     │ 日期范围 │
  └─────────────────┴────────┴──────────┘
