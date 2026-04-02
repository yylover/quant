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

class KDJMACombinationStrategy:
    def __init__(self, data, ma_period=50):
        self.data = data.copy()
        self.ma_period = ma_period
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_ma_combination"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_indicators(self):
        """计算技术指标"""
        # 计算KDJ
        self.k, self.d, self.j = calculate_kdj(self.data)
        self.data['k'] = self.k
        self.data['d'] = self.d
        self.data['j'] = self.j
        
        # 计算均线
        self.data['ma'] = self.data['close'].rolling(window=self.ma_period).mean()
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(max(self.ma_period, 1), len(self.data)):
            # 买入条件：价格在均线上方且KDJ金叉
            if (self.data['close'].iloc[i] > self.data['ma'].iloc[i] and
                self.data['k'].iloc[i] > self.data['d'].iloc[i] and
                self.data['k'].iloc[i-1] <= self.data['d'].iloc[i-1]):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 卖出条件：价格在均线下方且KDJ死叉
            elif (self.data['close'].iloc[i]< self.data['ma'].iloc[i] and
                  self.data['k'].iloc[i] <self.data['d'].iloc[i] and
                  self.data['k'].iloc[i-1] >= self.data['d'].iloc[i-1]):
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
        plt.plot(self.data.index, self.data['ma'], label=f'{self.ma_period}日均线', color='orange', linewidth=1.2)
        
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title('KDJ与均线结合策略回测 - 价格与交易信号', fontsize=14)
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
        plt.savefig(f"{self.output_dir}/kdj_ma_combination_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_results(self):
        """保存回测结果"""
        self.data.to_csv(f"{self.output_dir}/kdj_ma_combination_backtest.csv")
    
    def print_metrics(self):
        """打印回测指标"""
        print("=== KDJ与均线结合策略回测结果 ===")
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
    description = """# KDJ与均线结合策略说明

## 策略原理

### 核心思想
- **趋势确认**: 使用均线判断趋势方向
- **动量确认**: 使用KDJ寻找入场时机
- **优势**: 结合趋势和动量指标，提高信号可靠性

### 参数设置
- **KDJ周期**: 9天（标准参数）
- **均线周期**: 50天（中期趋势）

## 策略规则

### 买入条件
1. 价格在均线上方（趋势向上）
2. KDJ形成金叉（动量向上）

### 卖出条件
1. 价格在均线下方（趋势向下）
2. KDJ形成死叉（动量向下）

## 策略优势
1. **趋势确认**: 通过均线确认趋势方向，避免逆势交易
2. **动量确认**: 通过KDJ寻找合适的入场时机
3. **信号过滤**: 减少假信号，提高胜率
4. **适用性强**: 适用于各种市场环境

## 策略局限性
1. **参数敏感**: 均线周期的选择影响策略表现
2. **信号延迟**: 可能错过最佳入场时机
3. **震荡市场**: 在横盘震荡市场中信号较少
4. **趋势判断**: 均线可能滞后于实际趋势变化

## 优化建议
1. **参数优化**: 根据不同市场调整均线周期
2. **多周期均线**: 使用多条均线确认趋势
3. **波动率过滤**: 根据市场波动率调整策略参数
4. **成交量配合**: 要求成交量配合确认信号有效性

## 回测结果
- **总收益率**: 待回测
- **年化收益率**: 待回测
- **夏普比率**: 待回测
- **最大回撤**: 待回测
- **胜率**: 待回测
- **总交易次数**: 待回测
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_ma_combination"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/kdj_ma_combination说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 生成数据
    data = generate_hs300_data()
    
    # 创建策略实例
    strategy = KDJMACombinationStrategy(data)
    
    # 执行策略
    strategy.calculate_indicators()
    strategy.generate_signals()
    strategy.backtest()
    strategy.calculate_metrics()
    strategy.plot_results()
    strategy.save_results()
    
    # 打印结果
    strategy.print_metrics()
