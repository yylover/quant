# 趋势跟踪策略文档

## 概述

`trend_following.py` 模块包含了 10 种经典的趋势跟踪策略，适用于单边上涨或下跌行情。

## 策略分类

### 1. 均线类策略

#### 双均线交叉 (ma_cross)
- **原理**: 短期均线突破长期均线时买入，跌破时卖出
- **参数**:
  - `fast`: 短期均线周期（默认 10）
  - `slow`: 长期均线周期（默认 30）
- **适用**: 明显趋势行情
- **参数建议**:
  - 快速交易: fast=5, slow=20
  - 中期趋势: fast=10, slow=30
  - 长期趋势: fast=20, slow=60

#### 均线择时 (timing_ma)
- **原理**: 与双均线相同，专用于指数/ETF 择时
- **参数**: fast=20, slow=60
- **适用**: 宽基指数、行业 ETF

#### 均线斜率 (ma_slope)
- **原理**: 通过均线变化率判断趋势强度，结合价格位置确认
- **参数**:
  - `window`: 均线周期（默认 60）
  - `slope_window`: 斜率窗口（默认 5）
  - `enter_slope`: 入场斜率阈值（默认 0）
  - `exit_slope`: 出场斜率阈值（默认 0）
- **优势**: 比单纯交叉更早发现趋势转折

#### EMA 斜率趋势 (ema_slope_trend)
- **原理**: 快速 EMA 与斜率调整 EMA 的交叉，支持二次确认
- **参数**:
  - `buy_ema`: 买入线周期（默认 2）
  - `sell_ema`: 卖出线周期（默认 42）
  - `slope_n`: 斜率窗口（默认 21）
  - `slope_scale`: 斜率放大倍数（默认 20）
  - `confirm`: 是否使用二次确认（默认 True）
- **优势**: 自适应价格动能，更敏感

### 2. 动量类策略

#### ROC 动量 (momentum)
- **原理**: 基于价格变动率 (ROC) 判断趋势强弱
- **参数**:
  - `lookback`: 回看周期（默认 60）
  - `enter_th`: 入场阈值（默认 0）
  - `exit_th`: 出场阈值（默认 0）
- **优势**: 直接衡量动能，无均线滞后

#### 唐奇安通道突破 (donchian)
- **原理**: 突破 N 日新高买入，跌破 M 日新低卖出（海龟交易原型）
- **参数**:
  - `entry_n`: 入场通道周期（默认 20）
  - `exit_n`: 出场通道周期（默认 10）
- **优势**: 捕捉大级别趋势，风险可控

### 3. 指标类策略

#### MACD 趋势 (macd)
- **原理**: MACD 线与信号线交叉
- **参数**:
  - `fast`: 快线周期（默认 12）
  - `slow`: 慢线周期（默认 26）
  - `signal`: 信号线周期（默认 9）
- **优势**: 结合快慢均线，更稳定

#### SuperTrend 超级趋势 (supertrend)
- **原理**: 基于 ATR 的自适应趋势跟踪
- **参数**:
  - `atr_window`: ATR 窗口（默认 10）
  - `multiplier`: ATR 倍数（默认 3.0）
- **优势**: 自适应波动率，可视化效果好

#### 布林带突破 (boll_breakout)
- **原理**: 价格突破上轨买入，跌破中轨卖出
- **参数**:
  - `window`: 布林带窗口（默认 20）
  - `n_std`: 标准差倍数（默认 2.0）
- **注意**: 与均值回归策略不同，这里用于捕捉强势突破

#### 布林带挤压突破 (bb_squeeze)
- **原理**: 波动率压缩后，价格突破上轨买入
- **参数**:
  - `window`: 布林带窗口（默认 20）
  - `n_std`: 标准差倍数（默认 2.0）
  - `squeeze_q`: 挤压分位数（默认 0.2）
- **优势**: 捕捉波动率爆发后的趋势

## 使用方法

### 方法 1: 直接调用策略函数

```python
from sharecode.strategies.trend_following import ma_cross_signals
import pandas as pd

# 准备数据（需包含日期和收盘价列）
df = pd.read_csv('your_data.csv')

# 生成信号
close, entries, exits = ma_cross_signals(df, fast=10, slow=30)

# entries 和 exits 是布尔序列，True 表示该日有买入/卖出信号
print(f"买入信号数: {entries.sum()}")
print(f"卖出信号数: {exits.sum()}")
```

