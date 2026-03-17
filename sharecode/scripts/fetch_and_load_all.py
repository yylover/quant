"""Batch-fetch ETF daily bars from AkShare (东方财富 fund_etf_hist_em) and
insert into MySQL via INSERT IGNORE.

Features
--------
- Rate-limited with configurable --delay between requests (default 5 s)
- Random jitter added to each inter-request sleep to avoid detection
- Long --cooldown sleep after a symbol fails all retries (default 60 s)
- Exponential back-off retry on AkShare errors
- --skip-existing: skip symbols already having bar data in DB
- --save-csv: also write fetched data to data/<symbol>_daily_qfq.csv
- --dry-run: fetch only, do not touch the database
- --symbols: process only the given comma-separated subset
- Full summary of ok / skipped / failed at the end

Usage
-----
    conda activate aquant
    cd sharecode
    python scripts/fetch_and_load_all.py --save-csv
    python scripts/fetch_and_load_all.py --delay 5 --cooldown 60 --skip-existing --save-csv
    python scripts/fetch_and_load_all.py --symbols 510300,512800 --dry-run
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd
import pymysql
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "sharecode" / "config.yaml"
DATA_DIR = ROOT / "data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AkShare fetch
# ---------------------------------------------------------------------------

def fetch_etf(
    symbol: str,
    market: str,
    start: str,
    end: str,
    retries: int,
    delay: float,
) -> pd.DataFrame:
    """Fetch ETF daily history via fund_etf_hist_sina (新浪财经).

    market: 'sh' or 'sz', combined with symbol to form e.g. 'sh510300'.
    start/end: YYYYMMDD strings used to filter the full returned history.
    Returns DataFrame with Chinese column names (日期/开盘/收盘/最高/最低/成交量/成交额).
    """
    full_symbol = f"{market}{symbol}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            df = ak.fund_etf_hist_sina(symbol=full_symbol)
            if df.empty:
                return df
            rename_map = {
                "date": "日期", "open": "开盘", "high": "最高",
                "low": "最低", "close": "收盘", "volume": "成交量", "amount": "成交额",
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            df["日期"] = pd.to_datetime(df["日期"])
            start_ts = pd.to_datetime(start)
            end_ts   = pd.to_datetime(end)
            df = df[(df["日期"] >= start_ts) & (df["日期"] <= end_ts)].reset_index(drop=True)
            return df
        except Exception as exc:
            last_err = exc
            wait = 10.0 * (attempt + 1)
            log.warning(
                "    attempt %d/%d failed: %s — retry in %.0fs",
                attempt + 1, retries, exc, wait,
            )
            if attempt < retries - 1:
                time.sleep(wait)
    raise RuntimeError(f"all {retries} fetch attempts failed") from last_err


# ---------------------------------------------------------------------------
# MySQL helpers
# ---------------------------------------------------------------------------

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


def upsert_instrument(
    conn: pymysql.connections.Connection,
    symbol: str,
    exchange: str,
    name: str,
    etf_type: str,
) -> int:
    symbol_std = f"{symbol}.{'SH' if exchange.upper() == 'SSE' else 'SZ'}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO instrument (symbol, raw_symbol, exchange, name, type)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              exchange = VALUES(exchange),
              name     = IF(VALUES(name) <> '', VALUES(name), name),
              type     = VALUES(type)
            """,
            (symbol_std, symbol, exchange, name, etf_type),
        )
        cur.execute("SELECT id FROM instrument WHERE symbol = %s", (symbol_std,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"instrument id not found after upsert: {symbol_std}")
        return int(row[0])


def count_existing_bars(
    conn: pymysql.connections.Connection,
    instrument_id: int,
    interval: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM bar WHERE instrument_id = %s AND `interval` = %s",
            (instrument_id, interval),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def insert_bars(
    conn: pymysql.connections.Connection,
    instrument_id: int,
    interval: str,
    df: pd.DataFrame,
) -> int:
    """Bulk-insert bars using executemany + INSERT IGNORE.

    Builds the rows list via vectorized pandas operations instead of iterrows
    for better performance on large DataFrames.
    """
    if df.empty:
        return 0

    df = df.copy()
    date_col  = "日期"  if "日期"  in df.columns else "date"
    open_col  = "开盘"  if "开盘"  in df.columns else "open"
    high_col  = "最高"  if "最高"  in df.columns else "high"
    low_col   = "最低"  if "最低"  in df.columns else "low"
    close_col = "收盘"  if "收盘"  in df.columns else "close"
    vol_col   = "成交量" if "成交量" in df.columns else ("volume"  if "volume"  in df.columns else None)
    amt_col   = "成交额" if "成交额" in df.columns else ("amount"  if "amount"  in df.columns else None)

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    n = len(df)

    timestamps = [ts.to_pydatetime() for ts in df[date_col]]
    opens  = df[open_col].astype(float).tolist()
    highs  = df[high_col].astype(float).tolist()
    lows   = df[low_col].astype(float).tolist()
    closes = df[close_col].astype(float).tolist()
    vols   = (
        [None if pd.isna(v) else int(v) for v in df[vol_col]]
        if vol_col else [None] * n
    )
    amts   = (
        [None if pd.isna(v) else float(v) for v in df[amt_col]]
        if amt_col else [None] * n
    )

    rows: list[tuple[Any, ...]] = [
        (instrument_id, interval, ts, o, h, l, c, v, a)
        for ts, o, h, l, c, v, a in zip(timestamps, opens, highs, lows, closes, vols, amts)
    ]

    sql = """
    INSERT IGNORE INTO bar (
      instrument_id, `interval`, ts,
      open_price, high_price, low_price, close_price,
      volume, amount
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    return n


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Batch-fetch all ETFs from AkShare and load into MySQL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--config", default=str(CONFIG_PATH), help="Path to config.yaml")
    p.add_argument("--start", default="", help="Override start date (YYYYMMDD)")
    p.add_argument("--end",   default="", help="Override end date (YYYYMMDD); default: today")
    p.add_argument("--delay",   type=float, default=5.0,
                   help="Seconds to sleep between AkShare requests")
    p.add_argument("--jitter",  type=float, default=3.0,
                   help="Max random extra seconds added to each inter-request sleep")
    p.add_argument("--cooldown", type=float, default=60.0,
                   help="Seconds to sleep after a symbol fails all retries")
    p.add_argument("--retries", type=int,   default=3,
                   help="Retry attempts per symbol")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip symbols that already have bar rows in the DB")
    p.add_argument("--save-csv", action="store_true",
                   help="Save fetched data as data/<symbol>_daily_qfq.csv")
    p.add_argument("--dry-run", action="store_true",
                   help="Fetch only; do not write to DB")
    p.add_argument("--symbols", default="",
                   help="Comma-separated subset of symbols to process, e.g. 510300,512800")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db_cfg   = cfg["db"]
    data_cfg = cfg["data"]
    adjust   = data_cfg.get("adjust", "qfq")
    start    = args.start or data_cfg["start"]
    end      = args.end   or date.today().strftime("%Y%m%d")
    interval = "1d"

    etfs: list[dict] = data_cfg["etfs"]
    if args.symbols:
        wanted = set(args.symbols.split(","))
        etfs = [e for e in etfs if e["symbol"] in wanted]
        if not etfs:
            log.error("None of the requested symbols found in config.")
            sys.exit(1)

    log.info(
        "=== fetch_and_load_all  symbols=%d  %s→%s  delay=%.0fs  jitter=%.0fs  cooldown=%.0fs ===",
        len(etfs), start, end, args.delay, args.jitter, args.cooldown,
    )

    conn: pymysql.connections.Connection | None = None
    if not args.dry_run:
        conn = connect_db(db_cfg)

    ok_list:      list[str]         = []
    skip_list:    list[str]         = []
    fail_list:    list[tuple[str, str]] = []

    try:
        for idx, etf in enumerate(etfs, 1):
            symbol   = etf["symbol"]
            exchange = etf["exchange"]
            name     = etf["name"]
            etf_type = etf.get("type", "etf")

            log.info("[%d/%d] %s  %s", idx, len(etfs), symbol, name)

            # --- fetch from AkShare (新浪财经) ---
            try:
                df = fetch_etf(symbol, etf["market"], start, end, args.retries, args.delay)
            except Exception as exc:
                log.error("  FAIL fetch: %s", exc)
                fail_list.append((symbol, f"fetch: {exc}"))
                # Long cooldown so the remote rate-limit window resets.
                if idx < len(etfs):
                    log.info("  cooling down for %.0fs before next symbol …", args.cooldown)
                    time.sleep(args.cooldown)
                continue

            if df.empty:
                log.warning("  SKIP: empty DataFrame returned by AkShare")
                skip_list.append(symbol)
                if idx < len(etfs):
                    time.sleep(args.delay + random.uniform(0, args.jitter))
                continue

            date_col = "日期" if "日期" in df.columns else "date"
            log.info(
                "  fetched %d rows  %s → %s",
                len(df),
                str(df[date_col].iloc[0])[:10],
                str(df[date_col].iloc[-1])[:10],
            )

            # --- save CSV (optional) ---
            if args.save_csv:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                csv_path = DATA_DIR / f"{symbol}_daily_{adjust}.csv"
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                log.info("  CSV → %s", csv_path)

            # --- write to DB ---
            if args.dry_run or conn is None:
                ok_list.append(symbol)
            else:
                try:
                    inst_id = upsert_instrument(conn, symbol, exchange, name, etf_type)

                    if args.skip_existing:
                        existing = count_existing_bars(conn, inst_id, interval)
                        if existing > 0:
                            conn.commit()
                            log.info("  SKIP DB: already has %d bars", existing)
                            skip_list.append(symbol)
                            if idx < len(etfs):
                                time.sleep(args.delay + random.uniform(0, args.jitter))
                            continue

                    inserted = insert_bars(conn, inst_id, interval, df)
                    conn.commit()
                    log.info("  DB ok  instrument_id=%d  rows=%d", inst_id, inserted)
                    ok_list.append(symbol)

                except Exception as exc:
                    conn.rollback()
                    log.error("  FAIL DB: %s", exc)
                    fail_list.append((symbol, f"db: {exc}"))

            # rate-limit: sleep between requests (skip after the last one)
            if idx < len(etfs):
                sleep_time = args.delay + random.uniform(0, args.jitter)
                log.info("  sleeping %.1fs before next request …", sleep_time)
                time.sleep(sleep_time)

    finally:
        if conn is not None:
            conn.close()

    # --- summary ---
    total = len(etfs)
    log.info("")
    log.info("=" * 60)
    log.info(
        "Done  total=%d  ok=%d  skipped=%d  failed=%d",
        total, len(ok_list), len(skip_list), len(fail_list),
    )
    if skip_list:
        log.info("Skipped: %s", ", ".join(skip_list))
    if fail_list:
        log.warning("Failed:")
        for sym, reason in fail_list:
            log.warning("  %-10s  %s", sym, reason)

    sys.exit(1 if fail_list else 0)


if __name__ == "__main__":
    main()
