"""Visualize backtest results with charts.

可视化回测结果图表.
"""
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
import numpy as np
from pathlib import Path

# 设置中文字体支持
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).resolve().parents[1]
results_path = ROOT / "data" / "hs300_mean_reversion_backtest_results.csv"

# 读取回测结果
df = pd.read_csv(results_path, encoding="utf-8-sig")

# 创建图表
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('沪深300指数均值回归策略回测结果分析', fontsize=16, fontweight='bold')

# 1. 总收益对比柱状图
ax1 = axes[0, 0]
colors = ['green' if x > 0 else 'red' for x in df['超额收益%']]
bars = ax1.barh(df['策略'].str.replace(' \\(.*\\)', ''), df['总收益%'], color=colors)
ax1.axvline(x=df['基准收益%'].iloc[0], color='blue', linestyle='--', linewidth=2, label='基准收益')
ax1.set_xlabel('总收益率 (%)', fontsize=12)
ax1.set_title('各策略总收益对比', fontsize=14, fontweight='bold')
ax1.legend()
ax1.grid(axis='x', alpha=0.3)

# 在柱状图上显示数值
for bar, value in zip(bars, df['总收益%']):
    ax1.text(value + (1 if value >= 0 else -3), bar.get_y() + bar.get_height()/2,
            f'{value:.1f}%', va='center', ha='left' if value >= 0 else 'right', fontsize=9)

# 2. 收益 vs 回撤散点图
ax2 = axes[0, 1]
sc = ax2.scatter(df['最大回撤%'].abs(), df['总收益%'],
                s=200, c=df['总收益%'], cmap='RdYlGn', alpha=0.7, edgecolors='black')
ax2.axhline(y=df['基准收益%'].iloc[0], color='blue', linestyle='--', linewidth=2, label='基准收益')
ax2.set_xlabel('最大回撤 (%)', fontsize=12)
ax2.set_ylabel('总收益率 (%)', fontsize=12)
ax2.set_title('风险-收益关系分析', fontsize=14, fontweight='bold')
ax2.legend()
ax2.grid(alpha=0.3)

# 添加标签
for i, txt in enumerate(df['策略'].str.replace(' \\(.*\\)', '')):
    ax2.annotate(txt, (df['最大回撤%'].abs().iloc[i], df['总收益%'].iloc[i]),
                fontsize=8, ha='center', va='bottom')

# 3. 超额收益对比
ax3 = axes[1, 0]
colors = ['green' if x > 0 else 'red' for x in df['超额收益%']]
bars = ax3.barh(df['策略'].str.replace(' \\(.*\\)', ''), df['超额收益%'], color=colors)
ax3.axvline(x=0, color='black', linestyle='-', linewidth=1)
ax3.set_xlabel('超额收益率 (%)', fontsize=12)
ax3.set_title('各策略超额收益对比', fontsize=14, fontweight='bold')
ax3.grid(axis='x', alpha=0.3)

# 在柱状图上显示数值
for bar, value in zip(bars, df['超额收益%']):
    ax3.text(value + (0.5 if value >= 0 else -0.5), bar.get_y() + bar.get_height()/2,
            f'{value:.1f}%', va='center', ha='left' if value >= 0 else 'right', fontsize=9)

# 4. 投资收益对比
ax4 = axes[1, 1]
initial_capital = 100000
df['期末资金'] = initial_capital * (1 + df['总收益%'] / 100)
df['盈亏'] = df['期末资金'] - initial_capital
colors = ['green' if x > 0 else 'red' for x in df['盈亏']]
bars = ax4.barh(df['策略'].str.replace(' \\(.*\\)', ''), df['期末资金'], color=colors)
ax4.axvline(x=initial_capital * (1 + df['基准收益%'].iloc[0] / 100),
             color='blue', linestyle='--', linewidth=2, label='基准期末资金')
ax4.set_xlabel('期末资金 (元)', fontsize=12)
ax4.set_title('投资10万元期末资金对比', fontsize=14, fontweight='bold')
ax4.legend()
ax4.grid(axis='x', alpha=0.3)

# 在柱状图上显示数值
for bar, value in zip(bars, df['期末资金']):
    ax4.text(value + 2000, bar.get_y() + bar.get_height()/2,
            f'{value:,.0f}元', va='center', ha='left', fontsize=8)

plt.tight_layout()

# 保存图表
output_path = ROOT / "data" / "hs300_mean_reversion_backtest_charts.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"图表已保存到: {output_path}")
plt.show()

# 创建第二个图表: 新旧策略对比
fig2, ax = plt.subplots(1, 1, figsize=(12, 6))

new_strategies = ['KDJ 回归', 'Williams %R 回归', 'CCI 回归']
df['类别'] = ['新策略' if any(x in s for x in new_strategies) else '原有策略' for s in df['策略']]

# 分组柱状图
x = np.arange(len(df))
width = 0.35

colors_new = ['#2ecc71', '#27ae60']
colors_old = ['#e74c3c', '#c0392b']

bars_old = ax.bar([i - width/2 for i in x], df[df['类别'] == '原有策略']['总收益%'],
                 width, label='原有策略', color=colors_old[0], alpha=0.8)
bars_new = ax.bar([i + width/2 for i in x], df[df['类别'] == '新策略']['总收益%'],
                 width, label='新策略', color=colors_new[0], alpha=0.8)

ax.axhline(y=df['基准收益%'].iloc[0], color='blue', linestyle='--', linewidth=2, label='基准收益')
ax.set_ylabel('总收益率 (%)', fontsize=12)
ax.set_title('新旧策略对比', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(df['策略'].str.replace(' \\(.*\\)', ''), rotation=45, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# 添加数值标签
for bars in [bars_old, bars_new]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -2),
                f'{height:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)

plt.tight_layout()
output_path2 = ROOT / "data" / "hs300_new_vs_old_strategies.png"
plt.savefig(output_path2, dpi=150, bbox_inches='tight')
print(f"对比图表已保存到: {output_path2}")
plt.show()
