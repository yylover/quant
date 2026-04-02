import pandas as pd
import numpy as np
import sys
import os

# 添加路径
sys.path.append('/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/atr')

# 生成测试数据
np.random.seed(42)
end_date = pd.Timestamp('2026-04-01')
start_date = end_date - pd.Timedelta(days=5*365)
dates = pd.date_range(start=start_date, end=end_date, freq='B')
base_price = 4000
trend = np.linspace(0, 0.1, len(dates))
volatility = np.random.normal(0, 0.015, len(dates))
prices = base_price * (1 + trend + np.cumsum(volatility))

data = pd.DataFrame({
    'date': dates,
    'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
    'high': prices * (1 + np.random.normal(0.003, 0.005, len(dates))),
    'low': prices * (1 + np.random.normal(-0.003, 0.005, len(dates))),
    'close': prices,
    'volume': np.random.randint(10000000, 50000000, len(dates))
})
data['high'] = data[['open', 'high', 'close']].max(axis=1)
data['low'] = data[['open', 'low', 'close']].min(axis=1)
data.set_index('date', inplace=True)

print('数据生成完成')
print(f'数据长度: {len(data)}')

# 测试突破策略的信号生成
from atr_breakout.strategy_atr_breakout import AtrBreakoutStrategy
print('\n测试ATR突破策略信号生成...')
strategy = AtrBreakoutStrategy(data)

# 计算ATR
strategy.calculate_atr()
print(f'ATR计算完成')
print(f'ATR统计: 最小值={strategy.data['atr'].min():.4f}, 最大值={strategy.data['atr'].max():.4f}, 平均值={strategy.data['atr'].mean():.4f}')

# 计算突破水平
strategy.calculate_breakout_levels()
print(f'突破水平计算完成')

# 生成信号
strategy.generate_signals()
print(f'信号生成完成')

# 检查信号
buy_signals = strategy.data[strategy.data['signal'] == 1]
sell_signals = strategy.data[strategy.data['signal'] == -1]
print(f'买入信号数: {len(buy_signals)}')
print(f'卖出信号数: {len(sell_signals)}')

# 显示前几个信号
print('\n前5个买入信号:')
print(buy_signals.head())

print('\n前5个卖出信号:')
print(sell_signals.head())

# 检查数据是否有NaN值
print(f'\n数据检查:')
print(f'breakout_high NaN值数量: {strategy.data['breakout_high'].isna().sum()}')
print(f'breakout_low NaN值数量: {strategy.data['breakout_low'].isna().sum()}')
print(f'ATR NaN值数量: {strategy.data['atr'].isna().sum()}')
