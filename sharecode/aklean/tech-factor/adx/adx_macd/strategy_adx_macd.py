import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ADXMACDStrategy:
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
    
    def calculate_adx(self, period=14):
        """计算ADX指标"""
        data = self.data.copy()
        
        # 计算真实范围(TR)
        data['tr'] = np.maximum(
            data['high'] - data['low'],
            np.maximum(
                abs(data['high'] - data['close'].shift(1)),
                abs(data['low'] - data['close'].shift(1))
            )
        )
        
        # 计算正趋向变动(+DM)和负趋向变动(-DM)
        data['plus_dm'] = np.where(
            (data['high'] - data['high'].shift(1)) > (data['low'].shift(1) - data['low']),
            np.maximum(data['high'] - data['high'].shift(1), 0),
            0
        )
        
        data['minus_dm'] = np.where(
            (data['low'].shift(1) - data['low']) > (data['high'] - data['high'].shift(1)),
            np.maximum(data['low'].shift(1) - data['low'], 0),
            0
        )
        
        # 计算平滑的TR、+DM和-DM
        data['smooth_tr'] = data['tr'].rolling(window=period).mean()
        data['smooth_plus_dm'] = data['plus_dm'].rolling(window=period).mean()
        data['smooth_minus_dm'] = data['minus_dm'].rolling(window=period).mean()
        
        # 计算方向性指标(DI)
        data['plus_di'] = (data['smooth_plus_dm'] / data['smooth_tr']) * 100
        data['minus_di'] = (data['smooth_minus_dm'] / data['smooth_tr']) * 100
        
        # 计算趋向指数(DX)
        data['dx'] = (abs(data['plus_di'] - data['minus_di']) / 
                      (data['plus_di'] + data['minus_di'])) * 100
        
        # 计算平均趋向指数(ADX)
        data['adx'] = data['dx'].rolling(window=period).mean()
        
        self.data = data
    
    def calculate_macd(self, fast_period=12, slow_period=26, signal_period=9):
        """计算MACD指标"""
        data = self.data.copy()
        
        # 计算快速和慢速移动平均线
        data['ema_fast'] = data['close'].ewm(span=fast_period, adjust=False).mean()
        data['ema_slow'] = data['close'].ewm(span=slow_period, adjust=False).mean()
        
        # 计算MACD线
        data['macd_line'] = data['ema_fast'] - data['ema_slow']
        
        # 计算信号线
        data['signal_line'] = data['macd_line'].ewm(span=signal_period, adjust=False).mean()
        
        # 计算柱状图
        data['macd_histogram'] = data['macd_line'] - data['signal_line']
        
        self.data = data
    
    def generate_signals(self):
        """生成ADX+MACD交易信号"""
        data = self.data.copy()
        
        # ADX+MACD组合策略：
        # 买入：ADX > 20（趋势存在），+DI > -DI（上升趋势），MACD柱状图从负转正
        # 卖出：ADX > 20（趋势存在），-DI > +DI（下降趋势），MACD柱状图从正转负
        
        # 买入信号
        buy_condition = (
            (data['adx'] > 20) &
            (data['plus_di'] > data['minus_di']) &
            (data['macd_histogram'] > 0) &
            (data['macd_histogram'].shift(1) <= 0)
        )
        
        # 卖出信号
        sell_condition = (
            (data['adx'] > 20) &
            (data['minus_di'] > data['plus_di']) &
            (data['macd_histogram'] < 0) &
            (data['macd_histogram'].shift(1) >= 0)
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
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(16, 20), gridspec_kw={'height_ratios': [3, 1, 1, 1]})
        
        # 绘制价格和信号
        ax1.plot(data.index, data['close'], label='沪深300收盘价', color='blue')
        
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
        
        ax1.set_title('ADX+MACD组合策略 - 沪深300', fontsize=16)
        ax1.set_ylabel('价格', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # 绘制ADX指标
        ax2.plot(data.index, data['adx'], label='ADX', color='black')
        ax2.plot(data.index, data['plus_di'], label='+DI', color='green')
        ax2.plot(data.index, data['minus_di'], label='-DI', color='red')
        
        # 添加ADX阈值线
        ax2.axhline(y=20, color='gray', linestyle='--', label='ADX阈值(20)')
        
        ax2.set_ylabel('ADX/DI值', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')
        
        # 绘制MACD指标
        ax3.plot(data.index, data['macd_line'], label='MACD线', color='blue')
        ax3.plot(data.index, data['signal_line'], label='信号线', color='red')
        
        # 绘制MACD柱状图
        ax3.bar(data.index, data['macd_histogram'], color='gray', alpha=0.5, label='MACD柱状图')
        
        # 添加零轴
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax3.set_ylabel('MACD值', fontsize=12)
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper left')
        
        # 绘制收益率对比
        ax4.plot(data.index, data['cumulative_return'], label='策略收益率', color='blue', linewidth=2)
        ax4.plot(data.index, data['benchmark_return'], label='基准收益率', color='gray', linewidth=1.5)
        
        ax4.set_xlabel('日期', fontsize=12)
        ax4.set_ylabel('累计收益率', fontsize=12)
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='upper left')
        
        plt.tight_layout()
        plt.savefig('adx_macd_strategy_backtest.png', dpi=300, bbox_inches='tight')
    
    def save_results(self):
        """保存回测结果"""
        # 保存交易记录
        trades = self.data[self.data['signal'] != 0].copy()
        trades.to_csv('adx_macd_strategy_backtest.csv')
    
    def generate_report(self):
        """生成策略说明文档"""
        report = f"""# ADX+MACD组合策略说明

## 策略原理
ADX+MACD组合策略结合ADX指标识别趋势强度和方向，同时使用MACD指标确认趋势动能变化，提高交易信号的准确性。

## 策略逻辑

### 买入条件
1. ADX > 20（趋势存在）
2. +DI > -DI（上升趋势）
3. MACD柱状图从负值转为正值（动能增强）

### 卖出条件
1. ADX > 20（趋势存在）
2. -DI > +DI（下降趋势）
3. MACD柱状图从正值转为负值（动能减弱）

## 策略参数
- **ADX周期**：14
- **MACD快速周期**：12
- **MACD慢速周期**：26
- **MACD信号周期**：9
- **趋势阈值**：ADX > 20

## 回测结果
- **策略总收益率**：{self.results['total_return']:.2%}
- **基准收益率**：{self.results['benchmark_return']:.2%}
- **超额收益**：{(self.results['total_return'] - self.results['benchmark_return']):.2%}
- **年化收益率**：{self.results['annualized_return']:.2%}
- **最大回撤**：{self.results['max_drawdown']:.2%}
- **胜率**：{self.results['win_rate']:.2%}
- **盈亏比**：{self.results['profit_loss_ratio']:.2f}

## 策略特点
1. **趋势与动能结合**：ADX识别趋势，MACD确认动能
2. **信号确认**：多指标确认提高信号可靠性
3. **趋势过滤**：ADX < 20时不交易，避免震荡市场
4. **及时响应**：MACD能及时捕捉动能变化

## 适用市场环境
- 适合明显趋势市场
- 在震荡市场中保持观望
- 对趋势反转反应及时

## 优化建议
1. 调整ADX周期参数
2. 优化MACD参数组合
3. 加入成交量确认
4. 设置动态止损策略
"""
        
        with open('adx_macd_strategy说明.md', 'w', encoding='utf-8') as f:
            f.write(report)
    
    def run(self):
        """运行完整的策略回测"""
        self.generate_hs300_data()
        self.calculate_adx()
        self.calculate_macd()
        self.generate_signals()
        self.calculate_returns()
        self.plot_results()
        self.save_results()
        self.generate_report()
        
        print("ADX+MACD组合策略回测完成！")
        print(f"策略总收益率: {self.results['total_return']:.2%}")
        print(f"基准收益率: {self.results['benchmark_return']:.2%}")
        print(f"超额收益: {(self.results['total_return'] - self.results['benchmark_return']):.2%}")

if __name__ == '__main__':
    strategy = ADXMACDStrategy()
    strategy.run()
