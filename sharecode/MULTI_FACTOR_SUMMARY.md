# 多因子选股策略模块完成总结

## 📋 项目概览

本次实现完成了一个完整的多因子选股策略模块，包含因子计算、因子处理、因子合成和选股功能，适用于 ETF 轮动、行业轮动、主题投资等量化策略场景。

---

## ✅ 完成清单

### 1. 核心模块 (`sharecode/strategies/multi_factor.py`)

#### 核心数据结构
- ✅ `FactorConfig`: 因子配置类
- ✅ `SelectionConfig`: 选股配置类

#### 因子计算函数 (9 种)
| 因子名 | 类型 | 说明 |
|-------|------|------|
| `momentum_factor` | 动量 | N日变动率/累计收益率 |
| `reversal_factor` | 反转 | 短期反转效应 |
| `volatility_factor` | 波动率 | 价格波动程度 |
| `ma_distance_factor` | 均线偏离 | 价格相对均线位置 |
| `rsi_factor` | 技术指标 | 相对强弱指标 |
| `macd_factor` | 技术指标 | MACD 柱状图 |
| `bollinger_position_factor` | 技术指标 | 布林带位置 |
| `price_trend_factor` | 趋势 | 短长期均线关系 |
| `high_low_ratio_factor` | 区间 | 价格相对区间位置 |

#### 内置因子库
- ✅ 9 种预设因子配置 (`BUILTIN_FACTORS`)
- ✅ 包含参数、方向、权重、说明

#### 因子处理函数
- ✅ `winsorize()`: MAD/Std 去极值
- ✅ `standardize()`: Z-Score/Rank 标准化
- ✅ `combine_factors()`: 等权/权重合并

#### 选股逻辑
- ✅ `select_by_score()`: Top-N 选股
- ✅ 支持定期调仓
- ✅ 支持多种权重方案（等权/反波动率/得分加权）

#### 选股器类 (`MultiFactorSelector`)
- ✅ 因子管理（添加/计算/合成）
- ✅ 一键运行 (`run()`)
- ✅ 支持灵活配置

#### 便捷函数（预设策略）
- ✅ `create_momentum_reversion_selector()`: 动量反转策略
- ✅ `create_quality_value_selector()`: 质量价值策略
- ✅ `create_trend_strength_selector()`: 趋势强度策略

---

### 2. 回测脚本 (`scripts/vectorbt_multi_factor_from_mysql.py`)

#### 功能
- ✅ 从 MySQL 加载多标的收盘价数据
- ✅ 支持 3 种预设策略和自定义因子
- ✅ 支持反波动率加权
- ✅ 输出完整的回测统计结果
- ✅ 支持参数调优（Top-N、调仓频率、权重方案等）

#### 命令行参数
| 参数 | 说明 |
|------|------|
| `--preset` | 预设策略 (momentum_reversion / quality_value / trend_strength) |
| `--factors` | 自定义因子列表 |
| `--top-n` | 选择前 N 只标的 |
| `--rebalance-days` | 调仓频率 |
| `--weight-scheme` | 权重方案 (equal / inv_vol / score) |
| `--max-weight` | 单一标的最大权重 |
| `--no-winsorize` | 不去极值 |
| `--no-standardize` | 不标准化 |

---

### 3. 使用文档 (`sharecode/strategies/MULTI_FACTOR_README.md`)

#### 内容
- ✅ 概述和核心概念
- ✅ 因子库详细介绍（9 种因子）
- ✅ 快速开始指南
- ✅ 详细使用方法（代码示例）
- ✅ 4 种回测示例
- ✅ 常见问题解答
- ✅ 进阶扩展建议

---

### 4. 模块更新

#### `sharecode/strategies/__init__.py`
- ✅ 导出 `multi_factor` 模块
- ✅ 更新模块列表

---

## 📊 文件清单

| 文件路径 | 行数 | 说明 |
|---------|------|------|
| `sharecode/strategies/multi_factor.py` | 900+ | 核心模块 |
| `scripts/vectorbt_multi_factor_from_mysql.py` | 400+ | 回测脚本 |
| `sharecode/strategies/MULTI_FACTOR_README.md` | 400+ | 使用文档 |
| `MULTI_FACTOR_SUMMARY.md` | 本文件 | 项目总结 |

---

## 🎯 核心特性

### 1. 灵活的因子系统
- 9 种内置技术因子
- 支持自定义因子扩展
- 灵活的因子方向和权重配置

### 2. 完善的因子处理
- 去极值（MAD/Std）
- 标准化（Z-Score/Rank）
- 因子合成（等权/权重/得分）

### 3. 多种选股策略
- Top-N 选股
- 定期调仓
- 多种权重方案

### 4. 便捷的使用方式
- 3 种预设策略
- 命令行回测脚本
- 代码内直接调用

---

## 🚀 快速开始

### 方式 1: 使用回测脚本

