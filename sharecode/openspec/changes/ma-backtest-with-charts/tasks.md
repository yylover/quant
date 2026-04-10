## 1. 项目设置和依赖

- [x] 1.1 检查并安装 matplotlib 依赖（如未安装）
- [x] 1.2 创建 `sharecode/strategies/ma_visualization.py` 文件
- [x] 1.3 创建 `sharecode/strategies/ma_backtest_chart.py` 文件
- [x] 1.4 创建 `scripts/run_ma_backtest_with_charts.py` 脚本文件

## 2. 核心可视化类实现

- [x] 2.1 实现 `ChartConfig` 配置类（图表尺寸、颜色、字体等）
- [x] 2.2 实现 `MABacktestVisualizer` 类的初始化方法
- [x] 2.3 实现价格和均线图表绘制方法 `plot_price_and_ma()`
- [x] 2.4 实现交易信号标记功能 `plot_signals()`

## 3. 持仓和收益图表

- [x] 3.1 实现持仓状态图表绘制方法 `plot_position()`
- [x] 3.2 实现收益曲线图表绘制方法 `plot_returns()`
- [x] 3.3 实现基准收益对比功能
- [x] 3.4 实现收益统计信息展示 `plot_stats()`

## 4. 回撤和综合图表

- [x] 4.1 实现回撤计算功能 `calculate_drawdown()`
- [x] 4.2 实现回撤图表绘制方法 `plot_drawdown()`
- [x] 4.3 实现综合图表布局方法 `plot_comprehensive_chart()`
- [x] 4.4 实现图表导出功能 `save_chart()`

## 5. 回测集成和脚本

- [x] 5.1 集成可视化功能到现有均线回测策略
- [x] 5.2 实现 `run_ma_backtest_with_charts.py` 运行脚本
- [x] 5.3 支持从 CSV 文件加载数据并生成图表
- [x] 5.4 添加命令行参数支持（股票代码、时间范围、均线参数等）

## 6. 测试和优化

- [ ] 6.1 测试图表生成功能是否正常
- [ ] 6.2 验证中文字体显示是否正确
- [ ] 6.3 测试不同数据量下的性能
- [ ] 6.4 优化图表美观度和可读性
