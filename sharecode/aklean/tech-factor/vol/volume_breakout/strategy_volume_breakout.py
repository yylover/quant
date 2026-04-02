import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

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
    
    # 生成成交量数据
    base_volume = 20000000
    volume_trend = np.linspace(0, 0.5, len(dates))
    price_volatility = np.abs(np.diff(prices, prepend=prices[0])) / prices * 100
    volume_seasonal = 0.3 * np.sin(np.linspace(0, 8*np.pi, len(dates)))
    
    volumes = base_volume * (
        1 + volume_trend + 
        price_volatility * 5 + 
        volume_seasonal + 
        np.random.normal(0, 0.2, len(dates))
    )
    
    volumes = np.maximum(volumes, base_volume * 0.3)
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
        'high': prices * (1 + np.random.normal(0.003, 0.005, len(dates))),
        'low': prices * (1 + np.random.normal(-0.003, 0.005, len(dates))),
        'close': prices,
        'volume': volumes.astype(int)
    })
    
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    data.set_index('date', inplace=True)
    
    return data

class VolumeBreakoutStrategy:
    def __init__(self, data, volume_period=20, price_period=20, volume_threshold=2.0, stop_loss=0.05, take_profit=0.15):
        self.data = data.copy()
        self.volume_period = volume_period
        self.price_period = price_period
        self.volume_threshold = volume_threshold
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol/volume_breakout"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_indicators(self):
        """计算成交量突破指标"""
        # 成交量均线
        self.data['volume_ma'] = self.data['volume'].rolling(self.volume_period).mean()
        self.data['volume_ratio'] = self.data['volume'] / self.data['volume_ma']
        
        # 价格支撑阻力位
        self.data['resistance'] = self.data['high'].rolling(self.price_period).max().shift(1)
        self.data['support'] = self.data['low'].rolling(self.price_period).min().shift(1)
        
        # 价格突破信号
        self.data['price_breakout'] = self.data['close'] > self.data['resistance']
        self.data['price_breakdown'] = self.data['close']< self.data['support']
        
        # 成交量突破信号
        self.data['volume_breakout'] = self.data['volume_ratio'] >self.volume_threshold
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(max(self.volume_period, self.price_period), len(self.data)):
            # 买入信号：价格突破阻力位 + 成交量突破
            if (self.data['price_breakout'].iloc[i] and
                self.data['volume_breakout'].iloc[i] and
                self.data['volume_ratio'].iloc[i] > self.volume_threshold):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 卖出信号：价格跌破支撑位 + 成交量放大
            elif (self.data['price_breakdown'].iloc[i] and
                  self.data['volume_ratio'].iloc[i] > 1.5):
                self.data.loc[self.data.index[i], 'signal'] = -1
        
        return self.data
    
    def backtest(self):
        """执行回测"""
        self.data['position'] = 0
        self.data['strategy_returns'] = 0
        self.data['stop_loss_level'] = 0
        self.data['take_profit_level'] = 0
        
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
            elif position == 1:
                if self.data['close'].iloc[i] > entry_price * 1.03:
                    new_trailing_stop = max(trailing_stop, self.data['close'].iloc[i] * 0.98)
                    trailing_stop = new_trailing_stop
                    self.data.loc[self.data.index[i], 'stop_loss_level'] = trailing_stop
            
            # 止损检查
            elif position == 1 and self.data['low'].iloc[i]< trailing_stop:
                position = 0
                self.data.loc[self.data.index[i], 'signal'] = -1
            
            # 止盈检查
            elif position == 1 and self.data['high'].iloc[i] >self.data['take_profit_level'].iloc[i]:
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
        plt.figure(figsize=(16, 12))
        
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300指数', color='blue', linewidth=1.5)
        plt.plot(self.data.index, self.data['resistance'], label='阻力位', color='red', linestyle='--', linewidth=1.2)
        plt.plot(self.data.index, self.data['support'], label='支撑位', color='green', linestyle='--', linewidth=1.2)
        
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title('成交量突破策略 - 价格与突破信号', fontsize=14)
        plt.ylabel('指数价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 2)
        plt.bar(self.data.index, self.data['volume'], label='成交量', color='orange', alpha=0.6)
        plt.plot(self.data.index, self.data['volume_ma'], label=f'{self.volume_period}日均线', color='blue', linewidth=1.5)
        plt.axhline(y=self.data['volume_ma'].mean() * self.volume_threshold, color='red', linestyle='--', label='突破阈值')
        
        plt.scatter(buy_signals.index, buy_signals['volume'], marker='^', color='red', s=100)
        plt.scatter(sell_signals.index, sell_signals['volume'], marker='v', color='green', s=100)
        
        plt.title('成交量变化', fontsize=14)
        plt.ylabel('成交量', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 3)
        plt.plot(self.data.index, self.data['cumulative_returns'], label='策略收益', color='red', linewidth=1.5)
        plt.plot(self.data.index, self.data['benchmark_returns'], label='基准收益', color='blue', linewidth=1.5)
        
        plt.title('累计收益率对比', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('累计收益', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/volume_breakout_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_results(self):
        """保存回测结果"""
        self.data.to_csv(f"{self.output_dir}/volume_breakout_backtest.csv")
    
    def print_metrics(self):
        """打印回测指标"""
        print("=== 成交量突破策略回测结果 ===")
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
    description = """# 成交量突破策略说明

## 策略原理

### 核心思想
- **成交量突破确认**：利用成交量的突然放大来确认价格突破的有效性
- **量价配合**：只有当价格突破和成交量突破同时发生时才入场
- **风险控制**：设置止损和止盈，保护本金和利润

### 参数设置
- **成交量周期**: 20天（计算成交量均线）
- **价格周期**: 20天（计算支撑阻力位）
- **成交量突破阈值**: 2.0（当前成交量是均线的2倍）
- **止损比例**: 5%
- **止盈比例**: 15%
- **移动止损**: 价格上涨3%时，止损上移2%

## 策略规则

### 买入条件
1. 价格突破20日最高价（阻力位）
2. 成交量突破20日均量的2倍
3. 当前成交量比率大于2.0

### 卖出条件
1. 价格跌破20日最低价（支撑位）且成交量放大（大于均量1.5倍）
2. 价格跌破移动止损线
3. 价格达到止盈线（买入价的15%）

## 策略优势
1. **确认突破有效性**：成交量突破确认价格突破的真实性
2. **避免假突破**：单一价格突破可能是假突破，成交量配合增加可信度
3. **风险控制**：严格的止损机制保护本金
4. **趋势跟踪**：捕捉趋势启动的最佳时机

## 策略局限性
1. **信号频率**：成交量突破信号相对较少
2. **参数敏感性**：成交量阈值需要根据市场情况调整
3. **滞后性**：需要等待成交量和价格同时突破，可能错过最佳入场点

## 优化建议
1. **参数优化**：根据不同市场调整成交量阈值
2. **波动率调整**：高波动时期降低成交量阈值
3. **多周期确认**：结合多个时间周期的成交量突破
4. **组合策略**：与其他指标结合使用

## 回测结果
- **总收益率**: 待回测
- **年化收益率**: 待回测
- **夏普比率**: 待回测
- **最大回撤**: 待回测
- **胜率**: 待回测
- **总交易次数**: 待回测
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol/volume_breakout"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/volume_breakout说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 生成数据
    data = generate_hs300_data()
    
    # 创建策略实例
    strategy = VolumeBreakoutStrategy(data)
    
    # 执行策略
    strategy.calculate_indicators()
    strategy.generate_signals()
    strategy.backtest()
    strategy.calculate_metrics()
    strategy.plot_results()
    strategy.save_results()
    
    # 打印结果
    strategy.print_metrics()
