import numpy as np
import pandas as pd
import backtrader as bt


class SmaCross(bt.Strategy):
    params = dict(fast=10, slow=30)

    def __init__(self):
        fast = bt.ind.SMA(self.data.close, period=self.p.fast)
        slow = bt.ind.SMA(self.data.close, period=self.p.slow)
        self.cross = bt.ind.CrossOver(fast, slow)

    def next(self):
        if not self.position and self.cross > 0:
            self.buy()
        elif self.position and self.cross < 0:
            self.sell()


def main() -> None:
    rng = np.random.default_rng(1)
    dates = pd.date_range("2024-01-01", periods=240, freq="B")
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, size=len(dates))))
    open_ = close
    high = open_ * (1 + np.abs(rng.normal(0.001, 0.002, size=len(dates))))
    low = open_ * (1 - np.abs(rng.normal(0.001, 0.002, size=len(dates))))
    volume = rng.integers(1_000_000, 5_000_000, size=len(dates))
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )

    data = bt.feeds.PandasData(dataname=df)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(SmaCross)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    print("backtrader_synth_ok")
    print("start", cerebro.broker.getvalue())
    cerebro.run()
    print("end", cerebro.broker.getvalue())


if __name__ == "__main__":
    main()

