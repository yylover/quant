# 趋势跟踪策略整理完成

## 改动概述

将项目中的 10 种趋势跟踪策略从 `common.py` 中分离出来，整理到独立的 `trend_following.py` 模块，并添加了详细的中文注释。

## 新增文件

### 1. `sharecode/strategies/trend_following.py` (30KB, 941 行)

包含以下内容：

#### 辅助函数
- `_first_col()`: 从候选列名中查找存在的列
- `_prepare_close()`: 标准化收盘价序列
- `_prepare_ohlc()`: 标准化 OHLC 数据

#### 均线类策略 (4 种)
- `ma_cross_signals()`: 双均线交叉策略
- `timing_ma_signals()`: 均线择时策略（指数/ETF 专用）
- `ma_slope_signals()`: 均线斜率策略
- `ema_slope_trend_signals()`: EMA 斜率调整趋势策略

#### 动量类策略 (2 种)
- `momentum_roc_signals()`: ROC 动量策略
- `donchian_breakout_signals()`: 唐奇安通道突破策略

#### 指标类策略 (4 种)
- `macd_trend_signals()`: MACD 趋势策略
- `supertrend_signals()`: SuperTrend 超级趋势策略
- `bollinger_breakout_signals()`: 布林带突破策略
- `bb_squeeze_breakout_signals()`: 布林带挤压突破策略

#### 分发器
- `dispatch_signals()`: 策略分发器，根据策略名称调用对应函数

#### 参数优化建议
- 文件末尾包含详细的参数优化建议注释块

### 2. `sharecode/strategies/TREND_FOLLOWING_README.md`

完整的使用文档，包含：
- 策略分类说明
- 每种策略的详细介绍
- 参数说明和建议
- 使用方法示例（3 种）
- 回测示例
- 常见问题解答
- 技术细节

## 修改文件

### 1. `sharecode/strategies/__init__.py`

添加了模块导入和导出：

```python
from . import common
from . import trend_following
from . import mean_reversion

__all__ = ["common", "trend_following", "mean_reversion"]
```

### 2. `sharecode/strategies/common.py`

更新了 `dispatch_signals()` 函数的文档字符串：

- 添加了详细的策略分类说明
- 列出所有支持的趋势策略和均值回归策略
- 添加了提示：趋势策略的完整实现请参考 `trend_following` 模块
- 更新了错误消息中的策略列表

## 策略清单

### 趋势跟踪策略 (10 种)

| 策略名称 | 分类 | 核心逻辑 |
|---------|------|---------|
| ma_cross | 均线类 | 双均线交叉（金叉买/死叉卖） |
| timing_ma | 均线类 | 均线择时（指数/ETF 专用） |
| ma_slope | 均线类 | 均线斜率 + 价格位置 |
| ema_slope_trend | 均线类 | EMA 斜率调整 + 二次确认 |
| momentum | 动量类 | ROC 变动率 |
| donchian | 动量类 | 唐奇安通道突破 |
| macd | 指标类 | MACD 线与信号线交叉 |
| supertrend | 指标类 | ATR 自适应趋势 |
| boll_breakout | 指标类 | 布林带上轨突破 |
| bb_squeeze | 指标类 | 布林带挤压后突破 |

### 均值回归策略 (13 种)

位于 `mean_reversion.py` 模块中：
- boll_reversion, rsi_reversion, zscore_reversion
- deviation_reversion, kdj_reversion, williams_r_reversion
- cci_reversion, macd_reversion, bias_reversion
- bb_width_reversion, atr_reversion, roc_reversion
- psar_reversion

## 向后兼容性

- ✅ 旧代码通过 `common.dispatch_signals()` 仍然可以正常使用所有策略
- ✅ 所有策略参数保持不变
- ✅ 所有策略名称保持不变
- ✅ 新代码可以直接导入 `trend_following` 模块使用

## 使用示例

### 旧方式（仍然支持）

```python
from sharecode.strategies.common import dispatch_signals

close, entries, exits = dispatch_signals(
    df,
    strategy="ma_cross",
    fast=10,
    slow=30
)
```

### 新方式（推荐）

```python
from sharecode.strategies.trend_following import dispatch_signals

close, entries, exits = dispatch_signals(
    df,
    strategy="ma_cross",
    fast=10,
    slow=30
)
```

### 直接调用策略函数

```python
from sharecode.strategies.trend_following import ma_cross_signals

close, entries, exits = ma_cross_signals(df, fast=10, slow=30)
```

## 文件结构

```
sharecode/strategies/
├── __init__.py                      # 模块包初始化
├── common.py                        # 通用策略（兼容层）
├── trend_following.py                # 趋势跟踪策略（新建）⭐
├── mean_reversion.py                # 均值回归策略
└── TREND_FOLLOWING_README.md        # 趋势策略文档（新建）⭐
```

## 特性

### 详细注释

每个策略函数都包含：
- ✅ 完整的中文文档字符串
- ✅ 策略逻辑说明
- ✅ 原理解释
- ✅ 适用场景
- ✅ 优势分析
- ✅ 参数说明
- ✅ 参数建议

### 代码质量

- ✅ 通过 Python 语法检查
- ✅ 统一的代码风格
- ✅ 清晰的函数命名
- ✅ 完整的类型注解
- ✅ 合理的异常处理

## 后续建议

1. **参数优化**: 根据实际品种和市场环境，对策略参数进行优化
2. **组合策略**: 考虑将趋势策略和均值回归策略组合使用
3. **风险管理**: 为每种策略添加适当的止损机制
4. **实盘验证**: 在模拟盘或小仓位实盘验证策略有效性
5. **文档完善**: 根据实际使用反馈，持续更新文档

## 总结

✅ 成功创建了独立的趋势跟踪策略模块  
✅ 添加了 941 行详细中文注释和文档  
✅ 保持了向后兼容性  
✅ 提供了完整的 README 文档  
✅ 包含了参数优化建议  

模块已就绪，可以开始使用！
