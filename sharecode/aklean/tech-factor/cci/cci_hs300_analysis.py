import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class CCIAnalysis:
    """基于沪深300的CCI指标分析"""
    
    def __init__(self):
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/cci"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_hs300_data(self):
        """生成模拟的沪深300数据（近5年）"""
        np.random.seed(42)
        
        end_date = pd.Timestamp('2026-04-02')
        start_date = end_date - pd.Timedelta(days=5*365)
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        # 基础价格趋势
        base_price = 4000
        trend = np.linspace(0, 0.15, len(dates))  # 5年15%的基础涨幅
        
        # 添加季节性和周期性波动
        seasonal = 0.06 * np.sin(np.linspace(0, 12*np.pi, len(dates)))
        cyclic = 0.04 * np.cos(np.linspace(0, 6*np.pi, len(dates)))
        
        # 添加随机波动
        volatility = np.random.normal(0, 0.018, len(dates))
        
        # 计算价格
        prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))
        
        # 创建DataFrame
        data = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.normal(0, 0.003, len(dates))),
            'high': prices * (1 + np.random.normal(0.004, 0.006, len(dates))),
            'low': prices * (1 + np.random.normal(-0.004, 0.006, len(dates))),
            'close': prices,
            'volume': np.random.randint(10000000, 80000000, len(dates))
        })
        
        # 确保high >= close, open，low<= close, open
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        data.set_index('date', inplace=True)
        
        return data
    
    def calculate_cci(self, data, period=20):
        """计算CCI指标"""
        # 计算典型价格
        data['TP'] = (data['high'] + data['low'] + data['close']) / 3
        
        # 计算典型价格的简单移动平均
        data['SMA_TP'] = data['TP'].rolling(window=period).mean()
        
        # 计算平均偏差
        def mean_deviation(x):
            return abs(x - x.mean()).mean()
        
        data['MD'] = data['TP'].rolling(window=period).apply(mean_deviation)
        
        # 计算CCI
        data['CCI'] = (data['TP'] - data['SMA_TP']) / (0.015 * data['MD'])
        
        return data
    
    def generate_signals(self, data):
        """生成交易信号"""
        data['signal'] = 0
        
        # 超买超卖策略
        # 买入信号：CCI从-100下方穿越上来
        buy_condition = (data['CCI'] > -100) & (data['CCI'].shift(1)<= -100)
        data.loc[buy_condition, 'signal'] = 1
        
        # 卖出信号：CCI从100上方穿越下来
        sell_condition = (data['CCI'] < 100) & (data['CCI'].shift(1) >= 100)
        data.loc[sell_condition, 'signal'] = -1
        
        return data
    
    def backtest_strategy(self, data):
        """回测策略"""
        data['position'] = 0.0
        data['strategy_returns'] = 0.0
        
        position = 0
        entry_price = 0
        
        for i in range(1, len(data)):
            # 买入信号
            if data['signal'].iloc[i] == 1 and position == 0:
                position = 1
                entry_price = data['close'].iloc[i]
            
            # 卖出信号
            elif data['signal'].iloc[i] == -1 and position == 1:
                position = 0
                exit_price = data['close'].iloc[i]
                data.at[data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
            
            data.at[data.index[i], 'position'] = position
        
        # 计算累计收益
        data['cumulative_returns'] = (1 + data['strategy_returns']).cumprod()
        
        # 计算基准收益（买入持有）
        data['benchmark_returns'] = data['close'].pct_change()
        data['benchmark_cumulative'] = (1 + data['benchmark_returns']).cumprod()
        
        return data
    
    def calculate_metrics(self, data):
        """计算绩效指标"""
        # 策略收益
        total_return = (data['cumulative_returns'].iloc[-1] - 1) * 100
        years = len(data) / 252
        annualized_return = ((1 + total_return/100) ** (1/years)) - 1
        
        # 基准收益
        benchmark_total_return = (data['benchmark_cumulative'].iloc[-1] - 1) * 100
        benchmark_annualized_return = ((1 + benchmark_total_return/100) ** (1/years)) - 1
        
        # 最大回撤
        data['drawdown'] = data['cumulative_returns'] / data['cumulative_returns'].cummax() - 1
        max_drawdown = data['drawdown'].min() * 100
        
        # 交易次数
        total_trades = len(data[data['strategy_returns'] != 0])
        winning_trades = len(data[data['strategy_returns'] > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 盈亏比
        avg_win = data[data['strategy_returns'] > 0]['strategy_returns'].mean() if winning_trades > 0 else 0
        avg_loss = abs(data[data['strategy_returns']< 0]['strategy_returns'].mean()) if (total_trades - winning_trades) >0 else 0
        profit_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else float('inf')
        
        metrics = {
            '总收益率': total_return,
            '年化收益率': annualized_return * 100,
            '基准总收益率': benchmark_total_return,
            '基准年化收益率': benchmark_annualized_return * 100,
            '最大回撤': max_drawdown,
            '总交易次数': total_trades,
            '胜率': win_rate,
            '盈亏比': profit_loss_ratio
        }
        
        return metrics
    
    def plot_analysis(self, data):
        """绘制分析图表"""
        # 图1：价格与CCI指标
        plt.figure(figsize=(15, 12))
        
        # 子图1：价格和信号
        plt.subplot(3, 1, 1)
        plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
        
        # 标记买入卖出信号
        buy_signals = data[data['signal'] == 1]
        sell_signals = data[data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='卖出信号')
        
        plt.title('沪深300指数与CCI交易信号')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：CCI指标
        plt.subplot(3, 1, 2)
        plt.plot(data.index, data['CCI'], label='CCI指标', color='purple', linewidth=2)
        plt.axhline(y=100, color='red', linestyle='--', alpha=0.7, label='超买阈值(100)')
        plt.axhline(y=-100, color='green', linestyle='--', alpha=0.7, label='超卖阈值(-100)')
        plt.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        
        plt.fill_between(data.index, data['CCI'], 100, where=data['CCI']> 100, color='red', alpha=0.2)
        plt.fill_between(data.index, data['CCI'], -100, where=data['CCI']< -100, color='green', alpha=0.2)
        
        plt.title('CCI指标走势')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图3：策略收益 vs 基准收益
        plt.subplot(3, 1, 3)
        plt.plot(data.index, data['cumulative_returns'], label='CCI策略收益', linewidth=2, color='blue')
        plt.plot(data.index, data['benchmark_cumulative'], label='基准收益(买入持有)', linewidth=2, color='gray')
        
        plt.title('策略收益对比')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/cci_hs300_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("图表已保存：cci_hs300_analysis.png")
    
    def analyze_cci_effectiveness(self, data):
        """分析CCI指标的有效性"""
        # 计算CCI在不同区间的价格表现
        analysis_results = []
        
        # 超买区域（CCI > 100）
        overbought_periods = data[data['CCI'] > 100]
        if not overbought_periods.empty:
            overbought_returns = overbought_periods['close'].pct_change().mean() * 252 * 100
            analysis_results.append({
                '区间': '超买区域 (CCI > 100)',
                '平均年化收益': overbought_returns,
                '样本数': len(overbought_periods)
            })
        
        # 超卖区域（CCI < -100）
        oversold_periods = data[data['CCI']< -100]
        if not oversold_periods.empty:
            oversold_returns = oversold_periods['close'].pct_change().mean() * 252 * 100
            analysis_results.append({
                '区间': '超卖区域 (CCI < -100)',
                '平均年化收益': oversold_returns,
                '样本数': len(oversold_periods)
            })
        
        # 多头区域（0 < CCI <= 100）
        bullish_periods = data[(data['CCI'] >0) & (data['CCI']<= 100)]
        if not bullish_periods.empty:
            bullish_returns = bullish_periods['close'].pct_change().mean() * 252 * 100
            analysis_results.append({
                '区间': '多头区域 (0 < CCI <= 100)',
                '平均年化收益': bullish_returns,
                '样本数': len(bullish_periods)
            })
        
        # 空头区域（-100 <= CCI <= 0）
        bearish_periods = data[(data['CCI'] >= -100) & (data['CCI']<= 0)]
        if not bearish_periods.empty:
            bearish_returns = bearish_periods['close'].pct_change().mean() * 252 * 100
            analysis_results.append({
                '区间': '空头区域 (-100 <= CCI <= 0)',
                '平均年化收益': bearish_returns,
                '样本数': len(bearish_periods)
            })
        
        return analysis_results
    
    def run_analysis(self):
        """运行完整分析"""
        print("开始生成沪深300数据...")
        data = self.generate_hs300_data()
        
        print("计算CCI指标...")
        data = self.calculate_cci(data)
        
        print("生成交易信号...")
        data = self.generate_signals(data)
        
        print("回测策略...")
        data = self.backtest_strategy(data)
        
        print("计算绩效指标...")
        metrics = self.calculate_metrics(data)
        
        print("绘制分析图表...")
        self.plot_analysis(data)
        
        print("分析CCI有效性...")
        effectiveness = self.analyze_cci_effectiveness(data)
        
        # 保存结果
        data.to_csv(f"{self.output_dir}/cci_hs300_data.csv")
        
        return metrics, effectiveness

if __name__ == "__main__":
    analysis = CCIAnalysis()
    metrics, effectiveness = analysis.run_analysis()
    
    print("\n=== 策略绩效指标 ===")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}%")
        else:
            print(f"{key}: {value}")
    
    print("\n=== CCI指标有效性分析 ===")
    for result in effectiveness:
        print(f"{result['区间']}:")
        print(f"  平均年化收益: {result['平均年化收益']:.2f}%")
        print(f"  样本数: {result['样本数']}")
        print()
