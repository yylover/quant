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

def generate_etf_data(symbol, base_price=4000, trend_factor=0.5):
    """生成模拟的ETF数据（近5年）"""
    np.random.seed(hash(symbol) % 1000)
    
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=5*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 根据不同ETF调整波动特性
    volatility_factors = {
        '510300': 0.01,   # 沪深300ETF - 低波动
        '159915': 0.015,  # 创业板ETF - 高波动
        '510500': 0.012,  # 中证500ETF - 中等波动
        '510050': 0.008,  # 上证50ETF - 低波动
        '588000': 0.02    # 科创板ETF - 高波动
    }
    
    volatility_factor = volatility_factors.get(symbol, 0.01)
    
    # 创建基础价格，加入趋势和季节性因素
    trend = np.linspace(0, trend_factor, len(dates))
    
    # 添加季节性和周期性波动
    seasonal = 0.03 * np.sin(np.linspace(0, 10*np.pi, len(dates)))
    cyclic = 0.02 * np.cos(np.linspace(0, 5*np.pi, len(dates)))
    
    # 添加随机波动
    volatility = np.random.normal(0, volatility_factor, len(dates))
    
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

class KDJMultiETFStrategy:
    def __init__(self, etf_symbols, kdj_period=9, ma_period=50, stop_loss=0.08, take_profit=0.20):
        self.etf_symbols = etf_symbols
        self.kdj_period = kdj_period
        self.ma_period = ma_period
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_multi_etf"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_indicators(self, data):
        """计算技术指标"""
        # 计算KDJ
        k, d, j = calculate_kdj(data, self.kdj_period)
        data['k'] = k
        data['d'] = d
        data['j'] = j
        
        # 计算均线
        data['ma'] = data['close'].rolling(window=self.ma_period).mean()
        
        # 计算KDJ动量
        data['kdj_momentum'] = data['j'] - data['d']
        
        return data
    
    def generate_signals(self, data):
        """生成交易信号"""
        data['signal'] = 0
        
        for i in range(max(self.kdj_period, self.ma_period), len(data)):
            # 买入条件
            if (data['k'].iloc[i] > data['d'].iloc[i] and
                data['k'].iloc[i-1] <= data['d'].iloc[i-1] and
                data['close'].iloc[i] > data['ma'].iloc[i] and
                data['kdj_momentum'].iloc[i] > 0 and
                30< data['k'].iloc[i]< 70):
                data.loc[data.index[i], 'signal'] = 1
            
            # 卖出条件
            elif (data['k'].iloc[i]< data['d'].iloc[i] and
                  data['k'].iloc[i-1] >=data['d'].iloc[i-1] and
                  (data['close'].iloc[i]< data['ma'].iloc[i] or
                   data['k'].iloc[i] >80) and
                  data['kdj_momentum'].iloc[i]< 0):
                data.loc[data.index[i], 'signal'] = -1
        
        return data
    
    def backtest(self, data):
        """执行回测"""
        data['position'] = 0
        data['strategy_returns'] = 0
        data['stop_loss_level'] = 0
        data['take_profit_level'] = 0
        
        position = 0
        entry_price = 0
        trailing_stop = 0
        
        for i in range(len(data)):
            # 买入信号
            if data['signal'].iloc[i] == 1 and position == 0:
                position = 1
                entry_price = data['close'].iloc[i]
                trailing_stop = entry_price * (1 - self.stop_loss)
                data.loc[data.index[i], 'stop_loss_level'] = trailing_stop
                data.loc[data.index[i], 'take_profit_level'] = entry_price * (1 + self.take_profit)
            
            # 动态移动止损
            elif position == 1:
                if data['close'].iloc[i] > entry_price * 1.05:
                    new_trailing_stop = max(trailing_stop, data['close'].iloc[i] * 0.98)
                    trailing_stop = new_trailing_stop
                    data.loc[data.index[i], 'stop_loss_level'] = trailing_stop
            
            # 止损检查
            elif position == 1 and data['low'].iloc[i]< trailing_stop:
                position = 0
                data.loc[data.index[i], 'signal'] = -1
            
            # 止盈检查
            elif position == 1 and data['high'].iloc[i] >data['take_profit_level'].iloc[i]:
                position = 0
                data.loc[data.index[i], 'signal'] = -1
            
            data.loc[data.index[i], 'position'] = position
        
        # 计算收益率
        data['returns'] = data['close'].pct_change()
        data['strategy_returns'] = data['returns'] * data['position'].shift(1)
        
        # 计算累计收益率
        data['cumulative_returns'] = (1 + data['strategy_returns']).cumprod()
        data['benchmark_returns'] = (1 + data['returns']).cumprod()
        
        return data
    
    def calculate_metrics(self, data):
        """计算回测指标"""
        total_return = (data['cumulative_returns'].iloc[-1] - 1) * 100
        annualized_return = (1 + total_return/100) ** (252/len(data)) - 1
        
        daily_returns = data['strategy_returns'].dropna()
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        cumulative = data['cumulative_returns']
        drawdown = (cumulative / cumulative.cummax() - 1) * 100
        max_drawdown = drawdown.min()
        
        # 计算胜率
        trades = []
        position = 0
        entry_price = 0
        
        for i in range(len(data)):
            if data['signal'].iloc[i] == 1 and position == 0:
                entry_price = data['close'].iloc[i]
                position = 1
            elif data['signal'].iloc[i] == -1 and position == 1:
                exit_price = data['close'].iloc[i]
                trades.append((exit_price - entry_price) / entry_price)
                position = 0
        
        win_rate = len([t for t in trades if t > 0]) / len(trades) * 100 if trades else 0
        profit_loss_ratio = np.mean([t for t in trades if t > 0]) / np.mean([abs(t) for t in trades if t< 0]) if trades else 0
        
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_trades': len(trades),
            'average_holding_days': len(data) / len(trades) if trades else 0
        }
        
        return metrics
    
    def plot_results(self, data, symbol):
        """绘制回测结果"""
        plt.figure(figsize=(16, 10))
        
        plt.subplot(2, 1, 1)
        plt.plot(data.index, data['close'], label=f'{symbol}价格', color='blue', linewidth=1.5)
        plt.plot(data.index, data['ma'], label=f'{self.ma_period}日均线', color='orange', linewidth=1.2)
        
        buy_signals = data[data['signal'] == 1]
        sell_signals = data[data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title(f'{symbol} - KDJ增强策略回测', fontsize=14)
        plt.ylabel('价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(2, 1, 2)
        plt.plot(data.index, data['cumulative_returns'], label='策略收益', color='red', linewidth=1.5)
        plt.plot(data.index, data['benchmark_returns'], label='基准收益', color='blue', linewidth=1.5)
        
        plt.title('累计收益率对比', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('累计收益', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/{symbol}_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_backtest(self):
        """运行多标的回测"""
        all_metrics = {}
        
        for symbol in self.etf_symbols:
            print(f"\n=== 开始回测 {symbol} ===")
            
            # 生成数据
            data = generate_etf_data(symbol)
            
            # 计算指标
            data = self.calculate_indicators(data)
            
            # 生成信号
            data = self.generate_signals(data)
            
            # 执行回测
            data = self.backtest(data)
            
            # 计算指标
            metrics = self.calculate_metrics(data)
            
            # 保存结果
            data.to_csv(f"{self.output_dir}/{symbol}_backtest.csv")
            
            # 绘制图表
            self.plot_results(data, symbol)
            
            # 保存指标
            all_metrics[symbol] = metrics
            
            # 打印结果
            print(f"\n{symbol} 回测结果:")
            print(f"总收益率: {metrics['total_return']:.2f}%")
            print(f"年化收益率: {metrics['annualized_return']:.2f}%")
            print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"最大回撤: {metrics['max_drawdown']:.2f}%")
            print(f"胜率: {metrics['win_rate']:.2f}%")
            print(f"盈亏比: {metrics['profit_loss_ratio']:.2f}")
            print(f"总交易次数: {metrics['total_trades']}")
        
        # 打印综合分析
        print("\n=== 多ETF回测综合分析 ===")
        
        # 计算平均表现
        total_returns = [m['total_return'] for m in all_metrics.values()]
        annualized_returns = [m['annualized_return'] for m in all_metrics.values()]
        sharpe_ratios = [m['sharpe_ratio'] for m in all_metrics.values()]
        max_drawdowns = [m['max_drawdown'] for m in all_metrics.values()]
        win_rates = [m['win_rate'] for m in all_metrics.values()]
        
        print(f"\n平均表现:")
        print(f"平均总收益率: {np.mean(total_returns):.2f}%")
        print(f"平均年化收益率: {np.mean(annualized_returns):.2f}%")
        print(f"平均夏普比率: {np.mean(sharpe_ratios):.2f}")
        print(f"平均最大回撤: {np.mean(max_drawdowns):.2f}%")
        print(f"平均胜率: {np.mean(win_rates):.2f}%")
        
        # 计算稳定性指标
        print(f"\n稳定性指标:")
        print(f"总收益率标准差: {np.std(total_returns):.2f}")
        print(f"年化收益率标准差: {np.std(annualized_returns):.2f}")
        print(f"夏普比率标准差: {np.std(sharpe_ratios):.2f}")
        
        # 排序表现
        sorted_by_return = sorted(all_metrics.items(), key=lambda x: x[1]['total_return'], reverse=True)
        print(f"\n收益率排名:")
        for i, (symbol, metrics) in enumerate(sorted_by_return, 1):
            print(f"{i}. {symbol}: {metrics['total_return']:.2f}%")
        
        return all_metrics

def create_strategy_description():
    """创建策略说明文档"""
    description = """# KDJ多ETF回测策略说明

## 策略原理

### 核心思想
- 使用增强版KDJ策略对多个ETF标的进行回测
- 验证策略在不同风格ETF上的稳定性
- 分析策略的适应性和稳健性

### 选择的ETF标的
1. **沪深300ETF (510300)** - 大盘价值风格
2. **创业板ETF (159915)** - 成长风格
3. **中证500ETF (510500)** - 中小盘风格
4. **上证50ETF (510050)** - 蓝筹风格
5. **科创板ETF (588000)** - 科技创新风格

### 策略参数
- **KDJ周期**: 9天（标准参数）
- **均线周期**: 50天（标准参数）
- **初始止损**: 8%
- **止盈比例**: 20%
- **移动止损**: 价格每上涨5%，止损上移2%

## 策略规则

### 买入条件
1. KDJ形成金叉（K线上穿D线）
2. 价格在50日均线上方
3. KDJ动量为正（J线 > D线）
4. K值在30-70之间（避免极端区域）

### 卖出条件
1. KDJ形成死叉（K线下穿D线）
2. 价格在50日均线下方 OR K值高于80
3. KDJ动量为负（J线 < D线）
4. 价格跌破移动止损线
5. 价格达到止盈线（买入价的20%）

## 回测目标
- 验证策略在不同风格ETF上的表现
- 评估策略的稳定性和适应性
- 分析不同ETF的收益差异
- 提供策略优化建议

## 结果分析要点
- 各ETF的收益率对比
- 夏普比率对比
- 最大回撤对比
- 胜率和盈亏比对比
- 策略稳定性评估

## 优化方向
- 根据不同ETF特性调整参数
- 开发ETF轮动策略
- 构建ETF组合策略
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_multi_etf"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/kdj_multi_etf说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 定义ETF标的
    etf_symbols = ['510300', '159915', '510500', '510050', '588000']
    
    # 创建策略实例
    strategy = KDJMultiETFStrategy(etf_symbols)
    
    # 运行回测
    all_metrics = strategy.run_backtest()
