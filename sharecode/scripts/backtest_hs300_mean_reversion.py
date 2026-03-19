"""Fetch CSI 300 index data and backtest mean reversion strategies.

获取沪深300指数数据并回测均值回归策略.

Usage:
    python scripts/backtest_hs300_mean_reversion.py
"""
from __future__ import annotations

import akshare as ak
import pandas as pd
import vectorbt as vbt
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from sharecode.strategies.mean_reversion import (
    bollinger_reversion_signals,
    rsi_reversion_signals,
    zscore_reversion_signals,
    deviation_reversion_signals,
    kdj_reversion_signals,
    williams_r_reversion_signals,
    cci_reversion_signals,
)


def fetch_hs300_data(start: str = "20180101", end: str | None = None) -> pd.DataFrame:
    """Fetch CSI 300 index daily data using AkShare.

    Args:
        start: Start date in YYYYMMDD format
        end: End date in YYYYMMDD format, default: today

    Returns:
        DataFrame with columns: 日期, 开盘, 最高, 最低, 收盘, 成交量, 成交额
    """
    if end is None:
        end = date.today().strftime("%Y%m%d")

    print(f"Fetching CSI 300 index data from {start} to {end}...")

    try:
        # 使用 AkShare 获取沪深300指数数据
        df = ak.stock_zh_index_daily_em(symbol="sh000300", start_date=start, end_date=end)

        if df.empty:
            raise ValueError("Empty DataFrame returned from AkShare")

        # 重命名列以匹配中文格式
        df = df.rename(columns={
            "date": "日期",
            "open": "开盘",
            "high": "最高",
            "low": "最低",
            "close": "收盘",
            "volume": "成交量",
            "amount": "成交额",
        })

        # 确保日期列是 datetime 类型
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期").reset_index(drop=True)

        print(f"Fetched {len(df)} rows from {df['日期'].iloc[0].date()} to {df['日期'].iloc[-1].date()}")
        return df

    except Exception as e:
        print(f"Error fetching CSI 300 data: {e}")
        raise


def backtest_strategy(
    df: pd.DataFrame,
    strategy_name: str,
    strategy_func,
    **kwargs,
) -> dict:
    """Run backtest for a single strategy.

    Args:
        df: Price data DataFrame
        strategy_name: Name of the strategy for display
        strategy_func: Strategy signal function
        **kwargs: Strategy parameters

    Returns:
        Dictionary with backtest results
    """
    print(f"\n{'='*60}")
    print(f"Backtesting: {strategy_name}")
    print(f"{'='*60}")

    # 生成交易信号
    close, entries, exits = strategy_func(df, **kwargs)

    # 使用 vectorbt 进行回测
    portfolio = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=100000.0,  # 初始资金10万
        fees=0.0003,  # 手续费 0.03%
        slippage=0.0001,  # 滑点 0.01%
    )

    # 计算基准收益(买入持有)
    buy_hold_return = ((close.iloc[-1] / close.iloc[0]) - 1) * 100

    # 获取回测统计
    stats = portfolio.stats()

    # 打印关键指标
    total_return = stats['Total Return [%]']
    print(f"总收益: {total_return:.2f}%")

    # 尝试获取年化收益,如果不可用则跳过
    try:
        annual_return = stats['Annual Return [%]']
        print(f"年化收益: {annual_return:.2f}%")
    except (KeyError, TypeError):
        annual_return = None
        print("年化收益: N/A")

    max_drawdown = stats['Max Drawdown [%]']
    print(f"最大回撤: {max_drawdown:.2f}%")

    # 尝试获取夏普比率
    try:
        sharpe_ratio = stats['Sharpe Ratio']
        print(f"夏普比率: {sharpe_ratio:.2f}")
    except (KeyError, TypeError):
        sharpe_ratio = None
        print("夏普比率: N/A")

    # 尝试获取收益回撤比
    try:
        calmar_ratio = stats['Calmar Ratio']
        print(f"收益回撤比: {calmar_ratio:.2f}")
    except (KeyError, TypeError):
        calmar_ratio = None
        print("收益回撤比: N/A")

    win_rate = stats['Win Rate [%]']
    print(f"胜率: {win_rate:.2f}%")

    # 尝试获取交易次数
    try:
        num_trades = stats['# Trades']
        print(f"交易次数: {num_trades:.0f}")
    except (KeyError, TypeError):
        num_trades = None
        print("交易次数: N/A")

    # 尝试获取持仓天数
    try:
        avg_trade_duration = stats['Avg Trade Duration']
        print(f"持仓天数: {avg_trade_duration:.1f}")
    except (KeyError, TypeError):
        avg_trade_duration = None
        print("持仓天数: N/A")

    print(f"基准收益(买入持有): {buy_hold_return:.2f}%")
    excess_return = total_return - buy_hold_return
    print(f"超额收益: {excess_return:.2f}%")

    return {
        "strategy_name": strategy_name,
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "num_trades": num_trades,
        "avg_trade_duration": avg_trade_duration,
        "buy_hold_return": buy_hold_return,
        "excess_return": excess_return,
    }


