import pandas as pd
import numpy as np
from strategy_bias import generate_hs300_data, BiasStrategy

# 生成模拟数据
data = generate_hs300_data()

# 创建策略实例
strategy = BiasStrategy(data, buy_threshold=-2.5, sell_threshold=3.5)

# 计算指标
strategy.calculate_bias()

# 生成基础策略信号
strategy.generate_signals(strategy_type='basic')

# 执行回测
strategy.backtest()

# 显示信号统计
buy_signals = (strategy.data['signal'] == 1).sum()
sell_signals = (strategy.data['signal'] == -1).sum()

print("信号统计：")
print(f"买入信号: {buy_signals}")
print(f"卖出信号: {sell_signals}")

# 计算指标
strategy.calculate_metrics()

# 显示回测结果
print("\n回测结果：")
print(f"总收益率: {strategy.metrics['total_return']:.2f}%")
print(f"年化收益率: {strategy.metrics['annualized_return']:.2f}%")
print(f"夏普比率: {strategy.metrics['sharpe_ratio']:.2f}")
print(f"最大回撤: {strategy.metrics['max_drawdown']:.2f}%")
print(f"胜率: {strategy.metrics['win_rate']:.2f}%")
print(f"盈亏比: {strategy.metrics['profit_loss_ratio']:.2f}")
print(f"总交易次数: {strategy.metrics['total_trades']}")
print(f"平均持仓天数: {strategy.metrics['average_holding_days']:.1f}")
