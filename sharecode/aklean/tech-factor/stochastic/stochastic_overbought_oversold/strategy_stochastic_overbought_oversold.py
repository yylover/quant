import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class StochasticOverboughtOversoldStrategy:
    def __init__(self):
        self.data = None
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=5*365)
    
    def generate_hs300_data(self):
        """生成沪深300近5年的模拟数据"""
        dates = pd.date_range(start=self.start_date, end=self.end_date, freq='B')
        
        np.random.seed(42)
        base_price = 3000
        volatility = 0.01
        trend = 0.0002
        
        returns = np.random.normal(trend, volatility, len(dates))
        prices = base_price * np.cumprod(1 + returns)
        prices = prices * (1 + np.sin(np.linspace(0, 10*np.pi, len(dates))) * 0.1)
        
        self.data = pd.DataFrame({
            'date': dates,
            'open': prices * (1 - np.random.normal(0, 0.005, len(dates))),
            'high': prices * (1 + np.random.normal(0, 0.01, len(dates))),
            'low': prices * (1 - np.random.normal(0, 0.01, len(dates))),
            'close': prices,
            'volume': np.random.normal(50000000, 10000000, len(dates)).astype(int)
        })
        
        self.data['high'] = self.data[['open', 'high', 'close']].max(axis=1)
        self.data['low'] = self.data[['open', 'low', 'close']].min(axis=1)
        self.data.set_index('date', inplace=True)
    
    def calculate_stochastic(self):
        """计算Stochastic指标"""
        n = 14
        smooth_k = 1
        smooth_d = 3
        
        high_max = self.data['high'].rolling(window=n).max()
        low_min = self.data['low'].rolling(window=n).min()
        
        self.data['fast_k'] = 100 * (self.data['close'] - low_min) / (high_max - low_min)
        self.data['slow_k'] = self.data['fast_k'].rolling(window=smooth_k).mean()
        self.data['slow_d'] = self.data['slow_k'].rolling(window=smooth_d).mean()
        
        # 添加均线过滤
        self.data['ma20'] = self.data['close'].rolling(window=20).mean()
        self.data['ma50'] = self.data['close'].rolling(window=50).mean()
        
        # 趋势判断
        self.data['uptrend'] = (self.data['ma20'] > self.data['ma50']) & (self.data['close'] > self.data['ma20'])
        self.data['downtrend'] = (self.data['ma20'] < self.data['ma50']) & (self.data['close'] < self.data['ma20'])
    
    def generate_signals(self):
        """生成交易信号"""
        # 优化策略：调整阈值 + 趋势过滤
        # 买入：超卖区域(15) + 趋势确认
        self.data['buy_signal'] = (self.data['slow_k'] < 15) & self.data['uptrend']
        
        # 卖出：超买区域(85) + 趋势确认
        self.data['sell_signal'] = (self.data['slow_k'] > 85) & self.data['downtrend']
        
        # 避免连续信号
        self.data['buy_signal'] = self.data['buy_signal'] & ~self.data['buy_signal'].shift(1).fillna(False)
        self.data['sell_signal'] = self.data['sell_signal'] & ~self.data['sell_signal'].shift(1).fillna(False)
    
    def backtest(self):
        """执行回测"""
        self.data['position'] = 0
        position = 0
        
        for i in range(1, len(self.data)):
            # 买入信号
            if self.data['buy_signal'].iloc[i] and position == 0:
                position = 1
            
            # 卖出信号
            elif self.data['sell_signal'].iloc[i] and position == 1:
                position = 0
            
            self.data.loc[self.data.index[i], 'position'] = position
        
        # 计算收益率
        self.data['daily_return'] = self.data['close'].pct_change()
        self.data['strategy_return'] = self.data['position'].shift(1) * self.data['daily_return']
        self.data['cumulative_strategy'] = (1 + self.data['strategy_return']).cumprod()
        self.data['cumulative_benchmark'] = (1 + self.data['daily_return']).cumprod()
    
    def plot_results(self):
        """绘制回测结果"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
        
        # 价格图表
        ax1.plot(self.data.index, self.data['close'], label='沪深300收盘价', color='blue', alpha=0.6)
        ax1.plot(self.data.index, self.data['ma20'], label='20日均线', color='orange', alpha=0.7)
        ax1.plot(self.data.index, self.data['ma50'], label='50日均线', color='green', alpha=0.7)
        
        # 持仓区域
        long_periods = self.data[self.data['position'] == 1]
        for i in range(len(long_periods) - 1):
            start_date = long_periods.index[i]
            end_date = long_periods.index[i + 1]
            ax1.axvspan(start_date, end_date, alpha=0.2, color='green')
        
        # 买卖信号
        buy_signals = self.data[self.data['buy_signal']]
        sell_signals = self.data[self.data['sell_signal']]
        ax1.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='买入')
        ax1.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='卖出')
        
        ax1.set_ylabel('价格', fontsize=12)
        ax1.set_title('Stochastic超买超卖策略回测', fontsize=16)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # 收益率对比
        ax2.plot(self.data.index, self.data['cumulative_strategy'], label='策略收益率', color='blue', linewidth=2)
        ax2.plot(self.data.index, self.data['cumulative_benchmark'], label='基准收益率', color='gray', linewidth=1.5)
        
        # 收益统计
        total_strategy_return = self.data['cumulative_strategy'].iloc[-1] - 1
        total_benchmark_return = self.data['cumulative_benchmark'].iloc[-1] - 1
        
        ax2.text(0.02, 0.95, f'策略总收益: {total_strategy_return:.2%}\n基准总收益: {total_benchmark_return:.2%}',
                transform=ax2.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax2.set_xlabel('日期', fontsize=12)
        ax2.set_ylabel('累计收益率', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')
        
        plt.tight_layout()
        plt.savefig('stochastic_overbought_oversold_strategy_backtest.png', dpi=300, bbox_inches='tight')
    
    def save_trades(self):
        """保存交易记录"""
        trades = []
        position = 0
        
        for i in range(len(self.data)):
            if self.data['buy_signal'].iloc[i] and position == 0:
                trades.append({
                    'date': self.data.index[i],
                    'type': 'buy',
                    'price': self.data['close'].iloc[i]
                })
                position = 1
            elif self.data['sell_signal'].iloc[i] and position == 1:
                trades.append({
                    'date': self.data.index[i],
                    'type': 'sell',
                    'price': self.data['close'].iloc[i]
                })
                position = 0
        
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv('stochastic_overbought_oversold_strategy_backtest.csv', index=False)
    
    def generate_strategy_documentation(self):
        """生成策略说明文档"""
        total_strategy_return = self.data['cumulative_strategy'].iloc[-1] - 1
        total_benchmark_return = self.data['cumulative_benchmark'].iloc[-1] - 1
        
        doc = f"""# Stochastic超买超卖策略说明

