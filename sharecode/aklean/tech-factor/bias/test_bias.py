import pandas as pd
import numpy as np

# 创建简单的测试数据
dates = pd.date_range('2023-01-01', '2023-01-30', freq='B')
prices = np.array([100, 102, 105, 103, 101, 99, 97, 95, 93, 91, 92, 94, 96, 98, 100, 102, 104, 106, 108, 110])

data = pd.DataFrame({
    'date': dates[:len(prices)],
    'close': prices
})
data.set_index('date', inplace=True)

# 计算BIAS
short_period = 6
data['ma_short'] = data['close'].rolling(short_period).mean()
data['bias_short'] = (data['close'] - data['ma_short']) / data['ma_short'] * 100

print("价格数据：")
print(data[['close', 'ma_short', 'bias_short']])
print("\nBIAS最小值:", data['bias_short'].min())
print("BIAS最大值:", data['bias_short'].max())
