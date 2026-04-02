import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def calculate_kdj(data, n=9):
    """计算KDJ指标"""
    low_n = data['low'].rolling(window=n).min()
    high_n = data['high'].rolling(window=n).max()
    rsv = (data['close'] - low_n) / (high_n - low_n) * 100
    
    k = pd.Series(0.0, index=data.index)
    k.iloc[n-1] = 50
    
    for i in range(n, len(data)):
        k.iloc[i] = (2/3) * k.iloc[i-1] + (1/3) * rsv.iloc[i]
    
    d = pd.Series(0.0, index=data.index)
    d.iloc[n-1] = 50
    
    for i in range(n, len(data)):
        d.iloc[i] = (2/3) * d.iloc[i-1] + (1/3) * k.iloc[i]
    
    j = 3 * k - 2 * d
    
    return k, d, j

def generate_hs300_data():
    """生成模拟的沪深300数据（近5年）"""
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

class KDJDivergenceStrategy:
    def __init__(self, data, lookback=10):
        self.data = data.copy()
        self.lookback = lookback
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_divergence"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_indicators(self):
        """计算技术指标"""
        self.k, self.d, self.j = calculate_kdj(self.data)
        self.data['k'] = self.k
        self.data['d'] = self.d
        self.data['j'] = self.j
    
    def detect_divergence(self):
        """检测KDJ背离"""
        self.data['bullish_divergence'] = False
        self.data['bearish_divergence'] = False
        
        for i in range(self.lookback * 2, len(self.data)):
            # 检测看涨背离：价格创新低，KDJ未创新低
            recent_low = self.data['close'].iloc[i-self.lookback:i+1].min()
            recent_low_idx = self.data['close'].iloc[i-self.lookback:i+1].idxmin()
            
            if recent_low_idx == self.data.index[i]:
                prev_low = self.data['close'].iloc[i-2*self.lookback:i-self.lookback].min()
                
                if recent_low< prev_low:
                    recent_k_low = self.data['k'].iloc[i-self.lookback:i+1].min()
                    prev_k_low = self.data['k'].iloc[i-2*self.lookback:i-self.lookback].min()
                    
                    if recent_k_low >prev_k_low:
                        self.data.loc[self.data.index[i], 'bullish_divergence'] = True
            
            # 检测看跌背离：价格创新高，KDJ未创新高
            recent_high = self.data['close'].iloc[i-self.lookback:i+1].max()
            recent_high_idx = self.data['close'].iloc[i-self.lookback:i+1].idxmax()
            
            if recent_high_idx == self.data.index[i]:
                prev_high = self.data['close'].iloc[i-2*self.lookback:i-self.lookback].max()
                
                if recent_high > prev_high:
                    recent_k_high = self.data['k'].iloc[i-self.lookback:i+1].max()
                    prev_k_high = self.data['k'].iloc[i-2*self.lookback:i-self.lookback].max()
                    
                    if recent_k_high< prev_k_high:
                        self.data.loc[self.data.index[i], 'bearish_divergence'] = True
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 检测背离
        self.detect_divergence()
        
        for i in range(len(self.data)):
            # 看涨背离买入
            if self.data['bullish_divergence'].iloc[i]:
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 看跌背离卖出
            elif self.data['bearish_divergence'].iloc[i]:
                self.data.loc[self.data.index[i], 'signal'] = -1
    
    def backtest(self):
        """执行回测"""
        self.data['position'] = 0
        self.data['strategy_returns'] = 0
        
        position = 0
        
        for i in range(len(self.data)):
            # 更新仓位
            if self.data['signal'].iloc[i] == 1:
                position = 1
            elif self.data['signal'].iloc[i] == -1:
                position = 0
            
            self.data.loc[self.data.index[i], 'position'] = position
        
        # 计算收益率
        self.data['returns'] = self.data['close'].pct_change()
        self.data['strategy_returns'] = self.data['returns'] * self.data['position'].shift(1)
        
        # 计算累计收益率
        self.data['cumulative_returns'] = (1 + self.data['strategy_returns']).cumprod()
        self.data['benchmark_returns'] = (1 + self.data['returns']).cumprod()
    
    def calculate_metrics(self):
        """计算回测指标"""
        total_return = (self.data['cumulative_returns'].iloc[-1] - 1) * 100
        annualized_return = (1 + total_return/100) ** (252/len(self.data)) - 1
        
        daily_returns = self.data['strategy_returns'].dropna()
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        
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
        
        win_rate = len([t for t in trades if t > 0]) / len(trades) * 100 if trades else 0
        profit_loss_ratio = np.mean([t for t in trades if t > 0]) / np.mean([abs(t) for t in trades if t< 0]) if trades else 0
        
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
    
    def plot_results(self):
        """绘制回测结果"""
        plt.figure(figsize=(16, 10))
        
        plt.subplot(2, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300指数', color='blue', linewidth=1.5)
        
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title('KDJ背离策略回测 - 价格与交易信号', fontsize=14)
        plt.ylabel('指数价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(2, 1, 2)
        plt.plot(self.data.index, self.data['k'], label='K线', color='blue', linewidth=1.2)
        plt.plot(self.data.index, self.data['d'], label='D线', color='red', linewidth=1.2)
        plt.plot(self.data.index, self.data['j'], label='J线', color='green', linewidth=1.2)
        plt.axhline(y=80, color='red', linestyle='--', alpha=0.7)
        plt.axhline(y=20, color='green', linestyle='--', alpha=0.7)
        plt.axhline(y=50, color='gray', linestyle='-', alpha=0.5)
        
        plt.scatter(buy_signals.index, buy_signals['k'], marker='^', color='red', s=100)
        plt.scatter(sell_signals.index, sell_signals['k'], marker='v', color='green', s=100)
        
        plt.title('KDJ指标', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('KDJ值', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/kdj_divergence_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_results(self):
        """保存回测结果"""
        self.data.to_csv(f"{self.output_dir}/kdj_divergence_backtest.csv")
    
    def print_metrics(self):
        """打印回测指标"""
        print("=== KDJ背离策略回测结果 ===")
        print(f"总收益率: {self.metrics['total_return']:.2f}%")
        print(f"年化收益率: {self.metrics['annualized_return']:.2f}%")
        print(f"夏普比率: {self.metrics['sharpe_ratio']:.2f}")
        print(f"最大回撤: {self.metrics['max_drawdown']:.2f}%")
        print(f"胜率: {self.metrics['win_rate']:.2f}%")
        print(f"盈亏比: {self.metrics['profit_loss_ratio']:.2f}")
        print(f"总交易次数: {self.metrics['total_trades']}")
        print(f"平均持仓天数: {self.metrics['average_holding_days']:.1f}")

def create_strategy_description():
    """创建策略说明文档"""
    description = """# KDJ背离策略说明

## 策略原理

### 核心思想
- **看涨背离**: 价格创新低，KDJ未创新低，预示可能反转上涨
- **看跌背离**: 价格创新高，KDJ未创新高，预示可能反转下跌
- **优势**: 能够提前识别潜在的反转点

### 参数设置
- **KDJ周期**: 9天（标准参数）
- **背离检测窗口**: 10天

## 策略规则

### 买入条件
- 价格创新低，但KDJ未创新低（看涨背离）

### 卖出条件
- 价格创新高，但KDJ未创新高（看跌背离）

## 策略优势
1. **提前预警**: 能够提前识别潜在的反转点
2. **高胜率**: 背离信号通常具有较高的可靠性
3. **风险控制**: 买入时价格相对较低，卖出时价格相对较高
4. **适用性广**: 适用于各种市场环境

## 策略局限性
1. **信号稀少**: 背离信号出现频率较低
2. **信号滞后**: 背离信号可能滞后于实际反转点
3. **假信号**: 可能出现假背离信号
4. **参数敏感**: 背离检测窗口的设置影响信号质量

## 优化建议
1. **多重背离**: 寻找连续出现的多次背离信号
2. **确认信号**: 结合其他指标确认背离信号的有效性
3. **成交量配合**: 要求成交量配合确认背离的有效性
4. **趋势确认**: 结合趋势指标判断背离的可靠性

## 回测结果
- **总收益率**: 待回测
- **年化收益率**: 待回测
- **夏普比率**: 待回测
- **最大回撤**: 待回测
- **胜率**: 待回测
- **总交易次数**: 待回测
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_divergence"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/kdj_divergence说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 生成数据
    data = generate_hs300_data()
    
    # 创建策略实例
    strategy = KDJDivergenceStrategy(data)
    
    # 执行策略
    strategy.calculate_indicators()
    strategy.generate_signals()
    strategy.backtest()
    strategy.calculate_metrics()
    strategy.plot_results()
    strategy.save_results()
    
    # 打印结果
    strategy.print_metrics()
