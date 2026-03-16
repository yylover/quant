import numpy as np
import pandas as pd
import vectorbt as vbt


def main() -> None:
    rng = np.random.default_rng(1)
    dates = pd.date_range("2024-01-01", periods=240, freq="B")
    rets = rng.normal(0, 0.01, size=len(dates))
    close = pd.Series(100 * np.exp(np.cumsum(rets)), index=dates, name="close")

    fast = vbt.MA.run(close, window=10)
    slow = vbt.MA.run(close, window=30)
    entries = fast.ma_crossed_above(slow)
    exits = fast.ma_crossed_below(slow)

    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=100000,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )

    print("vectorbt_synth_ok")
    print(pf.stats().loc[["Total Return [%]", "Max Drawdown [%]", "Total Trades"]])


if __name__ == "__main__":
    main()