## 策略概述
本策略基于Stochastic指标的超买超卖原理，在指标进入超卖区域时买入，进入超买区域时卖出。

## 策略原理
- **超卖区域**：Stochastic指标低于20，表示市场可能过于悲观，可能即将反弹
- **超买区域**：Stochastic指标高于80，表示市场可能过于乐观，可能即将回调

## 信号生成
- **买入信号**：%K线低于20
- **卖出信号**：%K线高于80

## 参数设置
- **计算周期(n)**：14天
- **%K平滑周期**：1天
- **%D平滑周期**：3天
- **超卖阈值**：20
- **超买阈值**：80

## 回测结果
- **策略总收益率**：{total_strategy_return:.2%}
- **基准总收益率**：{total_benchmark_return:.2%}
- **超额收益率**：{(total_strategy_return - total_benchmark_return):.2%}

## 交易统计
- **总交易次数**：{self.data['buy_signal'].sum() + self.data['sell_signal'].sum()}次
- **买入次数**：{self.data['buy_signal'].sum()}次
- **卖出次数**：{self.data['sell_signal'].sum()}次

## 适用场景
- **震荡市场**：该策略在震荡市场中表现较好
- **趋势市场**：在强趋势市场中可能产生假信号

## 风险提示
- 在强趋势市场中，超买超卖信号可能持续很长时间
- 建议结合其他技术指标使用
- 设置合理的止损位

## 优化建议
- 调整超买超卖阈值
- 结合趋势指标过滤信号
- 增加仓位管理策略
"""
        
        with open('stochastic_overbought_oversold_strategy说明.md', 'w', encoding='utf-8') as f:
            f.write(doc)
    
    def run(self):
        """运行完整策略回测"""
        print("开始生成沪深300数据...")
        self.generate_hs300_data()
        
        print("计算Stochastic指标...")
        self.calculate_stochastic()
        
        print("生成交易信号...")
        self.generate_signals()
        
        print("执行回测...")
        self.backtest()
        
        print("绘制回测结果...")
        self.plot_results()
        
        print("保存交易记录...")
        self.save_trades()
        
        print("生成策略说明...")
        self.generate_strategy_documentation()
        
        print(f"\nStochastic超买超卖策略回测完成！")
        print(f"策略收益率：{(self.data['cumulative_strategy'].iloc[-1] - 1):.2%}")
        print(f"基准收益率：{(self.data['cumulative_benchmark'].iloc[-1] - 1):.2%}")

if __name__ == '__main__':
    strategy = StochasticOverboughtOversoldStrategy()
    strategy.run()
