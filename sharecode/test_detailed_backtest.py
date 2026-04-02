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

# 测试突破策略的详细回测
from atr_breakout.strategy_atr_breakout import AtrBreakoutStrategy
print('\n测试ATR突破策略详细回测...')
strategy = AtrBreakoutStrategy(data)

# 计算ATR和信号
strategy.calculate_atr()
strategy.calculate_breakout_levels()
strategy.generate_signals()

# 统计信号
buy_signals = strategy.data[strategy.data['signal'] == 1]
sell_signals = strategy.data[strategy.data['signal'] == -1]
print(f'买入信号数: {len(buy_signals)}')
print(f'卖出信号数: {len(sell_signals)}')

# 手动执行回测逻辑
print('\n开始手动回测...')
position = 0
entry_price = 0
stop_loss_price = 0
take_profit_price = 0
trades = []

for i in range(1, len(strategy.data)):
    current_date = strategy.data.index[i]
    current_high = strategy.data['high'].iloc[i]
    current_low = strategy.data['low'].iloc[i]
    current_close = strategy.data['close'].iloc[i]
    current_signal = strategy.data['signal'].iloc[i]
    
    # 买入信号
    if current_signal == 1 and position == 0:
        position = 1
        entry_price = current_close
        atr_value = strategy.data['atr'].iloc[i]
        stop_loss_price = entry_price - atr_value * 2.5
        take_profit_price = entry_price + atr_value * 3.5
        print(f'买入: {current_date.date()}, 价格: {entry_price:.2f}, 止损: {stop_loss_price:.2f}, 止盈: {take_profit_price:.2f}')
    
    # 卖出信号
    elif current_signal == -1 and position == 1:
        position = 0
        exit_price = current_close
        profit = (exit_price - entry_price) / entry_price
        trades.append({
            'entry_date': entry_date,
            'exit_date': current_date,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit': profit
        })
        print(f'卖出(信号): {current_date.date()}, 价格: {exit_price:.2f}, 收益: {profit:.4f}')
    
    # 止损
    elif position == 1 and current_low<= stop_loss_price:
        position = 0
        exit_price = stop_loss_price
        profit = (exit_price - entry_price) / entry_price
        trades.append({
            'entry_date': entry_date,
            'exit_date': current_date,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit': profit
        })
        print(f'卖出(止损): {current_date.date()}, 价格: {exit_price:.2f}, 收益: {profit:.4f}')
    
    # 止盈
    elif position == 1 and current_high >= take_profit_price:
        position = 0
        exit_price = take_profit_price
        profit = (exit_price - entry_price) / entry_price
        trades.append({
            'entry_date': entry_date,
            'exit_date': current_date,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit': profit
        })
        print(f'卖出(止盈): {current_date.date()}, 价格: {exit_price:.2f}, 收益: {profit:.4f}')
    
    # 记录当前日期（用于卖出时的entry_date）
    if position == 1:
        entry_date = current_date

# 计算总收益
if trades:
    total_return = np.prod([1 + trade['profit'] for trade in trades]) - 1
    win_trades = [t for t in trades if t['profit'] > 0]
    lose_trades = [t for t in trades if t['profit'] < 0]
    
    print(f'\n回测结果:')
    print(f'总交易次数: {len(trades)}')
    print(f'盈利交易次数: {len(win_trades)}')
    print(f'亏损交易次数: {len(lose_trades)}')
    print(f'总收益率: {total_return*100:.2f}%')
    
    if win_trades:
        avg_win = np.mean([t['profit'] for t in win_trades])
        print(f'平均盈利: {avg_win*100:.2f}%')
    
    if lose_trades:
        avg_loss = np.mean([t['profit'] for t in lose_trades])
        print(f'平均亏损: {avg_loss*100:.2f}%')
else:
    print('\n没有交易发生')
