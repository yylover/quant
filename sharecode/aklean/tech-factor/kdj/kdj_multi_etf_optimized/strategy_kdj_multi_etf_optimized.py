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

def generate_etf_data(symbol):
    """生成更真实的ETF数据（近5年）"""
    np.random.seed(hash(symbol) % 1000)
    
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=5*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 基础价格和趋势设置
    base_prices = {
        '510300': 4000,   # 沪深300ETF
        '159915': 2500,   # 创业板ETF
        '510500': 6000,   # 中证500ETF
        '510050': 3500,   # 上证50ETF
        '588000': 1500    # 科创板ETF
    }
    
    base_price = base_prices.get(symbol, 4000)
    
    # 趋势因子设置（基于真实市场表现）
    trend_factors = {
        '510300': 0.4,    # 沪深300 - 中等上涨
        '159915': 0.2,    # 创业板 - 小幅上涨
        '510500': 0.3,    # 中证500 - 中等上涨
        '510050': 0.35,   # 上证50 - 中等上涨
        '588000': 0.5     # 科创板 - 较高上涨
    }
    
    trend_factor = trend_factors.get(symbol, 0.3)
    
    # 波动率设置
    volatility_factors = {
        '510300': 0.01,   # 沪深300 - 低波动
        '159915': 0.015,  # 创业板 - 中等波动
        '510500': 0.012,  # 中证500 - 中等波动
        '510050': 0.008,  # 上证50 - 低波动
        '588000': 0.018   # 科创板 - 高波动
    }
    
    volatility_factor = volatility_factors.get(symbol, 0.01)
    
    # 创建价格序列，加入趋势、季节性和随机波动
    trend = np.linspace(0, trend_factor, len(dates))
    
    # 添加季节性波动（每年一次）
    seasonal = 0.04 * np.sin(np.linspace(0, 5*np.pi, len(dates)))
    
    # 添加更长周期的波动
    long_term = 0.03 * np.cos(np.linspace(0, 2*np.pi, len(dates)))
    
    # 添加随机波动
    volatility = np.random.normal(0, volatility_factor, len(dates))
    
    # 计算价格
    prices = base_price * (1 + trend + seasonal + long_term + np.cumsum(volatility))
    
    # 确保价格为正
    prices = np.maximum(prices, base_price * 0.3)
    
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