### 方法 2: 使用策略分发器

```python
from sharecode.strategies.trend_following import dispatch_signals
import pandas as pd

# 准备数据
df = pd.read_csv('your_data.csv')

# 通过策略名称调用
close, entries, exits = dispatch_signals(
    df,
    strategy="ma_cross",
    fast=10,
    slow=30
)

# 也可以使用其他策略
close, entries, exits = dispatch_signals(
    df,
    strategy="supertrend",
    atr_window=10,
    multiplier=3.0
)
```

### 方法 3: 通过旧版 common.py 分发器（向后兼容）

```python
from sharecode.strategies.common import dispatch_signals

# 使用方式相同
close, entries, exits = dispatch_signals(
    df,
    strategy="ma_cross",
    fast=10,
    slow=30
)
```

## 回测示例

```python
from sharecode.strategies.trend_following import dispatch_signals
from sharecode.backtest.vectorbt_runner import run_signals_backtest
import pandas as pd

# 加载数据
df = pd.read_csv('your_data.csv')

# 生成信号
close, entries, exits = dispatch_signals(
    df,
    strategy="macd",
    macd_fast=12,
    macd_slow=26,
    macd_signal=9
)

# 回测
pf, stats = run_signals_backtest(
    close,
    entries,
    exits,
    init_cash=100000,
    fees=0.001,
    slippage=0.0005
)

# 查看结果
print(stats)
```

## 支持的策略列表

通过 `dispatch_signals` 支持的所有策略名称：

| 策略名称 | 描述 | 类型 |
|---------|------|------|
| `ma_cross` | 双均线交叉 | 均线类 |
| `timing_ma` | 均线择时 | 均线类 |
| `ma_slope` | 均线斜率 | 均线类 |
| `ema_slope_trend` | EMA 斜率调整趋势 | 均线类 |
| `momentum` | ROC 动量 | 动量类 |
| `donchian` | 唐奇安通道突破 | 动量类 |
| `macd` | MACD 趋势 | 指标类 |
| `supertrend` | 超级趋势 | 指标类 |
| `boll_breakout` | 布林带突破 | 指标类 |
| `bb_squeeze` | 布林带挤压突破 | 指标类 |

## 参数优化建议

详细的参数优化建议请参考模块末尾的注释块。主要原则：

1. **快速交易**: 使用较小的窗口期，信号多但假信号多
2. **中期趋势**: 使用中等窗口期，平衡频率和稳定性
3. **长期趋势**: 使用较大窗口期，信号少但稳健
4. **结合市场特性**: 根据品种的波动率和流动性调整
5. **避免过拟合**: 参数应具有普适性，不要过度优化历史数据

## 常见问题

### Q: 趋势策略 vs 均值回归策略如何选择？
A:
- **趋势策略**: 适用于明显上涨或下跌的行情，如牛市初期、强势品种
- **均值回归策略**: 适用于震荡市，如横盘整理、超涨超跌后回调

### Q: 如何判断当前市场适合哪种策略？
A:
- 观察价格走势：是否有明确的单边方向
- 观察波动率：高波动率更适合趋势策略
- 多策略组合：同时使用趋势和均值回归，动态分配仓位

### Q: 策略参数需要定期调整吗？
A:
- 一般来说，经典策略的参数相对稳定
- 建议每季度或半年评估一次策略表现
- 避免频繁调整参数，可能导致过拟合

## 技术细节

### 数据格式要求

输入 DataFrame 必须包含以下列（中文名称优先）：
- 日期/date: 日期列
- 收盘/close: 收盘价列

部分策略还需要 OHLC 数据：
- 开盘/open: 开盘价
- 最高/high: 最高价
- 最低/low: 最低价

### 返回值

每个策略函数返回三元组：
- `close`: 标准化的收盘价 Series（日期索引）
- `entries`: 买入信号布尔 Series
- `exits`: 卖出信号布尔 Series

## 参考资源

- 海龟交易法则
- Trend Following (Curtis Faith)
- VectorBT 文档: https://vectorbt.dev/
