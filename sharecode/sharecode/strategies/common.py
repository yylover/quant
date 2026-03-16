from __future__ import annotations

import pandas as pd
import vectorbt as vbt


def _prepare_close(df: pd.DataFrame) -> pd.Series:
    """Normalize AkShare daily DataFrame to a close price Series indexed by date."""
    df = df.copy()
    df["日期"] = pd.to_datetime(df["日期"])
    df = df.sort_values("日期")
    close = df.set_index("日期")["收盘"].astype(float)
    close.name = "close"
    return close


def ma_cross_signals(df: pd.DataFrame, fast: int = 10, slow: int = 30) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Dual moving average crossover trend-following strategy.

    Returns (close, entries, exits).
    """
    if fast >= slow:
        raise ValueError("fast window must be smaller than slow window")
    close = _prepare_close(df)
    fast_ma = vbt.MA.run(close, window=fast)
    slow_ma = vbt.MA.run(close, window=slow)
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    return close, entries, exits


def bollinger_breakout_signals(
    df: pd.DataFrame,
    window: int = 20,
    n_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands breakout trend strategy.

    Buy when price breaks above upper band from below; sell when price falls below middle band.
    """
    close = _prepare_close(df)
    bb = vbt.BBANDS.run(close, window=window, std=n_std)
    # breakout: yesterday close <= upper_band and today close > upper_band
    prev_below = close.shift(1) <= bb.upper.shift(1)
    now_above = close > bb.upper
    entries = prev_below & now_above
    exits = close < bb.middle
    return close, entries, exits


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
    prev_above = close.shift(1) >= bb.lower.shift(1)
    now_below = close < bb.lower
    entries = prev_above & now_below
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


def timing_ma_signals(df: pd.DataFrame, fast: int = 20, slow: int = 60) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Moving average timing strategy for index/ETF.

    Uses MA crossover to switch between full long and flat.
    """
    return ma_cross_signals(df, fast=fast, slow=slow)


def macd_trend_signals(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD trend-following strategy based on MACD/signal line crossover.

    Buy when MACD crosses above signal; sell when MACD crosses below signal.
    """
    if fast >= slow:
        raise ValueError("fast window must be smaller than slow window")
    close = _prepare_close(df)
    macd_ind = vbt.MACD.run(close, fast_window=fast, slow_window=slow, signal_window=signal)
    entries = macd_ind.macd_crossed_above(macd_ind.signal)
    exits = macd_ind.macd_crossed_below(macd_ind.signal)
    return close, entries, exits