class KDJMultiETFOptimizedStrategy:
    def __init__(self, etf_symbols):
        self.etf_symbols = etf_symbols
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_multi_etf_optimized"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_etf_params(self, symbol):
        """根据ETF类型获取优化参数"""
        params = {
            '510300': {'kdj_period': 9, 'ma_period': 50, 'stop_loss': 0.06, 'take_profit': 0.15, 'rsi_period': 14},
            '159915': {'kdj_period': 14, 'ma_period': 20, 'stop_loss': 0.08, 'take_profit': 0.20, 'rsi_period': 9},
            '510500': {'kdj_period': 9, 'ma_period': 30, 'stop_loss': 0.07, 'take_profit': 0.18, 'rsi_period': 14},
            '510050': {'kdj_period': 9, 'ma_period': 60, 'stop_loss': 0.05, 'take_profit': 0.12, 'rsi_period': 14},
            '588000': {'kdj_period': 14, 'ma_period': 20, 'stop_loss': 0.10, 'take_profit': 0.25, 'rsi_period': 9}
        }
        return params.get(symbol, params['510300'])
    
    def calculate_rsi(self, data, period=14):
        """计算RSI指标"""
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta< 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_indicators(self, data, params):
        """计算技术指标"""
        # 计算KDJ
        k, d, j = calculate_kdj(data, params['kdj_period'])
        data['k'] = k
        data['d'] = d
        data['j'] = j
        
        # 计算均线
        data['ma'] = data['close'].rolling(window=params['ma_period']).mean()
        
        # 计算RSI
        data['rsi'] = self.calculate_rsi(data, params['rsi_period'])
        
        # 计算KDJ动量
        data['kdj_momentum'] = data['j'] - data['d']
        
        # 计算均线斜率
        data['ma_slope'] = data['ma'].diff()
        
        return data
    
    def generate_signals(self, data, params):
        """生成优化的交易信号"""
        data['signal'] = 0
        
        for i in range(max(params['kdj_period'], params['ma_period'], params['rsi_period']), len(data)):
            # 买入条件：多指标确认
            if (data['k'].iloc[i] > data['d'].iloc[i] and
                data['k'].iloc[i-1] <= data['d'].iloc[i-1] and
                data['close'].iloc[i] > data['ma'].iloc[i] and
                data['ma_slope'].iloc[i] > 0 and
                data['kdj_momentum'].iloc[i] > 0 and
                data['rsi'].iloc[i] > 30 and
                data['rsi'].iloc[i]< 70):
                data.loc[data.index[i], 'signal'] = 1
            
            # 卖出条件：多指标确认
            elif (data['k'].iloc[i]< data['d'].iloc[i] and
                  data['k'].iloc[i-1] >=data['d'].iloc[i-1] and
                  (data['close'].iloc[i]< data['ma'].iloc[i] or
                   data['rsi'].iloc[i] >75) and
                  data['kdj_momentum'].iloc[i]< 0):
                data.loc[data.index[i], 'signal'] = -1
        
        return data
    
    def backtest(self, data, params):
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
                trailing_stop = entry_price * (1 - params['stop_loss'])
                data.loc[data.index[i], 'stop_loss_level'] = trailing_stop
                data.loc[data.index[i], 'take_profit_level'] = entry_price * (1 + params['take_profit'])
            
            # 动态移动止损
            elif position == 1:
                # 根据不同ETF调整移动止损参数
                if data['close'].iloc[i] > entry_price * 1.04:
                    new_trailing_stop = max(trailing_stop, data['close'].iloc[i] * 0.97)
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
        plt.figure(figsize=(16, 12))
        
        plt.subplot(3, 1, 1)
        plt.plot(data.index, data['close'], label=f'{symbol}价格', color='blue', linewidth=1.5)
        plt.plot(data.index, data['ma'], label=f'{data["ma"].name}日均线', color='orange', linewidth=1.2)
        
        buy_signals = data[data['signal'] == 1]
        sell_signals = data[data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='red', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='green', s=100, label='卖出信号')
        
        plt.title(f'{symbol} - KDJ优化策略回测', fontsize=14)
        plt.ylabel('价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 2)
        plt.plot(data.index, data['k'], label='K线', color='blue', linewidth=1.2)
        plt.plot(data.index, data['d'], label='D线', color='red', linewidth=1.2)
        plt.plot(data.index, data['j'], label='J线', color='green', linewidth=1.2)
        plt.axhline(y=80, color='red', linestyle='--', alpha=0.7)
        plt.axhline(y=20, color='green', linestyle='--', alpha=0.7)
        plt.axhline(y=50, color='gray', linestyle='-', alpha=0.5)
        
        plt.scatter(buy_signals.index, buy_signals['k'], marker='^', color='red', s=100)
        plt.scatter(sell_signals.index, sell_signals['k'], marker='v', color='green', s=100)
        
        plt.title('KDJ指标', fontsize=14)
        plt.ylabel('KDJ值', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 3)
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
        """运行优化的多标的回测"""
        all_metrics = {}
        
        for symbol in self.etf_symbols:
            print(f"\n=== 开始回测 {symbol} ===")
            
            # 获取ETF特定参数
            params = self.get_etf_params(symbol)
            print(f"使用参数: {params}")
            
            # 生成数据
            data = generate_etf_data(symbol)
            
            # 计算指标
            data = self.calculate_indicators(data, params)
            
            # 生成信号
            data = self.generate_signals(data, params)
            
            # 执行回测
            data = self.backtest(data, params)
            
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
        print("\n=== 多ETF优化策略回测综合分析 ===")
        
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
    description = """# KDJ多ETF优化策略说明

## 策略原理

### 核心思想
- 为每个ETF量身定制优化参数
- 结合KDJ、均线、RSI多指标确认
- 使用动态移动止损保护利润
- 基于ETF特性调整风险参数

### 选择的ETF标的
1. **沪深300ETF (510300)** - 大盘价值风格
2. **创业板ETF (159915)** - 成长风格
3. **中证500ETF (510500)** - 中小盘风格
4. **上证50ETF (510050)** - 蓝筹风格
5. **科创板ETF (588000)** - 科技创新风格

### ETF特定参数设置

| ETF代码 | KDJ周期 | 均线周期 | 止损比例 | 止盈比例 | RSI周期 |
|--------|--------|---------|---------|---------|--------|
| 510300 | 9天    | 50天    | 6%      | 15%     | 14天   |
| 159915 | 14天   | 20天    | 8%      | 20%     | 9天    |
| 510500 | 9天    | 30天    | 7%      | 18%     | 14天   |
| 510050 | 9天    | 60天    | 5%      | 12%     | 14天   |
| 588000 | 14天   | 20天    | 10%     | 25%     | 9天    |

## 策略规则

### 买入条件（多指标确认）
1. KDJ形成金叉（K线上穿D线）
2. 价格在均线上方
3. 均线斜率为正（确认上升趋势）
4. KDJ动量为正（J线 > D线）
5. RSI在30-70之间（避免极端区域）

### 卖出条件（多指标确认）
1. KDJ形成死叉（K线下穿D线）
2. 价格在均线下方 OR RSI高于75
3. KDJ动量为负（J线 < D线）
4. 价格跌破移动止损线
5. 价格达到止盈线

## 风险控制
- **动态移动止损**: 价格每上涨4%，止损上移3%
- **ETF特定参数**: 根据不同ETF的波动特性调整止损止盈比例
- **多指标确认**: 避免单一指标产生的假信号

## 回测目标
- 验证优化策略在不同ETF上的稳定性
- 评估策略的适应性和稳健性
- 分析不同ETF的收益差异
- 提供ETF轮动策略基础

## 结果分析要点
- 各ETF的收益率对比
- 夏普比率对比
- 最大回撤对比
- 胜率和盈亏比对比
- 策略稳定性评估

## 优化方向
- 开发ETF轮动策略
- 构建ETF组合策略
- 基于波动率动态调整参数
"""
    
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj/kdj_multi_etf_optimized"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/kdj_multi_etf_optimized说明.md", 'w', encoding='utf-8') as f:
        f.write(description)

if __name__ == "__main__":
    # 创建策略说明文档
    create_strategy_description()
    
    # 定义ETF标的
    etf_symbols = ['510300', '159915', '510500', '510050', '588000']
    
    # 创建策略实例
    strategy = KDJMultiETFOptimizedStrategy(etf_symbols)
    
    # 运行回测
    all_metrics = strategy.run_backtest()
