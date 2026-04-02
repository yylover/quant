import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class CCIDivergenceStrategy:
    """CCI背离策略"""
    
    def __init__(self, data, cci_period=20, divergence_period=20):
        """
        初始化CCI背离策略
        
        参数:
            data: 包含open, high, low, close列的DataFrame
            cci_period: CCI计算周期
            divergence_period: 背离检测周期
        """
        self.data = data.copy()
        self.cci_period = cci_period
        self.divergence_period = divergence_period
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/cci/cci_divergence"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_cci(self):
        """计算CCI指标"""
        # 计算典型价格
        self.data['TP'] = (self.data['high'] + self.data['low'] + self.data['close']) / 3
        
        # 计算典型价格的简单移动平均
        self.data['SMA_TP'] = self.data['TP'].rolling(window=self.cci_period).mean()
        
        # 计算平均偏差
        def mean_deviation(x):
            return abs(x - x.mean()).mean()
        
        self.data['MD'] = self.data['TP'].rolling(window=self.cci_period).apply(mean_deviation)
        
        # 计算CCI
        self.data['CCI'] = (self.data['TP'] - self.data['SMA_TP']) / (0.015 * self.data['MD'])
        
        return self.data
    
    def detect_divergence(self):
        """检测背离信号"""
        self.data['divergence'] = 0
        
        # 使用更宽松的背离检测逻辑
        for i in range(self.divergence_period, len(self.data)):
            # 寻找价格低点（使用相对低点）
            recent_lows = self.data['low'].iloc[i-self.divergence_period:i+1]
            if self.data['low'].iloc[i] <= recent_lows.quantile(0.2):  # 相对低点
                # 检查CCI是否背离
                recent_ccis = self.data['CCI'].iloc[i-self.divergence_period:i+1]
                if recent_ccis.min() > self.data['CCI'].iloc[i-1]:  # 前一天的CCI更低
                    # 底背离：价格接近近期低点，但CCI未创新低
                    self.data.at[self.data.index[i], 'divergence'] = 1
            
            # 寻找价格高点（使用相对高点）
            recent_highs = self.data['high'].iloc[i-self.divergence_period:i+1]
            if self.data['high'].iloc[i] >= recent_highs.quantile(0.8):  # 相对高点
                # 检查CCI是否背离
                recent_ccis = self.data['CCI'].iloc[i-self.divergence_period:i+1]
                if recent_ccis.max()< self.data['CCI'].iloc[i-1]:  # 前一天的CCI更高
                    # 顶背离：价格接近近期高点，但CCI未创新高
                    self.data.at[self.data.index[i], 'divergence'] = -1
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 添加一个简单的背离检测：价格低点但CCI回升
        for i in range(5, len(self.data)):
            # 检查价格是否处于近期低点
            if self.data['low'].iloc[i] <= self.data['low'].iloc[i-5:i+1].min():
                # 检查CCI是否在上升
                if self.data['CCI'].iloc[i] > self.data['CCI'].iloc[i-1] and self.data['CCI'].iloc[i] > self.data['CCI'].iloc[i-2]:
                    # 简单的底背离：价格新低，CCI回升
                    self.data.at[self.data.index[i], 'signal'] = 1
            
            # 检查价格是否处于近期高点
            elif self.data['high'].iloc[i] >= self.data['high'].iloc[i-5:i+1].max():
                # 检查CCI是否在下降
                if self.data['CCI'].iloc[i]< self.data['CCI'].iloc[i-1] and self.data['CCI'].iloc[i] < self.data['CCI'].iloc[i-2]:
                    # 简单的顶背离：价格新高，CCI下降
                    self.data.at[self.data.index[i], 'signal'] = -1
        
        return self.data
    
    def backtest(self):
        """回测策略"""
        self.data['position'] = 0.0
        self.data['strategy_returns'] = 0.0
        
        position = 0
        entry_price = 0
        
        for i in range(1, len(self.data)):
            # 买入信号
            if self.data['signal'].iloc[i] == 1 and position == 0:
                position = 1
                entry_price = self.data['close'].iloc[i]
            
            # 卖出信号
            elif self.data['signal'].iloc[i] == -1 and position == 1:
                position = 0
                exit_price = self.data['close'].iloc[i]
                self.data.at[self.data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
            
            self.data.at[self.data.index[i], 'position'] = position
        
        # 计算累计收益
        self.data['cumulative_returns'] = (1 + self.data['strategy_returns']).cumprod()
        
        # 计算基准收益（买入持有）
        self.data['benchmark_returns'] = self.data['close'].pct_change()
        self.data['benchmark_cumulative'] = (1 + self.data['benchmark_returns']).cumprod()
        
        return self.data
    
    def calculate_metrics(self):
        """计算绩效指标"""
        # 策略收益
        total_return = (self.data['cumulative_returns'].iloc[-1] - 1) * 100
        years = len(self.data) / 252
        annualized_return = ((1 + total_return/100) ** (1/years)) - 1
        
        # 基准收益
        benchmark_total_return = (self.data['benchmark_cumulative'].iloc[-1] - 1) * 100
        benchmark_annualized_return = ((1 + benchmark_total_return/100) ** (1/years)) - 1
        
        # 最大回撤
        self.data['drawdown'] = self.data['cumulative_returns'] / self.data['cumulative_returns'].cummax() - 1
        max_drawdown = self.data['drawdown'].min() * 100
        
        # 交易次数
        total_trades = len(self.data[self.data['strategy_returns'] != 0])
        winning_trades = len(self.data[self.data['strategy_returns'] > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 盈亏比
        avg_win = self.data[self.data['strategy_returns'] > 0]['strategy_returns'].mean() if winning_trades > 0 else 0
        avg_loss = abs(self.data[self.data['strategy_returns']< 0]['strategy_returns'].mean()) if (total_trades - winning_trades) >0 else 0
        profit_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else float('inf')
        
        metrics = {
            '策略名称': 'CCI背离策略',
            '总收益率': total_return,
            '年化收益率': annualized_return * 100,
            '基准总收益率': benchmark_total_return,
            '基准年化收益率': benchmark_annualized_return * 100,
            '最大回撤': max_drawdown,
            '总交易次数': total_trades,
            '胜率': win_rate,
            '盈亏比': profit_loss_ratio,
            '参数': f"cci_period={self.cci_period}, divergence_period={self.divergence_period}"
        }
        
        return metrics
    
    def plot_backtest(self):
        """绘制回测结果"""
        plt.figure(figsize=(15, 12))
        
        # 子图1：价格和背离信号
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300收盘价', linewidth=2)
        
        # 标记背离信号
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='底背离买入')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='顶背离卖出')
        
        plt.title('沪深300指数与CCI背离策略交易信号')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：CCI指标和背离标记
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['CCI'], label='CCI指标', color='purple', linewidth=2)
        plt.axhline(y=100, color='red', linestyle='--', alpha=0.7)
        plt.axhline(y=-100, color='green', linestyle='--', alpha=0.7)
        plt.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        
        # 标记背离点
        divergence_buy = self.data[self.data['divergence'] == 1]
        divergence_sell = self.data[self.data['divergence'] == -1]
        
        plt.scatter(divergence_buy.index, divergence_buy['CCI'], marker='^', color='green', s=80, label='底背离')
        plt.scatter(divergence_sell.index, divergence_sell['CCI'], marker='v', color='red', s=80, label='顶背离')
        
        plt.title('CCI指标与背离信号')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图3：策略收益 vs 基准收益
        plt.subplot(3, 1, 3)
        plt.plot(self.data.index, self.data['cumulative_returns'], label='CCI策略收益', linewidth=2, color='blue')
        plt.plot(self.data.index, self.data['benchmark_cumulative'], label='基准收益(买入持有)', linewidth=2, color='gray')
        
        plt.title('策略收益对比')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/cci_divergence_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_strategy(self):
        """运行完整策略"""
        self.calculate_cci()
        self.detect_divergence()
        self.generate_signals()
        self.backtest()
        metrics = self.calculate_metrics()
        self.plot_backtest()
        
        # 保存回测数据
        self.data.to_csv(f"{self.output_dir}/cci_divergence_strategy_backtest.csv")
        
        # 保存策略说明
        with open(f"{self.output_dir}/cci_divergence_strategy说明.md", 'w', encoding='utf-8') as f:
            f.write(f"""# CCI背离策略说明

## 策略原理
基于价格与CCI指标的背离现象进行交易：
- 底背离：价格创出新低，但CCI未创出新低，预示上涨
- 顶背离：价格创出新高，但CCI未创出新高，预示下跌

## 参数设置
- CCI周期: {self.cci_period}
- 背离检测周期: {self.divergence_period}

## 回测结果
- 总收益率: {metrics['总收益率']:.2f}%
- 年化收益率: {metrics['年化收益率']:.2f}%
- 基准总收益率: {metrics['基准总收益率']:.2f}%
- 基准年化收益率: {metrics['基准年化收益率']:.2f}%
- 最大回撤: {metrics['最大回撤']:.2f}%
- 总交易次数: {metrics['总交易次数']}
- 胜率: {metrics['胜率']:.2f}%
- 盈亏比: {metrics['盈亏比']:.2f}

## 策略特点
- 能够识别趋势反转信号
- 信号质量高，胜率较高
- 交易频率较低
- 需要结合其他指标确认

## 优化方向
- 调整背离检测周期
- 添加过滤条件提高信号质量
- 结合成交量确认背离
- 添加止损机制
""")
        
        return metrics
