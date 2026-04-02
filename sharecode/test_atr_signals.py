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

# 计算ATR
data['tr'] = np.maximum(
    data['high'] - data['low'],
    np.maximum(
        abs(data['high'] - data['close'].shift(1)),
        abs(data['low'] - data['close'].shift(1))
    )
)
data['atr'] = data['tr'].rolling(window=14).mean()

# 计算突破水平
data['high_rolling'] = data['high'].rolling(window=10).max()
data['low_rolling'] = data['low'].rolling(window=10).min()
data['breakout_high'] = data['high_rolling'] + data['atr'] * 0.5
data['breakout_low'] = data['low_rolling'] - data['atr'] * 0.5

# 生成信号
data['signal'] = 0
buy_condition = data['high'] > data['breakout_high'].shift(1)
sell_condition = data['low'] < data['breakout_low'].shift(1)
data.loc[buy_condition, 'signal'] = 1
data.loc[sell_condition, 'signal'] = -1

print(f'数据长度: {len(data)}')
print(f'ATR统计:')
print(f'  最小值: {data['atr'].min():.4f}')
print(f'  最大值: {data['atr'].max():.4f}')
print(f'  平均值: {data['atr'].mean():.4f}')
print(f'  标准差: {data['atr'].std():.4f}')
print(f'突破策略信号统计:')
print(f'  买入信号数: {len(data[data['signal'] == 1])}')
print(f'  卖出信号数: {len(data[data['signal'] == -1])}')
print(f'  无信号数: {len(data[data['signal'] == 0])}')

# 显示部分数据
print('\n前20行数据:')
print(data[['high', 'low', 'breakout_high', 'breakout_low', 'signal']].head(20))
