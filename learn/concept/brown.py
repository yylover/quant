import numpy as np
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

# 布朗运动参数
T = 1.0        # 总时间
N = 1000       # 时间步数
dt = T / N     # 时间间隔
t = np.linspace(0, T, N+1)

# 生成标准布朗运动
dW = np.random.normal(0, np.sqrt(dt), N)
W = np.cumsum(dW)
W = np.hstack(([0], W))  # 初始值 W(0)=0

# 绘图
plt.figure(figsize=(10, 5))
plt.plot(t, W, linewidth=1.2, color='#1f77b4', label='标准布朗运动 W(t)')
plt.grid(alpha=0.3)
plt.xlabel('时间 t')
plt.ylabel('W(t)')
plt.title('一维连续时间标准布朗运动')
plt.legend()
plt.tight_layout()
plt.savefig('./brownian_motion.png', dpi=200)
plt.close()

print("布朗运动模拟图已生成")