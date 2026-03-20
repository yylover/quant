# 聚宽量化策略示例

本目录包含基于 **聚宽 (JoinQuant)** 平台 API 编写的量化交易策略与文档。策略需 **复制到聚宽「研究 / 回测」** 中运行；本地仓库不自带聚宽回测引擎。

---

## 目录结构（与仓库一致）

```
joinquant/
├── README.md                 # 本文件
├── strategies/
│   ├── __init__.py
│   ├── bollinger_bands.py    # 根目录单文件策略（与 trend / mean_reversion 内部分策略可能主题相近）
│   ├── grid_trading.py
│   ├── macd_strategy.py
│   ├── mean_reversion.py
│   ├── multi_yinzi.py
│   ├── pe_timing.py
│   ├── rsi_strategy.py
│   ├── trend/                # 趋势 / ETF / 完整流程
│   ├── mean_reversion/       # 均值回归族（多文件）
│   ├── multi_factor/         # 多因子选股
│   └── ml_ai/                # 机器学习 / 深度学习示例
└── docs/
    ├── 回测与盈利说明.md
    ├── 完整交易系统流程说明.md
    ├── 交易策略.md
    ├── ETF轮动策略.md
    ├── 下载股票数据.md
    └── superpowers/          # 设计 / 计划类文档
        ├── plans/
        └── specs/
```

---

## `strategies/trend/`（趋势与相关）

| 文件 | 说明 |
|------|------|
| `ma_crossover.py` | 双均线金叉/死叉 |
| `momentum.py` | 动量 + 均线过滤 |
| `breakout.py` | N 日新高突破 / 新低或移动止损出场 |
| `bollinger_breakout.py` | 布林带突破类逻辑 |
| `volume_ma.py` | 放量突破均线 |
| `macd_trend.py` | MACD 趋势（与根目录 `macd_strategy.py` 为不同实现时可二选一） |
| `etf_rotation.py` | ETF 轮动 |
| `etf_trend_only_512800.py` | 证券 ETF（512800）趋势单策略 |
| `etf_trend_grid_512800.py` | 512800 趋势 + 网格 |
| `ema_slope_trendline_512800.py` | 512800 EMA 斜率 / 趋势线 |
| `stock_bond_switch.py` | 股债切换 |
| `complete_flow_system.py` | 「完整交易流程图」10 步：趋势→信号→止损→仓位→空间→开平仓→加仓 |

---

## `strategies/` 根目录（单文件策略）

| 文件 | 说明 |
|------|------|
| `rsi_strategy.py` | RSI 超买超卖 |
| `macd_strategy.py` | MACD 金叉/死叉与柱线 |
| `bollinger_bands.py` | 布林带上下轨交易 |
| `mean_reversion.py` | 均线 + 标准差均值回归 |
| `grid_trading.py` | 网格（区间内分档仓位） |
| `pe_timing.py` | PE 分位数 × 均线趋势双因子仓位（沪深300 ETF） |
| `multi_yinzi.py` | PB+ROE 选股 + RSRS 择时（与 `multi_factor/multi.py` 思路相近的另一实现） |

---

## `strategies/mean_reversion/`（均值回归族）

详细说明见 **[strategies/mean_reversion/README.md](strategies/mean_reversion/README.md)**。

| 文件 |
|------|
| `mean_reversion.py`、`deviation_reversion.py`、`zscore_reversion.py` |
| `bollinger_bands.py`、`bb_width_reversion.py` |
| `rsi_strategy.py`、`kdj_reversion.py`、`cci_reversion.py`、`williams_r_reversion.py` |
| `macd_reversion.py`、`roc_reversion.py`、`bias_reversion.py` |
| `atr_reversion.py`、`psar_reversion.py` |

---

## `strategies/multi_factor/`（多因子选股）

说明与回测参考见 **[strategies/multi_factor/README.md](strategies/multi_factor/README.md)**。

| 文件 | 说明 |
|------|------|
| `multi.py` | PB + ROE 等双因子示例 |
| `three_factor.py` | 三因子扩展 |
| `growth_value.py` | 成长 / 价值复合 |
| `low_vol_quality.py` | 低波 + 质量 |
| `sector_rotation.py` | 行业轮动 |

---

## `strategies/ml_ai/`（机器学习 / 深度学习）

说明见 **[strategies/ml_ai/README.md](strategies/ml_ai/README.md)**。

| 文件 |
|------|
| `xgboost_regression.py`、`lightgbm_classification.py`、`rf_feature_importance.py` |
| `lstm_prediction.py`、`cnn_kline.py`、`pca_factor.py` |

---

## 文档 `docs/`

| 文件 | 说明 |
|------|------|
| [回测与盈利说明.md](docs/回测与盈利说明.md) | 能否盈利、聚宽回测步骤、指标解读 |
| [完整交易系统流程说明.md](docs/完整交易系统流程说明.md) | `complete_flow_system.py` 与流程图对应关系 |
| [交易策略.md](docs/交易策略.md) | 交易策略相关笔记 |
| [ETF轮动策略.md](docs/ETF轮动策略.md) | ETF 轮动说明 |
| [下载股票数据.md](docs/下载股票数据.md) | 数据下载说明 |
| `docs/superpowers/` | 完整流程系统优化等设计 / 计划文档 |

---

## 策略能盈利吗？怎么测试？

**没有保证。** 盈利取决于市场、标的、参数与成本；回测仅代表历史区间表现。

**在聚宽回测：**

1. 打开 [聚宽](https://www.joinquant.com) → **回测**。
2. 新建回测，将目标策略 **整份代码** 复制进编辑器（例如 `strategies/trend/ma_crossover.py`）。
3. 设置回测区间（建议 ≥2–3 年）、初始资金、频率选 **日**。
4. 运行回测，查看收益曲线、最大回撤、夏普、胜率等。

更多说明见 [docs/回测与盈利说明.md](docs/回测与盈利说明.md)。

---

## 可调参数（通用）

多数策略在 `initialize(context)` 中通过 `g.xxx` 配置，常见项包括：

- **标的**：`g.security`（如 `510300.XSHG`）
- **均线 / 周期**：`g.short_window`、`g.long_window`、`g.lookback`、`g.window` 等
- **风险 / 网格**：`g.risk_pct`、`g.grid_num`、`g.range_days` 等（以各文件为准）

**完整流程系统** 的参数与步骤说明见 [docs/完整交易系统流程说明.md](docs/完整交易系统流程说明.md)。

---

## 注意事项

- 根目录与子目录下可能存在 **主题相近的不同实现**（如 MACD、布林带、均值回归），使用前请确认复制的是 intended 文件。
- 默认标的多为 ETF / 指数成分相关代码，可按聚宽规范改为其他股票或 ETF。
- 多因子、ML 类策略依赖聚宽 **股票池、财务、权限** 等，请以各子目录 README 与官方文档为准。
- 手续费通过 `set_order_cost` / `OrderCost` 设置；回测结果需自行评估过拟合与实盘差异。

---

## 依赖

策略在 **聚宽在线或官方提供的本地回测环境** 中运行，依赖聚宽 API（如 `initialize`、`run_daily`、`attribute_history`、`order_target`、`order_target_value`、`set_benchmark`、`set_order_cost`、`OrderCost`、`get_fundamentals` 等）。本地仓库 **不包含** 可独立运行的聚宽回测引擎；若使用官方本地 SDK，按其文档配置数据与运行方式。
