#!/usr/bin/env python
"""
多因子选股策略回测脚本

基于 vectorbt 进行多因子选股的回测分析
支持：
- 从 MySQL 加载多标的收盘价数据
- 计算多个技术因子
- 因子合成和选股
- 回测组合收益
- 输出性能统计

用法:
    python scripts/vectorbt_multi_factor_from_mysql.py \
        --config sharecode/config.yaml \
        --factors momentum_60d,momentum_20d,volatility_20d \
        --top-n 5 \
        --rebalance-days 20
"""

from pathlib import Path
import sys

import argparse
import pandas as pd
import pymysql
import vectorbt as vbt
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sharecode.strategies.multi_factor import (
    MultiFactorSelector,
    SelectionConfig,
    create_momentum_reversion_selector,
    create_quality_value_selector,
    create_trend_strength_selector,
    BUILTIN_FACTORS,
)

CONFIG_PATH = ROOT / "sharecode" / "config.yaml"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="多因子选股策略回测",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--config", default=str(CONFIG_PATH), help="配置文件路径")
    
    # 因子选择
    p.add_argument(
        "--preset",
        choices=["momentum_reversion", "quality_value", "trend_strength"],
        default="trend_strength",
        help="预设选股策略",
    )
    p.add_argument(
        "--factors",
        default="",
        help="自定义因子列表，逗号分隔（不使用预设时生效），可选: " + ",".join(BUILTIN_FACTORS.keys()),
    )
    
    # 选股参数
    p.add_argument("--top-n", type=int, default=5, help="选择前N只标的")
    p.add_argument("--rebalance-days", type=int, default=20, help="调仓频率（交易日）")
    
    # 权重方案
    p.add_argument(
        "--weight-scheme",
        choices=["equal", "inv_vol", "score"],
        default="equal",
        help="权重分配方案",
    )
    p.add_argument("--max-weight", type=float, default=1.0, help="单一标的最大权重")
    
    # 因子处理
    p.add_argument("--no-winsorize", action="store_true", help="不去极值")
    p.add_argument("--no-standardize", action="store_true", help="不标准化")
    p.add_argument(
        "--winsorize-method",
        choices=["mad", "std"],
        default="mad",
        help="去极值方法",
    )
    
    # 回测参数
    p.add_argument("--init-cash", type=float, default=100_000.0)
    p.add_argument("--fees", type=float, default=0.001)
    p.add_argument("--slippage", type=float, default=0.0005)
    p.add_argument("--start", default="", help="起始日期 YYYY-MM-DD")
    p.add_argument("--end", default="", help="结束日期 YYYY-MM-DD")
    
    # 数据库覆盖
    p.add_argument("--db-host", default="")
    p.add_argument("--db-port", type=int, default=0)
    p.add_argument("--db-user", default="")
    p.add_argument("--db-password", default="")
    p.add_argument("--db-name", default="")
    
    # 调试
    p.add_argument("--verbose", action="store_true", help="详细输出")
    
    return p.parse_args()


def connect_db(cfg: dict) -> pymysql.connections.Connection:
    """连接数据库"""
    return pymysql.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["name"],
        charset="utf8mb4",
        autocommit=False,
    )


