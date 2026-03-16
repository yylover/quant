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

