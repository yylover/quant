#!/usr/bin/env python
"""
RSRS+价值因子策略回测脚本

策略逻辑：
1. RSRS择时：用最高价对最低价回归，判断市场强弱
2. 价值选股：PB+ROE排名合成，选择低PB高ROE的标的
3. 低波动过滤：剔除高波动标的

作者：量化交易系统
日期：2026-03
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import vectorbt as vbt

# 尝试导入依赖
try:
    import yaml
    from sqlalchemy import create_engine, text
except ImportError:
    yaml = None

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sharecode.strategies.multi_factor import (
    MultiFactorSelector,
    rsrs_factor,
    value_rank_factor,
    low_quality_factor,
)


def load_config():
    """加载配置文件"""
    if yaml is None:
        return None
    config_path = PROJECT_ROOT / "sharecode" / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_db_engine(config):
    """获取数据库连接"""
    if config is None:
        return None
    db_config = config.get('database', {})
    url = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    return create_engine(url)


def load_data_from_mysql(
    engine,
    start_date: str = None,
    end_date: str = None,
    instrument_type: str = 'etf',
    min_bars: int = 500
):
    """从MySQL加载数据"""

    query = """
    SELECT
        i.symbol,
        b.ts as datetime,
        b.open_price as open,
        b.high_price as high,
        b.low_price as low,
        b.close_price as close,
        b.volume
    FROM bar b
    JOIN instrument i ON b.instrument_id = i.id
    WHERE i.type = :type
        AND b.interval = '1d'
        AND b.open_price > 0
        AND b.close_price > 0
    """

    if start_date:
        query += " AND b.ts >= :start_date"
    if end_date:
        query += " AND b.ts <= :end_date"

    query += " ORDER BY i.symbol, b.ts"

    params = {'type': instrument_type}
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date

    df = pd.read_sql(text(query), engine, params=params)

    if df.empty:
        print("⚠️ 未查询到数据")
        return None, None, None

    # 透视表
    open_df = df.pivot(index='datetime', columns='symbol', values='open')
    high_df = df.pivot(index='datetime', columns='symbol', values='high')
    low_df = df.pivot(index='datetime', columns='symbol', values='low')
    close_df = df.pivot(index='datetime', columns='symbol', values='close')
    volume_df = df.pivot(index='datetime', columns='symbol', values='volume')

    # 确保日期索引为datetime
    for df in [open_df, high_df, low_df, close_df, volume_df]:
        df.index = pd.to_datetime(df.index)

    # 剔除数据不足的标的
    min_bars = min_bars
    valid_symbols = (close_df.notna().sum() >= min_bars)
    valid_symbols = valid_symbols[valid_symbols].index

    print(f"✅ 原始标的数: {len(close_df.columns)}")
    print(f"✅ 有效标的数（数据充足）: {len(valid_symbols)}")

    # 过滤
    open_df = open_df[valid_symbols]
    high_df = high_df[valid_symbols]
    low_df = low_df[valid_symbols]
    close_df = close_df[valid_symbols]
    volume_df = volume_df[valid_symbols]

    # 前向填充缺失值
    close_df = close_df.ffill()
    high_df = high_df.ffill()
    low_df = low_df.ffill()

    return close_df, high_df, low_df


def simulate_value_factors(close_df, n_symbols=10):
    """
    模拟价值因子（PB、ROE）
    由于当前数据库没有财务数据，使用价格波动率作为代理
    """
    # 计算PB模拟：使用价格相对排名（价格越低PB越低）
    pb_df = pd.DataFrame(index=close_df.index, columns=close_df.columns)
    for date in close_df.index:
        if date < close_df.index[10]:  # 需要一定历史数据
            continue
        price_row = close_df.loc[date]
        # PB = 价格 / 某个基准，这里用相对排名模拟
        pb_df.loc[date] = 1 + (price_row - price_row.mean()) / price_row.mean()

    # 计算ROE模拟：使用60日动量作为代理
    momentum_60d = close_df.pct_change(60, fill_method=None)
    roe_df = 0.1 + momentum_60d  # ROE = 动量 + 0.1 (基准ROE)

    return pb_df, roe_df


def run_rsrs_backtest(
    close_df,
    high_df,
    low_df,
    pb_df,
    roe_df,
    top_n: int = 10,
    rebalance_days: int = 20,
    buy_threshold: float = 0.7,
    sell_threshold: float = -0.7,
    initial_cash: float = 100000,
    commission: float = 0.0003
):
    """运行RSRS+价值因子回测"""

    print("\n" + "="*60)
    print("RSRS+价值因子策略回测")
    print("="*60)

    # 1. 计算RSRS择时因子
    print("\n📊 计算RSRS择时因子...")
    rsrs_df = rsrs_factor(
        high_df,
        low_df,
        window=18,
        lookback=1100,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold
    )

    # 2. 计算价值因子
    print("📊 计算价值因子（PB+ROE排名）...")
    value_df = value_rank_factor(pb_df, roe_df, weight_pb=0.5, weight_roe=0.5)

    # 3. 计算低质量因子（低波动）
    print("📊 计算低质量因子...")
    low_quality = low_quality_factor(close_df, window=20)

    # 4. 合成因子得分
    print("📊 合成因子得分...")
    score_df = (value_df * 1.0 + low_quality * 0.5).dropna()

    # 5. 生成交易信号
    print("📊 生成交易信号...")
    weights_df = pd.DataFrame(index=close_df.index, columns=close_df.columns, data=0.0)

    # 调仓日期
    rebalance_dates = close_df.index[::rebalance_days]

    for date in rebalance_dates:
        if date not in score_df.index or date not in rsrs_df.index:
            continue

        # 检查RSRS择时信号
        rsrs_values = rsrs_df.loc[date]
        benchmark_rsrs = rsrs_values.mean() if rsrs_values.notna().sum() > 0 else 0

        if pd.isna(benchmark_rsrs) or benchmark_rsrs < buy_threshold:
            # 择时不满足，清仓或保持空仓
            continue

        # 择时满足，选股
        day_scores = score_df.loc[date].sort_values(ascending=False)
        top_symbols = day_scores.head(top_n).index

        # 等权分配
        weight = 1.0 / len(top_symbols)
        weights_df.loc[date, top_symbols] = weight

    # 6. 回测
    print("\n🚀 运行回测...")
    pf = vbt.Portfolio.from_signals(
        close=close_df,
        entries=(weights_df > 0),
        exits=(weights_df.shift(1) > 0) & (weights_df == 0),
        freq='1d',
        init_cash=initial_cash,
        fees=commission,
        slippage=0.0001,
    )

    # 7. 统计
    stats = pf.stats()
    returns = pf.returns()

    print("\n" + "="*60)
    print("📈 回测结果")
    print("="*60)
    print(f"回测区间: {close_df.index[0].date()} ~ {close_df.index[-1].date()}")
    print(f"初始资金: ¥{initial_cash:,.0f}")

    # 获取统计值（可能是Series或标量）
    end_val = stats.get('End Value')
    if hasattr(end_val, 'iloc'):
        end_val = end_val.iloc[0]
    print(f"最终资金: ¥{end_val:,.2f}")

    total_return = stats.get('Total Return [%]')
    if hasattr(total_return, 'iloc'):
        total_return = total_return.iloc[0]
    print(f"总收益率: {total_return:.2f}%")

    cagr = stats.get('CAGR %')
    if hasattr(cagr, 'iloc'):
        cagr = cagr.iloc[0]
    if cagr is not None:
        print(f"年化收益率: {cagr:.2f}%")

    max_dd = stats.get('Max Drawdown [%]')
    if hasattr(max_dd, 'iloc'):
        max_dd = max_dd.iloc[0]
    if max_dd is not None:
        print(f"最大回撤: {max_dd:.2f}%")

    sharpe = stats.get('Sharpe Ratio')
    if hasattr(sharpe, 'iloc'):
        sharpe = sharpe.iloc[0]
    if sharpe is not None:
        print(f"夏普比率: {sharpe:.2f}")

    sortino = stats.get('Sortino Ratio')
    if hasattr(sortino, 'iloc'):
        sortino = sortino.iloc[0]
    if sortino is not None:
        print(f"索提诺比率: {sortino:.2f}")

    win_rate = stats.get('Win Rate [%]')
    if hasattr(win_rate, 'iloc'):
        win_rate = win_rate.iloc[0]
    if win_rate is not None:
        print(f"胜率: {win_rate:.2f}%")

    num_trades = stats.get('# Trades')
    if hasattr(num_trades, 'iloc'):
        num_trades = num_trades.iloc[0]
    if num_trades is not None:
        print(f"交易次数: {num_trades:.0f}")

    # 选股次数统计
    rebalance_count = (weights_df > 0).sum().sum()
    print(f"调仓次数: {rebalance_count}")

    # 8. 对比基准
    print("\n📊 基准对比（等权买入持有）...")
    benchmark_weights = pd.DataFrame(index=close_df.index, columns=close_df.columns, data=0.0)
    benchmark_symbols = close_df.columns[:top_n]
    benchmark_weight = 1.0 / len(benchmark_symbols)
    benchmark_weights[benchmark_symbols] = benchmark_weight

    benchmark_pf = vbt.Portfolio.from_signals(
        close=close_df,
        entries=pd.Series(True, index=close_df.index),
        exits=pd.Series(False, index=close_df.index),
        freq='1d',
        init_cash=initial_cash,
        fees=commission,
        slippage=0.0001,
    )
    benchmark_stats = benchmark_pf.stats()

    bm_return = benchmark_stats.get('Total Return [%]')
    if hasattr(bm_return, 'iloc'):
        bm_return = bm_return.iloc[0]
    print(f"基准总收益率: {bm_return:.2f}%")

    bm_sharpe = benchmark_stats.get('Sharpe Ratio')
    if hasattr(bm_sharpe, 'iloc'):
        bm_sharpe = bm_sharpe.iloc[0]
    print(f"基准夏普比率: {bm_sharpe:.2f}")

    # 超额收益
    excess_return = total_return - bm_return
    print(f"超额收益: {excess_return:.2f}%")

    return {
        'strategy': stats,
        'benchmark': benchmark_stats,
        'portfolio': pf,
        'benchmark_portfolio': benchmark_pf,
        'weights_df': weights_df,
        'score_df': score_df,
        'rsrs_df': rsrs_df,
    }


def load_data_from_csv(start_date=None, end_date=None, min_bars=500):
    """
    从CSV文件加载数据（备用方案）
    支持两种格式：
    1. 单个OHLC文件：每列是一个标的
    2. 多个OHLC文件：每个文件一个标的
    """
    data_dir = PROJECT_ROOT / "data"

    # 检查是否有综合格式文件（每列一个标的）
    close_files = list(data_dir.glob("*close*.csv"))
    high_files = list(data_dir.glob("*high*.csv"))
    low_files = list(data_dir.glob("*low*.csv"))

    # 如果有综合格式文件
    if close_files and high_files and low_files:
        print(f"📥 从综合CSV加载数据")
        close_df = pd.read_csv(close_files[0], index_col=0, parse_dates=True)
        high_df = pd.read_csv(high_files[0], index_col=0, parse_dates=True)
        low_df = pd.read_csv(low_files[0], index_col=0, parse_dates=True)

        # 过滤日期
        if start_date:
            close_df = close_df[close_df.index >= pd.to_datetime(start_date)]
            high_df = high_df[high_df.index >= pd.to_datetime(start_date)]
            low_df = low_df[low_df.index >= pd.to_datetime(start_date)]

        if end_date:
            close_df = close_df[close_df.index <= pd.to_datetime(end_date)]
            high_df = high_df[high_df.index <= pd.to_datetime(end_date)]
            low_df = low_df[low_df.index <= pd.to_datetime(end_date)]

        # 剔除数据不足的标的
        valid_symbols = (close_df.notna().sum() >= min_bars)
        valid_symbols = valid_symbols[valid_symbols].index

        print(f"✅ 原始标的数: {len(close_df.columns)}")
        print(f"✅ 有效标的数: {len(valid_symbols)}")

        # 过滤
        close_df = close_df[valid_symbols]
        high_df = high_df[valid_symbols]
        low_df = low_df[valid_symbols]

        # 前向填充
        close_df = close_df.ffill()
        high_df = high_df.ffill()
        low_df = low_df.ffill()

        return close_df, high_df, low_df

    # 否则合并多个ETF文件
    print(f"📥 从多个ETF文件加载数据...")
    csv_files = list(data_dir.glob("*_daily_qfq.csv"))

    if not csv_files:
        print("❌ 未找到数据文件")
        return None, None, None

    # 选择数据充足的ETF
    etf_list = []
    for f in csv_files[:36]:  # 最多36个ETF
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)

            # 检查是否有OHLC列（支持中英文）
            required_cols_cn = ['开盘', '最高', '最低', '收盘']
            required_cols_en = ['open', 'high', 'low', 'close']

            # 确定列名
            col_map = {}
            if all(col in df.columns for col in required_cols_cn):
                col_map = {'开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close'}
                df = df.rename(columns=col_map)
            elif all(col in df.columns for col in required_cols_en):
                pass  # 已经是英文列名
            else:
                continue

            # 过滤日期
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df.index <= pd.to_datetime(end_date)]

            # 检查数据量
            if len(df) >= min_bars:
                symbol = f.stem.split('_')[0]
                etf_list.append((symbol, df))
        except Exception as e:
            print(f"⚠️ 读取 {f.name} 失败: {e}")
            continue

    if not etf_list:
        print("❌ 没有足够的数据")
        return None, None, None

    # 合并数据
    print(f"✅ 找到 {len(etf_list)} 个有效ETF")

    close_data = {}
    high_data = {}
    low_data = {}

    for symbol, df in etf_list:
        close_data[symbol] = df['close']
        high_data[symbol] = df['high']
        low_data[symbol] = df['low']

    close_df = pd.DataFrame(close_data)
    high_df = pd.DataFrame(high_data)
    low_df = pd.DataFrame(low_data)

    # 前向填充
    close_df = close_df.ffill()
    high_df = high_df.ffill()
    low_df = low_df.ffill()

    return close_df, high_df, low_df


def main():
    parser = argparse.ArgumentParser(description="RSRS+价值因子策略回测")
    parser.add_argument('--top-n', type=int, default=10, help='选股数量')
    parser.add_argument('--rebalance-days', type=int, default=20, help='调仓频率（交易日）')
    parser.add_argument('--buy-threshold', type=float, default=0.7, help='RSRS买入阈值')
    parser.add_argument('--sell-threshold', type=float, default=-0.7, help='RSRS卖出阈值')
    parser.add_argument('--start', type=str, default=None, help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=None, help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--initial-cash', type=float, default=100000, help='初始资金')
    parser.add_argument('--commission', type=float, default=0.0003, help='手续费率')
    parser.add_argument('--data-source', type=str, default='auto', choices=['mysql', 'csv', 'auto'],
                        help='数据源: mysql(数据库), csv(文件), auto(自动)')

    args = parser.parse_args()

    # 加载配置
    config = load_config()

    # 尝试从MySQL加载
    close_df, high_df, low_df = None, None, None

    if args.data_source == 'mysql' or (args.data_source == 'auto' and config is not None):
        try:
            engine = get_db_engine(config)
            print("📥 从MySQL加载数据...")
            close_df, high_df, low_df = load_data_from_mysql(
                engine,
                start_date=args.start,
                end_date=args.end,
                instrument_type='etf',
                min_bars=500
            )
        except Exception as e:
            print(f"⚠️ MySQL加载失败: {e}")

    # 如果MySQL失败，尝试CSV
    if close_df is None and (args.data_source == 'csv' or args.data_source == 'auto'):
        print("📥 尝试从CSV加载数据...")
        close_df, high_df, low_df = load_data_from_csv(
            start_date=args.start,
            end_date=args.end,
            min_bars=500
        )

    if close_df is None:
        print("❌ 数据加载失败")
        return

    # 模拟价值因子
    print("📊 模拟价值因子（PB、ROE）...")
    pb_df, roe_df = simulate_value_factors(close_df, n_symbols=36)

    # 运行回测
    results = run_rsrs_backtest(
        close_df,
        high_df,
        low_df,
        pb_df,
        roe_df,
        top_n=args.top_n,
        rebalance_days=args.rebalance_days,
        buy_threshold=args.buy_threshold,
        sell_threshold=args.sell_threshold,
        initial_cash=args.initial_cash,
        commission=args.commission,
    )

    # 保存结果
    output_dir = PROJECT_ROOT / "out"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"rsrs_backtest_{timestamp}.csv"

    results['weights_df'].to_csv(output_file)
    print(f"\n💾 权重数据已保存: {output_file}")

    # 保存净值曲线
    equity_file = output_dir / f"rsrs_equity_{timestamp}.csv"
    try:
        equity_df = pd.DataFrame({
            'strategy': results['portfolio'].value(),
            'benchmark': results['benchmark_portfolio'].value(),
        })
        equity_df.to_csv(equity_file)
        print(f"💾 净值曲线已保存: {equity_file}")
    except Exception as e:
        print(f"⚠️ 保存净值曲线失败: {e}")

    print("\n✅ 回测完成!")


if __name__ == "__main__":
    main()
