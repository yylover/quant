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

