import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class MAVolumeSystem:
    """均线与成交量结合交易系统"""
    
    def __init__(self, data, fast_ma=5, medium_ma=20, slow_ma=60, volume_period=20, high_period=50):
        """初始化交易系统"""
        self.data = data.copy()
        self.fast_ma = fast_ma            # 快线：5日
        self.medium_ma = medium_ma        # 中线：20日
        self.slow_ma = slow_ma            # 慢线：60日
        self.volume_period = volume_period  # 成交量均线周期：20日
        self.high_period = high_period      # 前期高点周期：50天
        self.position = 0  # 持仓状态：1=持有，0=空仓
        self.trades = []  # 交易记录
        
    def calculate_indicators(self):
        """计算技术指标"""
        # 计算各种均线
        self.data['fast_ma'] = self.data['收盘'].rolling(window=self.fast_ma).mean()
        self.data['medium_ma'] = self.data['收盘'].rolling(window=self.medium_ma).mean()
        self.data['slow_ma'] = self.data['收盘'].rolling(window=self.slow_ma).mean()
        
        # 计算成交量均线
        self.data['volume_ma'] = self.data['成交量'].rolling(window=self.volume_period).mean()
        
        # 计算成交量放大比率
        self.data['volume_ratio'] = self.data['成交量'] / self.data['volume_ma']
        
        # 计算前期高点
        self.data['high_50'] = self.data['最高'].rolling(window=self.high_period).max()
        
        # 计算均线差值
        self.data['fast_medium_diff'] = self.data['fast_ma'] - self.data['medium_ma']
        self.data['medium_slow_diff'] = self.data['medium_ma'] - self.data['slow_ma']
        
        # 价格与均线的关系
        self.data['price_above_medium'] = self.data['收盘'] > self.data['medium_ma']
        self.data['price_above_slow'] = self.data['收盘'] > self.data['slow_ma']
        
        # 成交量条件
        self.data['volume_above_ma'] = self.data['成交量'] > self.data['volume_ma']
        
        # 价格突破条件
        self.data['price_break_high'] = self.data['收盘'] > self.data['high_50'].shift(1)
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(1, len(self.data)):
            # 开仓条件（必须同时满足）：
            # 1. 5日均线在20日均线上方（多头排列）
            # 2. 成交量大于20日成交量均线（放量）
            # 3. 价格站在60日均线上方（趋势向上）
            if (self.data['fast_medium_diff'].iloc[i] > 0 and
                self.data['volume_above_ma'].iloc[i] and
                self.data['price_above_slow'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 平仓条件（满足任一即可）：
            # 1. 5日均线下穿20日均线
            # 2. 成交量明显萎缩（低于均线的50%）
            # 3. 价格跌破20日均线
            elif (self.data['fast_medium_diff'].iloc[i]< 0 and
                  self.data['fast_medium_diff'].iloc[i-1] >= 0) or \
                 (self.data['volume_ratio'].iloc[i]< 0.5) or \
                 (not self.data['price_above_medium'].iloc[i]):
                self.data.loc[self.data.index[i], 'signal'] = -1
    
    def backtest(self):
        """执行回测"""
        print(f"开始回测...")
        print(f"快线: {self.fast_ma}天, 中线: {self.medium_ma}天, 慢线: {self.slow_ma}天")
        
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
                    'volume_ratio': self.data['volume_ratio'].iloc[i]
                })
            
            # 卖出信号
            elif signal == -1 and self.position == 1:
                self.position = 0
                self.trades.append({
                    'date': self.data.index[i],
                    'type': 'sell',
                    'price': self.data['收盘'].iloc[i],
                    'position': self.position,
                    'volume_ratio': self.data['volume_ratio'].iloc[i]
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
        
        # 计算盈亏比
        total_profit = 0
        total_loss = 0
        for i in range(0, len(self.trades), 2):
            if i + 1 < len(self.trades):
                profit = self.trades[i+1]['price'] - self.trades[i]['price']
                if profit > 0:
                    total_profit += profit
                else:
                    total_loss += abs(profit)
        
        profit_factor = total_profit / total_loss if total_loss > 0 else np.inf
        
        return {
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_holding_days': avg_holding_days,
            'profit_factor': profit_factor,
            'days': days
        }
    
    def plot_results(self):
        """绘制回测结果"""
        plt.figure(figsize=(16, 20))
        
        # 绘制价格、均线和交易信号
        plt.subplot(5, 1, 1)
        plt.plot(self.data.index, self.data['收盘'], label='收盘价', color='#1f77b4', linewidth=2)
        plt.plot(self.data.index, self.data['fast_ma'], label=f'{self.fast_ma}日均线', color='#ff7f0e', linewidth=1.2)
        plt.plot(self.data.index, self.data['medium_ma'], label=f'{self.medium_ma}日均线', color='#2ca02c', linewidth=1.5)
        plt.plot(self.data.index, self.data['slow_ma'], label=f'{self.slow_ma}日均线', color='#9467bd', linewidth=1.5)
        plt.plot(self.data.index, self.data['high_50'], label=f'{self.high_period}日高点', color='#d62728', linewidth=1.2, linestyle='--')
        
        # 标记买卖点
        buy_dates = [trade['date'] for trade in self.trades if trade['type'] == 'buy']
        buy_prices = [trade['price'] for trade in self.trades if trade['type'] == 'buy']
        sell_dates = [trade['date'] for trade in self.trades if trade['type'] == 'sell']
        sell_prices = [trade['price'] for trade in self.trades if trade['type'] == 'sell']
        
        plt.scatter(buy_dates, buy_prices, marker='^', color='#2ca02c', s=120, label='买入', zorder=5)
        plt.scatter(sell_dates, sell_prices, marker='v', color='#d62728', s=120, label='卖出', zorder=5)
        
        plt.title('沪深300指数 - 均线与成交量结合系统', fontsize=16, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制仓位变化
        plt.subplot(5, 1, 2)
        # 创建仓位时间序列
        position_data = []
        for trade in self.trades:
            position_data.append({'date': trade['date'], 'position': trade['position']})
        
        if position_data:
            position_df = pd.DataFrame(position_data)
            position_df.set_index('date', inplace=True)
            
            # 填充仓位数据
            full_dates = pd.date_range(start=self.data.index[0], end=self.data.index[-1], freq='B')
            position_df = position_df.reindex(full_dates, method='ffill').fillna(0)
            
            plt.plot(position_df.index, position_df['position'], label='仓位', color='#9467bd', linewidth=2)
        
        plt.title('仓位变化', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('仓位', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制成交量
        plt.subplot(5, 1, 3)
        plt.bar(self.data.index, self.data['成交量'], label='成交量', color='#1f77b4', alpha=0.6)
        plt.plot(self.data.index, self.data['volume_ma'], label=f'{self.volume_period}日成交量均线', color='#2ca02c', linewidth=2)
        
        plt.title('成交量', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('成交量', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制成交量比率
        plt.subplot(5, 1, 4)
        plt.plot(self.data.index, self.data['volume_ratio'], label='成交量比率', color='#ff7f0e', linewidth=1.5)
        plt.axhline(y=1, color='blue', linestyle='--', label='成交量均线')
        plt.axhline(y=0.5, color='red', linestyle='--', label='萎缩阈值(0.5)')
        plt.fill_between(self.data.index, 1, self.data['volume_ratio'], 
                        where=self.data['volume_ratio'] > 1, color='green', alpha=0.1)
        plt.fill_between(self.data.index, self.data['volume_ratio'], 0.5, 
                        where=self.data['volume_ratio']< 0.5, color='red', alpha=0.1)
        
        plt.title('成交量比率', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('比率', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制累积收益率
        plt.subplot(5, 1, 5)
        plt.plot(self.data.index, self.data['cum_returns'], label='策略收益率', color='#1f77b4', linewidth=2)
        plt.plot(self.data.index, self.data['benchmark_returns'], label='基准收益率', color='#ff7f0e', linewidth=1.5)
        
        plt.title('累积收益率对比', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('累积收益', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        plt.tight_layout()
        plt.savefig(os.path.join(BASE_DIR, 'strategy5_backtest.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        print("回测图表已保存")
    
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
        self.calculate_indicators()
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
        print(f"盈亏比: {performance['profit_factor']:.2f}")
        print(f"总交易次数: {performance['total_trades']}")
        print(f"平均持仓天数: {performance['avg_holding_days']:.1f}天")
        print(f"回测天数: {performance['days']}天")
        
        # 打印交易日志
        self.print_trade_log()
        
        # 绘制结果
        self.plot_results()
        
        # 保存回测数据
        self.data.to_csv(os.path.join(BASE_DIR, 'strategy5_backtest.csv'))
        print("\n回测数据已保存")
        
        # 保存策略说明和结果
        self.save_strategy_report(performance)
        
        return performance
    
    def save_strategy_report(self, performance):
        """保存策略说明和回测结果"""
        report_content = f"""# 均线与成交量结合交易系统（策略5）

## 策略说明

### 核心思路
成交量确认均线信号的有效性。通过成交量的变化来确认趋势的强度和可靠性。

### 系统结构
- **均线**：5日、20日、60日均线
- **成交量指标**：20日成交量均线
- **前期高点**：50日高点

### 开仓条件（必须同时满足）
1. **5日均线在20日均线上方**：快线在中线上方，形成多头排列
2. **成交量 > 20日成交量均线**：放量上涨，确认上涨动能
3. **价格站在60日均线上方**：价格位于慢线上方，表明中期趋势向上

### 平仓条件（满足任一即可）
1. **5日均线下穿20日均线**：短期趋势反转
2. **成交量明显萎缩**：成交量低于均线的50%
3. **价格跌破20日均线**：中期趋势转弱

## 回测结果

### 性能指标
- **总收益率**: {performance['total_return']:.2%}
- **基准收益率**: {performance['benchmark_return']:.2%}
- **年化收益率**: {performance['annual_return']:.2%}
- **最大回撤**: {performance['max_drawdown']:.2%}
- **夏普比率**: {performance['sharpe_ratio']:.2f}
- **胜率**: {performance['win_rate']:.2%}
- **盈亏比**: {performance['profit_factor']:.2f}
- **总交易次数**: {performance['total_trades']}
- **平均持仓天数**: {performance['avg_holding_days']:.1f}天
- **回测天数**: {performance['days']}天

### 交易记录
"""
        
        for i, trade in enumerate(self.trades):
            report_content += f"{i+1}. {trade['date'].strftime('%Y-%m-%d')} - {trade['type']} - 价格: {trade['price']:.2f}\n"
        
        with open(os.path.join(BASE_DIR, 'strategy5说明.md'), 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print("策略说明和回测结果已保存")

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
    print("=== 均线与成交量结合交易系统（策略5） ===")
    
    try:
        # 生成模拟数据
        data = generate_simulation_data()
        print(f"数据生成成功，共 {len(data)} 条记录")
        
        # 运行策略回测
        system = MAVolumeSystem(data.copy())
        system.run()
        
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()
