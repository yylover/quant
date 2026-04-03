import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class StochasticDivergenceStrategy:
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
    
    def identify_divergences(self):
        """识别背离信号"""
        # 看涨背离：价格创出新低，但Stochastic指标未创出新低
        self.data['price_low'] = self.data['close'].rolling(window=20).min() == self.data['close']
        self.data['stoch_low'] = self.data['slow_k'].rolling(window=20).min() == self.data['slow_k']
        self.data['bullish_divergence'] = self.data['price_low'] & ~self.data['stoch_low']
        
        # 看跌背离：价格创出新高，但Stochastic指标未创出新高
        self.data['price_high'] = self.data['close'].rolling(window=20).max() == self.data['close']
        self.data['stoch_high'] = self.data['slow_k'].rolling(window=20).max() == self.data['slow_k']
        self.data['bearish_divergence'] = self.data['price_high'] & ~self.data['stoch_high']
    
    def generate_signals(self):
        """生成交易信号"""
        # 背离策略
        # 看涨背离买入，看跌背离卖出
        self.data['buy_signal'] = self.data['bullish_divergence'] & (self.data['slow_k'] < 30)
        self.data['sell_signal'] = self.data['bearish_divergence'] & (self.data['slow_k'] > 70)
        
        # 避免连续信号
        self.data['buy_signal'] = self.data['buy_signal'] & ~self.data['buy_signal'].shift(1).fillna(False)
        self.data['sell_signal'] = self.data['sell_signal'] & ~self.data['sell_signal'].shift(1).fillna(False)
    
    def backtest(self):
        """执行回测"""
        self.data['position'] = 0
        position = 0
        
        for i in range(1, len(self.data)):
            # 买入信号：看涨背离
            if self.data['buy_signal'].iloc[i] and position == 0:
                position = 1
            
            # 卖出信号：看跌背离
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
        
        # 背离信号
        bullish_div = self.data[self.data['bullish_divergence']]
        bearish_div = self.data[self.data['bearish_divergence']]
        ax1.scatter(bullish_div.index, bullish_div['close'], marker='o', color='orange', s=80, label='看涨背离')
        ax1.scatter(bearish_div.index, bearish_div['close'], marker='o', color='purple', s=80, label='看跌背离')
        
        ax1.set_ylabel('价格', fontsize=12)
        ax1.set_title('Stochastic背离策略回测', fontsize=16)
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
        plt.savefig('stochastic_divergence_strategy_backtest.png', dpi=300, bbox_inches='tight')
    
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
        trades_df.to_csv('stochastic_divergence_strategy_backtest.csv', index=False)
    
    def generate_strategy_documentation(self):
        """生成策略说明文档"""
        total_strategy_return = self.data['cumulative_strategy'].iloc[-1] - 1
        total_benchmark_return = self.data['cumulative_benchmark'].iloc[-1] - 1
        
        doc = f"""# Stochastic背离策略说明

## 策略概述
本策略基于Stochastic指标与价格之间的背离关系，当出现看涨背离时买入，出现看跌背离时卖出。

## 策略原理
- **看涨背离**：价格创出新低，但Stochastic指标未创出新低，预示可能反转上涨
- **看跌背离**：价格创出新高，但Stochastic指标未创出新高，预示可能反转下跌

## 信号生成
- **买入信号**：看涨背离 + Stochastic指标低于30
- **卖出信号**：看跌背离 + Stochastic指标高于70

## 参数设置
- **计算周期(n)**：14天
- **%K平滑周期**：1天
- **%D平滑周期**：3天
- **背离检测窗口**：20天
- **超卖阈值**：30
- **超买阈值**：70

## 回测结果
- **策略总收益率**：{total_strategy_return:.2%}
- **基准总收益率**：{total_benchmark_return:.2%}
- **超额收益率**：{(total_strategy_return - total_benchmark_return):.2%}

## 交易统计
- **总交易次数**：{self.data['buy_signal'].sum() + self.data['sell_signal'].sum()}次
- **买入次数**：{self.data['buy_signal'].sum()}次
- **卖出次数**：{self.data['sell_signal'].sum()}次
- **看涨背离次数**：{self.data['bullish_divergence'].sum()}次
- **看跌背离次数**：{self.data['bearish_divergence'].sum()}次

## 适用场景
- **趋势反转**：该策略在趋势反转时表现较好
- **震荡市场**：在震荡市场中也能捕捉转折点

## 风险提示
- 背离信号出现频率较低
- 需要较长时间才能确认背离
- 建议结合其他指标使用

## 优化建议
- 调整背离检测窗口大小
- 结合成交量确认背离
- 增加止损机制
"""
        
        with open('stochastic_divergence_strategy说明.md', 'w', encoding='utf-8') as f:
            f.write(doc)
    
    def run(self):
        """运行完整策略回测"""
        print("开始生成沪深300数据...")
        self.generate_hs300_data()
        
        print("计算Stochastic指标...")
        self.calculate_stochastic()
        
        print("识别背离信号...")
        self.identify_divergences()
        
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
        
        print(f"\nStochastic背离策略回测完成！")
        print(f"策略收益率：{(self.data['cumulative_strategy'].iloc[-1] - 1):.2%}")
        print(f"基准收益率：{(self.data['cumulative_benchmark'].iloc[-1] - 1):.2%}")

if __name__ == '__main__':
    strategy = StochasticDivergenceStrategy()
    strategy.run()
