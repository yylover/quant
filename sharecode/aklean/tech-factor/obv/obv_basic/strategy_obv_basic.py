import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class OBVBasicStrategy:
    """基础OBV策略"""
    
    def __init__(self, data):
        """
        初始化基础OBV策略
        
        参数:
            data: 包含open, high, low, close, volume列的DataFrame
        """
        self.data = data.copy()
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/obv/obv_basic"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_obv(self):
        """计算OBV指标"""
        # 初始化OBV
        self.data['OBV'] = 0.0
        
        # 计算价格变化
        self.data['price_change'] = self.data['close'].diff()
        
        # 计算OBV
        for i in range(1, len(self.data)):
            if self.data['price_change'].iloc[i] > 0:
                self.data.at[self.data.index[i], 'OBV'] = self.data['OBV'].iloc[i-1] + self.data['volume'].iloc[i]
            elif self.data['price_change'].iloc[i]< 0:
                self.data.at[self.data.index[i], 'OBV'] = self.data['OBV'].iloc[i-1] - self.data['volume'].iloc[i]
            else:
                self.data.at[self.data.index[i], 'OBV'] = self.data['OBV'].iloc[i-1]
        
        # 计算OBV的移动平均
        self.data['OBV_ma'] = self.data['OBV'].rolling(window=20).mean()
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 买入信号：OBV突破其移动平均
        buy_condition = (self.data['OBV'] > self.data['OBV_ma']) & \
                      (self.data['OBV'].shift(1)<= self.data['OBV_ma'].shift(1))
        self.data.loc[buy_condition, 'signal'] = 1
        
        # 卖出信号：OBV跌破其移动平均
        sell_condition = (self.data['OBV'] < self.data['OBV_ma']) & \
                       (self.data['OBV'].shift(1) >= self.data['OBV_ma'].shift(1))
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
            '策略名称': '基础OBV策略',
            '总收益率': total_return,
            '年化收益率': annualized_return * 100,
            '基准总收益率': benchmark_total_return,
            '基准年化收益率': benchmark_annualized_return * 100,
            '最大回撤': max_drawdown,
            '总交易次数': total_trades,
            '胜率': win_rate,
            '盈亏比': profit_loss_ratio,
            '参数': 'OBV_ma=20'
        }
        
        return metrics
    
    def plot_backtest(self):
        """绘制回测结果"""
        plt.figure(figsize=(15, 12))
        
        # 子图1：价格和OBV
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300收盘价', linewidth=2)
        
        plt.title('沪深300指数')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：OBV和OBV均线
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['OBV'], label='OBV', color='blue', linewidth=2)
        plt.plot(self.data.index, self.data['OBV_ma'], label='OBV均线', color='red', linewidth=2)
        
        # 标记买入卖出信号
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['OBV'], marker='^', color='green', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['OBV'], marker='v', color='red', s=100, label='卖出信号')
        
        plt.title('OBV指标与交易信号')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图3：策略收益 vs 基准收益
        plt.subplot(3, 1, 3)
        plt.plot(self.data.index, self.data['cumulative_returns'], label='OBV策略收益', linewidth=2, color='blue')
        plt.plot(self.data.index, self.data['benchmark_cumulative'], label='基准收益(买入持有)', linewidth=2, color='gray')
        
        plt.title('策略收益对比')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/obv_basic_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_strategy(self):
        """运行完整策略"""
        self.calculate_obv()
        self.generate_signals()
        self.backtest()
        metrics = self.calculate_metrics()
        self.plot_backtest()
        
        # 保存回测数据
        self.data.to_csv(f"{self.output_dir}/obv_basic_strategy_backtest.csv")
        
        # 保存策略说明
        with open(f"{self.output_dir}/obv_basic_strategy说明.md", 'w', encoding='utf-8') as f:
            f.write(f"""# 基础OBV策略说明

## 策略原理
基于OBV（On-Balance Volume）指标的变化进行交易：
- 当OBV突破其20日均线时买入
- 当OBV跌破其20日均线时卖出

## 参数设置
- OBV均线周期: 20

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
- 基于成交量变化预测价格趋势
- 简单直观，易于理解
- 能够提前预测价格变动
- 适合趋势跟踪

## 优化方向
- 调整OBV均线周期
- 结合其他指标提高信号质量
- 添加波动率过滤
- 设置止损止盈
""")
        
        return metrics
