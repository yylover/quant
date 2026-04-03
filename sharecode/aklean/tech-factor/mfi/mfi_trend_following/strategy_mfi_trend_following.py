import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class MFITrendFollowingStrategy:
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
        
        self.data = data
    
    def calculate_ma(self, ma_period=20):
        """计算移动平均线"""
        data = self.data.copy()
        data['ma'] = data['close'].rolling(window=ma_period).mean()
        self.data = data
    
    def generate_signals(self):
        """生成MFI趋势跟随交易信号"""
        data = self.data.copy()
        
        # MFI趋势跟随策略：
        # MFI > 50 表示资金流入，处于上升趋势
        # MFI < 50 表示资金流出，处于下降趋势
        
        # 买入信号：MFI > 50，价格在均线上方
        buy_condition = (
            (data['mfi'] > 50) &
            (data['close'] > data['ma'])
        )
        
        # 卖出信号：MFI < 50，价格在均线下方
        sell_condition = (
            (data['mfi'] < 50) &
            (data['close'] < data['ma'])
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
        ax1.plot(data.index, data['ma'], label='20日均线', color='orange', alpha=0.7)
        
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
        
        ax1.set_title('MFI趋势跟随策略 - 沪深300', fontsize=16)
        ax1.set_ylabel('价格', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # 绘制MFI指标
        ax2.plot(data.index, data['mfi'], label='MFI', color='purple')
        
        # 添加MFI中线
        ax2.axhline(y=50, color='gray', linestyle='--', label='MFI中线(50)')
        
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
        plt.savefig('mfi_trend_following_strategy_backtest.png', dpi=300, bbox_inches='tight')
    
    def save_results(self):
        """保存回测结果"""
        # 保存交易记录
        trades = self.data[self.data['signal'] != 0].copy()
        trades.to_csv('mfi_trend_following_strategy_backtest.csv')
    
    def generate_report(self):
        """生成策略说明文档"""
        report = f"""# MFI趋势跟随策略说明

## 策略原理
MFI趋势跟随策略基于资金流量指标判断市场趋势方向，结合移动平均线确认趋势强度。

## 策略逻辑

### 买入条件
1. MFI > 50（资金流入，处于上升趋势）
2. 价格在20日均线上方（趋势确认）

### 卖出条件
1. MFI < 50（资金流出，处于下降趋势）
2. 价格在20日均线下方（趋势确认）

## 策略参数
- **MFI周期**：14
- **移动平均线周期**：20日
- **趋势判断阈值**：MFI > 50（上升趋势），MFI < 50（下降趋势）

## 回测结果
- **策略总收益率**：{self.results['total_return']:.2%}
- **基准收益率**：{self.results['benchmark_return']:.2%}
- **超额收益**：{(self.results['total_return'] - self.results['benchmark_return']):.2%}
- **年化收益率**：{self.results['annualized_return']:.2%}
- **最大回撤**：{self.results['max_drawdown']:.2%}
- **胜率**：{self.results['win_rate']:.2%}
- **盈亏比**：{self.results['profit_loss_ratio']:.2f}

## 策略特点
1. **趋势跟随**：跟随市场主要趋势
2. **资金确认**：结合资金流向确认趋势
3. **均线过滤**：使用均线过滤假信号
4. **信号稳定**：减少频繁交易

## 适用市场环境
- 适合趋势市场
- 在震荡市场中表现可能不佳
- 对趋势变化反应较为及时

## 策略优势
1. 结合资金流向和价格趋势
2. 信号相对稳定，减少噪音
3. 适合中长期趋势跟踪

## 策略劣势
1. 在震荡市场中可能产生较多假信号
2. 趋势识别可能滞后于实际趋势变化
"""
        
        with open('mfi_trend_following_strategy说明.md', 'w', encoding='utf-8') as f:
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
        
        print("MFI趋势跟随策略回测完成！")
        print(f"策略总收益率: {self.results['total_return']:.2%}")
        print(f"基准收益率: {self.results['benchmark_return']:.2%}")
        print(f"超额收益: {(self.results['total_return'] - self.results['benchmark_return']):.2%}")

if __name__ == '__main__':
    strategy = MFITrendFollowingStrategy()
    strategy.run()
