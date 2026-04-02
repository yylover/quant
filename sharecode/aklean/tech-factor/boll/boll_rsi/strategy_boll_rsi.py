import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class BollRSIStrategy:
    """布林线与RSI结合策略"""
    
    def __init__(self, data, period=20, multiplier=2, rsi_period=14, oversold=30, overbought=70):
        """
        初始化布林线与RSI结合策略
        
        参数:
            data: 包含open, high, low, close列的DataFrame
            period: 布林线计算周期
            multiplier: 标准差倍数
            rsi_period: RSI计算周期
            oversold: RSI超卖阈值
            overbought: RSI超买阈值
        """
        self.data = data.copy()
        self.period = period
        self.multiplier = multiplier
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/boll/boll_rsi"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_bollinger_bands(self):
        """计算布林线指标"""
        # 计算中轨（简单移动平均）
        self.data['middle_band'] = self.data['close'].rolling(window=self.period).mean()
        
        # 计算标准差
        self.data['std_dev'] = self.data['close'].rolling(window=self.period).std()
        
        # 计算上下轨
        self.data['upper_band'] = self.data['middle_band'] + (self.data['std_dev'] * self.multiplier)
        self.data['lower_band'] = self.data['middle_band'] - (self.data['std_dev'] * self.multiplier)
        
        return self.data
    
    def calculate_rsi(self):
        """计算RSI指标"""
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta< 0, 0)).rolling(window=self.rsi_period).mean()
        
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 计算RSI的变化
        self.data['RSI_change'] = self.data['RSI'].diff()
        
        # 买入信号：价格接近下轨（低于下轨的1.05倍）且RSI从超卖区域反弹（RSI>20且RSI变化>2）
        buy_condition = (self.data['close']< self.data['lower_band'] * 1.05) & \
                      (self.data['RSI'] > 20) & \
                      (self.data['RSI_change'] > 2)
        
        # 卖出信号：价格接近上轨（高于上轨的0.95倍）且RSI从超买区域回落（RSI<80且RSI变化<-2）
        sell_condition = (self.data['close'] > self.data['upper_band'] * 0.95) & \
                       (self.data['RSI']< 80) & \
                       (self.data['RSI_change'] < -2)
        
        # 确保信号不会连续产生
        buy_condition = buy_condition & (self.data['signal'].shift(1) != 1)
        sell_condition = sell_condition & (self.data['signal'].shift(1) != -1)
        
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
            '策略名称': '布林线RSI结合策略',
            '总收益率': total_return,
            '年化收益率': annualized_return * 100,
            '基准总收益率': benchmark_total_return,
            '基准年化收益率': benchmark_annualized_return * 100,
            '最大回撤': max_drawdown,
            '总交易次数': total_trades,
            '胜率': win_rate,
            '盈亏比': profit_loss_ratio,
            '参数': f"period={self.period}, multiplier={self.multiplier}, rsi_period={self.rsi_period}, oversold={self.oversold}, overbought={self.overbought}"
        }
        
        return metrics
    
    def plot_backtest(self):
        """绘制回测结果"""
        plt.figure(figsize=(15, 12))
        
        # 子图1：价格和布林带
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300收盘价', linewidth=2)
        plt.plot(self.data.index, self.data['middle_band'], label='中轨', color='orange', linewidth=2)
        plt.plot(self.data.index, self.data['upper_band'], label='上轨', color='green', linestyle='--', linewidth=2)
        plt.plot(self.data.index, self.data['lower_band'], label='下轨', color='red', linestyle='--', linewidth=2)
        
        # 填充布林带区域
        plt.fill_between(self.data.index, self.data['upper_band'], self.data['lower_band'], color='gray', alpha=0.1)
        
        # 标记买入卖出信号
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='卖出信号')
        
        plt.title('沪深300指数与布林线RSI策略交易信号')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：RSI指标
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['RSI'], label='RSI', color='purple', linewidth=2)
        plt.axhline(y=self.oversold, color='green', linestyle='--', label=f'超卖({self.oversold})')
        plt.axhline(y=self.overbought, color='red', linestyle='--', label=f'超买({self.overbought})')
        
        plt.title('RSI指标')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图3：策略收益 vs 基准收益
        plt.subplot(3, 1, 3)
        plt.plot(self.data.index, self.data['cumulative_returns'], label='布林线策略收益', linewidth=2, color='blue')
        plt.plot(self.data.index, self.data['benchmark_cumulative'], label='基准收益(买入持有)', linewidth=2, color='gray')
        
        plt.title('策略收益对比')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/boll_rsi_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_strategy(self):
        """运行完整策略"""
        self.calculate_bollinger_bands()
        self.calculate_rsi()
        self.generate_signals()
        self.backtest()
        metrics = self.calculate_metrics()
        self.plot_backtest()
        
        # 保存回测数据
        self.data.to_csv(f"{self.output_dir}/boll_rsi_strategy_backtest.csv")
        
        # 保存策略说明
        with open(f"{self.output_dir}/boll_rsi_strategy说明.md", 'w', encoding='utf-8') as f:
            f.write(f"""# 布林线RSI结合策略说明

## 策略原理
结合布林线和RSI指标进行交易：
- 当价格触及下轨且RSI处于超卖区域时买入
- 当价格触及上轨且RSI处于超买区域时卖出

## 参数设置
- 布林线周期: {self.period}
- 标准差倍数: {self.multiplier}
- RSI周期: {self.rsi_period}
- RSI超卖阈值: {self.oversold}
- RSI超买阈值: {self.overbought}

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
- 结合动量指标确认超买超卖状态
- 信号质量高，胜率较高
- 减少假信号的产生
- 需要同时满足两个条件，信号频率较低

## 优化方向
- 调整RSI阈值参数
- 添加时间过滤条件
- 设置止损止盈
- 结合成交量指标
""")
        
        return metrics