```bash
# 趋势强度策略
python scripts/vectorbt_multi_factor_from_mysql.py \
    --preset trend_strength \
    --top-n 5 \
    --rebalance-days 20

# 自定义因子
python scripts/vectorbt_multi_factor_from_mysql.py \
    --factors momentum_60d,volatility_20d,rsi_14d \
    --top-n 5 \
    --rebalance-days 20
```

### 方式 2: 在代码中使用

```python
from sharecode.strategies.multi_factor import create_trend_strength_selector
import pandas as pd

# 加载收盘价数据
close_df = pd.read_csv("data/close_prices.csv", index_col=0, parse_dates=True)

# 创建选股器并运行
selector = create_trend_strength_selector(top_n=5, rebalance_days=20)
weights_df, selections_df, factor_dfs = selector.run(close_df)
```

---

## 📈 预设策略详解

### 1. 动量反转策略 (`momentum_reversion`)
**因子组成**: momentum_60d, momentum_20d, reversal_5d
**适用场景**: 趋势轮动市场
**特点**: 捕捉中期动量，避免短期追高

### 2. 质量价值策略 (`quality_value`)
**因子组成**: volatility_20d, ma_distance_60d, bollinger_position
**适用场景**: 防御性投资
**特点**: 选择低波动、低位布局标的

### 3. 趋势强度策略 (`trend_strength`)
**因子组成**: momentum_60d, price_trend, macd, ma_distance_60d
**适用场景**: 单边上涨市场
**特点**: 选择趋势最强的标的

---

## 🔄 工作流程

```
1. 加载数据
   ↓
2. 计算因子 (9 种技术因子)
   ↓
3. 因子处理 (去极值 → 标准化)
   ↓
4. 因子合成 (等权/权重/得分)
   ↓
5. Top-N 选股
   ↓
6. 权重分配 (等权/反波动率/得分加权)
   ↓
7. 定期调仓
   ↓
8. VectorBT 回测
```

---

## 🔧 技术栈

- **数据处理**: Pandas, NumPy
- **回测框架**: VectorBT
- **数据库**: PyMySQL
- **配置管理**: YAML

---

## 📝 使用示例

### 示例 1: 动量反转策略回测

```bash
python scripts/vectorbt_multi_factor_from_mysql.py \
    --preset momentum_reversion \
    --top-n 5 \
    --rebalance-days 20 \
    --weight-scheme inv_vol \
    --max-weight 0.40 \
    --start 2020-01-01
```

### 示例 2: 自定义因子组合

```python
from sharecode.strategies.multi_factor import MultiFactorSelector, SelectionConfig

selector = MultiFactorSelector()
selector.add_builtin_factors(["momentum_60d", "volatility_20d", "rsi_14d"])
selector.config = SelectionConfig(
    top_n=10,
    rebalance_days=20,
    weight_scheme="score",
    max_weight=0.30,
)
weights_df, selections_df, _ = selector.run(close_df)
```

---

## 🎓 学习资源

- **文档**: `sharecode/strategies/MULTI_FACTOR_README.md`
- **代码示例**: 见 README.md 中的使用示例
- **因子理论**: 参考 "Your Complete Guide to Factor Investing"

---

## 🚧 后续扩展建议

### 1. 基本面因子
- 接入 PE、PB、ROE、营收增长等财务数据
- 构建价值因子、成长因子、质量因子

### 2. 行业中性化
- 获取行业分类数据
- 在因子合成时进行行业调整

### 3. 机器学习因子合成
- 使用 XGBoost、LightGBM 等模型
- 基于历史因子和收益训练模型

### 4. 因子有效性检验
- 单因子回测
- 因子相关性分析
- 分层回测

---

## ✅ 验证

### 代码验证
所有代码已通过语法检查：
```bash
python3 -m py_compile sharecode/strategies/multi_factor.py  # ✓
python3 -m py_compile scripts/vectorbt_multi_factor_from_mysql.py  # ✓
```

### 回测验证
在 2018-2023 年期间使用 36 个 ETF 进行回测：

| 策略 | 收益率 | 最大回撤 | Sharpe |
|-----|--------|---------|--------|
| **momentum_120d** (最佳) | **+4.16%** | 5.82% | **0.28** |
| 动量反转组合 | -13.23% | 15.66% | -0.52 |
| 短期动量 | -8.27% | 11.53% | -0.30 |

**详细回测报告**: 见 `MULTI_FACTOR_BACKTEST_REPORT.md`

### 运行示例
```bash
# 运行最佳策略
python scripts/vectorbt_multi_factor_from_mysql.py \
    --factors momentum_120d \
    --top-n 5 \
    --rebalance-days 40 \
    --start 2018-01-01
```

---

## 📞 支持

如有问题，请参考：
1. `sharecode/strategies/MULTI_FACTOR_README.md` - 完整使用文档
2. `sharecode/strategies/multi_factor.py` - 代码注释
3. 项目 README.md - 总体介绍

---

**完成日期**: 2026-03
**版本**: v1.0
**作者**: 量化交易系统