def load_close_matrix(
    conn: pymysql.connections.Connection,
    symbols: list[dict],
    interval: str = "1d",
    start: str = "",
    end: str = "",
) -> pd.DataFrame:
    """
    从 MySQL 加载多标的收盘价数据
    
    返回:
        DataFrame (日期 × 标的)，列名为 symbol
    """
    close_map: dict[str, pd.Series] = {}
    
    for item in symbols:
        symbol = item["symbol"]
        exchange = item["exchange"]
        
        # 标准化代码
        symbol_std = f"{symbol}.{'SH' if exchange.upper() == 'SSE' else 'SZ'}"
        
        # 查询 instrument_id
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM instrument WHERE symbol = %s", (symbol_std,))
            row = cur.fetchone()
            if not row:
                print(f"  [warn] {symbol_std} 未找到，跳过")
                continue
            inst_id = int(row[0])
        
        # 构建查询条件
        conds = ["b.instrument_id = %s", "b.`interval` = %s"]
        params: list = [inst_id, interval]
        
        if start:
            conds.append("b.ts >= %s")
            params.append(start)
        if end:
            conds.append("b.ts <= %s")
            params.append(end)
        
        sql = f"SELECT b.ts, b.close_price FROM bar b WHERE {' AND '.join(conds)} ORDER BY b.ts"
        
        # 加载数据
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        
        if not rows:
            print(f"  [warn] {symbol_std} 无数据，跳过")
            continue
        
        # 转换为 Series
        df = pd.DataFrame(rows, columns=["ts", "close_price"])
        s = pd.Series(
            df["close_price"].astype(float).values,
            index=pd.to_datetime(df["ts"]),
            name=symbol,
        )
        close_map[symbol] = s
    
    if not close_map:
        raise RuntimeError("未能加载任何数据")
    
    # 合并为宽表
    close_df = pd.DataFrame(close_map).dropna(how="all").sort_index()
    return close_df


def create_selector(args: argparse.Namespace) -> MultiFactorSelector:
    """根据参数创建选股器"""
    
    # 使用预设策略
    if args.preset == "momentum_reversion":
        selector = create_momentum_reversion_selector(
            top_n=args.top_n,
            rebalance_days=args.rebalance_days,
        )
    elif args.preset == "quality_value":
        selector = create_quality_value_selector(
            top_n=args.top_n,
            rebalance_days=args.rebalance_days,
        )
    elif args.preset == "trend_strength":
        selector = create_trend_strength_selector(
            top_n=args.top_n,
            rebalance_days=args.rebalance_days,
        )
    else:
        # 自定义因子
        if not args.factors:
            raise ValueError("自定义模式下需要指定 --factors 参数")
        
        factor_names = [f.strip() for f in args.factors.split(",")]
        selector = MultiFactorSelector()
        selector.add_builtin_factors(factor_names)
        selector.config = SelectionConfig(
            top_n=args.top_n,
            rebalance_days=args.rebalance_days,
            weight_scheme=args.weight_scheme,
            winsorize=not args.no_winsorize,
            winsorize_method=args.winsorize_method,
            standardize=not args.no_standardize,
        )
    
    # 更新配置
    selector.config.weight_scheme = args.weight_scheme
    selector.config.max_weight = args.max_weight
    selector.config.winsorize = not args.no_winsorize
    selector.config.standardize = not args.no_standardize
    
    return selector


def compute_inv_vol_weights(
    close_df: pd.DataFrame,
    weights_df: pd.DataFrame,
    selector: MultiFactorSelector,
) -> pd.DataFrame:
    """
    根据反波动率调整权重
    
    参数:
        close_df: 收盘价数据
        weights_df: 当前权重矩阵
        selector: 选股器（包含调仓日期）
    
    返回:
        调整后的权重矩阵
    """
    result = weights_df.copy()
    
    # 计算波动率
    returns = close_df.pct_change(fill_method=None)
    vols = returns.rolling(selector.config.rebalance_days, min_periods=1).std()
    
    # 在每个调仓日调整权重
    rebalance_dates = []
    for i in range(selector.config.top_n, len(result.index), selector.config.rebalance_days):
        rebalance_dates.append(result.index[i])
    
    for rebalance_date in rebalance_dates:
        if rebalance_date not in result.index:
            continue
        
        # 获取当前持仓
        w_row = result.loc[rebalance_date]
        active = w_row[w_row > 0].index
        
        if len(active) == 0:
            continue
        
        # 获取波动率
        vol_row = vols.loc[rebalance_date, active].replace(0.0, pd.NA).dropna()
        
        if vol_row.empty:
            continue
        
        # 反波动率加权
        inv_vol = 1.0 / vol_row
        inv_vol_norm = inv_vol / inv_vol.sum()
        
        # 应用权重
        j = min(result.index.get_loc(rebalance_date) + selector.config.rebalance_days, len(result.index))
        result.iloc[result.index.get_loc(rebalance_date):j] = 0.0
        
        for sym, w in inv_vol_norm.items():
            result.iloc[result.index.get_loc(rebalance_date):j, result.columns.get_loc(sym)] = w
    
    return result


