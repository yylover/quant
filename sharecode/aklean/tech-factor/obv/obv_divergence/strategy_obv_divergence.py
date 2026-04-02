import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class OBVDivergenceStrategy:
    """OBV背离策略"""
    
    def __init__(self, data, lookback_period=20):
        """
        初始化OBV背离策略
        
        参数:
            data: 包含open, high, low, close, volume列的DataFrame
            lookback_period: 背离检测的回溯周期
        """
        self.data = data.copy()
        self.lookback_period = lookback_period
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/obv/obv_divergence"
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
        
        return self.data
    
    def detect_divergence(self):
        """检测价格和OBV的背离"""
        self.data['divergence_signal'] = 0
        
        for i in range(self.lookback_period, len(self.data)):
            # 获取回溯期内的数据
            recent_data = self.data.iloc[i-self.lookback_period:i+1]
            
            # 计算价格极值
            price_high = recent_data['close'].max()
            price_low = recent_data['close'].min()
            
            # 计算OBV极值
            obv_high = recent_data['OBV'].max()
            obv_low = recent_data['OBV'].min()
            
            # 找到极值的位置
            price_high_idx = recent_data['close'].idxmax()
            price_low_idx = recent_data['close'].idxmin()
            obv_high_idx = recent_data['OBV'].idxmax()
            obv_low_idx = recent_data['OBV'].idxmin()
            
            # 检测底背离（价格创新低，OBV未创新低）
            if self.data['close'].iloc[i] == price_low and \
               self.data['OBV'].iloc[i] > obv_low and \
               self.data['close'].iloc[i]< self.data['close'].iloc[i-self.lookback_period]:
                self.data.at[self.data.index[i], 'divergence_signal'] = 1
            
            # 检测顶背离（价格创新高，OBV未创新高）
            elif self.data['close'].iloc[i] == price_high and \
                 self.data['OBV'].iloc[i]< obv_high and \
                 self.data['close'].iloc[i] >self.data['close'].iloc[i-self.lookback_period]:
                self.data.at[self.data.index[i], 'divergence_signal'] = -1
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 使用背离信号作为交易信号
        self.data['signal'] = self.data['divergence_signal']
        
        # 确保信号不会连续产生
        self.data.loc[self.data['signal'] == self.data['signal'].shift(1), 'signal'] = 0
        
        return self.data
    
    def backtest(self):
        """回测策略"""
        self.data['position'] = 0.0
        self.data['strategy_returns'] = 0.0
        
        position = 0
        entry_price = 0
        
        for i in range(1, len(self.data)):
            # 买入信号（底背离）
            if self.data['signal'].iloc[i] == 1 and position == 0:
                position = 1
                entry_price = self.data['close'].iloc[i]
            
            # 卖出信号（顶背离）
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
            '策略名称': 'OBV背离策略',
            '总收益率': total_return,
            '年化收益率': annualized_return * 100,
            '基准总收益率': benchmark_total_return,
            '基准年化收益率': benchmark_annualized_return * 100,
            '最大回撤': max_drawdown,
            '总交易次数': total_trades,
            '胜率': win_rate,
            '盈亏比': profit_loss_ratio,
            '参数': f"lookback_period={self.lookback_period}"
        }
        
        return metrics
    
    def plot_backtest(self):
        """绘制回测结果"""
        plt.figure(figsize=(15, 12))
        
        # 子图1：价格和背离信号
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300收盘价', linewidth=2)
        
        # 标记买入卖出信号
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='买入信号(底背离)')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='卖出信号(顶背离)')
        
        plt.title('沪深300指数与OBV背离信号')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：OBV指标
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['OBV'], label='OBV', color='blue', linewidth=2)
        
        plt.scatter(buy_signals.index, buy_signals['OBV'], marker='^', color='green', s=100)
        plt.scatter(sell_signals.index, sell_signals['OBV'], marker='v', color='red', s=100)
        
        plt.title('OBV指标')
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
        plt.savefig(f"{self.output_dir}/obv_divergence_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_strategy(self):
        """运行完整策略"""
        self.calculate_obv()
        self.detect_divergence()
        self.generate_signals()
        self.backtest()
        metrics = self.calculate_metrics()
        self.plot_backtest()
        
        # 保存回测数据
        self.data.to_csv(f"{self.output_dir}/obv_divergence_strategy_backtest.csv")
        
        # 保存策略说明
        with open(f"{self.output_dir}/obv_divergence_strategy说明.md", 'w', encoding='utf-8') as f:
            f.write(f"""# OBV背离策略说明

## 策略原理
基于价格和OBV的背离关系进行交易：
- 底背离：价格创新低，OBV未创新低，预示可能上涨
- 顶背离：价格创新高，OBV未创新高，预示可能下跌

## 参数设置
- 背离检测回溯周期: {self.lookback_period}

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
- 能够识别趋势反转
- 信号频率较低但质量高
- 适合中长线交易
- 需要确认背离的有效性

## 优化方向
- 调整回溯周期参数
- 添加其他指标确认背离
- 设置止损止盈
- 结合成交量指标
""")
        
        return metrics
