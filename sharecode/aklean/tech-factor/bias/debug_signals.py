import pandas as pd
import numpy as np

# 生成模拟数据
np.random.seed(42)
end_date = pd.Timestamp('2026-04-01')
start_date = end_date - pd.Timedelta(days=5*365)
dates = pd.date_range(start=start_date, end=end_date, freq='B')

# 基础价格趋势
base_price = 4000
trend = np.linspace(0, 0.4, len(dates))
seasonal = 0.04 * np.sin(np.linspace(0, 10*np.pi, len(dates)))
cyclic = 0.03 * np.cos(np.linspace(0, 5*np.pi, len(dates)))
volatility = np.random.normal(0, 0.01, len(dates))
prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))

data = pd.DataFrame({
    'date': dates,
    'close': prices
})
data.set_index('date', inplace=True)

# 计算BIAS
short_period = 6
medium_period = 12
long_period = 24

data['ma_short'] = data['close'].rolling(short_period).mean()
data['ma_medium'] = data['close'].rolling(medium_period).mean()
data['ma_long'] = data['close'].rolling(long_period).mean()

data['bias_short'] = (data['close'] - data['ma_short']) / data['ma_short'] * 100
data['bias_medium'] = (data['close'] - data['ma_medium']) / data['ma_medium'] * 100
data['bias_long'] = (data['close'] - data['ma_long']) / data['ma_long'] * 100

# 设置阈值
buy_threshold = -2.5
sell_threshold = 3.5

# 生成交易信号
data['signal'] = 0
data['position'] = 0

position = 0

for i in range(1, len(data)):
    # 买入条件：短期BIAS低于买入阈值且未持仓
    if data['bias_short'].iloc[i]< buy_threshold and position == 0:
        data.loc[data.index[i], 'signal'] = 1
        position = 1
    # 卖出条件：短期BIAS高于卖出阈值且持有仓位
    elif data['bias_short'].iloc[i] > sell_threshold and position == 1:
        data.loc[data.index[i], 'signal'] = -1
        position = 0
    
    data.loc[data.index[i], 'position'] = position

# 打印信号统计
buy_signals = (data['signal'] == 1).sum()
sell_signals = (data['signal'] == -1).sum()

print(f"买入信号数量: {buy_signals}")
print(f"卖出信号数量: {sell_signals}")

# 查看有信号的日期
signal_dates = data[data['signal'] != 0]
print(f"\n信号日期:")
print(signal_dates[['close', 'ma_short', 'bias_short', 'signal']])

# 计算策略收益
data['returns'] = data['close'].pct_change()
data['strategy_returns'] = data['returns'] * data['position'].shift(1)

# 计算累计收益
data['cumulative_strategy'] = (1 + data['strategy_returns']).cumprod()
data['cumulative_benchmark'] = (1 + data['returns']).cumprod()

print(f"\n策略累计收益: {(data['cumulative_strategy'].iloc[-1] - 1) * 100:.2f}%")
print(f"基准累计收益: {(data['cumulative_benchmark'].iloc[-1] - 1) * 100:.2f}%")
