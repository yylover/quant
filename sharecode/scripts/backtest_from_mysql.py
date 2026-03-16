import argparse
from dataclasses import dataclass
from typing import Any
from pathlib import Path
import sys

import pandas as pd
import pymysql
import vectorbt as vbt

# Ensure local package root (../sharecode) is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sharecode.backtest.vectorbt_runner import print_basic_stats, run_signals_backtest
from sharecode.strategies import common as stg


@dataclass
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run backtest using prices loaded from MySQL bar table.")
    p.add_argument("--symbol", required=True, help="Raw symbol, e.g. 512800")
    p.add_argument("--exchange", default="SSE", help="Exchange, e.g. SSE or SZSE")
    p.add_argument("--interval", default="1d", help="Bar interval, e.g. 1d")
    p.add_argument("--start", default="", help="Start date (YYYY-MM-DD), optional")
    p.add_argument("--end", default="", help="End date (YYYY-MM-DD), optional")

    p.add_argument(
        "--strategy",
        required=True,
        choices=["ma_cross", "boll_breakout", "boll_reversion", "rsi_reversion", "timing_ma", "macd"],
    )

    # backtest params
    p.add_argument("--init-cash", type=float, default=100000.0)
    p.add_argument("--fees", type=float, default=0.001)
    p.add_argument("--slippage", type=float, default=0.0005)
    p.add_argument("--sl-pct", type=float, default=0.0)
    p.add_argument("--tp-pct", type=float, default=0.0)

    # MA params
    p.add_argument("--fast", type=int, default=10)
    p.add_argument("--slow", type=int, default=30)
    # Bollinger params
    p.add_argument("--window", type=int, default=20)
    p.add_argument("--n-std", type=float, default=2.0)
    # RSI params
    p.add_argument("--rsi-window", type=int, default=14)
    p.add_argument("--rsi-low", type=float, default=30.0)
    p.add_argument("--rsi-high", type=float, default=70.0)
    # MACD params
    p.add_argument("--macd-fast", type=int, default=12)
    p.add_argument("--macd-slow", type=int, default=26)
    p.add_argument("--macd-signal", type=int, default=9)

    # DB params
    p.add_argument("--db-host", default="127.0.0.1")
    p.add_argument("--db-port", type=int, default=3306)
    p.add_argument("--db-user", default="quant")
    p.add_argument("--db-password", default="")
    p.add_argument("--db-name", default="quant")

    return p.parse_args()


def connect_db(cfg: DbConfig) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        charset="utf8mb4",
        autocommit=False,
    )


def get_instrument_id(conn: pymysql.connections.Connection, symbol: str, exchange: str) -> int:
    symbol_std = f"{symbol}.{ 'SH' if exchange.upper() == 'SSE' else 'SZ' }"
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM instrument WHERE symbol = %s", (symbol_std,))
        row: Any = cur.fetchone()
        if not row:
            raise RuntimeError(f"instrument {symbol_std} not found in database")
        return int(row[0])


def load_close_series(
    conn: pymysql.connections.Connection,
    instrument_id: int,
    interval: str,
    start: str,
    end: str,
) -> pd.Series:
    sql = """
    SELECT ts, close_price
    FROM bar
    WHERE instrument_id = %s AND `interval` = %s
    ORDER BY ts
    """
    params: list[Any] = [instrument_id, interval]
    if start:
        sql = sql.replace("ORDER BY ts", "AND ts >= %s ORDER BY ts")
        params.append(start)
    if end:
        sql = sql.replace("ORDER BY ts", "AND ts <= %s ORDER BY ts")
        params.append(end)

    df = pd.read_sql(sql, conn, params=params)
    if df.empty:
        raise RuntimeError("no bar data loaded from database")
    s = pd.Series(df["close_price"].astype(float).values, index=pd.to_datetime(df["ts"]), name="close")
    return s


def wrap_close_to_df(close: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"日期": close.index, "收盘": close.values})
    return df


def main() -> None:
    args = parse_args()
    db_cfg = DbConfig(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
    )
    conn = connect_db(db_cfg)
    try:
        inst_id = get_instrument_id(conn, args.symbol, args.exchange)
        close = load_close_series(conn, inst_id, args.interval, args.start, args.end)
    finally:
        conn.close()

    df_for_signals = wrap_close_to_df(close)

    # Use close series returned by strategy functions to ensure index aligns with entries/exits
    if args.strategy == "ma_cross":
        close_sig, entries, exits = stg.ma_cross_signals(df_for_signals, fast=args.fast, slow=args.slow)
    elif args.strategy == "boll_breakout":
        close_sig, entries, exits = stg.bollinger_breakout_signals(df_for_signals, window=args.window, n_std=args.n_std)
    elif args.strategy == "boll_reversion":
        close_sig, entries, exits = stg.bollinger_reversion_signals(df_for_signals, window=args.window, n_std=args.n_std)
    elif args.strategy == "rsi_reversion":
        close_sig, entries, exits = stg.rsi_reversion_signals(
            df_for_signals,
            window=args.rsi_window,
            low=args.rsi_low,
            high=args.rsi_high,
        )
    elif args.strategy == "timing_ma":
        close_sig, entries, exits = stg.timing_ma_signals(df_for_signals, fast=args.fast, slow=args.slow)
    elif args.strategy == "macd":
        close_sig, entries, exits = stg.macd_trend_signals(
            df_for_signals,
            fast=args.macd_fast,
            slow=args.macd_slow,
            signal=args.macd_signal,
        )
    else:
        raise ValueError(f"Unknown strategy: {args.strategy}")

    print("strategy", args.strategy)
    print("symbol", args.symbol, "exchange", args.exchange, "interval", args.interval)

    pf, stats = run_signals_backtest(
        close_sig,
        entries,
        exits,
        init_cash=args.init_cash,
        fees=args.fees,
        slippage=args.slippage,
        sl_pct=args.sl_pct if args.sl_pct > 0 else None,
        tp_pct=args.tp_pct if args.tp_pct > 0 else None,
        freq="1D",
    )
    print_basic_stats(pf, stats)


if __name__ == "__main__":
    main()

