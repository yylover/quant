import argparse
import time
from pathlib import Path

import akshare as ak
import pandas as pd


def fetch_hist(symbol: str, start: str, end: str, adjust: str, retries: int) -> pd.DataFrame:
    last_err: Exception | None = None
    for i in range(retries):
        try:
            return ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust=adjust,
            )
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise last_err  # type: ignore[misc]


def default_out_path(symbol: str, adjust: str) -> Path:
    base = Path(__file__).resolve().parents[1] / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{symbol}_daily_{adjust}.csv"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="000001")
    p.add_argument("--start", default="20240101")
    p.add_argument("--end", default="20241231")
    p.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"])
    p.add_argument("--out", default="")
    p.add_argument("--retries", type=int, default=5)
    args = p.parse_args()

    out = Path(args.out) if args.out else default_out_path(args.symbol, args.adjust or "none")
    df = fetch_hist(args.symbol, args.start, args.end, args.adjust, args.retries)
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print("akshare_fetch_ok")
    print("saved_to", str(out))
    print("rows", len(df))
    print(df.head(3))


if __name__ == "__main__":
    main()

