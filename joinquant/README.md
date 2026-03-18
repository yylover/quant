# 聚宽量化策略示例

本目录包含基于 **聚宽 (JoinQuant)** 平台 API 编写的常见量化交易策略，可直接复制到聚宽研究/回测环境运行并测试。

## 策略列表

| 策略 | 文件 | 说明 |
|------|------|------|
| 双均线 | `strategies/trend/ma_crossover.py` | 短期均线上穿长期均线买入，下穿卖出；可调短/长周期与过滤阈值 |
| 动量 | `strategies/trend/momentum.py` | 基于 N 日收益率动量，配合均线过滤，动量为正且价格在均线上方做多 |
| 布林带 | `strategies/bollinger_bands.py` | 价格触及下轨附近买入，触及上轨附近卖出 |
| RSI | `strategies/rsi_strategy.py` | RSI < 超卖线买入，RSI > 超买线卖出 |
| **MACD** | `strategies/macd_strategy.py` | DIF 上穿 DEA 且柱状图非负时买入，死叉或柱状转负时卖出 |
| **突破** | `strategies/trend/breakout.py` | 突破 N 日新高买入，跌破 N 日新低或移动止损卖出 |
| **均值回归** | `strategies/mean_reversion.py` | 价格偏离均线超过 k 倍标准差时反向操作（超卖买、超买卖出） |
| **网格** | `strategies/grid_trading.py` | 在价格区间内分档，越跌仓位越高、越涨仓位越低，赚波动价差 |
| **量价** | `strategies/trend/volume_ma.py` | 放量突破均线时买入，跌破均线时卖出 |
| **完整流程系统** | `strategies/trend/complete_flow_system.py` | 按「最完善交易流程图」10 步：辨趋势→判方向→找位置→看信号→定止损→定仓位→看空间→开仓→平仓→加仓，可运行可回测 |

## 策略能盈利吗？怎么测试？

**没有保证。** 能否盈利取决于市场环境、标的、参数和成本；需要通过回测看历史表现，回测好不代表未来一定盈利。

**推荐测试方式**：在 **聚宽网站** 回测（本策略按聚宽 API 编写）：

1. 登录 [聚宽](https://www.joinquant.com) → 进入 **「回测」**。
2. 新建回测，把对应策略的 **完整代码**（如 `strategies/trend/ma_crossover.py`）复制到编辑器。
3. 设置 **回测区间**（建议至少 2–3 年）、**初始资金**、**频率选「日」**。
4. 点击 **「运行回测」**，看收益曲线、年化收益、最大回撤、夏普比率、胜率等。

更详细的说明（能否盈利、回测步骤、看哪些指标、本地回测）见：[**docs/回测与盈利说明.md**](docs/回测与盈利说明.md)。

## 如何使用（简要）

1. 登录 [聚宽](https://www.joinquant.com)，进入「研究」或「回测」。
2. 新建研究/回测，将对应策略的 **完整代码** 复制到编辑器中。
3. 设置回测区间、初始资金、频率（建议日频）等参数。
4. 运行回测，查看收益曲线、最大回撤、夏普等指标。

## 可调参数（在 `initialize` 中修改）

- **双均线**：`g.security`、`g.short_window` / `g.long_window`、`g.threshold`。
- **动量**：`g.security`、`g.lookback`、`g.ma_window`。
- **布林带**：`g.security`、`g.window`、`g.num_std`。
- **RSI**：`g.security`、`g.period`、`g.oversold` / `g.overbought`。
- **MACD**：`g.security`、`g.fast` / `g.slow` / `g.signal`（默认 12/26/9）。
- **突破**：`g.security`、`g.breakout_days`、`g.exit_days`（0 时用 `g.trailing_stop_pct` 移动止损）。
- **均值回归**：`g.security`、`g.window`、`g.num_std`、`g.revert_ratio`。
- **网格**：`g.security`、`g.use_adaptive_range`、`g.range_days`、`g.grid_num`。
- **量价**：`g.security`、`g.ma_period`、`g.vol_period`、`g.vol_ratio`。
- **完整流程系统**：见 [docs/完整交易系统流程说明.md](docs/完整交易系统流程说明.md)。

## 注意事项

- 默认交易标的为 `510300.XSHG`（沪深300ETF），可按需改为其他股票/ETF。
- 策略使用 `run_daily(..., time='open')` 在每日开盘后执行，避免使用未来数据。
- 手续费通过 `set_order_cost` 设置，可按券商实际费率调整。
- 回测结果依赖区间与标的，需自行评估过拟合与实盘差异。

## 依赖

代码仅在 **聚宽在线/本地回测环境** 下运行，依赖聚宽提供的 `initialize`、`run_daily`、`attribute_history`、`order_target`、`order_target_value`、`set_benchmark`、`set_order_cost`、`OrderCost` 等 API，无需在本地安装额外包（若本地用 JoinQuant SDK 需按官方文档配置）。
