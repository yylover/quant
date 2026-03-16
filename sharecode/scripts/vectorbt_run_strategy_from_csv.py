import argparse
from pathlib import Path
import sys

import pandas as pd

# Ensure local package root (../sharecode) is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sharecode.backtest.vectorbt_runner import print_basic_stats, run_signals_backtest
from sharecode.strategies import common as stg


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument(
        "--strategy",
        required=True,
        choices=["ma_cross", "boll_breakout", "boll_reversion", "rsi_reversion", "timing_ma", "macd"],
    )
    # common backtest params
    p.add_argument("--init-cash", type=float, default=100000.0)
    p.add_argument("--fees", type=float, default=0.001)
    p.add_argument("--slippage", type=float, default=0.0005)
    # risk management
    p.add_argument("--sl-pct", type=float, default=0.0, help="stop loss per trade, e.g. 0.05 for 5%")
    p.add_argument("--tp-pct", type=float, default=0.0, help="take profit per trade, e.g. 0.1 for 10%")
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
    return p.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    df = pd.read_csv(csv_path)

    close, entries, exits = stg.dispatch_signals(
        df,
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
    )

    print("strategy", args.strategy)
    print("csv", str(csv_path))
    pf, stats = run_signals_backtest(
        close,
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

