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

class KDJMultiPeriodStrategy:
    def __init__(self, data, periods=[5, 9, 14], stop_loss=0.05, take_profit=0.15):
        self.data = data.copy()
        self.periods = periods
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_multi_period"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_indicators(self):
        """计算多个周期的KDJ指标"""
        for period in self.periods:
            k, d, j = calculate_kdj(self.data, period)
            self.data[f'k_{period}'] = k
            self.data[f'd_{period}'] = d
            self.data[f'j_{period}'] = j
        
        # 计算均线
        self.data['ma20'] = self.data['close'].rolling(window=20).mean()
        self.data['ma50'] = self.data['close'].rolling(window=50).mean()
    
    def generate_signals(self):
        """生成多周期共振交易信号"""
        self.data['signal'] = 0
        
        for i in range(max(self.periods), len(self.data)):
            buy_count = 0
            
            # 检查每个周期的KDJ金叉信号
            for period in self.periods:
                if (self.data[f'k_{period}'].iloc[i] > self.data[f'd_{period}'].iloc[i] and
                    self.data[f'k_{period}'].iloc[i-1]<= self.data[f'd_{period}'].iloc[i-1]):
                    buy_count += 1
            
            # 趋势过滤：价格在均线上方
            trend_condition = (self.data['close'].iloc[i] >self.data['ma20'].iloc[i] and
                              self.data['ma20'].iloc[i] > self.data['ma50'].iloc[i])
            
            # 至少2个周期同时金叉且趋势向上
            if buy_count >= 2 and trend_condition:
                self.data.loc[self.data.index[i], 'signal'] = 1
    
    def backtest(self):
        """执行回测，包含止损止盈"""
        self.data['position'] = 0
        self.data['strategy_returns'] = 0
        self.data['stop_loss_level'] = 0
        self.data['take_profit_level'] = 0
        
        position = 0
        entry_price = 0
        
        for i in range(len(self.data)):
            # 买入信号
            if self.data['signal'].iloc[i] == 1 and position == 0:
                position = 1
                entry_price = self.data['close'].iloc[i]
                # 设置止损和止盈价格
                self.data.loc[self.data.index[i], 'stop_loss_level'] = entry_price * (1 - self.stop_loss)
                self.data.loc[self.data.index[i], 'take_profit_level'] = entry_price * (1 + self.take_profit)
            
            # 止损检查
            elif position == 1 and self.data['low'].iloc[i]< self.data['stop_loss_level'].iloc[i]:
                position = 0
                self.data.loc[self.data.index[i], 'signal'] = -1
            
            # 止盈检查
            elif position == 1 and self.data['high'].iloc[i] >self.data['take_profit_level'].iloc[i]:
                position = 0
                self.data.loc[self.data.index[i], 'signal'] = -1
            
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
        plt.plot(self.data.index, self.data['ma20'], label='20日均线', color='orange', linewidth=1.2)
        plt.plot(self.data.index, self.data['ma50'], label='50日均线', color='green', linewidth=1.2)
        
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title('KDJ多周期共振策略回测 - 价格与交易信号', fontsize=14)
        plt.ylabel('指数价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(2, 1, 2)
        for period in self.periods:
            plt.plot(self.data.index, self.data[f'k_{period}'], label=f'K线({period}天)', linewidth=1.0)
        
        plt.axhline(y=80, color='red', linestyle='--', alpha=0.7)
        plt.axhline(y=20, color='green', linestyle='--', alpha=0.7)
        plt.axhline(y=50, color='gray', linestyle='-', alpha=0.5)
        
        plt.scatter(buy_signals.index, [50]*len(buy_signals), marker='^', color='red', s=100)
        plt.scatter(sell_signals.index, [50]*len(sell_signals), marker='v', color='green', s=100)
        
        plt.title('多周期KDJ指标', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('KDJ值', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/kdj_multi_period_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_results(self):
        """保存回测结果"""
        self.data.to_csv(f"{self.output_dir}/kdj_multi_period_backtest.csv")
    
    def print_metrics(self):
        """打印回测指标"""
        print("=== KDJ多周期共振策略回测结果 ===")
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
    description = """# KDJ多周期共振策略说明

## 策略原理

### 核心思想
- **多周期共振**: 使用多个不同周期的KDJ指标（5天、9天、14天）
- **共振确认**: 要求至少2个周期同时发出买入信号
- **趋势过滤**: 使用均线确认趋势方向
- **风险控制**: 添加止损止盈机制

### 参数设置
- **KDJ周期**: 5天、9天、14天
- **均线周期**: 20天、50天
- **止损比例**: 5%
- **止盈比例**: 15%

## 策略规则

### 买入条件
1. 至少2个周期的KDJ同时形成金叉
2. 价格在20日均线上方
3. 20日均线在50日均线上方（趋势向上）

### 卖出条件
1. 价格跌破止损线（买入价的5%）
2. 价格达到止盈线（买入价的15%）

## 策略优势
1. **信号过滤**: 通过多周期共振过滤假信号
2. **趋势确认**: 确保在趋势方向上交易
3. **风险控制**: 严格的止损止盈机制
4. **高胜率**: 多周期确认提高信号可靠性
5. **稳定收益**: 风险控制确保收益稳定性

## 策略局限性
1. **信号稀少**: 多周期共振信号出现频率较低
2. **参数敏感**: 对参数设置较为敏感
3. **可能错过机会**: 过于严格的条件可能错过一些交易机会

## 优化建议
1. **参数优化**: 根据不同市场调整周期参数
2. **动态止损**: 使用ATR等指标设置动态止损
3. **仓位管理**: 根据信号强度调整仓位大小
4. **多策略组合**: 与其他策略结合使用

## 回测结果
- **总收益率**: 待回测
- **年化收益率**: 待回测
- **夏普比率**: 待回测
- **最大回撤**: 待回测
- **胜率**: 待回测
- **总交易次数**: 待回测
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_multi_period"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/kdj_multi_period说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 生成数据
    data = generate_hs300_data()
    
    # 创建策略实例
    strategy = KDJMultiPeriodStrategy(data)
    
    # 执行策略
    strategy.calculate_indicators()
    strategy.generate_signals()
    strategy.backtest()
    strategy.calculate_metrics()
    strategy.plot_results()
    strategy.save_results()
    
    # 打印结果
    strategy.print_metrics()
