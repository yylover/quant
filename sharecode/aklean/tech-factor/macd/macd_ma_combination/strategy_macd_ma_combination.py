import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class MACDMACombinationStrategy:
    def __init__(self, data, fast_period=12, slow_period=26, signal_period=9, ma_period=50):
        self.data = data.copy()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.ma_period = ma_period
        self.position = 0
        self.initial_capital = 100000
        self.capital = self.initial_capital
        self.shares = 0
        
    def calculate_indicators(self):
        """计算MACD和均线指标"""
        # 计算均线
        self.data['ma'] = self.data['close'].rolling(window=self.ma_period).mean()
        
        # 计算MACD指标
        alpha_fast = 2 / (self.fast_period + 1)
        ema_fast = self.data['close'].ewm(alpha=alpha_fast, adjust=False).mean()
        
        alpha_slow = 2 / (self.slow_period + 1)
        ema_slow = self.data['close'].ewm(alpha=alpha_slow, adjust=False).mean()
        
        self.data['dif'] = ema_fast - ema_slow
        
        alpha_signal = 2 / (self.signal_period + 1)
        self.data['dea'] = self.data['dif'].ewm(alpha=alpha_signal, adjust=False).mean()
        
        self.data['macd_hist'] = self.data['dif'] - self.data['dea']
        
        # 判断价格与均线的关系
        self.data['price_above_ma'] = self.data['close'] > self.data['ma']
        self.data['price_below_ma'] = self.data['close']< self.data['ma']
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(1, len(self.data)):
            # 买入信号：价格在均线上方且MACD金叉
            if (self.data['price_above_ma'].iloc[i] and
                self.data['dif'].iloc[i] >self.data['dea'].iloc[i] and 
                self.data['dif'].iloc[i-1] <= self.data['dea'].iloc[i-1]):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 卖出信号：价格在均线下方且MACD死叉
            elif (self.data['price_below_ma'].iloc[i] and
                  self.data['dif'].iloc[i]< self.data['dea'].iloc[i] and 
                  self.data['dif'].iloc[i-1] >=self.data['dea'].iloc[i-1]):
                self.data.loc[self.data.index[i], 'signal'] = -1
            
            # 额外卖出信号：价格跌破均线且有持仓
            elif (self.position == 1 and
                  self.data['price_below_ma'].iloc[i] and 
                  not self.data['price_below_ma'].iloc[i-1]):
                self.data.loc[self.data.index[i], 'signal'] = -1
    
    def backtest(self):
        """回测策略"""
        self.data['position'] = 0
        self.data['capital'] = self.initial_capital
        self.data['shares'] = 0
        self.data['total_value'] = self.initial_capital
        
        capital = self.initial_capital
        shares = 0
        self.position = 0
        
        for i in range(len(self.data)):
            # 更新持仓状态
            self.position = 1 if shares > 0 else 0
            
            # 执行交易信号
            if self.data['signal'].iloc[i] == 1 and capital >0:
                # 买入
                shares = capital / self.data['close'].iloc[i]
                capital = 0
            elif self.data['signal'].iloc[i] == -1 and shares > 0:
                # 卖出
                capital = shares * self.data['close'].iloc[i]
                shares = 0
            
            # 更新状态
            self.data.loc[self.data.index[i], 'position'] = 1 if shares > 0 else 0
            self.data.loc[self.data.index[i], 'capital'] = capital
            self.data.loc[self.data.index[i], 'shares'] = shares
            self.data.loc[self.data.index[i], 'total_value'] = capital + shares * self.data['close'].iloc[i]
    
    def calculate_returns(self):
        """计算收益率"""
        self.data['daily_return'] = self.data['total_value'].pct_change()
        self.data['cumulative_return'] = (1 + self.data['daily_return']).cumprod()
    
    def calculate_metrics(self):
        """计算绩效指标"""
        total_return = (self.data['total_value'].iloc[-1] / self.initial_capital - 1) * 100
        annualized_return = ((1 + total_return / 100) ** (252 / len(self.data)) - 1) * 100
        
        # 计算夏普比率
        daily_returns = self.data['daily_return'].dropna()
        if len(daily_returns) > 0:
            sharpe_ratio = np.sqrt(252) * daily_returns.mean() / (daily_returns.std() if daily_returns.std() != 0 else 1)
        else:
            sharpe_ratio = 0
        
        # 计算最大回撤
        cumulative = self.data['cumulative_return']
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min()
        
        # 计算胜率
        trades = []
        position = 0
        entry_price = 0
        
        for i in range(len(self.data)):
            if self.data['signal'].iloc[i] == 1 and position == 0:
                entry_price = self.data['close'].iloc[i]
                position = 1
            elif self.data['signal'].iloc[i] == -1 and position == 1:
                exit_price = self.data['close'].iloc[i]
                profit = (exit_price - entry_price) / entry_price * 100
                trades.append(profit)
                position = 0
        
        win_rate = len([t for t in trades if t > 0]) / len(trades) * 100 if trades else 0
        
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(trades)
        }
        
        return metrics
    
    def plot_results(self):
        """绘制回测结果"""
        plt.figure(figsize=(16, 12))
        
        # 绘制价格、均线和持仓
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='收盘价', color='blue', linewidth=1.5)
        plt.plot(self.data.index, self.data['ma'], label=f'{self.ma_period}日均线', color='red', linewidth=1.2)
        plt.plot(self.data.index, self.data['close'] * self.data['position'], label='持仓价格', color='green', linewidth=1.5)
        plt.title('MACD与均线结合策略回测结果', fontsize=14, fontweight='bold')
        plt.ylabel('价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 绘制MACD指标
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['dif'], label='DIF', color='blue', linewidth=1.2)
        plt.plot(self.data.index, self.data['dea'], label='DEA', color='red', linewidth=1.2)
        plt.bar(self.data.index, self.data['macd_hist'], label='MACD柱', color='green', alpha=0.5)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.ylabel('MACD值', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 绘制资金曲线
        plt.subplot(3, 1, 3)
        plt.plot(self.data.index, self.data['total_value'], label='总资产', color='green', linewidth=1.5)
        plt.plot(self.data.index, [self.initial_capital] * len(self.data), label='初始资金', color='gray', linestyle='--')
        plt.ylabel('资金', fontsize=12)
        plt.xlabel('日期', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        
        # 保存图表
        output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/macd/macd_ma_combination"
        os.makedirs(output_dir, exist_ok=True)
        
        plt.savefig(f"{output_dir}/macd_ma_combination_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_backtest(self):
        """运行完整回测"""
        self.calculate_indicators()
        self.generate_signals()
        self.backtest()
        self.calculate_returns()
        
        metrics = self.calculate_metrics()
        self.plot_results()
        
        # 保存回测数据
        output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/macd/macd_ma_combination"
        self.data.to_csv(f"{output_dir}/macd_ma_combination_backtest.csv")
        
        return metrics

def generate_hs300_data():
    """生成模拟的沪深300数据"""
    np.random.seed(42)
    
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=5*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    base_price = 4000
    trend = np.linspace(0, 0.5, len(dates))
    seasonal = 0.05 * np.sin(np.linspace(0, 10*np.pi, len(dates)))
    cyclic = 0.03 * np.cos(np.linspace(0, 5*np.pi, len(dates)))
    volatility = np.random.normal(0, 0.01, len(dates))
    
    prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
        'high': prices * (1 + np.random.normal(0.003, 0.005, len(dates))),
        'low': prices * (1 + np.random.normal(-0.003, 0.005, len(dates))),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, len(dates))
    })
    
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    data.set_index('date', inplace=True)
    
    return data

if __name__ == "__main__":
    # 生成数据
    hs300_data = generate_hs300_data()
    
    # 创建策略实例
    strategy = MACDMACombinationStrategy(hs300_data)
    
    # 运行回测
    metrics = strategy.run_backtest()
    
    # 输出结果
    print("=== MACD与均线结合策略回测结果 ===")
    print(f"总收益率: {metrics['total_return']:.2f}%")
    print(f"年化收益率: {metrics['annualized_return']:.2f}%")
    print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
    print(f"最大回撤: {metrics['max_drawdown']:.2f}%")
    print(f"胜率: {metrics['win_rate']:.2f}%")
    print(f"总交易次数: {metrics['total_trades']}")
