"""
均线回测策略可视化模块
提供持仓线、收益曲线、交易信号等图表功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
import warnings

# 设置中文字体
warnings.filterwarnings('ignore')


@dataclass
class ChartConfig:
    """图表配置类"""
    # 图表尺寸
    figsize: Tuple[int, int] = (16, 12)
    dpi: int = 100
    
    # 颜色配置
    price_color: str = '#333333'
    short_ma_color: str = '#1f77b4'  # 蓝色
    long_ma_color: str = '#d62728'   # 红色
    buy_signal_color: str = '#2ca02c'  # 绿色
    sell_signal_color: str = '#ff4444'  # 红色
    position_color: str = '#9467bd'  # 紫色
    returns_color: str = '#1f77b4'   # 蓝色
    benchmark_color: str = '#ff7f0e'  # 橙色
    drawdown_color: str = '#d62728'  # 红色
    
    # 线型配置
    price_linewidth: float = 1.0
    ma_linewidth: float = 1.5
    
    # 字体配置
    title_fontsize: int = 14
    label_fontsize: int = 10
    tick_fontsize: int = 9
    legend_fontsize: int = 9
    
    # 网格配置
    show_grid: bool = True
    grid_alpha: float = 0.3
    
    # 子图高度比例
    height_ratios: List[int] = field(default_factory=lambda: [3, 1, 2, 1])
    
    def __post_init__(self):
        """初始化后设置 matplotlib 参数"""
        self._setup_chinese_font()
    
    def _setup_chinese_font(self):
        """设置中文字体"""
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


class MABacktestVisualizer:
    """均线回测策略可视化类"""
    
    def __init__(self, config: Optional[ChartConfig] = None):
        """
        初始化可视化器
        
        Args:
            config: 图表配置对象，如果为 None 则使用默认配置
        """
        self.config = config or ChartConfig()
        self.fig: Optional[plt.Figure] = None
        self.axes: Optional[List[plt.Axes]] = None
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        准备数据，确保必要的列存在
        
        Args:
            df: 输入数据框
            
        Returns:
            处理后的数据框
        """
        data = df.copy()
        
        # 确保日期列为索引
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            data.set_index('date', inplace=True)
        
        # 确保索引是 datetime 类型
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        # 计算必要的派生列
        if 'returns' not in data.columns and 'close' in data.columns:
            data['returns'] = data['close'].pct_change()
        
        if 'cumulative_returns' not in data.columns and 'returns' in data.columns:
            data['cumulative_returns'] = (1 + data['returns']).cumprod() - 1
        
        if 'benchmark_returns' not in data.columns and 'close' in data.columns:
            data['benchmark_returns'] = data['close'].pct_change()
            data['benchmark_cumulative'] = (1 + data['benchmark_returns']).cumprod() - 1
        
        # 计算回撤
        if 'cumulative_returns' in data.columns:
            data = self._calculate_drawdown(data)
        
        return data
    
    def _calculate_drawdown(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算回撤"""
        data = df.copy()
        cumulative = (1 + data['cumulative_returns'])
        running_max = cumulative.expanding().max()
        data['drawdown'] = (cumulative - running_max) / running_max
        return data
    
    def create_subplots(self, n_plots: int = 4) -> Tuple[plt.Figure, List[plt.Axes]]:
        """
        创建子图布局
        
        Args:
            n_plots: 子图数量
            
        Returns:
            (fig, axes) 元组
        """
        height_ratios = self.config.height_ratios[:n_plots]
        
        fig, axes = plt.subplots(
            n_plots, 1, 
            figsize=self.config.figsize,
            dpi=self.config.dpi,
            gridspec_kw={'height_ratios': height_ratios},
            sharex=True
        )
        
        if n_plots == 1:
            axes = [axes]
        
        self.fig = fig
        self.axes = axes
        return fig, axes
    
    def plot_price_and_ma(self, df: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
        """
        绘制价格和均线图表
        
        Args:
            df: 数据框，需要包含 close, short_ma, long_ma 列
            ax: 指定的 axes，如果为 None 则创建新的
            
        Returns:
            axes 对象
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))
        
        # 绘制价格线
        ax.plot(df.index, df['close'], 
                color=self.config.price_color, 
                linewidth=self.config.price_linewidth,
                label='收盘价', alpha=0.8)
        
        # 绘制均线
        if 'short_ma' in df.columns:
            ax.plot(df.index, df['short_ma'], 
                    color=self.config.short_ma_color,
                    linewidth=self.config.ma_linewidth,
                    label='短期均线')
        
        if 'long_ma' in df.columns:
            ax.plot(df.index, df['long_ma'], 
                    color=self.config.long_ma_color,
                    linewidth=self.config.ma_linewidth,
                    label='长期均线')
        
        # 设置标题和标签
        ax.set_title('价格与均线', fontsize=self.config.title_fontsize)
        ax.set_ylabel('价格', fontsize=self.config.label_fontsize)
        ax.legend(loc='upper left', fontsize=self.config.legend_fontsize)
        
        if self.config.show_grid:
            ax.grid(True, alpha=self.config.grid_alpha)
        
        return ax
    
    def plot_signals(self, df: pd.DataFrame, ax: plt.Axes) -> plt.Axes:
        """
        在价格图上标记交易信号
        
        Args:
            df: 数据框，需要包含 position 列（0/1 表示空仓/持仓）
            ax: 价格图的 axes
            
        Returns:
            axes 对象
        """
        if 'position' not in df.columns:
            return ax
        
        # 计算信号点
        position = df['position']
        
        # 买入信号：position 从 0 变为 1
        buy_signals = (position == 1) & (position.shift(1) == 0)
        buy_points = df[buy_signals]
        
        # 卖出信号：position 从 1 变为 0
        sell_signals = (position == 0) & (position.shift(1) == 1)
        sell_points = df[sell_signals]
        
        # 绘制买入信号
        if not buy_points.empty:
            ax.scatter(buy_points.index, buy_points['close'], 
                      color=self.config.buy_signal_color,
                      marker='^', s=100, label='买入', zorder=5)
        
        # 绘制卖出信号
        if not sell_points.empty:
            ax.scatter(sell_points.index, sell_points['close'], 
                      color=self.config.sell_signal_color,
                      marker='v', s=100, label='卖出', zorder=5)
        
        # 更新图例
        ax.legend(loc='upper left', fontsize=self.config.legend_fontsize)
        
        return ax
    
    def plot_position(self, df: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
        """
        绘制持仓状态图表
        
        Args:
            df: 数据框，需要包含 position 列
            ax: 指定的 axes，如果为 None 则创建新的
            
        Returns:
            axes 对象
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 2))
        
        if 'position' not in df.columns:
            ax.set_title('持仓状态（无数据）', fontsize=self.config.title_fontsize)
            return ax
        
        # 绘制阶梯图
        ax.fill_between(df.index, 0, df['position'], 
                        color=self.config.position_color, 
                        alpha=0.5, step='post')
        ax.step(df.index, df['position'], 
                color=self.config.position_color, 
                linewidth=1.5, where='post')
        
        # 设置标题和标签
        ax.set_title('持仓状态', fontsize=self.config.title_fontsize)
        ax.set_ylabel('持仓', fontsize=self.config.label_fontsize)
        ax.set_ylim(-0.1, 1.1)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['空仓', '持仓'])
        
        if self.config.show_grid:
            ax.grid(True, alpha=self.config.grid_alpha, axis='y')
        
        return ax
    
    def plot_returns(self, df: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
        """
        绘制收益曲线图表
        
        Args:
            df: 数据框，需要包含 cumulative_returns 列
            ax: 指定的 axes，如果为 None 则创建新的
            
        Returns:
            axes 对象
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 4))
        
        # 绘制策略收益曲线
        if 'cumulative_returns' in df.columns:
            ax.plot(df.index, df['cumulative_returns'] * 100,
                   color=self.config.returns_color,
                   linewidth=1.5, label='策略收益')
        
        # 绘制基准收益曲线
        if 'benchmark_cumulative' in df.columns:
            ax.plot(df.index, df['benchmark_cumulative'] * 100,
                   color=self.config.benchmark_color,
                   linewidth=1.5, label='基准收益', linestyle='--')
        
        # 添加零线
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
        
        # 设置标题和标签
        ax.set_title('收益曲线', fontsize=self.config.title_fontsize)
        ax.set_ylabel('收益率 (%)', fontsize=self.config.label_fontsize)
        ax.legend(loc='upper left', fontsize=self.config.legend_fontsize)
        
        if self.config.show_grid:
            ax.grid(True, alpha=self.config.grid_alpha)
        
        return ax
    
    def plot_drawdown(self, df: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
        """
        绘制回撤图表
        
        Args:
            df: 数据框，需要包含 drawdown 列
            ax: 指定的 axes，如果为 None 则创建新的
            
        Returns:
            axes 对象
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 2))
        
        if 'drawdown' not in df.columns:
            ax.set_title('回撤分析（无数据）', fontsize=self.config.title_fontsize)
            return ax
        
        # 绘制回撤曲线
        drawdown_pct = df['drawdown'] * 100
        ax.fill_between(df.index, 0, drawdown_pct,
                       color=self.config.drawdown_color,
                       alpha=0.5)
        ax.plot(df.index, drawdown_pct,
               color=self.config.drawdown_color,
               linewidth=1.0)
        
        # 标记最大回撤
        max_dd_idx = drawdown_pct.idxmin()
        max_dd_value = drawdown_pct.min()
        ax.scatter([max_dd_idx], [max_dd_value],
                  color='red', s=50, zorder=5)
        ax.annotate(f'最大回撤: {max_dd_value:.2f}%',
                   xy=(max_dd_idx, max_dd_value),
                   xytext=(10, -20), textcoords='offset points',
                   fontsize=9, color='red',
                   arrowprops=dict(arrowstyle='->', color='red'))
        
        # 设置标题和标签
        ax.set_title('回撤分析', fontsize=self.config.title_fontsize)
        ax.set_ylabel('回撤 (%)', fontsize=self.config.label_fontsize)
        
        if self.config.show_grid:
            ax.grid(True, alpha=self.config.grid_alpha)
        
        return ax
    
    def add_stats_text(self, df: pd.DataFrame, ax: plt.Axes):
        """
        在图表上添加统计信息
        
        Args:
            df: 数据框
            ax: 要添加文本的 axes
        """
        stats = self._calculate_stats(df)
        
        # 格式化统计信息
        stats_text = (
            f"总收益率: {stats['total_return']:.2f}%\n"
            f"年化收益率: {stats['annual_return']:.2f}%\n"
            f"最大回撤: {stats['max_drawdown']:.2f}%\n"
            f"夏普比率: {stats['sharpe_ratio']:.2f}"
        )
        
        # 在图表右上角添加文本框
        ax.text(0.98, 0.98, stats_text,
               transform=ax.transAxes,
               fontsize=9,
               verticalalignment='top',
               horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    def _calculate_stats(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算统计指标"""
        stats = {}
        
        if 'cumulative_returns' in df.columns:
            total_return = df['cumulative_returns'].iloc[-1]
            stats['total_return'] = total_return * 100
            
            # 年化收益率
            n_years = len(df) / 252  # 假设每年252个交易日
            if n_years > 0:
                stats['annual_return'] = ((1 + total_return) ** (1/n_years) - 1) * 100
            else:
                stats['annual_return'] = 0
        else:
            stats['total_return'] = 0
            stats['annual_return'] = 0
        
        if 'drawdown' in df.columns:
            stats['max_drawdown'] = df['drawdown'].min() * 100
        else:
            stats['max_drawdown'] = 0
        
        if 'returns' in df.columns:
            returns_mean = df['returns'].mean()
            returns_std = df['returns'].std()
            if returns_std != 0:
                stats['sharpe_ratio'] = (returns_mean / returns_std) * np.sqrt(252)
            else:
                stats['sharpe_ratio'] = 0
        else:
            stats['sharpe_ratio'] = 0
        
        return stats
    
    def plot_comprehensive_chart(self, df: pd.DataFrame, 
                                  title: Optional[str] = None,
                                  show_stats: bool = True) -> Tuple[plt.Figure, List[plt.Axes]]:
        """
        绘制综合图表（包含所有子图）
        
        Args:
            df: 数据框
            title: 图表总标题
            show_stats: 是否显示统计信息
            
        Returns:
            (fig, axes) 元组
        """
        # 准备数据
        data = self.prepare_data(df)
        
        # 创建子图
        fig, axes = self.create_subplots(n_plots=4)
        
        # 1. 价格和均线
        self.plot_price_and_ma(data, axes[0])
        if 'position' in data.columns:
            self.plot_signals(data, axes[0])
        
        # 2. 持仓状态
        self.plot_position(data, axes[1])
        
        # 3. 收益曲线
        self.plot_returns(data, axes[2])
        if show_stats:
            self.add_stats_text(data, axes[2])
        
        # 4. 回撤
        self.plot_drawdown(data, axes[3])
        
        # 设置 x 轴格式
        axes[3].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        axes[3].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(axes[3].xaxis.get_majorticklabels(), rotation=45)
        
        # 设置总标题
        if title:
            fig.suptitle(title, fontsize=self.config.title_fontsize + 2, y=0.995)
        
        # 调整布局
        plt.tight_layout()
        plt.subplots_adjust(top=0.96)
        
        return fig, axes
    
    def save_chart(self, filepath: str, fig: Optional[plt.Figure] = None, 
                   dpi: Optional[int] = None):
        """
        保存图表到文件
        
        Args:
            filepath: 文件路径
            fig: 要保存的 figure，如果为 None 则使用当前 figure
            dpi: 分辨率，如果为 None 则使用配置中的 dpi
        """
        if fig is None:
            fig = self.fig
        
        if fig is None:
            raise ValueError("没有可保存的图表")
        
        save_dpi = dpi or self.config.dpi
        fig.savefig(filepath, dpi=save_dpi, bbox_inches='tight')
        print(f"图表已保存到: {filepath}")
    
    def show(self):
        """显示图表"""
        if self.fig:
            plt.show()


# 便捷函数
def plot_ma_backtest(df: pd.DataFrame, 
                     title: Optional[str] = None,
                     save_path: Optional[str] = None,
                     config: Optional[ChartConfig] = None) -> Tuple[plt.Figure, List[plt.Axes]]:
    """
    便捷函数：绘制均线回测综合图表
    
    Args:
        df: 数据框
        title: 图表标题
        save_path: 保存路径，如果为 None 则不保存
        config: 图表配置
        
    Returns:
        (fig, axes) 元组
    """
    visualizer = MABacktestVisualizer(config)
    fig, axes = visualizer.plot_comprehensive_chart(df, title)
    
    if save_path:
        visualizer.save_chart(save_path)
    
    return fig, axes
