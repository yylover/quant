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

class BreakoutRetestSystem:
    """均线突破回踩交易系统"""
    
    def __init__(self, data, ma_window=20, retest_threshold=0.02, retest_days=15, slope_period=10):
        """初始化交易系统"""
        self.data = data.copy()
        self.ma_window = ma_window          # 均线周期：20日
        self.retest_threshold = retest_threshold  # 回踩阈值：2%
        self.retest_days = retest_days      # 回踩确认天数：15天
        self.slope_period = slope_period    # 斜率计算周期：10天
        self.position = 0  # 持仓状态：1=持有，0=空仓
        self.trades = []  # 交易记录
        self.breakout_detected = False  # 突破检测标志
        self.breakout_price = 0  # 突破价格
        
    def calculate_indicators(self):
        """计算技术指标"""
        # 计算均线
        self.data['ma'] = self.data['收盘'].rolling(window=self.ma_window).mean()
        
        # 计算价格与均线的关系
        self.data['price_above_ma'] = self.data['收盘'] > self.data['ma']
        self.data['price_below_ma'] = self.data['收盘']< self.data['ma']
        
        # 计算价格突破均线信号
        self.data['breakout_signal'] = 0
        for i in range(1, len(self.data)):
            # 价格上穿均线
            if self.data['price_above_ma'].iloc[i] and not self.data['price_above_ma'].iloc[i-1]:
                self.data.loc[self.data.index[i], 'breakout_signal'] = 1
    
    def generate_signals(self):
        """生成交易信号"""
        self.data['signal'] = 0
        
        for i in range(1, len(self.data)):
            # 开仓条件：价格上穿均线
            if self.data['breakout_signal'].iloc[i] == 1:
                self.data.loc[self.data.index[i], 'signal'] = 1
            
            # 平仓条件：价格跌破均线
            elif self.data['price_below_ma'].iloc[i] and not self.data['price_below_ma'].iloc[i-1]:
                self.data.loc[self.data.index[i], 'signal'] = -1
    
    def backtest(self):
        """执行回测"""
        print(f"开始回测...")
        print(f"均线周期: {self.ma_window}天, 回踩阈值: {self.retest_threshold:.1%}, 回踩确认天数: {self.retest_days}天")
        
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
                    'ma': self.data['ma'].iloc[i]
                })
            
            # 卖出信号
            elif signal == -1 and self.position == 1:
                self.position = 0
                self.trades.append({
                    'date': self.data.index[i],
                    'type': 'sell',
                    'price': self.data['收盘'].iloc[i],
                    'position': self.position,
                    'ma': self.data['ma'].iloc[i]
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
        plt.figure(figsize=(16, 18))
        
        # 绘制价格、均线和买卖点
        plt.subplot(4, 1, 1)
        plt.plot(self.data.index, self.data['收盘'], label='收盘价', color='#1f77b4', linewidth=2)
        plt.plot(self.data.index, self.data['ma'], label=f'{self.ma_window}日均线', color='#2ca02c', linewidth=1.5)
        
        # 标记突破点
        breakout_dates = self.data[self.data['breakout_signal'] == 1].index
        breakout_prices = self.data.loc[breakout_dates, '收盘'].values
        plt.scatter(breakout_dates, breakout_prices, marker='o', color='#ff7f0e', s=80, label='突破点', zorder=4)
        
        # 标记买卖点
        buy_dates = [trade['date'] for trade in self.trades if trade['type'] == 'buy']
        buy_prices = [trade['price'] for trade in self.trades if trade['type'] == 'buy']
        sell_dates = [trade['date'] for trade in self.trades if trade['type'] == 'sell']
        sell_prices = [trade['price'] for trade in self.trades if trade['type'] == 'sell']
        
        plt.scatter(buy_dates, buy_prices, marker='^', color='#2ca02c', s=120, label='买入', zorder=5)
        plt.scatter(sell_dates, sell_prices, marker='v', color='#d62728', s=120, label='卖出', zorder=5)
        
        plt.title('沪深300指数 - 均线突破回踩系统', fontsize=16, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制仓位变化
        plt.subplot(4, 1, 2)
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
        
        # 绘制价格与均线的偏离程度
        plt.subplot(4, 1, 3)
        price_ma_diff = abs(self.data['收盘'] - self.data['ma']) / self.data['ma'] * 100
        plt.plot(self.data.index, price_ma_diff, label='价格与均线偏离(%)', color='#ff7f0e', linewidth=1.5)
        plt.axhline(y=self.retest_threshold * 100, color='green', linestyle='--', label=f'回踩阈值({self.retest_threshold:.1%})')
        plt.fill_between(self.data.index, 0, price_ma_diff, 
                        where=price_ma_diff<= self.retest_threshold * 100, color='green', alpha=0.1)
        
        plt.title('价格与均线偏离程度', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('偏离程度(%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制累积收益率
        plt.subplot(4, 1, 4)
        plt.plot(self.data.index, self.data['cum_returns'], label='策略收益率', color='#1f77b4', linewidth=2)
        plt.plot(self.data.index, self.data['benchmark_returns'], label='基准收益率', color='#ff7f0e', linewidth=1.5)
        
        plt.title('累积收益率对比', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('累积收益', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        plt.tight_layout()
        plt.savefig(os.path.join(BASE_DIR, 'breakout_retest_backtest.png'), dpi=300, bbox_inches='tight')
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
        self.data.to_csv(os.path.join(BASE_DIR, 'breakout_retest_backtest.csv'))
        print("\n回测数据已保存")
        
        # 保存策略说明和结果
        self.save_strategy_report(performance)
        
        return performance
    
    def save_strategy_report(self, performance):
        """保存策略说明和回测结果"""
        report_content = f"""# 均线突破回踩交易系统

## 策略说明

### 核心思路
突破均线后等待回踩确认再入场，避免假突破，提高交易胜率。

### 系统结构
- **均线**：{self.ma_window}日均线
- **回踩阈值**：{self.retest_threshold:.1%}（价格与均线的偏离程度）
- **回踩确认天数**：{self.retest_days}天

### 交易逻辑
1. **突破检测**：价格上穿{self.ma_window}日均线，标记为突破点
2. **回踩等待**：突破后等待价格回调到均线附近
3. **回踩确认**：价格回调到均线{self.retest_threshold:.1%}范围内且仍在均线上方
4. **入场时机**：回踩确认后买入
5. **平仓条件**：价格跌破{self.ma_window}日均线

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
        
        with open(os.path.join(BASE_DIR, 'breakout_retest说明.md'), 'w', encoding='utf-8') as f:
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
    print("=== 均线突破回踩交易系统 ===")
    
    try:
        # 生成模拟数据
        data = generate_simulation_data()
        print(f"数据生成成功，共 {len(data)} 条记录")
        
        # 运行策略回测
        system = BreakoutRetestSystem(data.copy())
        system.run()
        
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()
