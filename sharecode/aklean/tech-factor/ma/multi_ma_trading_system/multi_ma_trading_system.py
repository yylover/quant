import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class MultiMATradingSystem:
    """基于多均线结构的趋势交易系统"""
    
    def __init__(self, data, fast_window=5, medium_window=20, slow_window=60):
        """初始化交易系统"""
        self.data = data.copy()
        self.fast_window = fast_window      # 快线：5/10
        self.medium_window = medium_window  # 中线：20
        self.slow_window = slow_window      # 慢线：60/120
        self.position = 0  # 持仓状态：1=持有，0=空仓
        self.trades = []  # 交易记录
        
    def calculate_ma(self):
        """计算各种均线"""
        # 计算快线
        self.data['fast_ma'] = self.data['收盘'].rolling(window=self.fast_window).mean()
        # 计算中线
        self.data['medium_ma'] = self.data['收盘'].rolling(window=self.medium_window).mean()
        # 计算慢线
        self.data['slow_ma'] = self.data['收盘'].rolling(window=self.slow_window).mean()
        
        # 计算慢线斜率（判断大趋势）
        self.data['slow_slope'] = self.data['slow_ma'].diff(10) / 10
        
        # 计算均线差值
        self.data['fast_medium_diff'] = self.data['fast_ma'] - self.data['medium_ma']
        self.data['price_medium_diff'] = self.data['收盘'] - self.data['medium_ma']
        
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(1, len(self.data)):
            # 开仓条件（同时满足）：
            # 1. 慢线向上（大趋势向上）
            # 2. 价格 > 中线
            # 3. 快线上穿中线
            if (self.data['slow_slope'].iloc[i] > 0 and
                self.data['收盘'].iloc[i] > self.data['medium_ma'].iloc[i] and
                self.data['fast_ma'].iloc[i] > self.data['medium_ma'].iloc[i] and
                self.data['fast_ma'].iloc[i-1]<= self.data['medium_ma'].iloc[i-1]):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 平仓条件：
            # 1. 快线下穿中线
            # 或
            # 2. 价格跌破中线止损
            elif (self.data['fast_ma'].iloc[i]< self.data['medium_ma'].iloc[i] and
                  self.data['fast_ma'].iloc[i-1] >= self.data['medium_ma'].iloc[i-1]) or \
                 (self.data['收盘'].iloc[i]< self.data['medium_ma'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = -1
    
    def backtest(self):
        """执行回测"""
        print(f"开始回测...")
        print(f"快线: {self.fast_window}天, 中线: {self.medium_window}天, 慢线: {self.slow_window}天")
        
        # 计算收益率
        self.data['returns'] = self.data['收盘'].pct_change()
        
        # 初始化策略收益率
        self.data['strategy_returns'] = 0.0
        
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
                    'position': self.position,
                    'medium_ma': self.data['medium_ma'].iloc[i]  # 记录当时的中线位置（用于止损参考）
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
            self.data.loc[self.data.index[i], 'strategy_returns'] = float(self.position * self.data['returns'].iloc[i])
    
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
        if daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() - 0.03/252) / daily_returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # 计算胜率
        winning_trades = 0
        for i in range(0, len(self.trades), 2):
            if i + 1 < len(self.trades):
                if self.trades[i+1]['price'] > self.trades[i]['price']:
                    winning_trades += 1
        
        total_trades = len(self.trades) // 2  # 每笔交易包含买入和卖出
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 计算平均持仓天数
        avg_holding_days = 0
        for i in range(0, len(self.trades), 2):
            if i + 1 < len(self.trades):
                holding_days = (self.trades[i+1]['date'] - self.trades[i]['date']).days
                avg_holding_days += holding_days
        
        avg_holding_days = avg_holding_days / total_trades if total_trades > 0 else 0
        
        return {
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_holding_days': avg_holding_days,
            'days': days
        }
    
    def plot_results(self):
        """绘制回测结果"""
        plt.figure(figsize=(16, 12))
        
        # 绘制价格和均线
        plt.subplot(2, 1, 1)
        plt.plot(self.data.index, self.data['收盘'], label='收盘价', color='#1f77b4', linewidth=2)
        plt.plot(self.data.index, self.data['fast_ma'], label=f'{self.fast_window}日均线', color='#ff7f0e', linewidth=1.5)
        plt.plot(self.data.index, self.data['medium_ma'], label=f'{self.medium_window}日均线', color='#2ca02c', linewidth=1.5)
        plt.plot(self.data.index, self.data['slow_ma'], label=f'{self.slow_window}日均线', color='#9467bd', linewidth=1.5)
        
        # 标记买卖点
        buy_dates = [trade['date'] for trade in self.trades if trade['type'] == 'buy']
        buy_prices = [trade['price'] for trade in self.trades if trade['type'] == 'buy']
        sell_dates = [trade['date'] for trade in self.trades if trade['type'] == 'sell']
        sell_prices = [trade['price'] for trade in self.trades if trade['type'] == 'sell']
        
        plt.scatter(buy_dates, buy_prices, marker='^', color='#2ca02c', s=100, label='买入')
        plt.scatter(sell_dates, sell_prices, marker='v', color='#d62728', s=100, label='卖出')
        
        plt.title('沪深300指数 - 多均线趋势交易系统', fontsize=16, fontweight='bold')
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
        plt.savefig('multi_ma_trading_backtest.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("回测图表已保存为: multi_ma_trading_backtest.png")
    
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
        print(f"平均持仓天数: {performance['avg_holding_days']:.1f}天")
        print(f"回测天数: {performance['days']}天")
        
        # 打印交易日志
        self.print_trade_log()
        
        # 绘制结果
        self.plot_results()
        
        # 保存回测数据
        self.data.to_csv('multi_ma_trading_backtest.csv')
        print("\n回测数据已保存为: multi_ma_trading_backtest.csv")
        
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

def main():
    """主函数"""
    print("=== 多均线趋势交易系统 ===")
    
    try:
        # 生成模拟数据
        data = generate_simulation_data()
        print(f"数据生成成功，共 {len(data)} 条记录")
        
        # 使用多均线参数运行回测
        # 快线：5天，中线：20天，慢线：60天
        system = MultiMATradingSystem(data.copy(), fast_window=5, medium_window=20, slow_window=60)
        system.run()
        
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()
