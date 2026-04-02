import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class BiasDivergenceStrategy:
    def __init__(self, data, short_period=6, lookback_period=15, stop_loss=0.08, take_profit=0.20):
        self.data = data.copy()
        self.short_period = short_period
        self.lookback_period = lookback_period
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/bias/bias_divergence"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_bias(self):
        """计算BIAS指标"""
        # 计算移动平均线
        self.data['ma_short'] = self.data['close'].rolling(self.short_period).mean()
        
        # 计算BIAS
        self.data['bias_short'] = (self.data['close'] - self.data['ma_short']) / self.data['ma_short'] * 100
        
        # 计算最高价和最低价的移动窗口
        self.data['high_rolling'] = self.data['high'].rolling(self.lookback_period).max()
        self.data['low_rolling'] = self.data['low'].rolling(self.lookback_period).min()
        
        # 计算BIAS的移动窗口极值
        self.data['bias_high_rolling'] = self.data['bias_short'].rolling(self.lookback_period).max()
        self.data['bias_low_rolling'] = self.data['bias_short'].rolling(self.lookback_period).min()
        
        return self.data
    
    def detect_divergence(self):
        """检测背离现象"""
        self.data['top_divergence'] = False
        self.data['bottom_divergence'] = False
        
        for i in range(self.lookback_period, len(self.data)):
            # 顶背离检测：价格创新高，但BIAS没有创新高
            if (self.data['high'].iloc[i] == self.data['high_rolling'].iloc[i] and 
                self.data['bias_short'].iloc[i]< self.data['bias_high_rolling'].iloc[i]):
                self.data.loc[self.data.index[i], 'top_divergence'] = True
            
            # 底背离检测：价格创新低，但BIAS没有创新低
            if (self.data['low'].iloc[i] == self.data['low_rolling'].iloc[i] and 
                self.data['bias_short'].iloc[i] >self.data['bias_low_rolling'].iloc[i]):
                self.data.loc[self.data.index[i], 'bottom_divergence'] = True
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 买入信号：底背离
        self.data.loc[self.data['bottom_divergence'], 'signal'] = 1
        
        # 卖出信号：顶背离
        self.data.loc[self.data['top_divergence'], 'signal'] = -1
        
        return self.data
    
    def backtest(self):
        """执行回测"""
        self.data['position'] = 0
        self.data['strategy_returns'] = 0
        self.data['stop_loss_level'] = 0.0
        self.data['take_profit_level'] = 0.0
        
        position = 0
        entry_price = 0
        trailing_stop = 0
        
        for i in range(len(self.data)):
            # 买入信号
            if self.data['signal'].iloc[i] == 1 and position == 0:
                position = 1
                entry_price = self.data['close'].iloc[i]
                trailing_stop = entry_price * (1 - self.stop_loss)
                self.data.loc[self.data.index[i], 'stop_loss_level'] = trailing_stop
                self.data.loc[self.data.index[i], 'take_profit_level'] = entry_price * (1 + self.take_profit)
            
            # 动态移动止损
            if position == 1:
                if self.data['close'].iloc[i] > entry_price * 1.03:
                    new_trailing_stop = max(trailing_stop, self.data['close'].iloc[i] * 0.98)
                    trailing_stop = new_trailing_stop
                    self.data.loc[self.data.index[i], 'stop_loss_level'] = trailing_stop
            
            # 止损检查
            if position == 1 and self.data['low'].iloc[i]< trailing_stop:
                position = 0
                self.data.loc[self.data.index[i], 'signal'] = -1
            
            # 止盈检查
            if position == 1 and self.data['high'].iloc[i] >self.data['take_profit_level'].iloc[i]:
                position = 0
                self.data.loc[self.data.index[i], 'signal'] = -1
            
            # 卖出信号
            elif self.data['signal'].iloc[i] == -1 and position == 1:
                position = 0
            
            self.data.loc[self.data.index[i], 'position'] = position
        
        # 计算收益率
        self.data['returns'] = self.data['close'].pct_change()
        self.data['strategy_returns'] = self.data['returns'] * self.data['position'].shift(1)
        
        # 计算累计收益率
        self.data['cumulative_returns'] = (1 + self.data['strategy_returns']).cumprod()
        self.data['benchmark_returns'] = (1 + self.data['returns']).cumprod()
        
        return self.data
    
    def calculate_metrics(self):
        """计算回测指标"""
        total_return = (self.data['cumulative_returns'].iloc[-1] - 1) * 100
        annualized_return = (1 + total_return/100) ** (252/len(self.data)) - 1
        
        daily_returns = self.data['strategy_returns'].dropna()
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() >0 else 0
        
        cumulative = self.data['cumulative_returns']
        drawdown = (cumulative / cumulative.cummax() - 1) * 100
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
                trades.append((exit_price - entry_price) / entry_price)
                position = 0
        
        win_rate = len([t for t in trades if t >0]) / len(trades) * 100 if trades else 0
        profit_loss_ratio = np.mean([t for t in trades if t >0]) / np.mean([abs(t) for t in trades if t <0]) if trades else 0
        
        self.metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_trades': len(trades),
            'average_holding_days': len(self.data) / len(trades) if trades else 0
        }
        
        return self.metrics
    
    def plot_results(self):
        """绘制回测结果"""
        plt.figure(figsize=(16, 15))
        
        plt.subplot(4, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300指数', color='blue', linewidth=1.5)
        plt.plot(self.data.index, self.data['ma_short'], label=f'{self.short_period}日均线', color='red', linewidth=1.2)
        
        # 标记背离点
        plt.scatter(self.data[self.data['top_divergence']].index, self.data[self.data['top_divergence']]['high'], 
                   marker='o', color='red', s=80, label='顶背离')
        plt.scatter(self.data[self.data['bottom_divergence']].index, self.data[self.data['bottom_divergence']]['low'], 
                   marker='o', color='green', s=80, label='底背离')
        
        # 标记交易信号
        plt.scatter(self.data[self.data['signal'] == 1].index, self.data[self.data['signal'] == 1]['close'], 
                   marker='^', color='green', s=100, label='买入信号')
        plt.scatter(self.data[self.data['signal'] == -1].index, self.data[self.data['signal'] == -1]['close'], 
                   marker='v', color='red', s=100, label='卖出信号')
        
        plt.title('BIAS背离策略回测')
        plt.legend()
        plt.grid(True)
        
        plt.subplot(4, 1, 2)
        plt.plot(self.data.index, self.data['bias_short'], label='BIAS(6日)', color='purple', linewidth=1.5)
        plt.plot(self.data.index, self.data['bias_high_rolling'], label='BIAS近期高点', color='red', linestyle='--', linewidth=1)
        plt.plot(self.data.index, self.data['bias_low_rolling'], label='BIAS近期低点', color='green', linestyle='--', linewidth=1)
        plt.title('BIAS指标与近期极值')
        plt.legend()
        plt.grid(True)
        
        plt.subplot(4, 1, 3)
        plt.plot(self.data.index, self.data['high_rolling'], label='近期最高价', color='red', linewidth=1.2)
        plt.plot(self.data.index, self.data['low_rolling'], label='近期最低价', color='green', linewidth=1.2)
        plt.title('价格近期极值')
        plt.legend()
        plt.grid(True)
        
        plt.subplot(4, 1, 4)
        plt.plot(self.data.index, self.data['cumulative_returns'], label='策略累计收益', color='blue', linewidth=1.5)
        plt.plot(self.data.index, self.data['benchmark_returns'], label='基准收益', color='gray', linewidth=1.2)
        plt.title('策略收益对比')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/bias_divergence_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()

def generate_hs300_data():
    """生成模拟的沪深300数据（近5年）"""
    np.random.seed(42)
    
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=5*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 基础价格趋势
    base_price = 4000
    trend = np.linspace(0, 0.4, len(dates))
    
    # 添加季节性和周期性波动
    seasonal = 0.04 * np.sin(np.linspace(0, 10*np.pi, len(dates)))
    cyclic = 0.03 * np.cos(np.linspace(0, 5*np.pi, len(dates)))
    
    # 添加随机波动
    volatility = np.random.normal(0, 0.01, len(dates))
    
    # 计算价格
    prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))
    
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
    
    return data

