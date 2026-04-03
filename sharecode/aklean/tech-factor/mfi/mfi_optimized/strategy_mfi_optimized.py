import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class MFIOptimizedStrategy:
    def __init__(self):
        self.data = None
        self.results = {}
    
    def generate_hs300_data(self):
        """生成沪深300近5年的模拟数据"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5*365)
        
        # 创建日期序列
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        # 生成基础价格
        base_price = 4000
        volatility = 0.01
        trend = 0.0002
        
        # 生成随机价格序列
        np.random.seed(42)
        returns = np.random.normal(trend, volatility, len(dates))
        prices = base_price * np.cumprod(1 + returns)
        
        # 添加一些趋势和波动
        prices = prices * (1 + np.sin(np.linspace(0, 10*np.pi, len(dates))) * 0.05)
        
        # 创建DataFrame
        self.data = pd.DataFrame({
            'date': dates,
            'open': prices * (1 - np.random.normal(0, 0.005, len(dates))),
            'high': prices * (1 + np.random.normal(0, 0.01, len(dates))),
            'low': prices * (1 - np.random.normal(0, 0.01, len(dates))),
            'close': prices,
            'volume': np.random.normal(100000000, 20000000, len(dates)).astype(int)
        })
        
        # 确保最高价大于等于开盘价和收盘价，最低价小于等于开盘价和收盘价
        self.data['high'] = self.data[['open', 'high', 'close']].max(axis=1)
        self.data['low'] = self.data[['open', 'low', 'close']].min(axis=1)
        
        self.data.set_index('date', inplace=True)
    
    def calculate_mfi(self, period=14):
        """计算资金流量指标(MFI)"""
        data = self.data.copy()
        
        # 计算典型价格(Typical Price)
        data['typical_price'] = (data['high'] + data['low'] + data['close']) / 3
        
        # 计算资金流量(Money Flow)
        data['money_flow'] = data['typical_price'] * data['volume']
        
        # 计算正资金流量和负资金流量
        data['positive_mf'] = np.where(
            data['typical_price'] > data['typical_price'].shift(1),
            data['money_flow'],
            0
        )
        
        data['negative_mf'] = np.where(
            data['typical_price'] < data['typical_price'].shift(1),
            data['money_flow'],
            0
        )
        
        # 计算资金比率(Money Ratio)
        data['money_ratio'] = data['positive_mf'].rolling(window=period).sum() / data['negative_mf'].rolling(window=period).sum()
        
        # 计算资金流量指标(MFI)
        data['mfi'] = 100 - (100 / (1 + data['money_ratio']))
        
        # 计算MFI变化率
        data['mfi_change'] = data['mfi'].diff()
        
        self.data = data
    
    def calculate_ma(self):
        """计算多周期移动平均线"""
        data = self.data.copy()
        data['ma20'] = data['close'].rolling(window=20).mean()
        data['ma50'] = data['close'].rolling(window=50).mean()
        data['ma100'] = data['close'].rolling(window=100).mean()
        self.data = data
    
    def generate_signals(self):
        """生成优化的MFI交易信号"""
        data = self.data.copy()
        
        # 定义大趋势
        data['uptrend'] = (data['ma20'] > data['ma50']) & (data['ma50'] > data['ma100'])
        data['downtrend'] = (data['ma20'] < data['ma50']) & (data['ma50'] < data['ma100'])
        
        # MFI优化策略：
        # 在上升趋势中，寻找超卖机会买入
        # 在下降趋势中，寻找超买机会卖出
        
        # 买入信号：
        # 1. 大趋势向上
        # 2. MFI < 30（超卖）
        # 3. MFI开始上升（mfi_change > 0）
        buy_condition = (
            data['uptrend'] &
            (data['mfi'] < 30) &
            (data['mfi_change'] > 0)
        )
        
        # 卖出信号：
        # 1. 大趋势向下
        # 2. MFI > 70（超买）
        # 3. MFI开始下降（mfi_change < 0）
        sell_condition = (
            data['downtrend'] &
            (data['mfi'] > 70) &
            (data['mfi_change'] < 0)
        )
        
        # 持仓状态
        data['position'] = 0
        data.loc[buy_condition, 'position'] = 1
        data.loc[sell_condition, 'position'] = -1
        
        # 保持持仓状态，直到反向信号出现
        data['position'] = data['position'].ffill()
        
        # 交易信号：只有当持仓状态改变时才产生信号
        data['signal'] = data['position'] - data['position'].shift(1)
        
        self.data = data
    
    def calculate_returns(self):
        """计算策略收益率"""
        data = self.data.copy()
        
        # 计算每日收益率
        data['daily_return'] = data['close'].pct_change()
        
        # 计算策略收益率
        data['strategy_return'] = data['position'].shift(1) * data['daily_return']
        
        # 计算累计收益率
        data['cumulative_return'] = (1 + data['strategy_return']).cumprod()
        data['benchmark_return'] = (1 + data['daily_return']).cumprod()
        
        self.data = data
        
        # 保存结果
        self.results['total_return'] = data['cumulative_return'].iloc[-1] - 1
        self.results['benchmark_return'] = data['benchmark_return'].iloc[-1] - 1
        
        # 计算胜率
        winning_trades = len(data[data['strategy_return'] > 0])
        losing_trades = len(data[data['strategy_return'] < 0])
        self.results['win_rate'] = winning_trades / (winning_trades + losing_trades) if (winning_trades + losing_trades) > 0 else 0
        
        # 计算盈亏比
        avg_win = data[data['strategy_return'] > 0]['strategy_return'].mean()
        avg_loss = abs(data[data['strategy_return'] < 0]['strategy_return'].mean())
        self.results['profit_loss_ratio'] = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 计算最大回撤
        data['cum_max'] = data['cumulative_return'].cummax()
        data['drawdown'] = (data['cumulative_return'] / data['cum_max']) - 1
        self.results['max_drawdown'] = data['drawdown'].min()
        
        # 计算年化收益率
        days = len(data)
        self.results['annualized_return'] = (1 + self.results['total_return']) ** (252/days) - 1
    
    def plot_results(self):
        """绘制策略结果"""
        data = self.data.copy()
        
        # 创建图表
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 15), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # 绘制价格和信号
        ax1.plot(data.index, data['close'], label='沪深300收盘价', color='blue')
        ax1.plot(data.index, data['ma20'], label='20日均线', color='orange', alpha=0.7)
        ax1.plot(data.index, data['ma50'], label='50日均线', color='green', alpha=0.7)
        ax1.plot(data.index, data['ma100'], label='100日均线', color='red', alpha=0.7)
        
        # 标记买入信号
        buy_signals = data[data['signal'] > 0]
        ax1.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='买入信号')
        
        # 标记卖出信号
        sell_signals = data[data['signal'] < 0]
        ax1.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='卖出信号')
        
        # 绘制持仓区域
        long_periods = data[data['position'] == 1]
        short_periods = data[data['position'] == -1]
        
        for i in range(len(long_periods) - 1):
            start_date = long_periods.index[i]
            end_date = long_periods.index[i + 1]
            ax1.axvspan(start_date, end_date, alpha=0.1, color='green')
        
        for i in range(len(short_periods) - 1):
            start_date = short_periods.index[i]
            end_date = short_periods.index[i + 1]
            ax1.axvspan(start_date, end_date, alpha=0.1, color='red')
        
        ax1.set_title('MFI优化策略 - 沪深300', fontsize=16)
        ax1.set_ylabel('价格', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # 绘制MFI指标
        ax2.plot(data.index, data['mfi'], label='MFI', color='purple')
        
        # 添加MFI阈值线
        ax2.axhline(y=30, color='green', linestyle='--', label='超卖阈值(30)')
        ax2.axhline(y=70, color='red', linestyle='--', label='超买阈值(70)')
        
        ax2.set_ylabel('MFI值', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')
        
        # 绘制收益率对比
        ax3.plot(data.index, data['cumulative_return'], label='策略收益率', color='blue', linewidth=2)
        ax3.plot(data.index, data['benchmark_return'], label='基准收益率', color='gray', linewidth=1.5)
        
        ax3.set_xlabel('日期', fontsize=12)
        ax3.set_ylabel('累计收益率', fontsize=12)
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper left')
        
        plt.tight_layout()
        plt.savefig('mfi_optimized_strategy_backtest.png', dpi=300, bbox_inches='tight')
    
    def save_results(self):
        """保存回测结果"""
        # 保存交易记录
        trades = self.data[self.data['signal'] != 0].copy()
        trades.to_csv('mfi_optimized_strategy_backtest.csv')
    
    def generate_report(self):
        """生成策略说明文档"""
        report = f"""# MFI优化策略说明

