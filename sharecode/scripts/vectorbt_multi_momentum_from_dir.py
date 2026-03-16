import argparse
from pathlib import Path
from typing import Dict, List
import sys

import pandas as pd
import vectorbt as vbt

# Ensure local package root (../sharecode) is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sharecode.strategies.common import _prepare_close


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multi-stock momentum equal-weight portfolio backtest from CSV directory.")
    p.add_argument("--csv-dir", required=True, help="Directory containing multiple AkShare daily CSV files.")
    p.add_argument("--glob", default="*.csv", help="Filename pattern inside csv-dir, default: *.csv")
    p.add_argument("--lookback", type=int, default=60, help="Momentum lookback window in trading days.")
    p.add_argument("--top-n", type=int, default=5, help="Number of stocks to hold each rebalance.")
    p.add_argument("--rebalance-days", type=int, default=20, help="Rebalance frequency in trading days.")
    p.add_argument(
        "--weight-scheme",
        choices=["equal", "inv_vol"],
        default="equal",
        help="Weighting scheme among selected stocks: equal or inverse volatility.",
    )
    p.add_argument(
        "--max-weight",
        type=float,
        default=1.0,
        help="Optional cap on single-name weight (e.g. 0.2 for 20%%).",
    )
    p.add_argument("--init-cash", type=float, default=100000.0)
    p.add_argument("--fees", type=float, default=0.001)
    p.add_argument("--slippage", type=float, default=0.0005)
    return p.parse_args()


def load_close_matrix(csv_dir: Path, pattern: str) -> pd.DataFrame:
    paths: List[Path] = sorted(csv_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No CSV files matched {pattern} in {csv_dir}")

    close_map: Dict[str, pd.Series] = {}
    for p in paths:
        df = pd.read_csv(p)
        close = _prepare_close(df)
        symbol = p.stem
        close_map[symbol] = close

    close_df = pd.DataFrame(close_map).dropna(how="all").sort_index()
    return close_df


def build_momentum_weights(
    close_df: pd.DataFrame,
    lookback: int,
    top_n: int,
    rebalance_days: int,
) -> pd.DataFrame:
    """Generate base (equal-weight) target weights per symbol based on cross-sectional momentum."""
    # simple rolling return as momentum score
    mom = close_df.pct_change(lookback)

    dates = close_df.index
    weights = pd.DataFrame(0.0, index=dates, columns=close_df.columns)

    # rebalance at every rebalance_days-th date after lookback
    for i in range(lookback, len(dates), rebalance_days):
        date = dates[i]
        scores = mom.loc[date].dropna()
        if scores.empty:
            continue
        top = scores.sort_values(ascending=False).head(top_n).index
        if len(top) == 0:
            continue
        w = 1.0 / float(len(top))
        # determine next rebalance boundary
        j = min(i + rebalance_days, len(dates))
        rebalance_slice = dates[i:j]
        # reset weights for this slice, then assign equal weights to top symbols
        weights.loc[rebalance_slice, :] = 0.0
        weights.loc[rebalance_slice, top] = w

    return weights


def main() -> None:
    args = parse_args()
    csv_dir = Path(args.csv_dir)

    close_df = load_close_matrix(csv_dir, args.glob)
    print("loaded_symbols", list(close_df.columns))
    print("dates", close_df.index.min().date(), close_df.index.max().date(), "rows", close_df.shape[0])

    weights = build_momentum_weights(
        close_df,
        lookback=args.lookback,
        top_n=args.top_n,
        rebalance_days=args.rebalance_days,
    )

    if args.weight_scheme == "inv_vol":
        # adjust equal weights within each rebalance window using inverse volatility
        rets = close_df.pct_change().rolling(args.lookback)
        vols = rets.std()
        for date in weights.index:
            w_row = weights.loc[date]
            active = w_row[w_row > 0].index
            if len(active) == 0:
                continue
            vol_row = vols.loc[date, active]
            vol_row = vol_row.replace(0.0, pd.NA).dropna()
            if vol_row.empty:
                continue
            inv_vol = 1.0 / vol_row
            inv_vol = inv_vol / inv_vol.sum()
            weights.loc[date, active] = inv_vol

    if args.max_weight < 1.0:
        # cap single-name weight and renormalize within each date
        for date in weights.index:
            w_row = weights.loc[date]
            w_capped = w_row.clip(upper=args.max_weight)
            s = w_capped.sum()
            if s > 0:
                w_capped = w_capped / s
            weights.loc[date] = w_capped

    pf = vbt.Portfolio.from_orders(
        close_df,
        size=weights,
        size_type="targetpercent",
        fees=args.fees,
        slippage=args.slippage,
        init_cash=args.init_cash,
        freq="1D",
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
    print("multi_momentum_portfolio_ok")
    print(stats.loc[[k for k in keys if k in stats.index]])


if __name__ == "__main__":
    main()

