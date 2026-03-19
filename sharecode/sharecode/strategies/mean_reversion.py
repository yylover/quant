from __future__ import annotations

import pandas as pd
import vectorbt as vbt


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of columns found: {candidates}. Available: {list(df.columns)}")


def _prepare_close(df: pd.DataFrame) -> pd.Series:
    """Normalize AkShare daily DataFrame to a close Series indexed by date."""
    df = df.copy()
    date_col = _first_col(df, ["日期", "date"])
    close_col = _first_col(df, ["收盘", "close"])
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    close = df.set_index(date_col)[close_col].astype(float)
    close.name = "close"
    return close


def bollinger_reversion_signals(
    df: pd.DataFrame,
    window: int = 20,
    n_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands mean-reversion strategy.

    Buy when price drops below lower band; sell when price returns to middle band.
    """
    close = _prepare_close(df)
    bb = vbt.BBANDS.run(close, window=window, std=n_std)

    # Trigger entry only on the day the price first breaks below the lower band.
    prev_above = close.shift(1) >= bb.lower.shift(1)
    now_below = close < bb.lower
    entries = prev_above & now_below

    # Exit when price has mean-reverted back to (or above) the middle band.
    exits = close >= bb.middle
    return close, entries, exits


def rsi_reversion_signals(
    df: pd.DataFrame,
    window: int = 14,
    low: float = 30.0,
    high: float = 70.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """RSI mean-reversion strategy.

    Buy when RSI < low; sell when RSI > high.
    """
    close = _prepare_close(df)
    rsi = vbt.RSI.run(close, window=window).rsi
    entries = rsi < low
    exits = rsi > high
    return close, entries, exits


def zscore_reversion_signals(
    df: pd.DataFrame,
    window: int = 60,
    k: float = 2.0,
    exit_z: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Z-Score mean-reversion strategy.

    z = (close - rolling_mean) / rolling_std
    Entry: z crosses below -k
    Exit:  z crosses above exit_z (default 0, "back to mean")
    """
    close = _prepare_close(df)
    rolling_mean = close.rolling(window).mean()
    rolling_std = close.rolling(window).std()
    z = (close - rolling_mean) / rolling_std.replace(0.0, pd.NA)

    prev_z = z.shift(1)
    entries = (prev_z >= -k) & (z < -k)
    exits = (prev_z <= exit_z) & (z > exit_z)
    return close, entries, exits


def deviation_reversion_signals(
    df: pd.DataFrame,
    ma_window: int = 20,
    entry_dev: float = 0.05,
    exit_dev: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Moving-average deviation mean-reversion strategy.

    dev = close / MA(ma_window) - 1
    Entry: dev crosses below -entry_dev
    Exit:  dev crosses above exit_dev
    """
    close = _prepare_close(df)
    ma = close.rolling(ma_window).mean()
    dev = close / ma - 1.0

    prev_dev = dev.shift(1)
    entries = (prev_dev >= -entry_dev) & (dev < -entry_dev)
    exits = (prev_dev <= exit_dev) & (dev > exit_dev)
    return close, entries, exits