## 策略原理
MFI优化策略结合多周期均线确认大趋势，使用MFI指标寻找最佳入场时机，实现更可靠的交易信号。

## 策略逻辑

### 大趋势定义
- **上升趋势**：20日均线 > 50日均线 > 100日均线
- **下降趋势**：20日均线 < 50日均线 < 100日均线

### 买入条件
1. 大趋势向上（20日 > 50日 > 100日均线）
2. MFI < 30（超卖状态）
3. MFI开始上升（mfi_change > 0）

### 卖出条件
1. 大趋势向下（20日 < 50日 < 100日均线）
2. MFI > 70（超买状态）
3. MFI开始下降（mfi_change < 0）

## 策略参数
- **MFI周期**：14
- **均线周期**：20日、50日、100日
- **超卖阈值**：MFI < 30
- **超买阈值**：MFI > 70

## 回测结果
- **策略总收益率**：{self.results['total_return']:.2%}
- **基准收益率**：{self.results['benchmark_return']:.2%}
- **超额收益**：{(self.results['total_return'] - self.results['benchmark_return']):.2%}
- **年化收益率**：{self.results['annualized_return']:.2%}
- **最大回撤**：{self.results['max_drawdown']:.2%}
- **胜率**：{self.results['win_rate']:.2%}
- **盈亏比**：{self.results['profit_loss_ratio']:.2f}

## 策略特点
1. **多周期确认**：使用三条均线确认大趋势
2. **时机选择**：在趋势确认的基础上寻找最佳入场点
3. **逆向思维**：在超卖时买入，超买时卖出
4. **信号过滤**：通过趋势确认过滤假信号

## 适用市场环境
- 适合明显趋势市场
- 在震荡市场中保持观望
- 对市场转折点反应及时

## 策略优势
1. 多周期确认提高信号可靠性
2. 结合趋势和逆向思维
3. 减少不必要的交易
4. 风险控制较好

## 策略劣势
1. 信号频率较低
2. 在快速反转市场中可能反应滞后
"""
        
        with open('mfi_optimized_strategy说明.md', 'w', encoding='utf-8') as f:
            f.write(report)
    
    def run(self):
        """运行完整的策略回测"""
        self.generate_hs300_data()
        self.calculate_mfi()
        self.calculate_ma()
        self.generate_signals()
        self.calculate_returns()
        self.plot_results()
        self.save_results()
        self.generate_report()
        
        print("MFI优化策略回测完成！")
        print(f"策略总收益率: {self.results['total_return']:.2%}")
        print(f"基准收益率: {self.results['benchmark_return']:.2%}")
        print(f"超额收益: {(self.results['total_return'] - self.results['benchmark_return']):.2%}")

if __name__ == '__main__':
    strategy = MFIOptimizedStrategy()
    strategy.run()
