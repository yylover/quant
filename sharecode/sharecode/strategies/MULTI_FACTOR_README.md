# 多因子选股策略使用文档

## 目录

- [概述](#概述)
- [功能特性](#功能特性)
- [因子库](#因子库)
- [快速开始](#快速开始)
- [详细使用](#详细使用)
- [回测示例](#回测示例)
- [常见问题](#常见问题)

---

## 概述

多因子选股策略模块提供了一套完整的因子计算、处理、合成和选股框架。该模块基于技术指标和价格数据，支持构建多种选股策略，适用于 ETF 轮动、行业轮动、主题投资等场景。

### 核心概念

1. **因子（Factor）**: 衡量股票某一方面特征的量化指标，如动量、波动率、RSI 等
2. **因子处理**: 去极值、标准化、中性化等预处理步骤
3. **因子合成**: 将多个因子合并为综合得分
4. **选股逻辑**: 根据综合得分选择投资标的

---

## 功能特性

### ✅ 已支持的功能

| 功能 | 说明 |
|-----|------|
| **因子计算** | 9 种内置技术因子 |
| **因子处理** | MAD/Std 去极值、Z-Score/Rank 标准化 |
| **因子合成** | 等权、IC 加权、按得分加权 |
| **选股逻辑** | Top-N 选股、定期调仓 |
| **权重方案** | 等权、反波动率加权、得分加权 |
| **预设策略** | 动量反转、质量价值、趋势强度 |

---

## 因子库

### 1. 动量因子 (Momentum)

| 因子名 | 说明 | 参数 |
|-------|------|------|
| `momentum_20d` | 20 日动量 | lookback=20 |
| `momentum_60d` | 60 日动量 | lookback=60 |

**逻辑**: 衡量过去 N 日的价格涨幅，因子值越大表示动量越强（顺势买入）

**适用**: 趋势跟踪策略

---

### 2. 反转因子 (Reversal)

| 因子名 | 说明 | 参数 |
|-------|------|------|
| `reversal_5d` | 5 日反转 | lookback=5 |

**逻辑**: 短期价格下跌越多，反转可能性越大（抄底买入）

**适用**: 均值回归策略

---

### 3. 波动率因子 (Volatility)

| 因子名 | 说明 | 参数 |
|-------|------|------|
| `volatility_20d` | 20 日波动率 | window=20 |

**逻辑**: 波动率越低，股票越稳定（低波动异常收益）

**适用**: 防御性策略

---

### 4. 均线偏离因子 (MA Distance)

| 因子名 | 说明 | 参数 |
|-------|------|------|
| `ma_distance_60d` | 60 日均线偏离 | ma_window=60 |

**逻辑**: 价格远低于均线时，可能被低估（低吸）

**适用**: 价值投资策略

---

### 5. RSI 因子

| 因子名 | 说明 | 参数 |
|-------|------|------|
| `rsi_14d` | 14 日 RSI | window=14 |

**逻辑**: RSI < 30 时超卖（买入机会）

**适用**: 均值回归策略

---

### 6. MACD 因子

| 因子名 | 说明 | 参数 |
|-------|------|------|
| `macd` | MACD 柱状图 | fast=12, slow=26, signal=9 |

**逻辑**: MACD 柱状图 > 0 表示多头趋势

**适用**: 趋势跟踪策略

---

### 7. 布林带位置因子 (Bollinger Position)

| 因子名 | 说明 | 参数 |
|-------|------|------|
| `bollinger_position` | 布林带相对位置 | window=20, n_std=2.0 |

**逻辑**: 接近下轨时超卖（买入机会）

**适用**: 均值回归策略

---

### 8. 价格趋势因子 (Price Trend)

| 因子名 | 说明 | 参数 |
|-------|------|------|
| `price_trend` | 均线交叉趋势 | short=5, long=20 |

**逻辑**: 短期均线 > 长期均线表示金叉（上涨趋势）

**适用**: 趋势跟踪策略

---

## 快速开始

### 方式 1: 使用回测脚本（推荐）

```bash
# 1. 使用预设策略
python scripts/vectorbt_multi_factor_from_mysql.py \
    --preset trend_strength \
    --top-n 5 \
    --rebalance-days 20

# 2. 使用自定义因子
python scripts/vectorbt_multi_factor_from_mysql.py \
    --factors momentum_60d,volatility_20d,rsi_14d \
    --top-n 5 \
    --rebalance-days 20

# 3. 调整权重方案和风险控制
python scripts/vectorbt_multi_factor_from_mysql.py \
    --preset momentum_reversion \
    --top-n 3 \
    --rebalance-days 20 \
    --weight-scheme inv_vol \
    --max-weight 0.40 \
    --start 2020-01-01
```

### 方式 2: 在代码中使用

```python
import pandas as pd
from sharecode.strategies.multi_factor import create_trend_strength_selector

# 假设 close_df 是收盘价 DataFrame (日期 × 标的)
close_df = pd.read_csv("data/close_prices.csv", index_col=0, parse_dates=True)

# 创建选股器
selector = create_trend_strength_selector(top_n=5, rebalance_days=20)

# 运行选股
weights_df, selections_df, factor_dfs = selector.run(close_df)

print("权重矩阵:")
print(weights_df.tail())

print("\n选股结果:")
print(selections_df.tail())
```

---

## 详细使用

### 1. 创建自定义选股器

```python
from sharecode.strategies.multi_factor import (
    MultiFactorSelector,
    SelectionConfig,
    FactorConfig,
    momentum_factor,
    volatility_factor,
)

# 创建选股器
selector = MultiFactorSelector()

# 添加自定义因子配置
selector.add_factor(FactorConfig(
    name="custom_momentum",
    func=momentum_factor,
    direction="positive",
    params={"lookback": 30},
    weight=1.0,
    desc="30日动量",
))

selector.add_factor(FactorConfig(
    name="custom_volatility",
    func=volatility_factor,
    direction="positive",  # 取负值后，低波动得分为正
    params={"window": 20},
    weight=0.5,  # 权重较低
    desc="20日波动率",
))

# 配置选股参数
selector.config = SelectionConfig(
    top_n=10,
    rebalance_days=20,
    weight_scheme="equal",
    winsorize=True,
    standardize=True,
)

# 运行
weights_df, selections_df, factor_dfs = selector.run(close_df)
```

### 2. 调整因子处理

```python
from sharecode.strategies.multi_factor import MultiFactorSelector, SelectionConfig

selector = MultiFactorSelector()
selector.add_builtin_factors(["momentum_60d", "volatility_20d"])

# 自定义配置
selector.config = SelectionConfig(
    top_n=10,
    rebalance_days=20,
    
    # 因子处理
    winsorize=True,
    winsorize_method="std",  # 使用标准差去极值
    winsorize_n=2.5,         # 2.5 倍标准差
    standardize=True,
    
    # 权重方案
    weight_scheme="score",  # 按得分加权
    max_weight=0.30,        # 单一标的最大权重 30%
)

weights_df, selections_df, _ = selector.run(close_df)
```

### 3. 分析因子表现

```python
from sharecode.strategies.multi_factor import create_trend_strength_selector

selector = create_trend_strength_selector()
selector.compute_factors(close_df)

# 查看各因子统计
for factor_name, factor_df in selector.factor_dfs.items():
    print(f"\n{factor_name}:")
    print(f"  均值: {factor_df.mean().mean():.4f}")
    print(f"  标准差: {factor_df.std().mean():.4f}")

# 计算综合得分
score_df = selector.compute_score()

# 分析得分分布
print(f"\n综合得分:")
print(f"  均值: {score_df.mean().mean():.4f}")
print(f"  标准差: {score_df.std().mean():.4f}")

# 查看最近一次选股
weights_df, selections_df = selector.select()
last_selection = selections_df[selections_df.sum(axis=1) > 0].last('1D')
print(f"\n最新选股:")
print(last_selection)
```

---

## 回测示例

### 示例 1: 动量反转策略

适用于趋势轮动市场，捕捉中期动量同时避免短期追高。

```bash
python scripts/vectorbt_multi_factor_from_mysql.py \
    --preset momentum_reversion \
    --top-n 5 \
    --rebalance-days 20 \
    --weight-scheme inv_vol \
    --start 2020-01-01
```

**因子组成**:
- `momentum_60d` (60日动量): 权重 1.0
- `momentum_20d` (20日动量): 权重 1.0
- `reversal_5d` (5日反转): 权重 1.0

---

### 示例 2: 趋势强度策略

适用于单边上涨市场，选择趋势最强的标的。

```bash
python scripts/vectorbt_multi_factor_from_mysql.py \
    --preset trend_strength \
    --top-n 3 \
    --rebalance-days 20 \
    --weight-scheme score \
    --max-weight 0.50 \
    --start 2020-01-01
```

**因子组成**:
- `momentum_60d` (60日动量)
- `price_trend` (价格趋势)
- `macd` (MACD 趋势)
- `ma_distance_60d` (均线偏离)

---

### 示例 3: 质量价值策略

适用于防御性投资，选择低波动、低位布局的标的。

```bash
python scripts/vectorbt_multi_factor_from_mysql.py \
    --preset quality_value \
    --top-n 5 \
    --rebalance-days 20 \
    --weight-scheme inv_vol \
    --start 2020-01-01
```

**因子组成**:
- `volatility_20d` (20日波动率)
- `ma_distance_60d` (均线偏离)
- `bollinger_position` (布林带位置)

---

### 示例 4: 自定义因子组合

```bash
# 组合动量和反转因子
python scripts/vectorbt_multi_factor_from_mysql.py \
    --factors momentum_60d,momentum_20d,reversal_5d,rsi_14d \
    --top-n 5 \
    --rebalance-days 15 \
    --weight-scheme equal \
    --winsorize-method std \
    --winsorize-n 3.0
```

---

## 常见问题

### Q1: 如何选择合适的因子？

**A**: 根据市场环境选择：
- **趋势市场**: 动量因子 (`momentum_60d`)、趋势因子 (`price_trend`, `macd`)
- **震荡市场**: 反转因子 (`reversal_5d`)、RSI (`rsi_14d`)、布林带 (`bollinger_position`)
- **防御策略**: 波动率因子 (`volatility_20d`)、均线偏离 (`ma_distance_60d`)

### Q2: Top-N 和调仓频率如何设置？

**A**: 
- **Top-N**: 建议根据标的池大小选择，如 37 只 ETF 可选择 5-8 只
- **调仓频率**: 
  - 短期策略：10-15 个交易日
  - 中期策略：20 个交易日
  - 长期策略：40-60 个交易日

### Q3: 权重方案如何选择？

**A**: 
- **等权 (`equal`)**: 简单易用，适合测试
- **反波动率 (`inv_vol`)**: 降低高波动股票权重，更稳健
- **得分加权 (`score`)**: 综合得分越高权重越大，集中度高

### Q4: 如何添加新的因子？

**A**: 参考现有因子函数编写新的因子函数：

```python
def my_custom_factor(close_df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """自定义因子函数"""
    # 计算因子
    factor = close_df.rolling(window).mean()  # 示例
    return factor

# 添加到选股器
selector.add_factor(FactorConfig(
    name="my_factor",
    func=my_custom_factor,
    direction="positive",
    params={"window": 10},
    desc="我的自定义因子",
))
```

### Q5: 如何验证因子有效性？

**A**: 可以通过以下方式：
1. **单因子回测**: 单独使用每个因子回测，观察 IC (信息系数)
2. **因子相关性**: 计算因子间相关性，避免重复因子
3. **分层回测**: 按因子得分分组回测，观察单调性

---

## 进阶扩展

### 1. 接入基本面因子

当前模块仅支持技术因子，如需接入基本面因子（PE、PB、ROE 等），需要：
1. 获取财务数据（如 Tushare、AkShare）
2. 构建因子函数
3. 统一时间戳对齐

### 2. 行业中性化

如果需要行业中性化（避免行业集中度风险），需要：
1. 获取行业分类数据
2. 在因子合成时进行行业调整

### 3. 机器学习因子合成

当前支持线性合成，未来可扩展：
1. 使用 XGBoost、LightGBM 等模型
2. 基于历史因子和收益训练模型
3. 预测未来收益并选股

---

## 参考资料

- **因子投资理论**: "Your Complete Guide to Factor Investing" (Larry Swedroe)
- **量化投资**: "量化投资：策略与技术" (丁鹏)
- **VectorBT 文档**: https://vectorbt.dev/

---

## 更新日志

- **2026-03**: 初始版本，支持 9 种技术因子和 3 种预设策略
