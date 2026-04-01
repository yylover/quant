import numpy as np
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

# 随机游走参数
np.random.seed(42)
n_steps = 1000
epsilon = np.random.normal(loc=0, scale=1, size=n_steps)  # 随机残差项
random_walk = np.cumsum(epsilon)  # 累积和 = 随机游走

# 绘图
plt.figure(figsize=(12, 5))
plt.plot(random_walk, linewidth=1, color='#1f77b4', label='随机游走路径')
plt.axhline(y=0, color='red', linestyle='--', linewidth=0.8, alpha=0.7, label='均值线')
plt.title('一维随机游走（离散时间）', fontsize=14)
plt.xlabel('步数 t', fontsize=12)
plt.ylabel('位置 Xt', fontsize=12)
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()

# 保存图片
plt.savefig('./random_walk.png', dpi=150)
plt.close()

print("随机游走路径已生成")