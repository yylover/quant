import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class CCIDynamicThresholdStrategy:
    """CCI动态阈值策略"""
    
    def __init__(self, data, cci_period=20, volatility_period=20, base_threshold=100):
        """
        初始化CCI动态阈值策略
        
        参数:
            data: 包含open, high, low, close列的DataFrame
            cci_period: CCI计算周期
            volatility_period: 波动率计算周期
            base_threshold: 基础阈值
        """
        self.data = data.copy()
        self.cci_period = cci_period
        self.volatility_period = volatility_period
        self.base_threshold = base_threshold
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/cci/cci_dynamic_threshold"
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
    
    def calculate_volatility(self):
        """计算波动率"""
        # 计算每日收益率
        self.data['returns'] = self.data['close'].pct_change()
        
        # 计算滚动标准差作为波动率
        self.data['volatility'] = self.data['returns'].rolling(window=self.volatility_period).std() * np.sqrt(252)
        
        # 计算动态阈值
        # 波动率越高，阈值越大；波动率越低，阈值越小
        self.data['dynamic_threshold'] = self.base_threshold * (1 + self.data['volatility'] / self.data['volatility'].mean())
        
        # 确保阈值有合理范围
        self.data['dynamic_threshold'] = self.data['dynamic_threshold'].clip(lower=50, upper=200)
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 买入信号：CCI从动态超卖阈值下方上穿
        buy_condition = (self.data['CCI'] > -self.data['dynamic_threshold']) & \
                      (self.data['CCI'].shift(1)<= -self.data['dynamic_threshold'].shift(1))
        
        # 卖出信号：CCI从动态超买阈值上方下穿
        sell_condition = (self.data['CCI'] < self.data['dynamic_threshold']) & \
                       (self.data['CCI'].shift(1) >= self.data['dynamic_threshold'].shift(1))
        
        self.data.loc[buy_condition, 'signal'] = 1
        self.data.loc[sell_condition, 'signal'] = -1
        
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
            '策略名称': 'CCI动态阈值策略',
            '总收益率': total_return,
            '年化收益率': annualized_return * 100,
            '基准总收益率': benchmark_total_return,
            '基准年化收益率': benchmark_annualized_return * 100,
            '最大回撤': max_drawdown,
            '总交易次数': total_trades,
            '胜率': win_rate,
            '盈亏比': profit_loss_ratio,
            '参数': f"cci_period={self.cci_period}, volatility_period={self.volatility_period}, base_threshold={self.base_threshold}"
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
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='卖出信号')
        
        plt.title('沪深300指数与CCI动态阈值策略交易信号')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：CCI指标和动态阈值
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['CCI'], label='CCI指标', color='purple', linewidth=2)
        plt.plot(self.data.index, self.data['dynamic_threshold'], label='动态超买阈值', color='red', linestyle='--', alpha=0.7)
        plt.plot(self.data.index, -self.data['dynamic_threshold'], label='动态超卖阈值', color='green', linestyle='--', alpha=0.7)
        plt.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        
        plt.fill_between(self.data.index, self.data['CCI'], self.data['dynamic_threshold'], 
                        where=self.data['CCI']> self.data['dynamic_threshold'], color='red', alpha=0.2)
        plt.fill_between(self.data.index, self.data['CCI'], -self.data['dynamic_threshold'], 
                        where=self.data['CCI']< -self.data['dynamic_threshold'], color='green', alpha=0.2)
        
        plt.title('CCI指标与动态阈值')
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
        plt.savefig(f"{self.output_dir}/cci_dynamic_threshold_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_strategy(self):
        """运行完整策略"""
        self.calculate_cci()
        self.calculate_volatility()
        self.generate_signals()
        self.backtest()
        metrics = self.calculate_metrics()
        self.plot_backtest()
        
        # 保存回测数据
        self.data.to_csv(f"{self.output_dir}/cci_dynamic_threshold_strategy_backtest.csv")
        
        # 保存策略说明
        with open(f"{self.output_dir}/cci_dynamic_threshold_strategy说明.md", 'w', encoding='utf-8') as f:
            f.write(f"""# CCI动态阈值策略说明

## 策略原理
根据市场波动率动态调整CCI的超买超卖阈值：
- 高波动市场：使用更大的阈值
- 低波动市场：使用更小的阈值

## 参数设置
- CCI周期: {self.cci_period}
- 波动率计算周期: {self.volatility_period}
- 基础阈值: {self.base_threshold}

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
- 自适应市场波动率
- 在不同市场环境下表现更稳定
- 减少震荡市场中的假信号
- 提高趋势市场中的信号质量

## 优化方向
- 调整波动率计算方法
- 优化阈值调整公式
- 结合其他指标
- 添加止损机制
""")
        
        return metrics
