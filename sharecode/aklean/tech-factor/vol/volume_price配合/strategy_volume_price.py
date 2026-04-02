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

class VolumePriceStrategy:
    def __init__(self, data, ma_periods=[5, 20, 50], volume_ma_period=20, stop_loss=0.05, take_profit=0.15):
        self.data = data.copy()
        self.ma_periods = ma_periods
        self.volume_ma_period = volume_ma_period
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol/volume_price配合"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_indicators(self):
        """计算量价配合指标"""
        # 价格均线
        for period in self.ma_periods:
            self.data[f'ma{period}'] = self.data['close'].rolling(period).mean()
        
        # 成交量均线
        self.data['volume_ma'] = self.data['volume'].rolling(self.volume_ma_period).mean()
        self.data['volume_ratio'] = self.data['volume'] / self.data['volume_ma']
        
        # 价格变化率
        self.data['price_change'] = self.data['close'].pct_change()
        
        # 成交量变化率
        self.data['volume_change'] = self.data['volume'].pct_change()
        
        # 量价配合指标
        # 量价齐升：价格上涨且成交量增加
        self.data['price_volume_rise'] = (self.data['price_change'] > 0) & (self.data['volume_change'] > 0)
        
        # 量价齐跌：价格下跌且成交量增加
        self.data['price_volume_fall'] = (self.data['price_change']< 0) & (self.data['volume_change'] >0)
        
        # 价涨量缩：价格上涨但成交量减少
        self.data['price_rise_volume_fall'] = (self.data['price_change'] >0) & (self.data['volume_change']< 0)
        
        # 价跌量缩：价格下跌但成交量减少
        self.data['price_fall_volume_fall'] = (self.data['price_change'] < 0) & (self.data['volume_change'] < 0)
        
        # 均线多头排列
        self.data['ma_ascending'] = (self.data['ma5'] >self.data['ma20']) & (self.data['ma20'] > self.data['ma50'])
        
        # 均线空头排列
        self.data['ma_descending'] = (self.data['ma5']< self.data['ma20']) & (self.data['ma20'] < self.data['ma50'])
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(max(self.ma_periods + [self.volume_ma_period]), len(self.data)):
            # 买入信号：
            # 1. 量价齐升
            # 2. 成交量放大（大于均量1.3倍）
            # 3. 均线多头排列
            if (self.data['price_volume_rise'].iloc[i] and
                self.data['volume_ratio'].iloc[i] > 1.3 and
                self.data['ma_ascending'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 卖出信号：
            # 1. 量价齐跌
            # 2. 成交量放大（大于均量1.5倍）
            # 3. 均线空头排列
            elif (self.data['price_volume_fall'].iloc[i] and
                  self.data['volume_ratio'].iloc[i] > 1.5 and
                  self.data['ma_descending'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = -1
            
            # 警惕信号：价涨量缩可能预示上涨乏力
            elif (self.data['price_rise_volume_fall'].iloc[i] and
                  self.data['volume_ratio'].iloc[i]< 0.7):
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
        plt.plot(self.data.index, self.data['ma5'], label='5日均线', color='red', linewidth=1.2)
        plt.plot(self.data.index, self.data['ma20'], label='20日均线', color='orange', linewidth=1.2)
        plt.plot(self.data.index, self.data['ma50'], label='50日均线', color='green', linewidth=1.2)
        
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title('量价配合策略 - 价格与均线', fontsize=14)
        plt.ylabel('指数价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 2)
        plt.bar(self.data.index, self.data['volume'], label='成交量', color='purple', alpha=0.6)
        plt.plot(self.data.index, self.data['volume_ma'], label=f'{self.volume_ma_period}日均线', color='blue', linewidth=1.5)
        
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
        plt.savefig(f"{self.output_dir}/volume_price_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_results(self):
        """保存回测结果"""
        self.data.to_csv(f"{self.output_dir}/volume_price_strategy_backtest.csv")
    
    def print_metrics(self):
        """打印回测指标"""
        print("=== 量价配合策略回测结果 ===")
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
    description = """# 量价配合策略说明

## 策略原理

### 核心思想
- **量价配合**：价格和成交量的配合关系是判断趋势有效性的关键
- **均线确认**：通过均线系统确认趋势方向
- **信号过滤**：只有在量价配合良好时才入场

### 参数设置
- **均线周期**: 5日、20日、50日
- **成交量均线周期**: 20日
- **止损比例**: 5%
- **止盈比例**: 15%
- **移动止损**: 价格上涨3%时，止损上移2%

## 策略规则

### 买入条件
1. 量价齐升：价格上涨且成交量增加
2. 成交量放大：大于20日均量的1.3倍
3. 均线多头排列：5日均线 > 20日均线 > 50日均线

### 卖出条件
1. 量价齐跌：价格下跌且成交量增加
2. 成交量放大：大于20日均量的1.5倍
3. 均线空头排列：5日均线 < 20日均线 < 50日均线
4. 价涨量缩：价格上涨但成交量明显萎缩（小于均量70%）
5. 价格跌破移动止损线
6. 价格达到止盈线（买入价的15%）

## 策略优势
1. **趋势确认**：量价配合确认趋势的有效性
2. **信号可靠性**：多指标确认提高信号可靠性
3. **风险控制**：严格的止损机制
4. **趋势跟踪**：有效跟踪趋势的持续性

## 策略局限性
1. **信号频率**：量价配合信号相对较少
2. **参数敏感性**：需要调整均线参数
3. **滞后性**：均线系统存在一定滞后性

## 优化建议
1. **参数优化**：调整均线周期和成交量阈值
2. **波动率调整**：根据市场波动率调整参数
3. **多周期分析**：结合不同时间周期的量价关系
4. **成交量形态**：识别特定的成交量形态

## 回测结果
- **总收益率**: 待回测
- **年化收益率**: 待回测
- **夏普比率**: 待回测
- **最大回撤**: 待回测
- **胜率**: 待回测
- **总交易次数**: 待回测
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol/volume_price配合"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/volume_price_strategy说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 生成数据
    data = generate_hs300_data()
    
    # 创建策略实例
    strategy = VolumePriceStrategy(data)
    
    # 执行策略
    strategy.calculate_indicators()
    strategy.generate_signals()
    strategy.backtest()
    strategy.calculate_metrics()
    strategy.plot_results()
    strategy.save_results()
    
    # 打印结果
    strategy.print_metrics()
