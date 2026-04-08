import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# 生成模拟价格数据
np.random.seed(42)
time = np.arange(100)
# 生成带有趋势和噪声的价格数据
price = 100 + 0.5 * time + np.random.normal(0, 2, size=100)
# 添加一个明显的趋势变化点
price[50:] = price[50] + 0.1 * (time[50:] - time[50])

# 计算拉普拉斯值
def laplace_filter(data, window=1):
    laplace = np.zeros_like(data)
    for i in range(window, len(data) - window):
        laplace[i] = data[i+window] - 2 * data[i] + data[i-window]
    return laplace

# 应用拉普拉斯滤波器
laplace_values = laplace_filter(price)

# 绘制结果
plt.figure(figsize=(12, 6))
plt.subplot(2, 1, 1)
plt.plot(time, price, label='Price')
plt.title('Stock Price')
plt.legend()

plt.subplot(2, 1, 2)
plt.plot(time, laplace_values, label='Laplace')
plt.axhline(y=0, color='r', linestyle='--')
plt.title('Laplace Filter Output')
plt.legend()

plt.tight_layout()
plt.show()
