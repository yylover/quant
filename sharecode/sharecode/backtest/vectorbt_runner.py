from __future__ import annotations

from typing import Tuple

import pandas as pd
import vectorbt as vbt


def run_signals_backtest(
    close: pd.Series,
    entries: pd.Series | pd.DataFrame,
    exits: pd.Series | pd.DataFrame,
    *,
    init_cash: float = 100_000.0,
    fees: float = 0.001,
    slippage: float = 0.0005,
    freq: str = "1D",
) -> Tuple[vbt.Portfolio, pd.Series]:
    """Run a basic long-only backtest based on entry/exit signals."""
    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=init_cash,
        fees=fees,
        slippage=slippage,
        freq=freq,
    )
    stats = pf.stats()
    return pf, stats


def print_basic_stats(pf: vbt.Portfolio, stats: pd.Series) -> None:
    """Print key performance statistics."""
    keys = [
        "Start Value",
        "End Value",
        "Total Return [%]",
        "Max Drawdown [%]",
        "Sharpe Ratio",
        "Calmar Ratio",
        "Win Rate [%]",
        "Total Trades",
    ]
    existing_keys = [k for k in keys if k in stats.index]
    print("rows", pf.close.shape[0], "start", pf.close.index.min().date(), "end", pf.close.index.max().date())
    print(stats.loc[existing_keys])

