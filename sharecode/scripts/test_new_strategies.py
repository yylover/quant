"""
测试新增策略的信号生成
"""
import sys
sys.path.insert(0, '/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode')

import pandas as pd
from sharecode.strategies.mean_reversion import (
    macd_reversion_signals,
    bias_reversion_signals,
    bb_width_reversion_signals,
)

# 加载数据
print("加载数据...")
df = pd.read_csv('data/hs300_daily.csv')
print(f"数据行数: {len(df)}")

# 测试 MACD 回归
print("\n测试 MACD 回归...")
try:
    close, entries, exits = macd_reversion_signals(
        df,
        fast=12,
        slow=26,
        signal=9,
        hist_threshold=5.0
    )
    print(f"  数据长度: {len(close)}")
    print(f"  买入信号数量: {entries.sum()}")
    print(f"  卖出信号数量: {exits.sum()}")
    print(f"  收盘价范围: {close.min():.2f} - {close.max():.2f}")
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

# 测试 BIAS 回归
print("\n测试 BIAS 回归...")
try:
    close, entries, exits = bias_reversion_signals(
        df,
        window=20,
        low=-0.03,
        high=0.03
    )
    print(f"  数据长度: {len(close)}")
    print(f"  买入信号数量: {entries.sum()}")
    print(f"  卖出信号数量: {exits.sum()}")
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

# 测试布林带宽度回归
print("\n测试布林带宽度回归...")
try:
    close, entries, exits = bb_width_reversion_signals(
        df,
        window=20,
        n_std=2.0,
        width_percentile=0.1,
        exit_percentile=0.5
    )
    print(f"  数据长度: {len(close)}")
    print(f"  买入信号数量: {entries.sum()}")
    print(f"  卖出信号数量: {exits.sum()}")
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成!")
