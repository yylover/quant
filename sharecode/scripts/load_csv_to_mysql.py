import argparse
import os
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pymysql


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Load AkShare CSV into MySQL instrument/bar tables.")
    p.add_argument("--csv", required=True, help="Path to AkShare-style daily CSV file.")
    p.add_argument("--symbol", required=True, help="Raw symbol, e.g. 512800")
    p.add_argument("--exchange", required=True, help="Exchange, e.g. SSE or SZSE")
    p.add_argument("--name", default="", help="Instrument name (optional).")
    p.add_argument("--type", default="etf", help="Instrument type, e.g. stock/etf/index.")
    p.add_argument("--interval", default="1d", help="Bar interval, default 1d.")

    p.add_argument("--db-host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    p.add_argument("--db-port", type=int, default=int(os.environ.get("MYSQL_PORT", "3306")))
    p.add_argument("--db-user", default=os.environ.get("MYSQL_USER", "root"))
    p.add_argument("--db-password", default=os.environ.get("MYSQL_PASSWORD", ""))
    p.add_argument("--db-name", default=os.environ.get("MYSQL_DB", "quant"))
    return p.parse_args()


def connect_db(args: argparse.Namespace) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        charset="utf8mb4",
        autocommit=False,
    )


def upsert_instrument(conn: pymysql.connections.Connection, args: argparse.Namespace) -> int:
    symbol_std = f"{args.symbol}.{ 'SH' if args.exchange.upper() == 'SSE' else 'SZ' }"
    with conn.cursor() as cur:
        sql = """
        INSERT INTO instrument (symbol, raw_symbol, exchange, name, type)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          exchange = VALUES(exchange),
          name = IF(VALUES(name) <> '', VALUES(name), name),
          type = VALUES(type)
        """
        cur.execute(sql, (symbol_std, args.symbol, args.exchange, args.name, args.type))
        # get id
        cur.execute("SELECT id FROM instrument WHERE symbol = %s", (symbol_std,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Failed to fetch instrument id after upsert")
        return int(row[0])


def map_row_to_bar(row: pd.Series) -> Dict[str, Any]:
    # Support AkShare standard columns for A股/ETF日线
    date_col = "日期" if "日期" in row.index else "date"
    open_col = "开盘" if "开盘" in row.index else "open"
    high_col = "最高" if "最高" in row.index else "high"
    low_col = "最低" if "最低" in row.index else "low"
    close_col = "收盘" if "收盘" in row.index else "close"
    vol_col = "成交量" if "成交量" in row.index else "volume"
    amt_col = "成交额" if "成交额" in row.index else "amount"

    ts = pd.to_datetime(row[date_col])
    return {
        "ts": ts.to_pydatetime(),
        "open_price": float(row[open_col]),
        "high_price": float(row[high_col]),
        "low_price": float(row[low_col]),
        "close_price": float(row[close_col]),
        "volume": int(row[vol_col]) if vol_col in row.index and pd.notna(row[vol_col]) else None,
        "amount": float(row[amt_col]) if amt_col in row.index and pd.notna(row[amt_col]) else None,
    }


def insert_bars(
    conn: pymysql.connections.Connection,
    instrument_id: int,
    interval: str,
    df: pd.DataFrame,
) -> None:
    if df.empty:
        return
    df = df.copy()
    if "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期")
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

    rows = []
    for _, row in df.iterrows():
        mapped = map_row_to_bar(row)
        rows.append(
            (
                instrument_id,
                interval,
                mapped["ts"],
                mapped["open_price"],
                mapped["high_price"],
                mapped["low_price"],
                mapped["close_price"],
                mapped["volume"],
                mapped["amount"],
            )
        )

    sql = """
    INSERT IGNORE INTO bar (
      instrument_id, `interval`, ts,
      open_price, high_price, low_price, close_price,
      volume, amount
    ) VALUES (
      %s, %s, %s,
      %s, %s, %s, %s,
      %s, %s
    )
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    df = pd.read_csv(csv_path)

    conn = connect_db(args)
    try:
        inst_id = upsert_instrument(conn, args)
        insert_bars(conn, inst_id, args.interval, df)
        conn.commit()
        print("load_csv_to_mysql_ok")
        print("instrument_id", inst_id, "rows_inserted", len(df))
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    main()