def main():
    """Main function to fetch data and backtest strategies."""
    # 尝试从现有文件加载数据,如果不存在则获取数据
    data_dir = ROOT / "data"
    csv_path = data_dir / "000300_daily_qfq.csv"

    if csv_path.exists():
        print(f"Loading data from existing file: {csv_path}")
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # 确保日期列是 datetime 类型
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期").reset_index(drop=True)

        print(f"Loaded {len(df)} rows from {df['日期'].iloc[0].date()} to {df['日期'].iloc[-1].date()}")
    else:
        # 获取数据
        df = fetch_hs300_data(start="20180101")
        data_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\nData saved to: {csv_path}")

    # 回测所有策略
    strategies = [
        {
            "name": "布林带回归 (Bollinger Reversion)",
            "func": bollinger_reversion_signals,
            "params": {"window": 20, "n_std": 2.0},
        },
        {
            "name": "RSI 回归 (RSI Reversion)",
            "func": rsi_reversion_signals,
            "params": {"window": 14, "low": 30.0, "high": 70.0},
        },
        {
            "name": "Z-Score 回归 (Z-Score Reversion)",
            "func": zscore_reversion_signals,
            "params": {"window": 60, "k": 2.0, "exit_z": 0.0},
        },
        {
            "name": "偏离度回归 (Deviation Reversion)",
            "func": deviation_reversion_signals,
            "params": {"ma_window": 20, "entry_dev": 0.05, "exit_dev": 0.0},
        },
        {
            "name": "KDJ 回归 (KDJ Reversion)",
            "func": kdj_reversion_signals,
            "params": {"window": 9, "m1": 3, "m2": 3, "low": 20.0, "high": 80.0},
        },
        {
            "name": "Williams %R 回归 (Williams %R Reversion)",
            "func": williams_r_reversion_signals,
            "params": {"window": 14, "low": -80.0, "high": -20.0},
        },
        {
            "name": "CCI 回归 (CCI Reversion)",
            "func": cci_reversion_signals,
            "params": {"window": 20, "low": -100.0, "high": 100.0},
        },
    ]

    results = []
    for strategy in strategies:
        try:
            result = backtest_strategy(df, strategy["name"], strategy["func"], **strategy["params"])
            results.append(result)
        except Exception as e:
            print(f"\nError backtesting {strategy['name']}: {e}")
            import traceback
            traceback.print_exc()

    # 打印汇总表格
    print(f"\n{'='*100}")
    print("回测结果汇总 (Backtest Summary)")
    print(f"{'='*100}")

    # 创建结果 DataFrame
    results_df = pd.DataFrame(results)
    results_df = results_df[[
        "strategy_name", "total_return", "annual_return", "max_drawdown",
        "sharpe_ratio", "calmar_ratio", "win_rate", "num_trades",
        "avg_trade_duration", "buy_hold_return", "excess_return"
    ]]

    # 重命名列以便显示
    results_df.columns = [
        "策略", "总收益%", "年化收益%", "最大回撤%",
        "夏普比率", "收益回撤比", "胜率%", "交易次数",
        "持仓天数", "基准收益%", "超额收益%"
    ]

    print(results_df.to_string(index=False))

    # 保存结果
    results_path = data_dir / "hs300_mean_reversion_backtest_results.csv"
    results_df.to_csv(results_path, index=False, encoding="utf-8-sig")
    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()
