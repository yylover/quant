## Why

当前项目已经实现了基于均线的回测策略（如双均线交叉策略），但缺乏直观的可视化功能来展示回测结果。用户无法直观地查看持仓变化、收益曲线、交易信号等关键信息。增加可视化功能将帮助用户更好地理解策略表现，优化参数设置，并做出更明智的投资决策。

## What Changes

- 新增基于均线的回测策略可视化模块
- 支持绘制持仓线图表，展示策略在不同时间点的持仓状态
- 支持绘制收益曲线图表，对比策略收益与基准收益
- 支持绘制交易信号标记，直观显示买入/卖出点
- 支持绘制均线图表，展示短期和长期均线的走势
- 支持绘制回撤图表，展示策略的最大回撤情况
- 提供统一的图表生成接口，便于扩展其他可视化类型

## Capabilities

### New Capabilities
- `ma-backtest-visualization`: 基于均线回测策略的可视化功能，包括持仓线、收益曲线、交易信号、均线走势和回撤分析等图表

### Modified Capabilities
- （无现有功能需要修改需求）

## Impact

- **新增文件**:
  - `sharecode/strategies/ma_visualization.py`: 可视化核心模块
  - `sharecode/strategies/ma_backtest_chart.py`: 回测图表生成器
  - `scripts/run_ma_backtest_with_charts.py`: 带图表的回测运行脚本
- **依赖库**: 需要 matplotlib、plotly 或 seaborn 等可视化库
- **现有策略**: 可与现有的 `mean_reversion.py` 和 `trend_following.py` 策略集成