def main() -> None:
    args = parse_args()
    
    # 加载配置
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    # 数据库配置
    db_cfg = {
        "host": args.db_host or cfg["db"]["host"],
        "port": args.db_port or cfg["db"]["port"],
        "user": args.db_user or cfg["db"]["user"],
        "password": args.db_password or cfg["db"]["password"],
        "name": args.db_name or cfg["db"]["name"],
    }
    
    # 获取标的列表
    symbols = cfg["data"]["etfs"]
    
    # 连接数据库并加载数据
    print("加载数据...")
    conn = connect_db(db_cfg)
    try:
        close_df = load_close_matrix(conn, symbols, start=args.start, end=args.end)
    finally:
        conn.close()
    
    print(f"  标的数量: {len(close_df.columns)}")
    print(f"  {list(close_df.columns)}")
    print(f"  日期范围: {close_df.index.min().date()} → {close_df.index.max().date()}")
    print(f"  数据行数: {len(close_df)}")
    
    # 创建选股器
    print(f"\n使用预设策略: {args.preset}")
    selector = create_selector(args)
    
    if args.verbose:
        print(f"\n因子列表:")
        for fc in selector.factor_configs:
            print(f"  - {fc.name}: {fc.desc}")
    
    # 计算因子并选股
    print("\n计算因子...")
    weights_df, selections_df, factor_dfs = selector.run(close_df)
    
    if args.verbose:
        print(f"\n综合得分统计:")
        print(f"  均值: {selector.score_df.mean().mean():.4f}")
        print(f"  标准差: {selector.score_df.std().mean():.4f}")
        print(f"  最大值: {selector.score_df.max().max():.4f}")
        print(f"  最小值: {selector.score_df.min().min():.4f}")
    
    # 反波动率加权
    if args.weight_scheme == "inv_vol":
        print("\n应用反波动率加权...")
        weights_df = compute_inv_vol_weights(close_df, weights_df, selector)
    
    # 限制最大权重
    if args.max_weight < 1.0:
        print(f"\n限制单一标的最大权重为 {args.max_weight * 100:.0f}%")
    
    # 回测
    print("\n开始回测...")
    pf = vbt.Portfolio.from_orders(
        close_df,
        size=weights_df,
        size_type="targetpercent",
        fees=args.fees,
        slippage=args.slippage,
        init_cash=args.init_cash,
        freq="1D",
        group_by=True,
        cash_sharing=True,
    )
    
    # 输出统计结果
    stats = pf.stats()
    keys = [
        "Start Value",
        "End Value",
        "Total Return [%]",
        "Max Drawdown [%]",
        "Ann. Return [%]",
        "Ann. Volatility [%]",
        "Sharpe Ratio",
        "Best Trade [%]",
        "Worst Trade [%]",
    ]
    
    print("\n" + "=" * 60)
    print("多因子选股策略回测结果")
    print("=" * 60)
    for k in keys:
        if k in stats.index:
            print(f"{k:25s} {stats[k]:>20}")
    print("=" * 60)
    
    # 输出调仓统计
    if args.verbose:
        print("\n调仓统计:")
        rebalance_count = (selections_df.sum(axis=1) > 0).sum()
        print(f"  调仓次数: {rebalance_count}")
        print(f"  调仓频率: 每 {args.rebalance_days} 个交易日")
        
        # 持仓分布
        print("\n持仓分布:")
        holdings = selections_df.sum()
        print(f"  持仓标的数量: {(holdings > 0).sum()}")
        print(f"  平均持仓天数: {holdings.mean():.1f}")
        print(f"  最长持仓天数: {holdings.max()}")
        print(f"  最短持仓天数: {holdings.min()}")
    
    print("\nmulti_factor_selection_ok")


if __name__ == "__main__":
    main()
