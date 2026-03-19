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
    """Fetch ETF daily history via fund_etf_hist_em (东方财富).

    Supports full date range and qfq adjust natively. Returns DataFrame with
    AkShare standard Chinese column names (日期/开盘/收盘/最高/最低/成交量/成交额).
    Falls back to fund_etf_hist_sina on repeated failure.
    """
    last_err: Exception | None = None
    for i in range(retries):
        try:
            df = ak.fund_etf_hist_em(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="qfq",
            )
            return df
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))

    # fallback: fund_etf_hist_sina (older API, no date range params)
    full_symbol = f"{market or infer_etf_market(symbol)}{symbol}"
    for i in range(retries):
        try:
            df = ak.fund_etf_hist_sina(symbol=full_symbol)
            if df.empty:
                return df
            rename_map = {
                "date": "日期",
                "open": "开盘",
                "high": "最高",
                "low": "最低",
                "close": "收盘",
                "volume": "成交量",
                "amount": "成交额",
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"])
                df = df[(df["日期"] >= pd.to_datetime(start)) & (df["日期"] <= pd.to_datetime(end))]
            return df
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise last_err  # type: ignore[misc]


def fetch_index_hist(symbol: str, start: str, end: str, retries: int) -> pd.DataFrame:
    """Fetch A-share index history via AkShare.

    Example index: 000300 (沪深300).
    """
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        rename_map: dict[str, str] = {}
        if "date" in df.columns:
            rename_map["date"] = "日期"
        if "open" in df.columns:
            rename_map["open"] = "开盘"
        if "high" in df.columns:
            rename_map["high"] = "最高"
        if "low" in df.columns:
            rename_map["low"] = "最低"
        if "close" in df.columns:
            rename_map["close"] = "收盘"
        if "volume" in df.columns:
            rename_map["volume"] = "成交量"
        if "amount" in df.columns:
            rename_map["amount"] = "成交额"
        df = df.rename(columns=rename_map)
        if "日期" in df.columns:
            df["日期"] = pd.to_datetime(df["日期"])
            start_ts = pd.to_datetime(start)
            end_ts = pd.to_datetime(end)
            df = df[(df["日期"] >= start_ts) & (df["日期"] <= end_ts)]
        return df

    last_err: Exception | None = None
    for i in range(retries):
        # Try each data source independently. Failures in one should not prevent fallbacks.
        # 1) Eastmoney index_zh_a_hist
        try:
            if hasattr(ak, "index_zh_a_hist"):
                df = ak.index_zh_a_hist(symbol=symbol, period="daily", start_date=start, end_date=end)
                if not df.empty:
                    return _normalize(df)
        except Exception as e1:
            last_err = e1

        # 2) Eastmoney em index API (likely more stable)
        try:
            if hasattr(ak, "stock_zh_index_daily_em"):
                for prefix in ("sh", "sz"):
                    df = ak.stock_zh_index_daily_em(symbol=f"{prefix}{symbol}", start_date=start, end_date=end)
                    if not df.empty:
                        return _normalize(df)
        except Exception as e2:
            last_err = e2

        # 3) Sina legacy fallback
        try:
            if hasattr(ak, "stock_zh_index_daily"):
                for prefix in ("sh", "sz"):
                    # stock_zh_index_daily expects "sh000xxx"/"sz000xxx"
                    df = ak.stock_zh_index_daily(symbol=f"{prefix}{symbol}")
                    if not df.empty:
                        return _normalize(df)
        except Exception as e3:
            last_err = e3

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
        choices=["stock", "etf", "index"],
        help="Security type: stock (A股个股) / etf (场内ETF) / index (指数，如000300沪深300)",
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
    elif args.sec_type == "etf":
        df = fetch_etf_hist(args.symbol, args.start, args.end, args.retries, market=args.market or None)
    else:
        df = fetch_index_hist(args.symbol, args.start, args.end, args.retries)

    df.to_csv(out, index=False, encoding="utf-8-sig")

    print("akshare_fetch_ok")
    print("saved_to", str(out))
    print("rows", len(df))
    print(df.head(3))


if __name__ == "__main__":
    main()

