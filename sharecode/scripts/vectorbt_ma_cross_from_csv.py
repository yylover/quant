import argparse
from pathlib import Path

import pandas as pd
import vectorbt as vbt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--fast", type=int, default=10)
    p.add_argument("--slow", type=int, default=30)
    p.add_argument("--init-cash", type=float, default=100000.0)
    p.add_argument("--fees", type=float, default=0.001)
    p.add_argument("--slippage", type=float, default=0.0005)
    args = p.parse_args()

    csv_path = Path(args.csv)
    df = pd.read_csv(csv_path)
    df["日期"] = pd.to_datetime(df["日期"])
    df = df.sort_values("日期")
    close = df.set_index("日期")["收盘"].astype(float)

    fast = vbt.MA.run(close, window=args.fast)
    slow = vbt.MA.run(close, window=args.slow)
    entries = fast.ma_crossed_above(slow)
    exits = fast.ma_crossed_below(slow)

    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=args.init_cash,
        fees=args.fees,
        slippage=args.slippage,
        freq="1D",
    )

    print("vectorbt_csv_ok")
    print("rows", close.shape[0], "start", close.index.min().date(), "end", close.index.max().date())
    keys = ["Start Value", "End Value", "Total Return [%]", "Max Drawdown [%]", "Win Rate [%]", "Total Trades"]
    print(pf.stats().loc[keys])


if __name__ == "__main__":
    main()

