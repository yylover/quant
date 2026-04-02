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

# 基础价格趋势
base_price = 4000
trend = np.linspace(0, 0.1, len(dates))
seasonal = 0.04 * np.sin(np.linspace(0, 10*np.pi, len(dates)))
cyclic = 0.03 * np.cos(np.linspace(0, 5*np.pi, len(dates)))
volatility = np.random.normal(0, 0.015, len(dates))
prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))

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

# 测试突破策略
from atr_breakout.strategy_atr_breakout import AtrBreakoutStrategy
print('\n测试ATR突破策略...')

strategy = AtrBreakoutStrategy(data)
strategy.calculate_atr()
strategy.calculate_breakout_levels()
strategy.generate_signals()

# 手动执行策略的回测逻辑
print('\n开始执行策略的回测逻辑...')
strategy.data['position'] = 0.0
strategy.data['entry_price'] = 0.0
strategy.data['stop_loss'] = 0.0
strategy.data['take_profit'] = 0.0
strategy.data['strategy_returns'] = 0.0

position = 0
entry_price = 0

for i in range(1, len(strategy.data)):
    # 买入信号
    if strategy.data['signal'].iloc[i] == 1 and position == 0:
        position = 1
        entry_price = strategy.data['close'].iloc[i]
        # 设置止损和止盈
        stop_loss_price = entry_price - strategy.data['atr'].iloc[i] * 2.5
        take_profit_price = entry_price + strategy.data['atr'].iloc[i] * 3.5
        
        strategy.data.at[strategy.data.index[i], 'position'] = position
        strategy.data.at[strategy.data.index[i], 'entry_price'] = entry_price
        strategy.data.at[strategy.data.index[i], 'stop_loss'] = stop_loss_price
        strategy.data.at[strategy.data.index[i], 'take_profit'] = take_profit_price
    
    # 卖出信号
    elif strategy.data['signal'].iloc[i] == -1 and position == 1:
        position = 0
        exit_price = strategy.data['close'].iloc[i]
        strategy.data.at[strategy.data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
    
    # 止损
    elif position == 1 and strategy.data['low'].iloc[i]<= strategy.data['stop_loss'].iloc[i-1]:
        position = 0
        exit_price = strategy.data['stop_loss'].iloc[i-1]
        strategy.data.at[strategy.data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
    
    # 止盈
    elif position == 1 and strategy.data['high'].iloc[i] >= strategy.data['take_profit'].iloc[i-1]:
        position = 0
        exit_price = strategy.data['take_profit'].iloc[i-1]
        strategy.data.at[strategy.data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
    
    # 保持仓位
    else:
        strategy.data.at[strategy.data.index[i], 'position'] = position
        strategy.data.at[strategy.data.index[i], 'entry_price'] = entry_price

# 计算累计收益
strategy.data['cumulative_returns'] = (1 + strategy.data['strategy_returns']).cumprod()

# 计算指标
total_return = (strategy.data['cumulative_returns'].iloc[-1] - 1) * 100
years = len(strategy.data) / 252
annualized_return = ((1 + total_return/100) ** (1/years)) - 1

print(f'\n回测结果:')
print(f'总收益率: {total_return:.2f}%')
print(f'年化收益率: {annualized_return*100:.2f}%')

# 检查策略收益数据
print(f'\n策略收益数据统计:')
print(f'非零收益次数: {len(strategy.data[strategy.data["strategy_returns"] != 0])}')
print(f'最大单笔收益: {strategy.data["strategy_returns"].max()*100:.2f}%')
print(f'最小单笔收益: {strategy.data["strategy_returns"].min()*100:.2f}%')

# 检查累计收益的变化
print(f'\n累计收益变化:')
print(f'初始值: {strategy.data["cumulative_returns"].iloc[0]:.4f}')
print(f'最终值: {strategy.data["cumulative_returns"].iloc[-1]:.4f}')
