import pandas as pd
import numpy as np

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

# 计算ATR和信号
data['tr'] = np.maximum(
    data['high'] - data['low'],
    np.maximum(
        abs(data['high'] - data['close'].shift(1)),
        abs(data['low'] - data['close'].shift(1))
    )
)
data['atr'] = data['tr'].rolling(window=14).mean()
data['high_rolling'] = data['high'].rolling(window=10).max()
data['low_rolling'] = data['low'].rolling(window=10).min()
data['breakout_high'] = data['high_rolling'] + data['atr'] * 0.5
data['breakout_low'] = data['low_rolling'] - data['atr'] * 0.5
data['signal'] = 0
buy_condition = data['high'] > data['breakout_high'].shift(1)
sell_condition = data['low'] < data['breakout_low'].shift(1)
data.loc[buy_condition, 'signal'] = 1
data.loc[sell_condition, 'signal'] = -1

print(f'买入信号数: {len(data[data['signal'] == 1])}')
print(f'卖出信号数: {len(data[data['signal'] == -1])}')

# 执行回测逻辑
data['position'] = 0.0
data['entry_price'] = 0.0
data['stop_loss'] = 0.0
data['take_profit'] = 0.0
data['strategy_returns'] = 0.0

position = 0
entry_price = 0
stop_loss_price = 0
take_profit_price = 0

print('\n回测逻辑执行中...')

for i in range(1, len(data)):
    # 买入信号
    if data['signal'].iloc[i] == 1 and position == 0:
        position = 1
        entry_price = data['close'].iloc[i]
        stop_loss_price = entry_price - data['atr'].iloc[i] * 2.0
        take_profit_price = entry_price + data['atr'].iloc[i] * 3.0
        
        data.at[data.index[i], 'position'] = position
        data.at[data.index[i], 'entry_price'] = entry_price
        data.at[data.index[i], 'stop_loss'] = stop_loss_price
        data.at[data.index[i], 'take_profit'] = take_profit_price
        print(f'买入: {data.index[i].date()}, 价格: {entry_price:.2f}, 止损: {stop_loss_price:.2f}, 止盈: {take_profit_price:.2f}')
    
    # 卖出信号
    elif data['signal'].iloc[i] == -1 and position == 1:
        position = 0
        exit_price = data['close'].iloc[i]
        data.at[data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
        print(f'卖出(信号): {data.index[i].date()}, 价格: {exit_price:.2f}, 收益: {data.at[data.index[i], 'strategy_returns']:.4f}')
    
    # 止损
    elif position == 1 and data['low'].iloc[i] <= stop_loss_price:
        position = 0
        exit_price = stop_loss_price
        data.at[data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
        print(f'卖出(止损): {data.index[i].date()}, 价格: {exit_price:.2f}, 收益: {data.at[data.index[i], 'strategy_returns']:.4f}')
    
    # 止盈
    elif position == 1 and data['high'].iloc[i] >= take_profit_price:
        position = 0
        exit_price = take_profit_price
        data.at[data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
        print(f'卖出(止盈): {data.index[i].date()}, 价格: {exit_price:.2f}, 收益: {data.at[data.index[i], 'strategy_returns']:.4f}')
    
    # 保持仓位
    else:
        data.at[data.index[i], 'position'] = position
        if position == 1:
            data.at[data.index[i], 'stop_loss'] = stop_loss_price
            data.at[data.index[i], 'take_profit'] = take_profit_price

# 计算累计收益
data['cumulative_returns'] = (1 + data['strategy_returns']).cumprod()
total_return = (data['cumulative_returns'].iloc[-1] - 1) * 100
annualized_return = (1 + total_return/100) ** (252/len(data)) - 1

print(f'\n回测结果:')
print(f'总收益率: {total_return:.2f}%')
print(f'年化收益率: {annualized_return:.2f}%')

# 显示交易统计
trades = data[data['strategy_returns'] != 0]
print(f'\n交易统计:')
print(f'总交易次数: {len(trades)}')
print(f'盈利交易次数: {len(trades[trades['strategy_returns'] > 0])}')
print(f'亏损交易次数: {len(trades[trades['strategy_returns']< 0])}')
