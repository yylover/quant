import argparse
import time
from pathlib import Path

import akshare as ak
import pandas as pd


def fetch_stock_hist(symbol: str, start: str, end: str, adjust: str, retries: int) -> pd.DataFrame:
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


def infer_etf_market(symbol: str) -> str:
    """Very simple inference of ETF exchange for AkShare."""
    # 常见规则：5/6 开头多为沪市，15/16 多为深市
    if symbol.startswith(("5", "6")):
        return "sh"
    return "sz"


def fetch_etf_hist(symbol: str, start: str, end: str, retries: int, market: str | None = None) -> pd.DataFrame:
    """Fetch ETF daily history via AkShare and normalize to AkShare A股格式列名."""
    last_err: Exception | None = None
    full_symbol = f"{market or infer_etf_market(symbol)}{symbol}"
    for i in range(retries):
        try:
            df = ak.fund_etf_hist_sina(symbol=full_symbol)
            if df.empty:
                return df
            # 标准化列名：date/close -> 日期/收盘，便于后续复用
            if "date" in df.columns:
                df = df.rename(columns={"date": "日期"})
            if "close" in df.columns:
                df = df.rename(columns={"close": "收盘"})
            # 过滤日期区间
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"])
                start_ts = pd.to_datetime(start)
                end_ts = pd.to_datetime(end)
                df = df[(df["日期"] >= start_ts) & (df["日期"] <= end_ts)]
            return df
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
    p.add_argument(
        "--sec-type",
        default="stock",
        choices=["stock", "etf"],
        help="Security type: stock (A股个股) or etf (场内ETF)",
    )
    p.add_argument(
        "--market",
        default="",
        help="ETF 所在市场，sh 或 sz，仅在 --sec-type etf 时使用；留空则根据代码简单推断。",
    )
    p.add_argument("--out", default="")
    p.add_argument("--retries", type=int, default=5)
    args = p.parse_args()

    out = Path(args.out) if args.out else default_out_path(args.symbol, args.adjust or "none")

    if args.sec_type == "stock":
        df = fetch_stock_hist(args.symbol, args.start, args.end, args.adjust, args.retries)
    else:
        df = fetch_etf_hist(args.symbol, args.start, args.end, args.retries, market=args.market or None)

    df.to_csv(out, index=False, encoding="utf-8-sig")

    print("akshare_fetch_ok")
    print("saved_to", str(out))
    print("rows", len(df))
    print(df.head(3))


if __name__ == "__main__":
    main()

