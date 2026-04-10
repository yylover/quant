## Context

当前项目使用 vectorbt 和 backtrader 进行回测，已经实现了多种技术指标策略（如双均线、布林带、RSI、MACD 等）。回测结果目前以 CSV 和 HTML 报告形式输出，但缺乏直观的图表可视化功能。

现有的策略代码位于 `sharecode/strategies/` 目录，回测运行器位于 `sharecode/backtest/vectorbt_runner.py`。数据存储在 `data/` 目录下的 CSV 文件中。

## Goals / Non-Goals

**Goals:**
- 实现基于均线回测策略的可视化功能
- 支持持仓线、收益曲线、交易信号、均线走势、回撤分析等多种图表
- 提供统一的图表生成接口
- 与现有策略代码无缝集成
- 支持保存图表为图片文件

**Non-Goals:**
- 不实现实时数据可视化
- 不实现交互式 Web 图表（如 Dash、Streamlit）
- 不修改现有回测逻辑，仅添加可视化层

## Decisions

### 1. 使用 Matplotlib 作为主要可视化库
- **选择**: Matplotlib
- **理由**: 
  - 项目已熟悉该库（现有代码中有使用）
  - 支持保存高质量图片
  - 静态图表适合报告生成
- **替代方案**: Plotly（交互式但依赖更多）、Seaborn（基于 Matplotlib 的高级封装）

### 2. 图表布局采用多子图方式
- **选择**: 使用 `plt.subplots()` 创建 4-5 个子图垂直排列
- **布局设计**:
  1. 价格和均线图（主图）
  2. 持仓状态图
  3. 收益曲线图
  4. 回撤图
  5. 交易量图（可选）
- **理由**: 垂直排列便于时间轴对齐，一目了然查看策略全貌

### 3. 模块设计
- **选择**: 创建独立的可视化模块，与策略模块分离
- **模块结构**:
  - `MABacktestVisualizer`: 核心可视化类
  - `ChartConfig`: 图表配置类（颜色、线型、大小等）
  - `PlotUtils`: 绘图工具函数
- **理由**: 单一职责原则，便于测试和复用

### 4. 数据接口设计
- **选择**: 接受 pandas DataFrame 作为输入
- **必需列**: `date`, `open`, `high`, `low`, `close`, `volume`, `short_ma`, `long_ma`, `position`, `returns`, `cumulative_returns`
- **理由**: 与现有 vectorbt 回测结果格式兼容

## Risks / Trade-offs

- **[Risk]** 大量数据点可能导致图表渲染缓慢 → **Mitigation**: 提供数据采样选项，支持按日期范围筛选
- **[Risk]** 不同策略的参数差异导致图表不兼容 → **Mitigation**: 使用配置类封装图表参数，提供默认值
- **[Risk]** 中文字体显示问题 → **Mitigation**: 配置 Matplotlib 使用中文字体（如 SimHei 或系统默认字体）

## Migration Plan

1. **Phase 1**: 实现核心可视化模块和基础图表
2. **Phase 2**: 集成到现有回测脚本中
3. **Phase 3**: 添加更多图表类型和配置选项

## Open Questions

- 是否需要支持多子图导出为单独图片？
- 是否需要支持自定义颜色主题？
