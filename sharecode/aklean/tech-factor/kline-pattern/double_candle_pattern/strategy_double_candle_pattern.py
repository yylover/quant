import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class DoubleCandlePatternStrategy:
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
    
    def identify_double_candle_patterns(self):
        """识别双K线形态"""
        data = self.data.copy()
        
        # 计算K线实体和影线长度
        data['body'] = abs(data['open'] - data['close'])
        data['total_range'] = data['high'] - data['low']
        
        # 识别吞没形态(Bullish Engulfing)
        # 第一根K线：阴线，实体较小
        # 第二根K线：阳线，实体完全吞没第一根K线的实体
        data['bullish_engulfing'] = (
            (data['close'].shift(1) < data['open'].shift(1)) &  # 第一根阴线
            (data['close'] > data['open']) &  # 第二根阳线
            (data['open'] < data['close'].shift(1)) &  # 第二根开盘价低于第一根收盘价
            (data['close'] > data['open'].shift(1)) &  # 第二根收盘价高于第一根开盘价
            (data['body'] > 1.5 * data['body'].shift(1))  # 第二根实体较大
        )
        
        # 识别乌云盖顶(Bearish Engulfing)
        # 第一根K线：阳线，实体较大
        # 第二根K线：阴线，实体完全吞没第一根K线的实体
        data['bearish_engulfing'] = (
            (data['close'].shift(1) > data['open'].shift(1)) &  # 第一根阳线
            (data['close'] < data['open']) &  # 第二根阴线
            (data['open'] > data['close'].shift(1)) &  # 第二根开盘价高于第一根收盘价
            (data['close'] < data['open'].shift(1)) &  # 第二根收盘价低于第一根开盘价
            (data['body'] > 1.5 * data['body'].shift(1))  # 第二根实体较大
        )
        
        # 识别刺透形态(Piercing Pattern)
        # 第一根K线：大阴线
        # 第二根K线：阳线，收盘价超过第一根K线实体的一半
        data['piercing_pattern'] = (
            (data['close'].shift(1) < data['open'].shift(1)) &  # 第一根阴线
            (data['close'] > data['open']) &  # 第二根阳线
            (data['open'] < data['low'].shift(1)) &  # 第二根开盘价低于第一根最低价
            (data['close'] > (data['open'].shift(1) + data['close'].shift(1)) / 2)  # 收盘价超过第一根实体一半
        )
        
        # 识别乌云盖顶的变种(Dark Cloud Cover)
        # 第一根K线：阳线
        # 第二根K线：阴线，开盘价高于第一根最高价，收盘价低于第一根实体的一半
        data['dark_cloud_cover'] = (
            (data['close'].shift(1) > data['open'].shift(1)) &  # 第一根阳线
            (data['close'] < data['open']) &  # 第二根阴线
            (data['open'] > data['high'].shift(1)) &  # 第二根开盘价高于第一根最高价
            (data['close'] < (data['open'].shift(1) + data['close'].shift(1)) / 2)  # 收盘价低于第一根实体一半
        )
        
        # 识别早晨之星的简化版本(简化为双K线)
        data['morning_star_double'] = (
            (data['close'].shift(1) < data['open'].shift(1)) &  # 第一根阴线
            (data['close'] > data['open']) &  # 第二根阳线
            (data['body'] > data['body'].shift(1))  # 第二根实体较大
        )
        
        # 识别黄昏之星的简化版本(简化为双K线)
        data['evening_star_double'] = (
            (data['close'].shift(1) > data['open'].shift(1)) &  # 第一根阳线
            (data['close'] < data['open']) &  # 第二根阴线
            (data['body'] > data['body'].shift(1))  # 第二根实体较大
        )
        
        self.data = data
    
    def generate_signals(self):
        """生成双K线形态交易信号"""
        data = self.data.copy()
        
        # 定义趋势：使用简单的移动平均线
        data['ma20'] = data['close'].rolling(window=20).mean()
        data['ma50'] = data['close'].rolling(window=50).mean()
        data['uptrend'] = (data['ma20'] > data['ma50']) & (data['close'] > data['ma20'])
        data['downtrend'] = (data['ma20'] < data['ma50']) & (data['close'] < data['ma20'])
        
        # 买入信号：
        # 1. 看涨吞没形态 + 下跌趋势
        # 2. 刺透形态 + 下跌趋势
        # 3. 早晨之星简化版 + 下跌趋势
        buy_condition = (
            (data['bullish_engulfing'] | data['piercing_pattern'] | data['morning_star_double']) &
            data['downtrend']
        )
        
        # 卖出信号：
        # 1. 看跌吞没形态 + 上升趋势
        # 2. 乌云盖顶 + 上升趋势
        # 3. 黄昏之星简化版 + 上升趋势
        sell_condition = (
            (data['bearish_engulfing'] | data['dark_cloud_cover'] | data['evening_star_double']) &
            data['uptrend']
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
        
        ax1.set_title('双K线形态策略 - 沪深300', fontsize=16)
        ax1.set_ylabel('价格', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # 绘制双K线形态指标
        ax2.plot(data.index, data['bullish_engulfing'].astype(int), label='看涨吞没', color='green', alpha=0.7)
        ax2.plot(data.index, -data['bearish_engulfing'].astype(int), label='看跌吞没', color='red', alpha=0.7)
        ax2.plot(data.index, data['piercing_pattern'].astype(int)*2, label='刺透形态', color='blue', alpha=0.7)
        
        ax2.set_ylabel('双K线形态', fontsize=12)
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
        plt.savefig('double_candle_pattern_strategy_backtest.png', dpi=300, bbox_inches='tight')
    
    def save_results(self):
        """保存回测结果"""
        # 保存交易记录
        trades = self.data[self.data['signal'] != 0].copy()
        trades.to_csv('double_candle_pattern_strategy_backtest.csv')
    
    def generate_report(self):
        """生成策略说明文档"""
        report = f"""# 双K线形态策略说明

## 策略原理
双K线形态策略基于经典的双K线组合形态识别，通过识别特定的K线组合来判断市场转折点，进行买卖交易。

## 策略逻辑

### 识别的双K线形态
- **看涨吞没(Bullish Engulfing)**：第二根阳线完全吞没第一根阴线的实体
- **看跌吞没(Bearish Engulfing)**：第二根阴线完全吞没第一根阳线的实体
- **刺透形态(Piercing Pattern)**：第二根阳线收盘价超过第一根阴线实体的一半
- **乌云盖顶(Dark Cloud Cover)**：第二根阴线收盘价低于第一根阳线实体的一半
- **早晨之星简化版**：第一根阴线，第二根大阳线
- **黄昏之星简化版**：第一根阳线，第二根大阴线

### 买入条件
- 看涨吞没形态 + 下跌趋势
- 刺透形态 + 下跌趋势
- 早晨之星简化版 + 下跌趋势

### 卖出条件
- 看跌吞没形态 + 上升趋势
- 乌云盖顶 + 上升趋势
- 黄昏之星简化版 + 上升趋势

## 策略参数
- **均线周期**：20日、50日
- **趋势判断**：20日均线与50日均线的关系

## 回测结果
- **策略总收益率**：{self.results['total_return']:.2%}
- **基准收益率**：{self.results['benchmark_return']:.2%}
- **超额收益**：{(self.results['total_return'] - self.results['benchmark_return']):.2%}
- **年化收益率**：{self.results['annualized_return']:.2%}
- **最大回撤**：{self.results['max_drawdown']:.2%}
- **胜率**：{self.results['win_rate']:.2%}
- **盈亏比**：{self.results['profit_loss_ratio']:.2f}

## 策略特点
1. **形态确认**：基于双K线组合确认信号
2. **趋势结合**：结合均线判断趋势方向
3. **信号可靠**：双K线形态比单K线形态更可靠
4. **风险控制**：通过趋势过滤减少假信号

## 适用市场环境
- 适合震荡市场和趋势转折点
- 在明显趋势市场中表现较好
- 对市场情绪变化反应敏感

## 策略优势
1. 双K线形态提供更强的反转信号
2. 结合趋势判断，提高信号可靠性
3. 适合波段操作和中线交易

## 策略劣势
1. K线形态识别可能存在主观性
2. 信号频率较低，可能错过一些交易机会
3. 在快速波动市场中可能产生假信号
"""
        
        with open('double_candle_pattern_strategy说明.md', 'w', encoding='utf-8') as f:
            f.write(report)
    
    def run(self):
        """运行完整的策略回测"""
        self.generate_hs300_data()
        self.identify_double_candle_patterns()
        self.generate_signals()
        self.calculate_returns()
        self.plot_results()
        self.save_results()
        self.generate_report()
        
        print("双K线形态策略回测完成！")
        print(f"策略总收益率: {self.results['total_return']:.2%}")
        print(f"基准收益率: {self.results['benchmark_return']:.2%}")
        print(f"超额收益: {(self.results['total_return'] - self.results['benchmark_return']):.2%}")

if __name__ == '__main__':
    strategy = DoubleCandlePatternStrategy()
    strategy.run()
