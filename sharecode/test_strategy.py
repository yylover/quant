import pandas as pd
import numpy as np
import sys
import os

# 添加路径
sys.path.append('/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/atr')

# 生成测试数据
np.random.seed(42)
end_date = pd.Timestamp('2026-04-01')
start_date = end_date - pd.Timedelta(days=5*365)
dates = pd.date_range(start=start_date, end=end_date, freq='B')
base_price = 4000
trend = np.linspace(0, 0.1, len(dates))
volatility = np.random.normal(0, 0.015, len(dates))
prices = base_price * (1 + trend + np.cumsum(volatility))

data = pd.DataFrame({
    'date': dates,
    'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
    'high': prices * (1 + np.random.normal(0.003, 0.005, len(dates))),
    'low': prices * (1 + np.random.normal(-0.003, 0.005, len(dates))),
    'close': prices,
    'volume': np.random.randint(10000000, 50000000, len(dates))
})
data['high'] = data[['open', 'high', 'close']].max(axis=1)
data['low'] = data[['open', 'low', 'close']].min(axis=1)
data.set_index('date', inplace=True)

print('数据生成完成')
print(f'数据长度: {len(data)}')

# 测试突破策略
from atr_breakout.strategy_atr_breakout import AtrBreakoutStrategy
print('\n运行ATR突破策略...')
strategy = AtrBreakoutStrategy(data)
metrics = strategy.run_strategy()
print(f'总收益率: {metrics['总收益率']:.2f}%')
print(f'年化收益率: {metrics['年化收益率']:.2f}%')
print(f'最大回撤: {metrics['最大回撤']:.2f}%')
print(f'胜率: {metrics['胜率']:.2f}%')
print(f'盈亏比: {metrics['盈亏比']:.2f}')
print(f'总交易次数: {metrics['总交易次数']}')