if __name__ == "__main__":
    # 生成数据
    data = generate_hs300_data()
    
    # 创建策略实例
    strategy = BiasDivergenceStrategy(data, short_period=6, lookback_period=20)
    
    # 计算指标
    strategy.calculate_bias()
    
    # 检测背离
    strategy.detect_divergence()
    
    # 生成信号
    strategy.generate_signals()
    
    # 执行回测
    strategy.backtest()
    
    # 计算指标
    metrics = strategy.calculate_metrics()
    
    # 绘制结果
    strategy.plot_results()
    
    # 打印结果
    print("=== BIAS背离策略回测结果 ===")
    print(f"总收益率: {metrics['total_return']:.2f}%")
    print(f"年化收益率: {metrics['annualized_return']:.2f}%")
    print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
    print(f"最大回撤: {metrics['max_drawdown']:.2f}%")
    print(f"胜率: {metrics['win_rate']:.2f}%")
    print(f"盈亏比: {metrics['profit_loss_ratio']:.2f}")
    print(f"总交易次数: {metrics['total_trades']}")
    print(f"平均持仓天数: {metrics['average_holding_days']:.1f}")
    
    # 统计背离次数
    top_divergences = strategy.data['top_divergence'].sum()
    bottom_divergences = strategy.data['bottom_divergence'].sum()
    print(f"\n背离统计：")
    print(f"顶背离次数: {top_divergences}")
    print(f"底背离次数: {bottom_divergences}")
