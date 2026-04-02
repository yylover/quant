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

class TurnoverStrategy:
    def __init__(self, data, shares_outstanding=50000000000, turnover_ma_period=20, stop_loss=0.06, take_profit=0.18):
        self.data = data.copy()
        self.shares_outstanding = shares_outstanding  # 流通股本（假设500亿股）
        self.turnover_ma_period = turnover_ma_period
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol/volume_turnover"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_turnover(self):
        """计算换手率指标"""
        # 计算换手率
        self.data['turnover'] = self.data['volume'] / self.shares_outstanding * 100
        
        # 换手率均线
        self.data['turnover_ma'] = self.data['turnover'].rolling(self.turnover_ma_period).mean()
        
        # 换手率变化率
        self.data['turnover_change'] = self.data['turnover'].pct_change()
        
        # 换手率趋势
        self.data['turnover_trend'] = self.data['turnover'] > self.data['turnover_ma']
        
        # 异常换手率
        self.data['abnormal_turnover'] = self.data['turnover'] > self.data['turnover_ma'] * 2
        
        # 极低换手率
        self.data['extremely_low_turnover'] = self.data['turnover']< self.data['turnover_ma'] * 0.3
        
        # 换手率与价格的关系
        self.data['price_change'] = self.data['close'].pct_change()
        self.data['turnover_price_rise'] = (self.data['turnover_trend']) & (self.data['price_change'] >0)
        self.data['turnover_price_fall'] = (self.data['turnover_trend']) & (self.data['price_change']< 0)
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(self.turnover_ma_period, len(self.data)):
            # 买入信号：
            # 1. 换手率持续上升（连续3天）
            # 2. 价格同步上升
            # 3. 换手率低于历史高位（避免在顶部买入）
            turnover_rise = (self.data['turnover'].iloc[i] > self.data['turnover'].iloc[i-1]) & \
                          (self.data['turnover'].iloc[i-1] > self.data['turnover'].iloc[i-2])
            price_rise = self.data['price_change'].iloc[i] > 0
            turnover_not_high = self.data['turnover'].iloc[i] < self.data['turnover'].rolling(60).max().iloc[i] * 0.8
            
            # 卖出信号：
            # 1. 换手率突然急剧上升（可能是出货）
            # 2. 换手率达到历史高位
            # 3. 价格出现滞涨
            abnormal_rise = self.data['turnover_change'].iloc[i] > 0.5
            turnover_high = self.data['turnover'].iloc[i] > self.data['turnover'].rolling(60).max().iloc[i] * 0.9
            price_stagnation = abs(self.data['price_change'].iloc[i]) < 0.005
            
            if turnover_rise and price_rise and turnover_not_high:
                self.data.loc[self.data.index[i], 'signal'] = 1
            elif abnormal_rise or turnover_high or price_stagnation:
                self.data.loc[self.data.index[i], 'signal'] = -1
            elif self.data['extremely_low_turnover'].iloc[i]:
                self.data.loc[self.data.index[i], 'signal'] = 1
        
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
                if self.data['close'].iloc[i] > entry_price * 1.04:
                    new_trailing_stop = max(trailing_stop, self.data['close'].iloc[i] * 0.97)
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
        
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title('换手率策略 - 价格与交易信号', fontsize=14)
        plt.ylabel('指数价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['turnover'] * 100, label='换手率(%)', color='red', linewidth=1.5)
        plt.plot(self.data.index, self.data['turnover_ma'] * 100, label=f'{self.turnover_ma_period}日均线', color='blue', linewidth=1.5)
        
        plt.scatter(buy_signals.index, buy_signals['turnover'] * 100, marker='^', color='red', s=100)
        plt.scatter(sell_signals.index, sell_signals['turnover'] * 100, marker='v', color='green', s=100)
        
        plt.title('换手率变化', fontsize=14)
        plt.ylabel('换手率(%)', fontsize=12)
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
        plt.savefig(f"{self.output_dir}/turnover_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_results(self):
        """保存回测结果"""
        self.data.to_csv(f"{self.output_dir}/turnover_strategy_backtest.csv")
    
    def print_metrics(self):
        """打印回测指标"""
        print("=== 换手率策略回测结果 ===")
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
    description = """# 换手率策略说明

## 策略原理

### 核心思想
- **换手率反映市场活跃度**：换手率的变化反映市场参与者的情绪和资金流动
- **趋势确认**：换手率的持续上升往往预示着趋势的开始
- **风险控制**：通过换手率识别潜在的顶部风险

### 参数设置
- **流通股本**: 500亿股（假设）
- **换手率均线周期**: 20天
- **止损比例**: 6%
- **止盈比例**: 18%
- **移动止损**: 价格上涨4%时，止损上移3%

## 策略规则

### 买入条件
1. 换手率连续3天上升
2. 价格同步上升
3. 换手率低于60日最高换手率的80%（避免在顶部买入）

### 卖出条件
1. 换手率突然急剧上升（日变化率>50%）
2. 换手率达到60日最高换手率的90%
3. 价格出现滞涨（价格变化率<0.5%）
4. 价格跌破移动止损线
5. 价格达到止盈线（买入价的18%）

### 特殊买入信号
- 换手率极度萎缩（低于均量30%）可能是底部信号

## 策略优势
1. **市场情绪指标**：换手率反映真实的市场情绪
2. **提前预警**：换手率变化往往领先于价格变化
3. **风险识别**：通过异常换手率识别潜在风险
4. **底部识别**：极低换手率往往是底部特征

## 策略局限性
1. **数据依赖性**：需要准确的流通股本数据
2. **参数敏感性**：换手率阈值需要调整
3. **市场差异**：不同市场的换手率特征不同

## 优化建议
1. **动态调整**：根据市场情况动态调整换手率阈值
2. **多周期分析**：结合不同时间周期的换手率
3. **成交量配合**：结合成交量指标确认信号
4. **行业特性**：考虑不同行业的换手率特性

## 回测结果
- **总收益率**: 待回测
- **年化收益率**: 待回测
- **夏普比率**: 待回测
- **最大回撤**: 待回测
- **胜率**: 待回测
- **总交易次数**: 待回测
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol/volume_turnover"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/turnover_strategy说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 生成数据
    data = generate_hs300_data()
    
    # 创建策略实例
    strategy = TurnoverStrategy(data)
    
    # 执行策略
    strategy.calculate_turnover()
    strategy.generate_signals()
    strategy.backtest()
    strategy.calculate_metrics()
    strategy.plot_results()
    strategy.save_results()
    
    # 打印结果
    strategy.print_metrics()
