import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class TrendTradingSystem:
    """基于均线的趋势交易系统"""
    
    def __init__(self, data, short_window=20, long_window=60):
        """初始化交易系统"""
        self.data = data.copy()
        self.short_window = short_window
        self.long_window = long_window
        self.position = 0  # 持仓状态：1=持有，0=空仓
        self.trades = []  # 交易记录
        
    def calculate_ma(self):
        """计算均线"""
        # 计算短期均线
        self.data['short_ma'] = self.data['收盘'].rolling(window=self.short_window).mean()
        # 计算长期均线
        self.data['long_ma'] = self.data['收盘'].rolling(window=self.long_window).mean()
        # 计算均线差值
        self.data['ma_diff'] = self.data['short_ma'] - self.data['long_ma']
        # 计算均线斜率
        self.data['short_slope'] = self.data['short_ma'].diff(10) / 10
        self.data['long_slope'] = self.data['long_ma'].diff(10) / 10
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        # 均线交叉策略 + 趋势确认
        for i in range(1, len(self.data)):
            # 金叉：短期均线上穿长期均线，且长期均线斜率为正
            if (self.data['short_ma'].iloc[i] > self.data['long_ma'].iloc[i] and 
                self.data['short_ma'].iloc[i-1] <= self.data['long_ma'].iloc[i-1] and
                self.data['long_slope'].iloc[i] > 0):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 死叉：短期均线下穿长期均线，且长期均线斜率为负
            elif (self.data['short_ma'].iloc[i] < self.data['long_ma'].iloc[i] and 
                  self.data['short_ma'].iloc[i-1] >= self.data['long_ma'].iloc[i-1] and
                  self.data['long_slope'].iloc[i] < 0):
                self.data.loc[self.data.index[i], 'signal'] = -1
    
    def backtest(self):
        """执行回测"""
        print(f"开始回测...")
        print(f"短期均线: {self.short_window}天, 长期均线: {self.long_window}天")
        
        # 计算收益率
        self.data['returns'] = self.data['收盘'].pct_change()
        
        # 初始化策略收益率
        self.data['strategy_returns'] = 0
        
        # 执行交易
        for i in range(1, len(self.data)):
            signal = self.data['signal'].iloc[i]
            
            # 买入信号
            if signal == 1 and self.position == 0:
                self.position = 1
                self.trades.append({
                    'date': self.data.index[i],
                    'type': 'buy',
                    'price': self.data['收盘'].iloc[i],
                    'position': self.position
                })
            
            # 卖出信号
            elif signal == -1 and self.position == 1:
                self.position = 0
                self.trades.append({
                    'date': self.data.index[i],
                    'type': 'sell',
                    'price': self.data['收盘'].iloc[i],
                    'position': self.position
                })
            
            # 策略收益率 = 持仓状态 * 当日收益率
            self.data.loc[self.data.index[i], 'strategy_returns'] = self.position * self.data['returns'].iloc[i]
    
    def calculate_performance(self):
        """计算性能指标"""
        # 计算累积收益率
        self.data['cum_returns'] = (1 + self.data['strategy_returns']).cumprod()
        self.data['benchmark_returns'] = (1 + self.data['returns']).cumprod()
        
        # 计算关键指标
        total_return = self.data['cum_returns'].iloc[-1] - 1
        benchmark_return = self.data['benchmark_returns'].iloc[-1] - 1
        
        # 计算年化收益率
        days = (self.data.index[-1] - self.data.index[0]).days
        annual_return = (1 + total_return) ** (365 / days) - 1
        
        # 计算最大回撤
        running_max = self.data['cum_returns'].cummax()
        drawdown = (self.data['cum_returns'] - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 计算夏普比率 (假设无风险利率为3%)
        daily_returns = self.data['strategy_returns'].dropna()
        sharpe_ratio = (daily_returns.mean() - 0.03/252) / daily_returns.std() * np.sqrt(252)
        
        # 计算胜率
        winning_trades = sum(1 for trade in self.trades if trade['type'] == 'sell')
        total_trades = len(self.trades) // 2  # 每笔交易包含买入和卖出
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'days': days
        }
    
    def plot_results(self):
        """绘制回测结果"""
        plt.figure(figsize=(16, 12))
        
        # 绘制价格和均线
        plt.subplot(2, 1, 1)
        plt.plot(self.data.index, self.data['收盘'], label='收盘价', color='#1f77b4', linewidth=2)
        plt.plot(self.data.index, self.data['short_ma'], label=f'{self.short_window}日均线', color='#ff7f0e', linewidth=1.5)
        plt.plot(self.data.index, self.data['long_ma'], label=f'{self.long_window}日均线', color='#2ca02c', linewidth=1.5)
        
        # 标记买卖点
        buy_dates = [trade['date'] for trade in self.trades if trade['type'] == 'buy']
        buy_prices = [trade['price'] for trade in self.trades if trade['type'] == 'buy']
        sell_dates = [trade['date'] for trade in self.trades if trade['type'] == 'sell']
        sell_prices = [trade['price'] for trade in self.trades if trade['type'] == 'sell']
        
        plt.scatter(buy_dates, buy_prices, marker='^', color='#2ca02c', s=100, label='买入')
        plt.scatter(sell_dates, sell_prices, marker='v', color='#d62728', s=100, label='卖出')
        
        plt.title('沪深300指数 - 均线趋势交易系统', fontsize=16, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制累积收益率
        plt.subplot(2, 1, 2)
        plt.plot(self.data.index, self.data['cum_returns'], label='策略收益率', color='#1f77b4', linewidth=2)
        plt.plot(self.data.index, self.data['benchmark_returns'], label='基准收益率', color='#ff7f0e', linewidth=1.5)
        
        plt.title('累积收益率对比', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('累积收益', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        plt.tight_layout()
        plt.savefig('trend_trading_backtest.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("回测图表已保存为: trend_trading_backtest.png")
    
    def print_trade_log(self):
        """打印交易日志"""
        print("\n=== 交易日志 ===")
        if not self.trades:
            print("无交易记录")
            return
        
        for i, trade in enumerate(self.trades):
            print(f"{i+1}. {trade['date'].strftime('%Y-%m-%d')} - {trade['type']} - 价格: {trade['price']:.2f}")
    
    def run(self):
        """运行完整的回测流程"""
        self.calculate_ma()
        self.generate_signals()
        self.backtest()
        performance = self.calculate_performance()
        
        # 打印性能指标
        print("\n=== 回测性能指标 ===")
        print(f"总收益率: {performance['total_return']:.2%}")
        print(f"基准收益率: {performance['benchmark_return']:.2%}")
        print(f"年化收益率: {performance['annual_return']:.2%}")
        print(f"最大回撤: {performance['max_drawdown']:.2%}")
        print(f"夏普比率: {performance['sharpe_ratio']:.2f}")
        print(f"胜率: {performance['win_rate']:.2%}")
        print(f"总交易次数: {performance['total_trades']}")
        print(f"回测天数: {performance['days']}天")
        
        # 打印交易日志
        self.print_trade_log()
        
        # 绘制结果
        self.plot_results()
        
        # 保存回测数据
        self.data.to_csv('trend_trading_backtest.csv')
        print("\n回测数据已保存为: trend_trading_backtest.csv")
        
        return performance

def generate_simulation_data():
    """生成模拟的沪深300数据"""
    print("生成模拟的沪深300数据...")
    
    # 生成近3年的日期序列
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 生成模拟的价格数据
    # 基础趋势 + 随机波动 + 季节性因素
    base_price = 4000
    trend = np.linspace(0, 1000, len(dates))  # 3年上涨1000点
    
    # 添加季节性波动（每年的波动模式）
    seasonal = 50 * np.sin(2 * np.pi * np.arange(len(dates)) / 252)
    
    # 添加随机波动
    random_walk = np.cumsum(np.random.normal(0, 15, len(dates)))
    
    close_prices = base_price + trend + seasonal + random_walk
    
    # 创建DataFrame
    data = pd.DataFrame({
        '日期': dates,
        '开盘': close_prices * (1 + np.random.normal(0, 0.002, len(dates))),
        '收盘': close_prices,
        '最高': close_prices * (1 + np.random.normal(0, 0.005, len(dates))),
        '最低': close_prices * (1 - np.random.normal(0, 0.005, len(dates))),
        '成交量': np.random.randint(1000000, 5000000, len(dates)),
        '成交额': close_prices * np.random.randint(1000000, 5000000, len(dates)) / 10000
    })
    
    # 设置日期为索引
    data.set_index('日期', inplace=True)
    
    return data

def optimize_parameters(data, short_range=(10, 30), long_range=(40, 80)):
    """优化均线参数"""
    print(f"\n优化参数中...")
    print(f"短期均线范围: {short_range[0]}-{short_range[1]}")
    print(f"长期均线范围: {long_range[0]}-{long_range[1]}")
    
    best_sharpe = -np.inf
    best_params = None
    best_performance = None
    
    for short in range(short_range[0], short_range[1]+1):
        for long in range(long_range[0], long_range[1]+1):
            if short >= long:
                continue
            
            system = TrendTradingSystem(data.copy(), short_window=short, long_window=long)
            system.calculate_ma()
            system.generate_signals()
            system.backtest()
            performance = system.calculate_performance()
            
            if performance['sharpe_ratio'] > best_sharpe:
                best_sharpe = performance['sharpe_ratio']
                best_params = (short, long)
                best_performance = performance
    
    print(f"\n最优参数: 短期均线={best_params[0]}天, 长期均线={best_params[1]}天")
    print(f"最优夏普比率: {best_sharpe:.2f}")
    
    return best_params, best_performance

def main():
    """主函数"""
    print("=== 基于均线的趋势交易系统 ===")
    
    try:
        # 生成模拟数据
        data = generate_simulation_data()
        print(f"数据生成成功，共 {len(data)} 条记录")
        
        # 优化参数
        best_params, best_performance = optimize_parameters(data)
        
        # 使用最优参数运行回测
        print(f"\n使用最优参数运行完整回测...")
        system = TrendTradingSystem(data.copy(), short_window=best_params[0], long_window=best_params[1])
        system.run()
        
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()
