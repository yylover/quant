import argparse
from pathlib import Path
import sys

import pandas as pd
import pymysql
import vectorbt as vbt
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "sharecode" / "config.yaml"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Multi-ETF momentum portfolio backtest loaded from MySQL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--config", default=str(CONFIG_PATH), help="Path to config.yaml")
    p.add_argument("--lookback",      type=int,   default=60,     help="Momentum lookback window in trading days.")
    p.add_argument("--top-n",         type=int,   default=5,      help="Number of ETFs to hold each rebalance.")
    p.add_argument("--rebalance-days",type=int,   default=20,     help="Rebalance frequency in trading days.")
    p.add_argument("--weight-scheme", choices=["equal", "inv_vol"], default="equal",
                   help="Weighting scheme: equal or inverse volatility.")
    p.add_argument("--max-weight",    type=float, default=1.0,
                   help="Cap on single-name weight (e.g. 0.25 for 25%%).")
    p.add_argument("--init-cash",     type=float, default=100_000.0)
    p.add_argument("--fees",          type=float, default=0.001)
    p.add_argument("--slippage",      type=float, default=0.0005)
    p.add_argument("--start", default="", help="Filter start date YYYY-MM-DD (optional)")
    p.add_argument("--end",   default="", help="Filter end date YYYY-MM-DD (optional)")
    # DB overrides (fallback to config.yaml values)
    p.add_argument("--db-host",     default="")
    p.add_argument("--db-port",     type=int, default=0)
    p.add_argument("--db-user",     default="")
    p.add_argument("--db-password", default="")
    p.add_argument("--db-name",     default="")
    return p.parse_args()


def connect_db(cfg: dict) -> pymysql.connections.Connection:
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
    etfs: list[dict],
    interval: str = "1d",
    start: str = "",
    end: str = "",
) -> pd.DataFrame:
    """Load close prices for all ETFs from MySQL into a wide DataFrame (date × symbol)."""
    close_map: dict[str, pd.Series] = {}

    conditions = ["b.instrument_id = %s", "b.`interval` = %s"]
    base_params: list = []

    for etf in etfs:
        symbol   = etf["symbol"]
        exchange = etf["exchange"]
        symbol_std = f"{symbol}.{'SH' if exchange.upper() == 'SSE' else 'SZ'}"

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM instrument WHERE symbol = %s", (symbol_std,))
            row = cur.fetchone()
            if not row:
                print(f"  [warn] {symbol_std} not found in instrument table, skipping")
                continue
            inst_id = int(row[0])

        conds = ["b.instrument_id = %s", "b.`interval` = %s"]
        params: list = [inst_id, interval]
        if start:
            conds.append("b.ts >= %s")
            params.append(start)
        if end:
            conds.append("b.ts <= %s")
            params.append(end)
        sql = f"SELECT b.ts, b.close_price FROM bar b WHERE {' AND '.join(conds)} ORDER BY b.ts"

        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        if not rows:
            print(f"  [warn] no bar data for {symbol_std}, skipping")
            continue

        df = pd.DataFrame(rows, columns=["ts", "close_price"])

        s = pd.Series(
            df["close_price"].astype(float).values,
            index=pd.to_datetime(df["ts"]),
            name=symbol,
        )
        close_map[symbol] = s

    if not close_map:
        raise RuntimeError("No close data loaded from database.")

    close_df = pd.DataFrame(close_map).dropna(how="all").sort_index()
    return close_df


def build_momentum_weights(
    close_df: pd.DataFrame,
    lookback: int,
    top_n: int,
    rebalance_days: int,
) -> pd.DataFrame:
    """Generate equal-weight target weights based on cross-sectional momentum."""
    mom = close_df.pct_change(lookback, fill_method=None)
    dates = close_df.index
    weights = pd.DataFrame(0.0, index=dates, columns=close_df.columns)

    for i in range(lookback, len(dates), rebalance_days):
        scores = mom.iloc[i].dropna()
        if scores.empty:
            continue
        top = scores.sort_values(ascending=False).head(top_n).index
        if len(top) == 0:
            continue
        w = 1.0 / float(len(top))
        j = min(i + rebalance_days, len(dates))
        weights.iloc[i:j] = 0.0
        top_idx = [weights.columns.get_loc(c) for c in top]
        weights.iloc[i:j, top_idx] = w

    return weights


def main() -> None:
    args = parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db_cfg = {
        "host":     args.db_host     or cfg["db"]["host"],
        "port":     args.db_port     or cfg["db"]["port"],
        "user":     args.db_user     or cfg["db"]["user"],
        "password": args.db_password or cfg["db"]["password"],
        "name":     args.db_name     or cfg["db"]["name"],
    }
    etfs = cfg["data"]["etfs"]

    conn = connect_db(db_cfg)
    try:
        close_df = load_close_matrix(conn, etfs, start=args.start, end=args.end)
    finally:
        conn.close()

    print("loaded_symbols", list(close_df.columns))
    print("dates", close_df.index.min().date(), "→", close_df.index.max().date(),
          "rows", close_df.shape[0], "symbols", close_df.shape[1])

    weights = build_momentum_weights(
        close_df,
        lookback=args.lookback,
        top_n=args.top_n,
        rebalance_days=args.rebalance_days,
    )

    if args.weight_scheme == "inv_vol":
        vols = close_df.pct_change(fill_method=None).rolling(args.lookback).std()
        dates = close_df.index
        for i in range(args.lookback, len(dates), args.rebalance_days):
            w_row = weights.iloc[i]
            active = w_row[w_row > 0].index
            if len(active) == 0:
                continue
            vol_row = vols.iloc[i][active].replace(0.0, pd.NA).dropna()
            if vol_row.empty:
                continue
            inv_vol_norm = (1.0 / vol_row)
            inv_vol_norm = inv_vol_norm / inv_vol_norm.sum()
            j = min(i + args.rebalance_days, len(dates))
            weights.iloc[i:j] = 0.0
            for sym, w in inv_vol_norm.items():
                weights.iloc[i:j, weights.columns.get_loc(sym)] = w

    if args.max_weight < 1.0:
        dates = weights.index
        for i in range(args.lookback, len(dates), args.rebalance_days):
            w_row = weights.iloc[i].clip(upper=args.max_weight)
            s = w_row.sum()
            if s > 0:
                w_row = w_row / s
            j = min(i + args.rebalance_days, len(dates))
            weights.iloc[i:j] = w_row.values

    pf = vbt.Portfolio.from_orders(
        close_df,
        size=weights,
        size_type="targetpercent",
        fees=args.fees,
        slippage=args.slippage,
        init_cash=args.init_cash,
        freq="1D",
        group_by=True,
        cash_sharing=True,
    )

    keys = [
        "Start Value",
        "End Value",
        "Total Return [%]",
        "Max Drawdown [%]",
        "Ann. Return [%]",
        "Ann. Volatility [%]",
        "Sharpe Ratio",
    ]
    stats = pf.stats()
    print("\nmulti_momentum_portfolio_ok")
    print(stats.loc[[k for k in keys if k in stats.index]])


if __name__ == "__main__":
    main()
