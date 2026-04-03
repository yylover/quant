import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class StochasticOptimizedStrategy:
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
    
    def calculate_indicators(self):
        """计算技术指标"""
        # Stochastic指标
        n = 14
        smooth_k = 1
        smooth_d = 3
        
        high_max = self.data['high'].rolling(window=n).max()
        low_min = self.data['low'].rolling(window=n).min()
        
        self.data['fast_k'] = 100 * (self.data['close'] - low_min) / (high_max - low_min)
        self.data['slow_k'] = self.data['fast_k'].rolling(window=smooth_k).mean()
        self.data['slow_d'] = self.data['slow_k'].rolling(window=smooth_d).mean()
        
        # 移动平均线
        self.data['ma20'] = self.data['close'].rolling(window=20).mean()
        self.data['ma50'] = self.data['close'].rolling(window=50).mean()
        
        # MACD指标
        self.data['ema12'] = self.data['close'].ewm(span=12, adjust=False).mean()
        self.data['ema26'] = self.data['close'].ewm(span=26, adjust=False).mean()
        self.data['macd_line'] = self.data['ema12'] - self.data['ema26']
        self.data['signal_line'] = self.data['macd_line'].ewm(span=9, adjust=False).mean()
        self.data['macd_histogram'] = self.data['macd_line'] - self.data['signal_line']
        
        # 趋势判断
        self.data['uptrend'] = (self.data['ma20'] > self.data['ma50']) & (self.data['close'] > self.data['ma20'])
        self.data['downtrend'] = (self.data['ma20'] < self.data['ma50']) & (self.data['close'] < self.data['ma20'])
    
    def identify_divergences(self):
        """识别背离信号"""
        self.data['price_low'] = self.data['close'].rolling(window=20).min() == self.data['close']
        self.data['stoch_low'] = self.data['slow_k'].rolling(window=20).min() == self.data['slow_k']
        self.data['bullish_divergence'] = self.data['price_low'] & ~self.data['stoch_low']
        
        self.data['price_high'] = self.data['close'].rolling(window=20).max() == self.data['close']
        self.data['stoch_high'] = self.data['slow_k'].rolling(window=20).max() == self.data['slow_k']
        self.data['bearish_divergence'] = self.data['price_high'] & ~self.data['stoch_high']
    
    def generate_signals(self):
        """生成交易信号"""
        # 优化策略：结合多种指标
        # 买入信号：超卖区域 + 黄金交叉 + 看涨背离 + 趋势确认
        self.data['buy_signal'] = (
            (self.data['slow_k'] < 20) &  # 超卖
            ((self.data['slow_k'] > self.data['slow_d']) & (self.data['slow_k'].shift(1) <= self.data['slow_d'].shift(1))) &  # 黄金交叉
            (self.data['macd_histogram'] > 0) &  # MACD柱状图为正
            (self.data['close'] > self.data['ma20'])  # 价格在均线上方
        )
        
        # 卖出信号：超买区域 + 死亡交叉 + 看跌背离 + 趋势确认
        self.data['sell_signal'] = (
            (self.data['slow_k'] > 80) &  # 超买
            ((self.data['slow_k'] < self.data['slow_d']) & (self.data['slow_k'].shift(1) >= self.data['slow_d'].shift(1))) &  # 死亡交叉
            (self.data['macd_histogram'] < 0) &  # MACD柱状图为负
            (self.data['close'] < self.data['ma20'])  # 价格在均线下方
        )
        
        # 额外的买入信号：看涨背离
        self.data['buy_signal'] = self.data['buy_signal'] | (
            self.data['bullish_divergence'] & 
            (self.data['slow_k'] < 30) &
            (self.data['macd_histogram'] > 0)
        )
        
        # 额外的卖出信号：看跌背离
        self.data['sell_signal'] = self.data['sell_signal'] | (
            self.data['bearish_divergence'] & 
            (self.data['slow_k'] > 70) &
            (self.data['macd_histogram'] < 0)
        )
        
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
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(16, 20), sharex=True)
        
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
        ax1.set_title('Stochastic优化策略回测', fontsize=16)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # Stochastic指标
        ax2.plot(self.data.index, self.data['slow_k'], label='%K线', color='blue', linewidth=2)
        ax2.plot(self.data.index, self.data['slow_d'], label='%D线', color='red', linewidth=2)
        ax2.axhline(y=80, color='red', linestyle='--', label='超买线(80)')
        ax2.axhline(y=20, color='green', linestyle='--', label='超卖线(20)')
        ax2.fill_between(self.data.index, 80, 100, color='red', alpha=0.1)
        ax2.fill_between(self.data.index, 0, 20, color='green', alpha=0.1)
        ax2.set_ylabel('Stochastic值', fontsize=12)
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')
        
        # MACD指标
        ax3.plot(self.data.index, self.data['macd_line'], label='MACD线', color='blue')
        ax3.plot(self.data.index, self.data['signal_line'], label='信号线', color='red')
        ax3.bar(self.data.index, self.data['macd_histogram'], label='柱状图', color='gray', alpha=0.5)
        ax3.set_ylabel('MACD', fontsize=12)
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper left')
        
        # 收益率对比
        ax4.plot(self.data.index, self.data['cumulative_strategy'], label='策略收益率', color='blue', linewidth=2)
        ax4.plot(self.data.index, self.data['cumulative_benchmark'], label='基准收益率', color='gray', linewidth=1.5)
        
        # 收益统计
        total_strategy_return = self.data['cumulative_strategy'].iloc[-1] - 1
        total_benchmark_return = self.data['cumulative_benchmark'].iloc[-1] - 1
        
        ax4.text(0.02, 0.95, f'策略总收益: {total_strategy_return:.2%}\n基准总收益: {total_benchmark_return:.2%}',
                transform=ax4.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax4.set_xlabel('日期', fontsize=12)
        ax4.set_ylabel('累计收益率', fontsize=12)
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='upper left')
        
        plt.tight_layout()
        plt.savefig('stochastic_optimized_strategy_backtest.png', dpi=300, bbox_inches='tight')
    
    def save_trades(self):
        """保存交易记录"""
        trades = []
        position = 0
        
        for i in range(len(self.data)):
            if self.data['buy_signal'].iloc[i] and position == 0:
                trades.append({
                    'date': self.data.index[i],
                    'type': 'buy',
                    'price': self.data['close'].iloc[i],
                    'slow_k': self.data['slow_k'].iloc[i],
                    'slow_d': self.data['slow_d'].iloc[i],
                    'macd_histogram': self.data['macd_histogram'].iloc[i]
                })
                position = 1
            elif self.data['sell_signal'].iloc[i] and position == 1:
                trades.append({
                    'date': self.data.index[i],
                    'type': 'sell',
                    'price': self.data['close'].iloc[i],
                    'slow_k': self.data['slow_k'].iloc[i],
                    'slow_d': self.data['slow_d'].iloc[i],
                    'macd_histogram': self.data['macd_histogram'].iloc[i]
                })
                position = 0
        
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv('stochastic_optimized_strategy_backtest.csv', index=False)
    
    def generate_strategy_documentation(self):
        """生成策略说明文档"""
        total_strategy_return = self.data['cumulative_strategy'].iloc[-1] - 1
        total_benchmark_return = self.data['cumulative_benchmark'].iloc[-1] - 1
        
        doc = f"""# Stochastic优化策略说明

## 策略概述
本策略是一个综合优化的Stochastic策略，结合了多种技术指标进行多维度确认，提高信号的准确性。

## 策略原理
- **Stochastic指标**：识别超买超卖状态和动量变化
- **移动平均线**：确认趋势方向
- **MACD指标**：确认动量方向
- **背离信号**：识别潜在的趋势反转

## 信号生成

### 买入信号（满足以下任一条件）：
1. **主要买入条件**：
   - Stochastic指标低于20（超卖）
   - %K线上穿%D线（黄金交叉）
   - MACD柱状图为正
   - 价格在20日均线上方

2. **辅助买入条件**：
   - 出现看涨背离
   - Stochastic指标低于30
   - MACD柱状图为正

### 卖出信号（满足以下任一条件）：
1. **主要卖出条件**：
   - Stochastic指标高于80（超买）
   - %K线下穿%D线（死亡交叉）
   - MACD柱状图为负
   - 价格在20日均线下方

2. **辅助卖出条件**：
   - 出现看跌背离
   - Stochastic指标高于70
   - MACD柱状图为负

## 参数设置
- **Stochastic计算周期(n)**：14天
- **%K平滑周期**：1天
- **%D平滑周期**：3天
- **超卖阈值**：20
- **超买阈值**：80
- **移动平均线**：20日、50日
- **MACD参数**：12, 26, 9
- **背离检测窗口**：20天

## 回测结果
- **策略总收益率**：{total_strategy_return:.2%}
- **基准总收益率**：{total_benchmark_return:.2%}
- **超额收益率**：{(total_strategy_return - total_benchmark_return):.2%}

## 交易统计
- **总交易次数**：{self.data['buy_signal'].sum() + self.data['sell_signal'].sum()}次
- **买入次数**：{self.data['buy_signal'].sum()}次
- **卖出次数**：{self.data['sell_signal'].sum()}次

## 适用场景
- **趋势市场**：该策略在趋势市场中表现较好
- **震荡市场**：在震荡市场中也能捕捉转折点

## 优势分析
- **多维度确认**：结合多种指标提高信号准确性
- **趋势过滤**：通过均线过滤趋势方向
- **动量确认**：通过MACD确认动量方向
- **背离识别**：捕捉潜在的趋势反转

## 风险提示
- 参数优化可能导致过拟合
- 市场环境变化可能影响策略表现
- 建议定期重新优化参数

## 后续优化方向
- 结合波动率指标调整参数
- 加入止损和止盈机制
- 优化背离检测算法
"""
        
        with open('stochastic_optimized_strategy说明.md', 'w', encoding='utf-8') as f:
            f.write(doc)
    
    def run(self):
        """运行完整策略回测"""
        print("开始生成沪深300数据...")
        self.generate_hs300_data()
        
        print("计算技术指标...")
        self.calculate_indicators()
        
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
        
        print(f"\nStochastic优化策略回测完成！")
        print(f"策略收益率：{(self.data['cumulative_strategy'].iloc[-1] - 1):.2%}")
        print(f"基准收益率：{(self.data['cumulative_benchmark'].iloc[-1] - 1):.2%}")

if __name__ == '__main__':
    strategy = StochasticOptimizedStrategy()
    strategy.run()
