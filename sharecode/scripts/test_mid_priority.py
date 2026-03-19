"""
测试中优先级策略的信号生成
"""
import sys
sys.path.insert(0, '/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode')

import pandas as pd
from sharecode.strategies.mean_reversion import (
    atr_reversion_signals,
    roc_reversion_signals,
    psar_reversion_signals,
)

# 加载数据
print("加载数据...")
df = pd.read_csv('data/hs300_daily.csv')
print(f"数据行数: {len(df)}")

# 测试 ATR 回归
print("\n测试 ATR 回归...")
try:
    close, entries, exits = atr_reversion_signals(
        df,
        window=14,
        atr_multiplier=2.0
    )
    print(f"  数据长度: {len(close)}")
    print(f"  买入信号数量: {entries.sum()}")
    print(f"  卖出信号数量: {exits.sum()}")
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

# 测试 ROC 回归
print("\n测试 ROC 回归...")
try:
    close, entries, exits = roc_reversion_signals(
        df,
        window=12,
        low=-0.08,
        high=0.08
    )
    print(f"  数据长度: {len(close)}")
    print(f"  买入信号数量: {entries.sum()}")
    print(f"  卖出信号数量: {exits.sum()}")
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

# 测试 PSAR 逆向
print("\n测试 PSAR 逆向...")
try:
    close, entries, exits = psar_reversion_signals(
        df,
        af=0.02,
        max_af=0.2,
        lookback=3
    )
    print(f"  数据长度: {len(close)}")
    print(f"  买入信号数量: {entries.sum()}")
    print(f"  卖出信号数量: {exits.sum()}")
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成!")
