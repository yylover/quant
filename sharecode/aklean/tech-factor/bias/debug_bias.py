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

# 打印统计信息
print("BIAS统计信息：")
print(f"短期BIAS范围: {data['bias_short'].min():.2f}% 到 {data['bias_short'].max():.2f}%")
print(f"中期BIAS范围: {data['bias_medium'].min():.2f}% 到 {data['bias_medium'].max():.2f}%")
print(f"长期BIAS范围: {data['bias_long'].min():.2f}% 到 {data['bias_long'].max():.2f}%")

# 检查阈值设置
buy_threshold = -5
sell_threshold = 5

print(f"\n阈值设置：")
print(f"买入阈值: {buy_threshold}%")
print(f"卖出阈值: {sell_threshold}%")

# 检查满足条件的天数
oversold_days = (data['bias_short']< buy_threshold).sum()
overbought_days = (data['bias_short'] >sell_threshold).sum()

print(f"\n满足条件的天数：")
print(f"超卖天数 (BIAS < {buy_threshold}%): {oversold_days}")
print(f"超买天数 (BIAS > {sell_threshold}%): {overbought_days}")

# 查看一些样本数据
print("\n样本数据（最近20天）：")
print(data[['close', 'ma_short', 'bias_short']].tail(20))
