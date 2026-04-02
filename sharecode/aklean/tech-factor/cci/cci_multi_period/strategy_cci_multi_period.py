import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class CCIMultiPeriodStrategy:
    """CCI多周期策略"""
    
    def __init__(self, data, fast_period=10, slow_period=30):
        """
        初始化CCI多周期策略
        
        参数:
            data: 包含open, high, low, close列的DataFrame
            fast_period: 快速CCI周期
            slow_period: 慢速CCI周期
        """
        self.data = data.copy()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/cci/cci_multi_period"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_cci(self, period):
        """计算指定周期的CCI"""
        tp = (self.data['high'] + self.data['low'] + self.data['close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        
        def mean_deviation(x):
            return abs(x - x.mean()).mean()
        
        md = tp.rolling(window=period).apply(mean_deviation)
        cci = (tp - sma_tp) / (0.015 * md)
        
        return cci
    
    def calculate_multi_period_cci(self):
        """计算多周期CCI"""
        # 计算快速CCI
        self.data['CCI_Fast'] = self.calculate_cci(self.fast_period)
        
        # 计算慢速CCI
        self.data['CCI_Slow'] = self.calculate_cci(self.slow_period)
        
        # 计算CCI差值
        self.data['CCI_Diff'] = self.data['CCI_Fast'] - self.data['CCI_Slow']
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 金叉信号：快速CCI上穿慢速CCI，且慢速CCI为正
        buy_condition = (self.data['CCI_Fast'] > self.data['CCI_Slow']) & \
                      (self.data['CCI_Fast'].shift(1)<= self.data['CCI_Slow'].shift(1)) & \
                      (self.data['CCI_Slow'] > 0)
        
        # 卖出信号：快速CCI下穿慢速CCI，或者慢速CCI转为负值
        sell_condition = ((self.data['CCI_Fast'] < self.data['CCI_Slow']) & \
                        (self.data['CCI_Fast'].shift(1) >= self.data['CCI_Slow'].shift(1))) | \
                       (self.data['CCI_Slow']< 0)
        
        self.data.loc[buy_condition, 'signal'] = 1
        self.data.loc[sell_condition & (self.data['signal'] != 1), 'signal'] = -1
        
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
            '策略名称': 'CCI多周期策略',
            '总收益率': total_return,
            '年化收益率': annualized_return * 100,
            '基准总收益率': benchmark_total_return,
            '基准年化收益率': benchmark_annualized_return * 100,
            '最大回撤': max_drawdown,
            '总交易次数': total_trades,
            '胜率': win_rate,
            '盈亏比': profit_loss_ratio,
            '参数': f"fast_period={self.fast_period}, slow_period={self.slow_period}"
        }
        
        return metrics
    
    def plot_backtest(self):
        """绘制回测结果"""
        plt.figure(figsize=(15, 12))
        
        # 子图1：价格和信号
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300收盘价', linewidth=2)
        
        # 标记买入卖出信号
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='金叉买入')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='死叉卖出')
        
        plt.title('沪深300指数与CCI多周期策略交易信号')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：多周期CCI
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['CCI_Fast'], label=f'快速CCI({self.fast_period})', color='blue', linewidth=2)
        plt.plot(self.data.index, self.data['CCI_Slow'], label=f'慢速CCI({self.slow_period})', color='red', linewidth=2)
        plt.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        
        # 填充CCI差值区域
        plt.fill_between(self.data.index, self.data['CCI_Fast'], self.data['CCI_Slow'], 
                        where=self.data['CCI_Fast']> self.data['CCI_Slow'], color='green', alpha=0.2)
        plt.fill_between(self.data.index, self.data['CCI_Fast'], self.data['CCI_Slow'], 
                        where=self.data['CCI_Fast']< self.data['CCI_Slow'], color='red', alpha=0.2)
        
        plt.title('多周期CCI指标对比')
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
        plt.savefig(f"{self.output_dir}/cci_multi_period_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_strategy(self):
        """运行完整策略"""
        self.calculate_multi_period_cci()
        self.generate_signals()
        self.backtest()
        metrics = self.calculate_metrics()
        self.plot_backtest()
        
        # 保存回测数据
        self.data.to_csv(f"{self.output_dir}/cci_multi_period_strategy_backtest.csv")
        
        # 保存策略说明
        with open(f"{self.output_dir}/cci_multi_period_strategy说明.md", 'w', encoding='utf-8') as f:
            f.write(f"""# CCI多周期策略说明

## 策略原理
结合快速CCI和慢速CCI的交叉信号：
- 金叉：快速CCI上穿慢速CCI，买入
- 死叉：快速CCI下穿慢速CCI，卖出

## 参数设置
- 快速CCI周期: {self.fast_period}
- 慢速CCI周期: {self.slow_period}

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
- 结合短期和长期动量
- 信号更加稳定可靠
- 减少震荡市场中的假信号
- 适合趋势跟踪

## 优化方向
- 调整快速和慢速周期
- 添加过滤条件
- 结合波动率调整参数
- 添加止损机制
""")
        
        return metrics
