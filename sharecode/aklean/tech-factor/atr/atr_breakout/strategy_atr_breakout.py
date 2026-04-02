import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class AtrBreakoutStrategy:
    def __init__(self, data, atr_period=14, breakout_period=10, breakout_multiplier=0.4, stop_loss=0.08, take_profit=0.20):
        self.data = data.copy()
        self.atr_period = atr_period
        self.breakout_period = breakout_period
        self.breakout_multiplier = breakout_multiplier
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/atr/atr_breakout"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_true_range(self):
        """计算真实范围"""
        self.data['tr'] = np.maximum(
            self.data['high'] - self.data['low'],
            np.maximum(
                abs(self.data['high'] - self.data['close'].shift(1)),
                abs(self.data['low'] - self.data['close'].shift(1))
            )
        )
        return self.data
    
    def calculate_atr(self):
        """计算平均真实范围"""
        self.calculate_true_range()
        
        # 计算初始ATR（前period个TR的简单平均）
        self.data['atr'] = self.data['tr'].rolling(window=self.atr_period).mean()
        
        # 使用平滑公式更新ATR（从第一个有效ATR开始）
        first_valid_idx = self.data['atr'].first_valid_index()
        if first_valid_idx is not None:
            start_idx = self.data.index.get_loc(first_valid_idx)
            for i in range(start_idx + 1, len(self.data)):
                if pd.notna(self.data.loc[self.data.index[i], 'tr']):
                    self.data.loc[self.data.index[i], 'atr'] = (
                        self.data.loc[self.data.index[i-1], 'atr'] * (self.atr_period - 1) + 
                        self.data.loc[self.data.index[i], 'tr']
                    ) / self.atr_period
        
        return self.data
    
    def calculate_breakout_levels(self):
        """计算突破水平"""
        # 计算近期最高价和最低价
        self.data['high_rolling'] = self.data['high'].rolling(window=self.breakout_period).max()
        self.data['low_rolling'] = self.data['low'].rolling(window=self.breakout_period).min()
        
        # 计算突破阈值
        self.data['breakout_high'] = self.data['high_rolling'] + self.data['atr'] * self.breakout_multiplier
        self.data['breakout_low'] = self.data['low_rolling'] - self.data['atr'] * self.breakout_multiplier
        
        return self.data
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 买入信号：价格突破上方阈值
        buy_condition = self.data['high'] > self.data['breakout_high'].shift(1)
        self.data.loc[buy_condition, 'signal'] = 1
        
        # 卖出信号：价格突破下方阈值
        sell_condition = self.data['low']< self.data['breakout_low'].shift(1)
        self.data.loc[sell_condition, 'signal'] = -1
        
        return self.data
    
    def backtest(self):
        """执行回测"""
        self.data['position'] = 0.0
        self.data['entry_price'] = 0.0
        self.data['stop_loss'] = 0.0
        self.data['take_profit'] = 0.0
        self.data['strategy_returns'] = 0.0
        
        position = 0
        entry_price = 0
        stop_loss_price = 0
        take_profit_price = 0
        
        for i in range(1, len(self.data)):
            # 买入信号
            if self.data['signal'].iloc[i] == 1 and position == 0:
                position = 1
                entry_price = self.data['close'].iloc[i]
                # 设置止损和止盈
                stop_loss_price = entry_price - self.data['atr'].iloc[i] * 2.5
                take_profit_price = entry_price + self.data['atr'].iloc[i] * 3.5
                
                self.data.at[self.data.index[i], 'position'] = position
                self.data.at[self.data.index[i], 'entry_price'] = entry_price
                self.data.at[self.data.index[i], 'stop_loss'] = stop_loss_price
                self.data.at[self.data.index[i], 'take_profit'] = take_profit_price
            
            # 卖出信号
            elif self.data['signal'].iloc[i] == -1 and position == 1:
                position = 0
                exit_price = self.data['close'].iloc[i]
                self.data.at[self.data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
            
            # 止损
            elif position == 1 and self.data['low'].iloc[i]<= stop_loss_price:
                position = 0
                exit_price = stop_loss_price
                self.data.at[self.data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
            
            # 止盈
            elif position == 1 and self.data['high'].iloc[i] >= take_profit_price:
                position = 0
                exit_price = take_profit_price
                self.data.at[self.data.index[i], 'strategy_returns'] = (exit_price - entry_price) / entry_price
            
            # 保持仓位
            else:
                self.data.at[self.data.index[i], 'position'] = position
                self.data.at[self.data.index[i], 'entry_price'] = entry_price
                if position == 1:
                    self.data.at[self.data.index[i], 'stop_loss'] = stop_loss_price
                    self.data.at[self.data.index[i], 'take_profit'] = take_profit_price
                
        # 计算累计收益
        self.data['cumulative_returns'] = (1 + self.data['strategy_returns']).cumprod()
        
        return self.data
    
    def calculate_metrics(self):
        """计算回测指标"""
        total_return = (self.data['cumulative_returns'].iloc[-1] - 1) * 100
        
        # 计算年化收益率 - 使用正确的公式
        years = len(self.data) / 252
        annualized_return = ((1 + total_return/100) ** (1/years)) - 1
        
        # 计算最大回撤
        self.data['drawdown'] = self.data['cumulative_returns'] / self.data['cumulative_returns'].cummax() - 1
        max_drawdown = self.data['drawdown'].min() * 100
        
        # 计算胜率
        winning_trades = len(self.data[self.data['strategy_returns'] > 0])
        total_trades = len(self.data[self.data['strategy_returns'] != 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 计算盈亏比
        avg_win = self.data[self.data['strategy_returns'] > 0]['strategy_returns'].mean()
        avg_loss = abs(self.data[self.data['strategy_returns']< 0]['strategy_returns'].mean())
        profit_loss_ratio = (avg_win / avg_loss) if avg_loss >0 else float('inf')
        
        metrics = {
            '总收益率': total_return,
            '年化收益率': annualized_return * 100,
            '最大回撤': max_drawdown,
            '胜率': win_rate,
            '盈亏比': profit_loss_ratio,
            '总交易次数': total_trades,
            '平均持仓天数': None
        }
        
        return metrics
    
    def plot_results(self):
        """绘制回测结果"""
        plt.figure(figsize=(12, 8))
        
        # 价格和突破水平
        plt.subplot(2, 1, 1)
        plt.plot(self.data['close'], label='收盘价', linewidth=2)
        plt.plot(self.data['breakout_high'], label='突破上限', color='green', linestyle='--', alpha=0.7)
        plt.plot(self.data['breakout_low'], label='突破下限', color='red', linestyle='--', alpha=0.7)
        
        # 标记买入和卖出信号
        buy_signals = self.data[self.data['signal'] == 1]
        sell_signals = self.data[self.data['signal'] == -1]
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='卖出信号')
        
        plt.title('ATR突破策略 - 价格与突破水平')
        plt.legend()
        plt.grid(True)
        
        # 累计收益
        plt.subplot(2, 1, 2)
        plt.plot(self.data['cumulative_returns'], label='策略收益', linewidth=2)
        plt.plot((1 + self.data['close'].pct_change()).cumprod(), label='基准收益', color='gray', alpha=0.7)
        
        plt.title('ATR突破策略 - 累计收益')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/atr_breakout_strategy_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_strategy(self):
        """运行完整策略"""
        self.calculate_atr()
        self.calculate_breakout_levels()
        self.generate_signals()
        self.backtest()
        metrics = self.calculate_metrics()
        self.plot_results()
        
        # 保存回测数据
        self.data.to_csv(f"{self.output_dir}/atr_breakout_strategy_backtest.csv")
        
        return metrics

if __name__ == "__main__":
    # 生成模拟数据
    np.random.seed(42)
    dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='B')
    base_price = 4000
    trend = np.linspace(0, 0.2, len(dates))
    volatility = np.random.normal(0, 0.015, len(dates))
    prices = base_price * (1 + trend + np.cumsum(volatility))
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
        'high': prices * (1 + np.random.normal(0.003, 0.005, len(dates))),
        'low': prices * (1 + np.random.normal(-0.003, 0.005, len(dates))),
        'close': prices,
        'volume': np.random.randint(10000000, 50000000, len(dates))
    })
    
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    data.set_index('date', inplace=True)
    
    # 运行策略
    strategy = AtrBreakoutStrategy(data)
    metrics = strategy.run_strategy()
    
    print("ATR突破策略回测结果：")
    print(f"总收益率: {metrics['总收益率']:.2f}%")
    print(f"年化收益率: {metrics['年化收益率']:.2f}%")
    print(f"最大回撤: {metrics['最大回撤']:.2f}%")
    print(f"胜率: {metrics['胜率']:.2f}%")
    print(f"盈亏比: {metrics['盈亏比']:.2f}")
    print(f"总交易次数: {metrics['总交易次数']}")
