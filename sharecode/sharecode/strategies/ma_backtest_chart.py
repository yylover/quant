"""
均线回测图表生成器
整合回测逻辑和可视化功能
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
import os

from .ma_visualization import MABacktestVisualizer, ChartConfig, plot_ma_backtest


class MABacktestChart:
    """
    均线回测图表生成器
    整合数据加载、回测计算和图表生成
    """
    
    def __init__(self, 
                 short_window: int = 20,
                 long_window: int = 60,
                 config: Optional[ChartConfig] = None):
        """
        初始化回测图表生成器
        
        Args:
            short_window: 短期均线窗口
            long_window: 长期均线窗口
            config: 图表配置
        """
        self.short_window = short_window
        self.long_window = long_window
        self.config = config or ChartConfig()
        self.visualizer = MABacktestVisualizer(self.config)
        self.data: Optional[pd.DataFrame] = None
        self.results: Optional[pd.DataFrame] = None
    
    def load_data(self, 
                  filepath: str,
                  start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> pd.DataFrame:
        """
        从 CSV 文件加载数据
        
        Args:
            filepath: CSV 文件路径
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'
            
        Returns:
            加载的数据框
        """
        # 读取 CSV
        df = pd.read_csv(filepath)
        
        # 处理日期列
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
        
        # 确保索引是 datetime
        df.index = pd.to_datetime(df.index)
        
        # 日期过滤
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        self.data = df.copy()
        return df
    
    def run_backtest(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        运行均线回测
        
        Args:
            df: 数据框，如果为 None 则使用已加载的数据
            
        Returns:
            包含回测结果的数据框
        """
        if df is None:
            df = self.data
        
        if df is None:
            raise ValueError("没有数据可供回测，请先调用 load_data()")
        
        data = df.copy()
        
        # 计算均线
        data['short_ma'] = data['close'].rolling(window=self.short_window).mean()
        data['long_ma'] = data['close'].rolling(window=self.long_window).mean()
        
        # 生成交易信号
        data['signal'] = 0
        data.loc[data['short_ma'] > data['long_ma'], 'signal'] = 1
        
        # 计算持仓状态（去除连续相同信号）
        data['position'] = data['signal'].diff().ne(0).cumsum()
        data['position'] = data['signal']
        
        # 去除第一个信号之前的部分
        first_valid = data['short_ma'].first_valid_index()
        if first_valid:
            data = data.loc[first_valid:].copy()
        
        # 计算收益率
        data['returns'] = data['close'].pct_change()
        data['strategy_returns'] = data['position'].shift(1) * data['returns']
        
        # 计算累计收益
        data['cumulative_returns'] = (1 + data['strategy_returns']).cumprod() - 1
        data['benchmark_cumulative'] = (1 + data['returns']).cumprod() - 1
        
        # 计算回撤
        running_max = (1 + data['cumulative_returns']).expanding().max()
        data['drawdown'] = ((1 + data['cumulative_returns']) - running_max) / running_max
        
        self.results = data.copy()
        return data
    
    def generate_chart(self, 
                       title: Optional[str] = None,
                       save_path: Optional[str] = None,
                       show_stats: bool = True) -> Any:
        """
        生成回测图表
        
        Args:
            title: 图表标题
            save_path: 保存路径
            show_stats: 是否显示统计信息
            
        Returns:
            matplotlib Figure 对象
        """
        if self.results is None:
            raise ValueError("没有回测结果，请先调用 run_backtest()")
        
        # 生成标题
        if title is None:
            title = f"均线回测策略 (MA{self.short_window}/MA{self.long_window})"
        
        # 绘制综合图表
        fig, axes = self.visualizer.plot_comprehensive_chart(
            self.results, 
            title=title,
            show_stats=show_stats
        )
        
        # 保存图表
        if save_path:
            self.visualizer.save_chart(save_path, fig)
        
        return fig
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取回测摘要统计
        
        Returns:
            统计信息字典
        """
        if self.results is None:
            raise ValueError("没有回测结果，请先调用 run_backtest()")
        
        data = self.results
        
        # 计算各项指标
        total_return = data['cumulative_returns'].iloc[-1] * 100
        
        n_years = len(data) / 252
        annual_return = ((1 + data['cumulative_returns'].iloc[-1]) ** (1/n_years) - 1) * 100 if n_years > 0 else 0
        
        max_drawdown = data['drawdown'].min() * 100
        
        returns_mean = data['strategy_returns'].mean()
        returns_std = data['strategy_returns'].std()
        sharpe_ratio = (returns_mean / returns_std) * np.sqrt(252) if returns_std != 0 else 0
        
        # 计算交易次数
        trades = data['position'].diff().abs().sum() / 2
        
        # 计算胜率
        winning_days = (data['strategy_returns'] > 0).sum()
        total_trading_days = (data['position'] > 0).sum()
        win_rate = (winning_days / total_trading_days * 100) if total_trading_days > 0 else 0
        
        # 基准收益
        benchmark_return = data['benchmark_cumulative'].iloc[-1] * 100
        
        return {
            'short_window': self.short_window,
            'long_window': self.long_window,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'trades': int(trades),
            'win_rate': win_rate,
            'benchmark_return': benchmark_return,
            'excess_return': total_return - benchmark_return,
            'start_date': data.index[0].strftime('%Y-%m-%d'),
            'end_date': data.index[-1].strftime('%Y-%m-%d'),
            'total_days': len(data)
        }
    
    def print_summary(self):
        """打印回测摘要"""
        summary = self.get_summary()
        
        print("\n" + "="*50)
        print("均线回测策略结果摘要")
        print("="*50)
        print(f"均线参数: MA{summary['short_window']} / MA{summary['long_window']}")
        print(f"回测区间: {summary['start_date']} 至 {summary['end_date']}")
        print(f"交易日数: {summary['total_days']}")
        print("-"*50)
        print(f"总收益率:     {summary['total_return']:>10.2f}%")
        print(f"年化收益率:   {summary['annual_return']:>10.2f}%")
        print(f"最大回撤:     {summary['max_drawdown']:>10.2f}%")
        print(f"夏普比率:     {summary['sharpe_ratio']:>10.2f}")
        print(f"交易次数:     {summary['trades']:>10d}")
        print(f"胜率:         {summary['win_rate']:>10.2f}%")
        print("-"*50)
        print(f"基准收益率:   {summary['benchmark_return']:>10.2f}%")
        print(f"超额收益:     {summary['excess_return']:>10.2f}%")
        print("="*50 + "\n")


def run_backtest_with_chart(data_path: str,
                            short_window: int = 20,
                            long_window: int = 60,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            output_dir: str = './',
                            show_chart: bool = False) -> Dict[str, Any]:
    """
    便捷函数：运行回测并生成图表
    
    Args:
        data_path: 数据文件路径
        short_window: 短期均线窗口
        long_window: 长期均线窗口
        start_date: 开始日期
        end_date: 结束日期
        output_dir: 输出目录
        show_chart: 是否显示图表
        
    Returns:
        回测结果摘要
    """
    # 创建回测器
    backtest = MABacktestChart(
        short_window=short_window,
        long_window=long_window
    )
    
    # 加载数据
    print(f"正在加载数据: {data_path}")
    backtest.load_data(data_path, start_date, end_date)
    
    # 运行回测
    print(f"正在运行回测 (MA{short_window}/MA{long_window})...")
    backtest.run_backtest()
    
    # 打印摘要
    backtest.print_summary()
    
    # 生成图表
    # 从数据路径提取股票代码
    stock_code = os.path.basename(data_path).split('_')[0]
    chart_filename = f"{stock_code}_MA{short_window}_{long_window}_backtest.png"
    chart_path = os.path.join(output_dir, chart_filename)
    
    print(f"正在生成图表: {chart_path}")
    fig = backtest.generate_chart(save_path=chart_path)
    
    if show_chart:
        import matplotlib.pyplot as plt
        plt.show()
    
    return backtest.get_summary()


# 批量回测函数
def batch_backtest(data_dir: str,
                   short_windows: List[int] = [10, 20],
                   long_windows: List[int] = [30, 60],
                   output_dir: str = './',
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
    """
    批量运行多个参数组合的回测
    
    Args:
        data_dir: 数据文件目录
        short_windows: 短期均线窗口列表
        long_windows: 长期均线窗口列表
        output_dir: 输出目录
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        回测结果汇总 DataFrame
    """
    import glob
    
    # 获取所有 CSV 文件
    csv_files = glob.glob(os.path.join(data_dir, '*_daily*.csv'))
    
    results = []
    
    for csv_file in csv_files:
        stock_code = os.path.basename(csv_file).split('_')[0]
        print(f"\n处理股票: {stock_code}")
        
        for short in short_windows:
            for long in long_windows:
                if short >= long:
                    continue
                
                try:
                    summary = run_backtest_with_chart(
                        data_path=csv_file,
                        short_window=short,
                        long_window=long,
                        start_date=start_date,
                        end_date=end_date,
                        output_dir=output_dir,
                        show_chart=False
                    )
                    summary['stock_code'] = stock_code
                    results.append(summary)
                except Exception as e:
                    print(f"  回测失败 (MA{short}/MA{long}): {e}")
    
    # 创建结果 DataFrame
    if results:
        df_results = pd.DataFrame(results)
        # 保存结果
        result_path = os.path.join(output_dir, 'batch_backtest_results.csv')
        df_results.to_csv(result_path, index=False)
        print(f"\n批量回测结果已保存: {result_path}")
        return df_results
    else:
        print("没有成功的回测结果")
        return pd.DataFrame()
