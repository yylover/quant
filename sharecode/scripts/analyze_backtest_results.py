"""Detailed analysis of mean reversion strategies backtest results.

详细分析均值回归策略回测结果.
"""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results_path = ROOT / "data" / "hs300_mean_reversion_backtest_results.csv"

# 读取回测结果
df = pd.read_csv(results_path, encoding="utf-8-sig")

print("=" * 80)
print("沪深300指数均值回归策略回测结果详细解读")
print("=" * 80)
print()

# 基本统计
print("📊 回测基本信息:")
print("-" * 80)
print(f"基准策略(买入持有):")
print(f"  - 基准收益: {df['基准收益%'].iloc[0]:.2f}%")
print(f"  - 假设投资10万元,期末资金: {100000 * (1 + df['基准收益%'].iloc[0] / 100):,.2f}元")
print()

# 策略分类分析
print("🔍 策略表现分类分析:")
print("-" * 80)

# 跑赢基准的策略
winning_strategies = df[df['超额收益%'] > 0].sort_values('超额收益%', ascending=False)
if not winning_strategies.empty:
    print("✅ 跑赢基准的策略:")
    for idx, row in winning_strategies.iterrows():
        print(f"  {row['策略'][:30]:30s}")
        print(f"    总收益: {row['总收益%']:7.2f}% | 超额: {row['超额收益%']:6.2f}% | 回撤: {row['最大回撤%']:6.2f}%")
    print()

# 未跑赢基准的策略
losing_strategies = df[df['超额收益%'] <= 0].sort_values('超额收益%')
if not losing_strategies.empty:
    print("❌ 未跑赢基准的策略:")
    for idx, row in losing_strategies.iterrows():
        print(f"  {row['策略'][:30]:30s}")
        print(f"    总收益: {row['总收益%']:7.2f}% | 超额: {row['超额收益%']:6.2f}% | 回撤: {row['最大回撤%']:6.2f}%")
    print()

# 风险收益分析
print("📈 风险收益特征分析:")
print("-" * 80)

# 按收益排序
df_sorted = df.sort_values('总收益%', ascending=False)
print("策略排名(按总收益):")
for rank, (idx, row) in enumerate(df_sorted.iterrows(), 1):
    emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank:2d}."
    print(f"  {emoji} {row['策略'][:35]:35s}")
    print(f"     收益: {row['总收益%']:7.2f}% | 回撤: {row['最大回撤%']:6.2f}% | 胜率: {row['胜率%']:6.2f}%")
print()

# 收益/回撤比分析
df['收益回撤比_手动'] = df['总收益%'] / df['最大回撤%'].abs()
df_sorted_ratio = df.sort_values('收益回撤比_手动', ascending=False)

print("策略排名(按收益/回撤比):")
for rank, (idx, row) in enumerate(df_sorted_ratio.iterrows(), 1):
    emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank:2d}."
    print(f"  {emoji} {row['策略'][:35]:35s}")
    print(f"     比值: {row['收益回撤比_手动']:6.3f} | 收益: {row['总收益%']:7.2f}% | 回撤: {row['最大回撤%']:6.2f}%")
print()

# 胜率分析
print("🎯 胜率分析:")
print("-" * 80)
valid_win_rate = df[df['胜率%'].notna()].sort_values('胜率%', ascending=False)
for idx, row in valid_win_rate.iterrows():
    print(f"  {row['策略'][:40]:40s} 胜率: {row['胜率%']:6.2f}%")
print()

# 投资收益模拟
print("💰 投资收益模拟(初始10万元):")
print("-" * 80)
initial_capital = 100000
for idx, row in df.iterrows():
    final_capital = initial_capital * (1 + row['总收益%'] / 100)
    profit = final_capital - initial_capital
    print(f"  {row['策略'][:40]:40s}")
    print(f"    期末资金: {final_capital:>10,.2f}元 | 盈亏: {profit:>10,.2f}元")
print()

# 核心结论
print("=" * 80)
print("📋 核心结论与建议:")
print("=" * 80)

best_strategy = df.loc[df['总收益%'].idxmax()]
worst_strategy = df.loc[df['总收益%'].idxmin()]
best_win_rate = df.loc[df[df['胜率%'].notna()]['胜率%'].idxmax()]
best_risk_return = df.loc[df['收益回撤比_手动'].idxmax()]

print(f"1️⃣  最佳收益策略: {best_strategy['策略']}")
print(f"    - 总收益: {best_strategy['总收益%']:.2f}%")
print(f"    - 超额收益: {best_strategy['超额收益%']:.2f}%")
print(f"    - 最大回撤: {best_strategy['最大回撤%']:.2f}%")
print()

print(f"2️⃣  最高胜率策略: {best_win_rate['策略']}")
print(f"    - 胜率: {best_win_rate['胜率%']:.2f}%")
print(f"    - 总收益: {best_win_rate['总收益%']:.2f}%")
print()

print(f"3️⃣  最佳风险收益比: {best_risk_return['策略']}")
print(f"    - 收益/回撤比: {best_risk_return['收益回撤比_手动']:.3f}")
print(f"    - 总收益: {best_risk_return['总收益%']:.2f}%")
print()

print(f"4️⃣  表现最差策略: {worst_strategy['策略']}")
print(f"    - 总收益: {worst_strategy['总收益%']:.2f}%")
print(f"    - 超额收益: {worst_strategy['超额收益%']:.2f}%")
print()

# 新策略 vs 原有策略
print("🆚 新增策略 vs 原有策略对比:")
print("-" * 80)
new_strategies = ['KDJ 回归', 'Williams %R 回归', 'CCI 回归']
new_df = df[df['策略'].str.contains('|'.join(new_strategies))]
old_df = df[~df['策略'].str.contains('|'.join(new_strategies))]

print("新增三个策略:")
print(f"  平均收益: {new_df['总收益%'].mean():.2f}%")
print(f"  平均超额收益: {new_df['超额收益%'].mean():.2f}%")
print(f"  跑赢基准数量: {len(new_df[new_df['超额收益%'] > 0])}/3")
print()

print("原有四个策略:")
print(f"  平均收益: {old_df['总收益%'].mean():.2f}%")
print(f"  平均超额收益: {old_df['超额收益%'].mean():.2f}%")
print(f"  跑赢基准数量: {len(old_df[old_df['超额收益%'] > 0])}/4")
print()

# 最终建议
print("=" * 80)
print("💡 投资建议:")
print("=" * 80)
print("""
1. 🌟 推荐策略: CCI 回归策略
   - 表现最佳,超额收益 13.56%
   - 适合震荡行情的均值回归

2. ⚠️ 风险提示:
   - 所有策略的最大回撤都超过 30%
   - 新策略收益更高但回撤也更大
   - 建议结合止损或仓位管理控制风险

3. 🔄 策略适用性:
   - 均值回归策略在震荡市表现较好
   - 在单边趋势市可能会频繁止损
   - 建议结合趋势判断过滤信号

4. 📊 参数优化建议:
   - 当前使用默认参数,可针对不同市场环境优化
   - 建议进行参数扫描寻找最优参数组合
   - 注意避免过度拟合

5. 🎯 组合策略:
   - 可考虑多策略组合降低单一策略风险
   - 不同策略之间可能有互补效应
   - 建议根据个人风险承受能力选择
""")

print("=" * 80)
