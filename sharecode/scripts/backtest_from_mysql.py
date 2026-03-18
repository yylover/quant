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
        choices=[
            "ma_cross",
            "boll_breakout",
            "boll_reversion",
            "rsi_reversion",
            "timing_ma",
            "macd",
            "ema_slope_trend",
            "donchian",
            "momentum",
            "ma_slope",
            "bb_squeeze",
            "supertrend",
        ],
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
    # EMA slope-trend params
    p.add_argument("--buy-ema", type=int, default=2)
    p.add_argument("--slope-n", type=int, default=21)
    p.add_argument("--slope-scale", type=float, default=20.0)
    p.add_argument("--sell-ema", type=int, default=42)
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--no-confirm", action="store_true")
    p.add_argument("--guide-ema2", type=int, default=2)
    p.add_argument("--boundary-ma", type=int, default=27)
    # Donchian params
    p.add_argument("--entry-n", type=int, default=20)
    p.add_argument("--exit-n", type=int, default=10)
    # Momentum params
    p.add_argument("--lookback", type=int, default=60)
    p.add_argument("--enter-th", type=float, default=0.0)
    p.add_argument("--exit-th", type=float, default=0.0)
    # MA slope params
    p.add_argument("--slope-window", type=int, default=5)
    p.add_argument("--enter-slope", type=float, default=0.0)
    p.add_argument("--exit-slope", type=float, default=0.0)
    # BB squeeze params
    p.add_argument("--squeeze-q", type=float, default=0.2)
    # SuperTrend params
    p.add_argument("--atr-window", type=int, default=10)
    p.add_argument("--multiplier", type=float, default=3.0)

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
    """Backward-compatible helper: load close series only.

    Prefer `load_ohlc_df` for strategies that need OHLC (e.g. supertrend, donchian).
    """
    df = load_ohlc_df(conn, instrument_id, interval, start, end)
    s = pd.Series(df["收盘"].astype(float).values, index=pd.to_datetime(df["日期"]), name="close")
    return s


def load_ohlc_df(
    conn: pymysql.connections.Connection,
    instrument_id: int,
    interval: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    sql = """
    SELECT ts, open_price, high_price, low_price, close_price
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
    df["ts"] = pd.to_datetime(df["ts"])
    # Convert to the column convention used by strategies (Chinese AkShare-like)
    out = pd.DataFrame(
        {
            "日期": df["ts"],
            "开盘": df["open_price"].astype(float),
            "最高": df["high_price"].astype(float),
            "最低": df["low_price"].astype(float),
            "收盘": df["close_price"].astype(float),
        }
    )
    return out


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
        ohlc_df = load_ohlc_df(conn, inst_id, args.interval, args.start, args.end)
    finally:
        conn.close()

    df_for_signals = ohlc_df

    close_sig, entries, exits = stg.dispatch_signals(
        df_for_signals,
        args.strategy,
        fast=args.fast,
        slow=args.slow,
        window=args.window,
        n_std=args.n_std,
        rsi_window=args.rsi_window,
        rsi_low=args.rsi_low,
        rsi_high=args.rsi_high,
        macd_fast=args.macd_fast,
        macd_slow=args.macd_slow,
        macd_signal=args.macd_signal,
        buy_ema=args.buy_ema,
        slope_n=args.slope_n,
        slope_scale=args.slope_scale,
        sell_ema=args.sell_ema,
        confirm=not args.no_confirm,
        guide_ema2=args.guide_ema2,
        boundary_ma=args.boundary_ma,
        entry_n=args.entry_n,
        exit_n=args.exit_n,
        lookback=args.lookback,
        enter_th=args.enter_th,
        exit_th=args.exit_th,
        slope_window=args.slope_window,
        enter_slope=args.enter_slope,
        exit_slope=args.exit_slope,
        squeeze_q=args.squeeze_q,
        atr_window=args.atr_window,
        multiplier=args.multiplier,
    )

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

