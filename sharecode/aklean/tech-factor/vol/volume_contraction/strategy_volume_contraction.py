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

class VolumeContractionStrategy:
    def __init__(self, data, volume_ma_period=20, contraction_days=3, stop_loss=0.05, take_profit=0.20):
        self.data = data.copy()
        self.volume_ma_period = volume_ma_period
        self.contraction_days = contraction_days
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol/volume_contraction"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_contraction(self):
        """计算成交量萎缩指标"""
        # 成交量均线
        self.data['volume_ma'] = self.data['volume'].rolling(self.volume_ma_period).mean()
        self.data['volume_ratio'] = self.data['volume'] / self.data['volume_ma']
        
        # 成交量萎缩模式
        # 连续萎缩
        self.data['volume_contraction'] = True
        for i in range(self.contraction_days, len(self.data)):
            contraction = True
            for j in range(1, self.contraction_days + 1):
                if self.data['volume'].iloc[i-j+1] >= self.data['volume'].iloc[i-j]:
                    contraction = False
                    break
            self.data.loc[self.data.index[i], 'volume_contraction'] = contraction
        
        # 极度缩量
        self.data['extremely_low_volume'] = self.data['volume_ratio']< 0.5
        
        # 缩量后放量
        self.data['volume_expansion'] = (self.data['volume'] >self.data['volume'].shift(1)) & \
                                      (self.data['volume'].shift(1)< self.data['volume'].shift(2))
        
        # 价格止跌信号
        self.data['price_rebound'] = (self.data['close'] >self.data['close'].shift(1)) & \
                                   (self.data['close'].shift(1)<= self.data['close'].shift(2))
        
        # 支撑位检查
        self.data['support_level'] = self.data['low'].rolling(20).max().shift(1)
        self.data['price_above_support'] = self.data['close'] > self.data['support_level']
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(max(self.volume_ma_period, self.contraction_days), len(self.data)):
            # 买入信号：
            # 1. 连续缩量（默认3天）
            # 2. 极度缩量（低于均量50%）
            # 3. 价格出现止跌信号
            # 4. 价格在支撑位上方
            if (self.data['volume_contraction'].iloc[i] and
                self.data['extremely_low_volume'].iloc[i] and
                self.data['price_rebound'].iloc[i] and
                self.data['price_above_support'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 买入信号：缩量后放量
            elif (self.data['volume_expansion'].iloc[i] and
                  self.data['volume_ratio'].iloc[i] > 1.2 and
                  self.data['price_rebound'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 卖出信号：
            # 1. 价格跌破支撑位
            # 2. 成交量异常放大（可能是出货）
            # 3. 价格达到止盈目标
            elif (self.data['close'].iloc[i]< self.data['support_level'].iloc[i] or
                  self.data['volume_ratio'].iloc[i] > 3):
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
                if self.data['close'].iloc[i] > entry_price * 1.05:
                    new_trailing_stop = max(trailing_stop, self.data['close'].iloc[i] * 0.95)
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
        plt.plot(self.data.index, self.data['support_level'], label='支撑位', color='green', linestyle='--', linewidth=1.2)
        
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title('成交量萎缩策略 - 价格与交易信号', fontsize=14)
        plt.ylabel('指数价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 2)
        plt.bar(self.data.index, self.data['volume'], label='成交量', color='orange', alpha=0.6)
        plt.plot(self.data.index, self.data['volume_ma'], label=f'{self.volume_ma_period}日均线', color='blue', linewidth=1.5)
        plt.axhline(y=self.data['volume_ma'].mean() * 0.5, color='red', linestyle='--', label='极度缩量阈值')
        
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
        plt.savefig(f"{self.output_dir}/volume_contraction_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_results(self):
        """保存回测结果"""
        self.data.to_csv(f"{self.output_dir}/volume_contraction_strategy_backtest.csv")
    
    def print_metrics(self):
        """打印回测指标"""
        print("=== 成交量萎缩策略回测结果 ===")
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
    description = """# 成交量萎缩策略说明

## 策略原理

### 核心思想
- **缩量见底**：成交量的极度萎缩往往预示着市场即将反转
- **量价配合**：缩量后放量上涨是可靠的买入信号
- **支撑位确认**：价格在支撑位上方止跌更可靠

### 参数设置
- **成交量均线周期**: 20天
- **连续缩量天数**: 3天
- **止损比例**: 5%
- **止盈比例**: 20%
- **移动止损**: 价格上涨5%时，止损上移5%

## 策略规则

### 买入条件（主信号）
1. 成交量连续3天萎缩
2. 成交量极度萎缩（低于20日均量的50%）
3. 价格出现止跌信号（阳包阴或反转形态）
4. 价格在20日最高低点形成的支撑位上方

### 买入条件（辅助信号）
1. 成交量从萎缩转为放量（放量>1.2倍均量）
2. 价格同步上涨

### 卖出条件
1. 价格跌破支撑位
2. 成交量异常放大（>3倍均量，可能是出货）
3. 价格跌破移动止损线
4. 价格达到止盈线（买入价的20%）

## 策略优势
1. **底部识别**：成交量萎缩是重要的底部特征
2. **风险控制**：在相对低点买入，风险较小
3. **可靠性高**：多条件确认提高信号可靠性
4. **收益潜力**：底部反转往往有较大上涨空间

## 策略局限性
1. **信号频率**：成交量萎缩信号相对较少
2. **假信号**：有时缩量后可能继续缩量
3. **时效性**：底部形成需要时间确认

## 优化建议
1. **参数调整**：根据市场情况调整缩量天数和阈值
2. **形态确认**：结合K线形态确认底部
3. **多周期分析**：结合周线、月线的成交量变化
4. **均线配合**：结合均线系统确认趋势

## 回测结果
- **总收益率**: 待回测
- **年化收益率**: 待回测
- **夏普比率**: 待回测
- **最大回撤**: 待回测
- **胜率**: 待回测
- **总交易次数**: 待回测
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol/volume_contraction"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/volume_contraction_strategy说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 生成数据
    data = generate_hs300_data()
    
    # 创建策略实例
    strategy = VolumeContractionStrategy(data)
    
    # 执行策略
    strategy.calculate_contraction()
    strategy.generate_signals()
    strategy.backtest()
    strategy.calculate_metrics()
    strategy.plot_results()
    strategy.save_results()
    
    # 打印结果
    strategy.print_metrics()
