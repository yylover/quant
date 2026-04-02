import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class RSI_MA_CombinationSystem:
    """RSI与均线结合交易系统"""
    
    def __init__(self, data, rsi_period=14, ma_window=20, overbought_level=70, oversold_level=30):
        """初始化交易系统"""
        self.data = data.copy()
        self.rsi_period = rsi_period          # RSI周期：14天
        self.ma_window = ma_window            # 均线周期：20天
        self.overbought_level = overbought_level  # 超买阈值：70
        self.oversold_level = oversold_level      # 超卖阈值：30
        self.position = 0  # 持仓状态：1=持有，0=空仓
        self.trades = []  # 交易记录
    
    def calculate_indicators(self):
        """计算技术指标"""
        # 计算均线
        self.data['ma'] = self.data['收盘'].rolling(window=self.ma_window).mean()
        
        # 计算价格与均线的关系
        self.data['price_above_ma'] = self.data['收盘'] > self.data['ma']
        self.data['price_below_ma'] = self.data['收盘']< self.data['ma']
        
        # 计算RSI指标
        delta = self.data['收盘'].diff()
        gain = (delta.where(delta >0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        self.data['rsi'] = 100 - (100 / (1 + rs))
        
        # 标记超买超卖区域
        self.data['overbought'] = self.data['rsi'] >= self.overbought_level
        self.data['oversold'] = self.data['rsi']<= self.oversold_level
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(1, len(self.data)):
            # 买入信号：
            # 条件1：价格在均线上方（趋势向上）
            # 条件2：RSI从超卖区域回升
            if (self.data['price_above_ma'].iloc[i] and
                self.data['oversold'].iloc[i-1] and 
                not self.data['oversold'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 卖出信号：
            # 条件1：价格在均线下方（趋势向下）
            # 条件2：RSI从超买区域回落
            elif (self.data['price_below_ma'].iloc[i] and
                  self.data['overbought'].iloc[i-1] and 
                  not self.data['overbought'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = -1
            
            # 额外卖出信号：价格跌破均线且RSI仍在超买区域
            elif (self.position == 1 and
                  self.data['price_below_ma'].iloc[i] and 
                  not self.data['price_below_ma'].iloc[i-1]):
                self.data.loc[self.data.index[i], 'signal'] = -1
    
    def backtest(self):
        """执行回测"""
        print(f"开始回测...")
        print(f"RSI周期: {self.rsi_period}天, 均线周期: {self.ma_window}天")
        print(f"超买阈值: {self.overbought_level}, 超卖阈值: {self.oversold_level}")
        
        # 初始化回测数据
        self.data['position'] = 0
        self.data['strategy_return'] = 0
        self.data['benchmark_return'] = self.data['收盘'].pct_change()
        
        for i in range(1, len(self.data)):
            # 执行交易
            if self.data['signal'].iloc[i] == 1 and self.position == 0:
                self.position = 1
                self.trades.append({
                    'date': self.data.index[i],
                    'type': 'buy',
                    'price': self.data['收盘'].iloc[i]
                })
            
            elif self.data['signal'].iloc[i] == -1 and self.position == 1:
                self.position = 0
                self.trades.append({
                    'date': self.data.index[i],
                    'type': 'sell',
                    'price': self.data['收盘'].iloc[i]
                })
            
            # 更新持仓状态
            self.data.loc[self.data.index[i], 'position'] = self.position
            
            # 计算策略收益率
            if self.position == 1:
                self.data.loc[self.data.index[i], 'strategy_return'] = self.data['benchmark_return'].iloc[i]
        
        # 计算累计收益率
        self.data['cumulative_strategy'] = (1 + self.data['strategy_return']).cumprod()
        self.data['cumulative_benchmark'] = (1 + self.data['benchmark_return']).cumprod()
        
        return self.calculate_performance()
    
    def calculate_performance(self):
        """计算绩效指标"""
        total_return = (self.data['cumulative_strategy'].iloc[-1] - 1) * 100
        benchmark_return = (self.data['cumulative_benchmark'].iloc[-1] - 1) * 100
        
        # 计算年化收益率
        days = len(self.data)
        annualized_return = ((1 + total_return / 100) ** (365 / days) - 1) * 100
        
        # 计算最大回撤
        cumulative = self.data['cumulative_strategy']
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_drawdown = drawdown.min() * 100
        
        # 计算夏普比率（假设无风险利率为3%）
        daily_returns = self.data['strategy_return'].dropna()
        if len(daily_returns) > 0:
            sharpe_ratio = (daily_returns.mean() * 365 - 0.03) / (daily_returns.std() * np.sqrt(365))
        else:
            sharpe_ratio = 0
        
        # 计算胜率和盈亏比
        win_count = 0
        loss_count = 0
        total_profit = 0
        total_loss = 0
        
        for i in range(1, len(self.trades), 2):
            if i < len(self.trades):
                buy_price = self.trades[i-1]['price']
                sell_price = self.trades[i]['price']
                profit = sell_price - buy_price
                
                if profit > 0:
                    win_count += 1
                    total_profit += profit
                else:
                    loss_count += 1
                    total_loss += abs(profit)
        
        win_rate = (win_count / (win_count + loss_count) * 100) if (win_count + loss_count) > 0 else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
        
        # 计算平均持仓天数
        total_holding_days = 0
        trade_count = len(self.trades) // 2
        
        for i in range(1, len(self.trades), 2):
            if i < len(self.trades):
                buy_date = self.trades[i-1]['date']
                sell_date = self.trades[i]['date']
                total_holding_days += (sell_date - buy_date).days
        
        avg_holding_days = total_holding_days / trade_count if trade_count > 0 else 0
        
        # 输出绩效指标
        print(f"\n=== 回测性能指标 ===")
        print(f"总收益率: {total_return:.2f}%")
        print(f"基准收益率: {benchmark_return:.2f}%")
        print(f"年化收益率: {annualized_return:.2f}%")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"夏普比率: {sharpe_ratio:.2f}")
        print(f"胜率: {win_rate:.2f}%")
        print(f"盈亏比: {profit_factor:.2f}")
        print(f"总交易次数: {trade_count}")
        print(f"平均持仓天数: {avg_holding_days:.1f}天")
        print(f"回测天数: {days}天")
        
        # 输出交易日志
        print(f"\n=== 交易日志 ===")
        for i, trade in enumerate(self.trades, 1):
            print(f"{i}. {trade['date'].strftime('%Y-%m-%d')} - {trade['type']} - 价格: {trade['price']:.2f}")
        
        return {
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'trade_count': trade_count,
            'avg_holding_days': avg_holding_days,
            'days': days
        }
    
    def plot_results(self):
        """绘制回测结果"""
        plt.figure(figsize=(15, 12))
        
        # 绘制价格、均线和交易点
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['收盘'], label='收盘价', color='blue')
        plt.plot(self.data.index, self.data['ma'], label=f'{self.ma_window}日均线', color='red', linestyle='--')
        
        # 标记交易点
        buy_dates = [t['date'] for t in self.trades if t['type'] == 'buy']
        buy_prices = [t['price'] for t in self.trades if t['type'] == 'buy']
        sell_dates = [t['date'] for t in self.trades if t['type'] == 'sell']
        sell_prices = [t['price'] for t in self.trades if t['type'] == 'sell']
        
        plt.scatter(buy_dates, buy_prices, marker='^', color='green', s=100, label='买入')
        plt.scatter(sell_dates, sell_prices, marker='v', color='red', s=100, label='卖出')
        
        plt.title('RSI与均线结合交易系统')
        plt.ylabel('价格')
        plt.legend()
        plt.grid(True)
        
        plt.subplot(3, 1, 2)
        plt.plot(self.data.index, self.data['rsi'], label='RSI', color='purple')
        plt.axhline(y=self.overbought_level, color='red', linestyle='--', label=f'超买({self.overbought_level})')
        plt.axhline(y=self.oversold_level, color='green', linestyle='--', label=f'超卖({self.oversold_level})')
        plt.ylabel('RSI')
        plt.legend()
        plt.grid(True)
        
        plt.subplot(3, 1, 3)
        plt.plot(self.data.index, self.data['cumulative_strategy'], label='策略收益', color='red')
        plt.plot(self.data.index, self.data['cumulative_benchmark'], label='基准收益', color='blue')
        plt.ylabel('累计收益')
        plt.xlabel('日期')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        
        # 保存图表
        output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/rsi"
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(f"{output_dir}/rsi_ma_combination_backtest.png", dpi=300, bbox_inches='tight')
        plt.close()
        print("回测图表已保存")
    
    def save_results(self):
        """保存回测数据"""
        output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/rsi"
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存回测数据
        self.data.to_csv(f"{output_dir}/rsi_ma_combination_backtest.csv")
        print("回测数据已保存")
        
        # 保存策略说明和回测结果
        with open(f"{output_dir}/rsi_ma_combination说明.md", 'w', encoding='utf-8') as f:
            f.write("# RSI与均线结合交易系统\n\n")
            f.write("## 策略说明\n\n")
            f.write("### 核心思路\n")
            f.write("结合RSI指标和均线指标，在趋势确认的基础上利用RSI的超买超卖状态进行交易。\n\n")
            f.write("### 系统结构\n")
            f.write(f"- **RSI周期**: {self.rsi_period}天\n")
            f.write(f"- **均线周期**: {self.ma_window}天\n")
            f.write(f"- **超买阈值**: {self.overbought_level}\n")
            f.write(f"- **超卖阈值**: {self.oversold_level}\n\n")
            f.write("### 交易逻辑\n")
            f.write("1. **买入条件**: 价格在均线上方（趋势向上）且RSI从超卖区域回升\n")
            f.write("2. **卖出条件**: 价格在均线下方（趋势向下）且RSI从超买区域回落\n")
            f.write("3. **额外卖出**: 价格跌破均线时卖出\n\n")
            f.write("## 回测结果\n\n")
            f.write("### 性能指标\n")
            total_return = (self.data['cumulative_strategy'].iloc[-1] - 1) * 100
            benchmark_return = (self.data['cumulative_benchmark'].iloc[-1] - 1) * 100
            days = len(self.data)
            annualized_return = ((1 + total_return / 100) ** (365 / days) - 1) * 100
            
            cumulative = self.data['cumulative_strategy']
            peak = cumulative.cummax()
            drawdown = (cumulative - peak) / peak
            max_drawdown = drawdown.min() * 100
            
            daily_returns = self.data['strategy_return'].dropna()
            sharpe_ratio = (daily_returns.mean() * 365 - 0.03) / (daily_returns.std() * np.sqrt(365)) if len(daily_returns) >0 else 0
            
            win_count = 0
            loss_count = 0
            for i in range(1, len(self.trades), 2):
                if i < len(self.trades):
                    buy_price = self.trades[i-1]['price']
                    sell_price = self.trades[i]['price']
                    if sell_price > buy_price:
                        win_count += 1
                    else:
                        loss_count += 1
            
            win_rate = (win_count / (win_count + loss_count) * 100) if (win_count + loss_count) > 0 else 0
            trade_count = len(self.trades) // 2
            
            f.write(f"- **总收益率**: {total_return:.2f}%\n")
            f.write(f"- **基准收益率**: {benchmark_return:.2f}%\n")
            f.write(f"- **年化收益率**: {annualized_return:.2f}%\n")
            f.write(f"- **最大回撤**: {max_drawdown:.2f}%\n")
            f.write(f"- **夏普比率**: {sharpe_ratio:.2f}\n")
            f.write(f"- **胜率**: {win_rate:.2f}%\n")
            f.write(f"- **总交易次数**: {trade_count}\n")
            f.write(f"- **回测天数**: {days}天\n\n")
            
            f.write("### 交易记录\n")
            for i, trade in enumerate(self.trades, 1):
                f.write(f"{i}. {trade['date'].strftime('%Y-%m-%d')} - {trade['type']} - 价格: {trade['price']:.2f}\n")
        
        print("策略说明和回测结果已保存")

def generate_simulation_data(days=1095):
    """生成模拟的沪深300数据"""
    print("生成模拟的沪深300数据...")
    
    # 设置随机种子
    np.random.seed(42)
    
    # 创建日期索引
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 生成基础价格（带有趋势和波动）
    base_price = 4000
    trend = np.linspace(0, 0.3, len(dates))  # 30%的总体趋势
    volatility = np.random.normal(0, 0.01, len(dates))  # 每日波动
    prices = base_price * (1 + trend + np.cumsum(volatility))
    
    # 创建DataFrame
    data = pd.DataFrame({
        '日期': dates,
        '收盘': prices
    })
    data.set_index('日期', inplace=True)
    
    print(f"数据生成成功，共 {len(data)} 条记录")
    return data

if __name__ == "__main__":
    # 生成模拟数据
    data = generate_simulation_data()
    
    # 创建并运行RSI与均线结合交易系统
    rsi_system = RSI_MA_CombinationSystem(data)
    
    # 计算技术指标
    rsi_system.calculate_indicators()
    
    # 生成交易信号
    rsi_system.generate_signals()
    
    # 执行回测
    performance = rsi_system.backtest()
    
    # 绘制结果
    rsi_system.plot_results()
    
    # 保存结果
    rsi_system.save_results()
