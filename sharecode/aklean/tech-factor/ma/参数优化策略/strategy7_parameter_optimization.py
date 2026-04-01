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

class ParameterOptimizationSystem:
    """参数优化交易系统"""
    
    def __init__(self, data):
        """初始化交易系统"""
        self.data = data.copy()
        self.optimization_results = []  # 参数优化结果
        self.best_params = None  # 最优参数
        self.best_performance = None  # 最优性能指标
        self.trades = []  # 交易记录
        
    def backtest_strategy(self, fast_period, slow_period):
        """使用特定参数回测策略"""
        data = self.data.copy()
        
        # 计算均线
        data['fast_ma'] = data['收盘'].rolling(window=fast_period).mean()
        data['slow_ma'] = data['收盘'].rolling(window=slow_period).mean()
        
        # 计算均线差值
        data['ma_diff'] = data['fast_ma'] - data['slow_ma']
        
        # 生成交易信号
        data['signal'] = 0
        for i in range(1, len(data)):
            # 买入信号：快线上穿慢线
            if data['ma_diff'].iloc[i] > 0 and data['ma_diff'].iloc[i-1] <= 0:
                data.loc[data.index[i], 'signal'] = 1
            # 卖出信号：快线下穿慢线
            elif data['ma_diff'].iloc[i]< 0 and data['ma_diff'].iloc[i-1] >= 0:
                data.loc[data.index[i], 'signal'] = -1
        
        # 执行回测
        data['returns'] = data['收盘'].pct_change()
        data['strategy_returns'] = 0.0
        
        position = 0
        for i in range(1, len(data)):
            signal = data['signal'].iloc[i]
            
            if signal == 1 and position == 0:
                position = 1
            elif signal == -1 and position == 1:
                position = 0
            
            data.loc[data.index[i], 'strategy_returns'] = float(position * data['returns'].iloc[i])
        
        # 计算性能指标
        data['cum_returns'] = (1 + data['strategy_returns']).cumprod()
        
        total_return = data['cum_returns'].iloc[-1] - 1
        
        # 计算年化收益率
        days = (data.index[-1] - data.index[0]).days
        annual_return = (1 + total_return) ** (365 / days) - 1
        
        # 计算最大回撤
        running_max = data['cum_returns'].cummax()
        drawdown = (data['cum_returns'] - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 计算夏普比率 (假设无风险利率为3%)
        daily_returns = data['strategy_returns'].dropna()
        if daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() - 0.03/252) / daily_returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        return {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'data': data
        }
    
    def optimize_parameters(self):
        """网格搜索优化参数"""
        print("开始参数优化...")
        
        # 定义参数搜索范围
        fast_periods = list(range(5, 30, 5))  # 快线周期：5, 10, 15, 20, 25
        slow_periods = list(range(30, 100, 10))  # 慢线周期：30, 40, 50, 60, 70, 80, 90
        
        print(f"搜索参数组合: 快线={fast_periods}, 慢线={slow_periods}")
        
        # 执行网格搜索
        for fast in fast_periods:
            for slow in slow_periods:
                if fast >= slow:
                    continue
                
                print(f"测试参数: 快线={fast}天, 慢线={slow}天")
                result = self.backtest_strategy(fast, slow)
                self.optimization_results.append(result)
        
        # 找到最优参数（按夏普比率排序）
        if self.optimization_results:
            self.optimization_results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
            self.best_params = self.optimization_results[0]
            self.best_performance = {
                'total_return': self.best_params['total_return'],
                'annual_return': self.best_params['annual_return'],
                'max_drawdown': self.best_params['max_drawdown'],
                'sharpe_ratio': self.best_params['sharpe_ratio']
            }
            
            print(f"\n找到最优参数: 快线={self.best_params['fast_period']}天, 慢线={self.best_params['slow_period']}天")
            print(f"夏普比率: {self.best_params['sharpe_ratio']:.2f}")
            
        return self.best_params
    
    def run_best_strategy(self):
        """使用最优参数运行策略"""
        if not self.best_params:
            print("未找到最优参数，请先运行优化")
            return
        
        data = self.best_params['data'].copy()
        
        # 计算基准收益率
        data['benchmark_returns'] = (1 + data['returns']).cumprod()
        
        # 提取交易记录
        position = 0
        for i in range(1, len(data)):
            signal = data['signal'].iloc[i]
            
            if signal == 1 and position == 0:
                position = 1
                self.trades.append({
                    'date': data.index[i],
                    'type': 'buy',
                    'price': data['收盘'].iloc[i],
                    'position': position
                })
            elif signal == -1 and position == 1:
                position = 0
                self.trades.append({
                    'date': data.index[i],
                    'type': 'sell',
                    'price': data['收盘'].iloc[i],
                    'position': position
                })
        
        return data
    
    def calculate_performance(self):
        """计算性能指标"""
        if not self.best_params:
            return None
        
        data = self.best_params['data'].copy()
        
        # 计算基准收益率
        data['benchmark_returns'] = (1 + data['returns']).cumprod()
        benchmark_return = data['benchmark_returns'].iloc[-1] - 1
        
        # 计算胜率
        winning_trades = 0
        for i in range(0, len(self.trades), 2):
            if i + 1< len(self.trades):
                if self.trades[i+1]['price'] >self.trades[i]['price']:
                    winning_trades += 1
        
        total_trades = len(self.trades) // 2
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 计算平均持仓天数
        avg_holding_days = 0
        for i in range(0, len(self.trades), 2):
            if i + 1< len(self.trades):
                holding_days = (self.trades[i+1]['date'] - self.trades[i]['date']).days
                avg_holding_days += holding_days
        
        avg_holding_days = avg_holding_days / total_trades if total_trades >0 else 0
        
        # 计算盈亏比
        total_profit = 0
        total_loss = 0
        for i in range(0, len(self.trades), 2):
            if i + 1< len(self.trades):
                profit = self.trades[i+1]['price'] - self.trades[i]['price']
                if profit >0:
                    total_profit += profit
                else:
                    total_loss += abs(profit)
        
        profit_factor = total_profit / total_loss if total_loss >0 else np.inf
        
        # 确保 self.best_performance 存在
        if not hasattr(self, 'best_performance') or self.best_performance is None:
            self.best_performance = {
                'total_return': self.best_params['total_return'],
                'annual_return': self.best_params['annual_return'],
                'max_drawdown': self.best_params['max_drawdown'],
                'sharpe_ratio': self.best_params['sharpe_ratio']
            }
        
        return {
            'total_return': self.best_performance['total_return'],
            'benchmark_return': benchmark_return,
            'annual_return': self.best_performance['annual_return'],
            'max_drawdown': self.best_performance['max_drawdown'],
            'sharpe_ratio': self.best_performance['sharpe_ratio'],
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_holding_days': avg_holding_days,
            'profit_factor': profit_factor,
            'best_fast_period': self.best_params['fast_period'],
            'best_slow_period': self.best_params['slow_period']
        }
    
    def plot_results(self):
        """绘制回测结果"""
        if not self.best_params:
            print("未找到最优参数，无法绘制结果")
            return
        
        data = self.best_params['data'].copy()
        
        # 确保基准收益率存在
        if 'benchmark_returns' not in data.columns:
            data['benchmark_returns'] = (1 + data['returns']).cumprod()
        
        plt.figure(figsize=(16, 15))
        
        # 绘制价格、均线和交易信号
        plt.subplot(3, 1, 1)
        plt.plot(data.index, data['收盘'], label='收盘价', color='#1f77b4', linewidth=2)
        plt.plot(data.index, data['fast_ma'], label=f'{self.best_params["fast_period"]}日均线', color='#ff7f0e', linewidth=1.5)
        plt.plot(data.index, data['slow_ma'], label=f'{self.best_params["slow_period"]}日均线', color='#2ca02c', linewidth=1.5)
        
        # 标记买卖点
        buy_dates = [trade['date'] for trade in self.trades if trade['type'] == 'buy']
        buy_prices = [trade['price'] for trade in self.trades if trade['type'] == 'buy']
        sell_dates = [trade['date'] for trade in self.trades if trade['type'] == 'sell']
        sell_prices = [trade['price'] for trade in self.trades if trade['type'] == 'sell']
        
        plt.scatter(buy_dates, buy_prices, marker='^', color='#2ca02c', s=120, label='买入', zorder=5)
        plt.scatter(sell_dates, sell_prices, marker='v', color='#d62728', s=120, label='卖出', zorder=5)
        
        plt.title(f'沪深300指数 - 参数优化策略 (最优参数: 快线={self.best_params["fast_period"]}天, 慢线={self.best_params["slow_period"]}天)', 
                 fontsize=16, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制仓位变化
        plt.subplot(3, 1, 2)
        # 创建仓位时间序列
        position_data = []
        for trade in self.trades:
            position_data.append({'date': trade['date'], 'position': trade['position']})
        
        if position_data:
            position_df = pd.DataFrame(position_data)
            position_df.set_index('date', inplace=True)
            
            # 填充仓位数据
            full_dates = pd.date_range(start=data.index[0], end=data.index[-1], freq='B')
            position_df = position_df.reindex(full_dates, method='ffill').fillna(0)
            
            plt.plot(position_df.index, position_df['position'], label='仓位', color='#9467bd', linewidth=2)
        
        plt.title('仓位变化', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('仓位', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        # 绘制累积收益率
        plt.subplot(3, 1, 3)
        plt.plot(data.index, data['cum_returns'], label='策略收益率', color='#1f77b4', linewidth=2)
        plt.plot(data.index, data['benchmark_returns'], label='基准收益率', color='#ff7f0e', linewidth=1.5)
        
        plt.title('累积收益率对比', fontsize=14, fontweight='bold')
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('累积收益', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        plt.tight_layout()
        plt.savefig(os.path.join(BASE_DIR, 'strategy7_backtest.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        print("回测图表已保存")
    
    def plot_optimization_results(self):
        """绘制参数优化结果"""
        if not self.optimization_results:
            print("无优化结果，无法绘制")
            return
        
        # 创建优化结果DataFrame
        results_df = pd.DataFrame([{
            'fast_period': r['fast_period'],
            'slow_period': r['slow_period'],
            'sharpe_ratio': r['sharpe_ratio'],
            'total_return': r['total_return'],
            'max_drawdown': r['max_drawdown']
        } for r in self.optimization_results])
        
        plt.figure(figsize=(16, 12))
        
        # 绘制夏普比率热力图
        plt.subplot(2, 2, 1)
        # 使用正确的pivot参数格式
        pivot_sharpe = results_df.pivot(index='slow_period', columns='fast_period', values='sharpe_ratio')
        im = plt.imshow(pivot_sharpe, cmap='RdYlGn')
        plt.colorbar(im)
        plt.title('夏普比率热力图', fontsize=14, fontweight='bold')
        plt.xlabel('快线周期', fontsize=12)
        plt.ylabel('慢线周期', fontsize=12)
        plt.xticks(range(len(pivot_sharpe.columns)), pivot_sharpe.columns)
        plt.yticks(range(len(pivot_sharpe.index)), pivot_sharpe.index)
        
        # 在热力图上标注数值
        for i in range(len(pivot_sharpe.index)):
            for j in range(len(pivot_sharpe.columns)):
                plt.text(j, i, f"{pivot_sharpe.iloc[i, j]:.2f}", ha='center', va='center', color='black')
        
        # 绘制总收益率热力图
        plt.subplot(2, 2, 2)
        pivot_return = results_df.pivot(index='slow_period', columns='fast_period', values='total_return')
        im = plt.imshow(pivot_return, cmap='RdYlGn')
        plt.colorbar(im)
        plt.title('总收益率热力图', fontsize=14, fontweight='bold')
        plt.xlabel('快线周期', fontsize=12)
        plt.ylabel('慢线周期', fontsize=12)
        plt.xticks(range(len(pivot_return.columns)), pivot_return.columns)
        plt.yticks(range(len(pivot_return.index)), pivot_return.index)
        
        # 在热力图上标注数值
        for i in range(len(pivot_return.index)):
            for j in range(len(pivot_return.columns)):
                plt.text(j, i, f"{pivot_return.iloc[i, j]:.1%}", ha='center', va='center', color='black')
        
        # 绘制最大回撤热力图
        plt.subplot(2, 2, 3)
        pivot_drawdown = results_df.pivot(index='slow_period', columns='fast_period', values='max_drawdown')
        im = plt.imshow(pivot_drawdown, cmap='RdYlGn_r')  # 注意这里使用反转的颜色映射
        plt.colorbar(im)
        plt.title('最大回撤热力图', fontsize=14, fontweight='bold')
        plt.xlabel('快线周期', fontsize=12)
        plt.ylabel('慢线周期', fontsize=12)
        plt.xticks(range(len(pivot_drawdown.columns)), pivot_drawdown.columns)
        plt.yticks(range(len(pivot_drawdown.index)), pivot_drawdown.index)
        
        # 在热力图上标注数值
        for i in range(len(pivot_drawdown.index)):
            for j in range(len(pivot_drawdown.columns)):
                plt.text(j, i, f"{pivot_drawdown.iloc[i, j]:.1%}", ha='center', va='center', color='black')
        
        # 绘制参数性能对比
        plt.subplot(2, 2, 4)
        top_results = results_df.sort_values('sharpe_ratio', ascending=False).head(10)
        x = range(len(top_results))
        plt.bar([i-0.25 for i in x], top_results['sharpe_ratio'], width=0.25, label='夏普比率')
        plt.bar([i+0.00 for i in x], top_results['total_return']*100, width=0.25, label='总收益率(%)')
        plt.bar([i+0.25 for i in x], top_results['max_drawdown']*100, width=0.25, label='最大回撤(%)')
        
        plt.title('参数性能对比', fontsize=14, fontweight='bold')
        plt.xlabel('参数组合', fontsize=12)
        plt.ylabel('数值', fontsize=12)
        plt.xticks(x, [f"{r['fast_period']}/{r['slow_period']}" for _, r in top_results.iterrows()], rotation=45)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10, loc='best')
        
        plt.tight_layout()
        plt.savefig(os.path.join(BASE_DIR, 'strategy7_optimization_results.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        print("参数优化结果图表已保存")
    
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
        # 优化参数
        self.optimize_parameters()
        
        if not self.best_params:
            print("参数优化失败")
            return None
        
        # 使用最优参数运行策略
        data = self.run_best_strategy()
        
        # 计算性能指标
        performance = self.calculate_performance()
        
        # 打印性能指标
        print("\n=== 回测性能指标 ===")
        print(f"最优参数: 快线={performance['best_fast_period']}天, 慢线={performance['best_slow_period']}天")
        print(f"总收益率: {performance['total_return']:.2%}")
        print(f"基准收益率: {performance['benchmark_return']:.2%}")
        print(f"年化收益率: {performance['annual_return']:.2%}")
        print(f"最大回撤: {performance['max_drawdown']:.2%}")
        print(f"夏普比率: {performance['sharpe_ratio']:.2f}")
        print(f"胜率: {performance['win_rate']:.2%}")
        print(f"盈亏比: {performance['profit_factor']:.2f}")
        print(f"总交易次数: {performance['total_trades']}")
        print(f"平均持仓天数: {performance['avg_holding_days']:.1f}天")
        
        # 打印交易日志
        self.print_trade_log()
        
        # 绘制结果
        self.plot_results()
        self.plot_optimization_results()
        
        # 保存回测数据
        data.to_csv(os.path.join(BASE_DIR, 'strategy7_backtest.csv'))
        print("\n回测数据已保存")
        
        # 保存参数优化结果
        results_df = pd.DataFrame([{
            'fast_period': r['fast_period'],
            'slow_period': r['slow_period'],
            'sharpe_ratio': r['sharpe_ratio'],
            'total_return': r['total_return'],
            'annual_return': r['annual_return'],
            'max_drawdown': r['max_drawdown']
        } for r in self.optimization_results])
        results_df.to_csv(os.path.join(BASE_DIR, 'strategy7_optimization_results.csv'), index=False)
        print("参数优化结果已保存")
        
        # 保存策略说明和结果
        self.save_strategy_report(performance)
        
        return performance
    
    def save_strategy_report(self, performance):
        """保存策略说明和回测结果"""
        # 安全检查performance字典的键
        total_return = performance.get('total_return', 0)
        benchmark_return = performance.get('benchmark_return', 0)
        annual_return = performance.get('annual_return', 0)
        max_drawdown = performance.get('max_drawdown', 0)
        sharpe_ratio = performance.get('sharpe_ratio', 0)
        win_rate = performance.get('win_rate', 0)
        profit_factor = performance.get('profit_factor', 0)
        total_trades = performance.get('total_trades', 0)
        avg_holding_days = performance.get('avg_holding_days', 0)
        best_fast_period = performance.get('best_fast_period', 0)
        best_slow_period = performance.get('best_slow_period', 0)
        
        report_content = f"""# 参数优化交易系统（策略7）

## 策略说明

### 核心思路
通过回测优化均线参数，找到最优组合。使用网格搜索方法测试不同的均线参数组合，选择夏普比率最高的参数。

### 优化方法
- **参数搜索范围**：
  - 快线周期：5, 10, 15, 20, 25天
  - 慢线周期：30, 40, 50, 60, 70, 80, 90天
- **优化目标**：夏普比率最大化
- **回测策略**：均线交叉策略（快线上穿慢线买入，快线下穿慢线卖出）

### 最优参数
- **快线周期**: {best_fast_period}天
- **慢线周期**: {best_slow_period}天

## 回测结果

### 性能指标
- **总收益率**: {total_return:.2%}
- **基准收益率**: {benchmark_return:.2%}
- **年化收益率**: {annual_return:.2%}
- **最大回撤**: {max_drawdown:.2%}
- **夏普比率**: {sharpe_ratio:.2f}
- **胜率**: {win_rate:.2%}
- **盈亏比**: {profit_factor:.2f}
- **总交易次数**: {total_trades}
- **平均持仓天数**: {avg_holding_days:.1f}天

### 交易记录
"""
        
        for i, trade in enumerate(self.trades):
            report_content += f"{i+1}. {trade['date'].strftime('%Y-%m-%d')} - {trade['type']} - 价格: {trade['price']:.2f}\n"
        
        with open(os.path.join(BASE_DIR, 'strategy7说明.md'), 'w', encoding='utf-8') as f:
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
    print("=== 参数优化交易系统（策略7） ===")
    
    try:
        # 生成模拟数据
        data = generate_simulation_data()
        print(f"数据生成成功，共 {len(data)} 条记录")
        
        # 运行策略回测
        system = ParameterOptimizationSystem(data.copy())
        system.run()
        
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()
