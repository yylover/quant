from __future__ import annotations

import pandas as pd
import vectorbt as vbt


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of columns found: {candidates}. Available: {list(df.columns)}")


def _prepare_close(df: pd.DataFrame) -> pd.Series:
    """Normalize AkShare daily DataFrame to a close price Series indexed by date."""
    df = df.copy()
    # AkShare 日线通常使用中文列名，这里把“日期”统一为 datetime 并按时间升序，
    # 确保后续技术指标与信号生成在“时间轴”上是严格对齐的。
    date_col = _first_col(df, ["日期", "date"])
    close_col = _first_col(df, ["收盘", "close"])
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    close = df.set_index(date_col)[close_col].astype(float)
    close.name = "close"
    return close


def _prepare_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize to an OHLC DataFrame indexed by date.

    Supports AkShare Chinese columns and common English columns.
    Returns columns: open, high, low, close.
    """
    df = df.copy()
    date_col = _first_col(df, ["日期", "date"])
    open_col = _first_col(df, ["开盘", "open"])
    high_col = _first_col(df, ["最高", "high"])
    low_col = _first_col(df, ["最低", "low"])
    close_col = _first_col(df, ["收盘", "close"])

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    out = df.set_index(date_col)[[open_col, high_col, low_col, close_col]].astype(float)
    out.columns = ["open", "high", "low", "close"]
    return out


def _ema(s: pd.Series, span: int) -> pd.Series:
    if span <= 0:
        raise ValueError("EMA span must be > 0")
    return s.ewm(span=span, adjust=False).mean()


def _sma(s: pd.Series, window: int) -> pd.Series:
    if window <= 0:
        raise ValueError("SMA window must be > 0")
    return s.rolling(window).mean()


def ema_slope_trend_signals(
    df: pd.DataFrame,
    *,
    buy_ema: int = 2,
    slope_n: int = 21,
    slope_scale: float = 20.0,
    sell_ema: int = 42,
    confirm: bool = True,
    guide_emas: tuple[int, int, int, int] = (4, 6, 12, 24),
    guide_ema2: int = 2,
    boundary_ma: int = 27,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """EMA + slope-adjusted trend line crossover.

    Based on the formula:
      buy_line  = EMA(C, buy_ema)
      sell_line = EMA(SLOPE(C, slope_n) * slope_scale + C, sell_ema)

    Where SLOPE(C, n) is approximated as (C - C.shift(n)) / n (per-bar change).

    Optional secondary confirmation (confirm=True):
      guide    = EMA( (EMA(C,4)+EMA(C,6)+EMA(C,12)+EMA(C,24))/4 , 2 )
      boundary = MA(C, 27)
    - Entry requires buy_line crosses above sell_line AND guide >= boundary.
    - Exit triggers on sell_line crosses above buy_line OR boundary crosses above guide.
    """
    close = _prepare_close(df)

    buy_line = _ema(close, buy_ema)
    slope = (close - close.shift(slope_n)) / float(slope_n)
    sell_src = slope * float(slope_scale) + close
    sell_line = _ema(sell_src, sell_ema)

    bu = buy_line.vbt.crossed_above(sell_line)
    sel = sell_line.vbt.crossed_above(buy_line)

    if not confirm:
        entries = bu
        exits = sel
        return close, entries.fillna(False), exits.fillna(False)

    e1, e2, e3, e4 = guide_emas
    guide_raw = (_ema(close, e1) + _ema(close, e2) + _ema(close, e3) + _ema(close, e4)) / 4.0
    guide = _ema(guide_raw, guide_ema2)
    boundary = _sma(close, boundary_ma)

    entries = bu & (guide >= boundary)
    exits = sel | boundary.vbt.crossed_above(guide)
    return close, entries.fillna(False), exits.fillna(False)


def ma_cross_signals(df: pd.DataFrame, fast: int = 10, slow: int = 30) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Dual moving average crossover trend-following strategy.

    Returns (close, entries, exits).
    """
    if fast >= slow:
        raise ValueError("fast window must be smaller than slow window")
    close = _prepare_close(df)
    # 趋势跟踪的经典形式：短均线与长均线的“交叉事件”作为入场/出场触发点，
    # 避免用“短均线始终大于长均线”导致的重复信号。
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
    # 仅在“从下向上突破上轨”的那一天触发入场：
    # 用 shift(1) 判断“昨天还在上轨下方”，避免价格持续在上轨上方时重复入场。
    prev_below = close.shift(1) <= bb.upper.shift(1)
    now_above = close > bb.upper
    entries = prev_below & now_above
    # 出场这里用“跌破中轨”作为趋势转弱/回撤保护的近似规则（可根据偏好改为下轨/上轨）。
    exits = close < bb.middle
    return close, entries, exits


def bollinger_reversion_signals(
    df: pd.DataFrame,
    window: int = 20,
    n_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands mean-reversion strategy.

    Logic moved to `mean_reversion.py` to keep strategy categories separated.
    """
    from sharecode.strategies.mean_reversion import bollinger_reversion_signals as _fn

    return _fn(df, window=window, n_std=n_std)


def rsi_reversion_signals(
    df: pd.DataFrame,
    window: int = 14,
    low: float = 30.0,
    high: float = 70.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """RSI mean-reversion strategy.

    Logic moved to `mean_reversion.py` to keep strategy categories separated.
    """
    from sharecode.strategies.mean_reversion import rsi_reversion_signals as _fn

    return _fn(df, window=window, low=low, high=high)


def zscore_reversion_signals(
    df: pd.DataFrame,
    window: int = 60,
    k: float = 2.0,
    exit_z: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Z-Score mean-reversion strategy (wrapper)."""
    from sharecode.strategies.mean_reversion import zscore_reversion_signals as _fn

    return _fn(df, window=window, k=k, exit_z=exit_z)


def deviation_reversion_signals(
    df: pd.DataFrame,
    ma_window: int = 20,
    entry_dev: float = 0.05,
    exit_dev: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Deviation (close/MA) mean-reversion strategy (wrapper)."""
    from sharecode.strategies.mean_reversion import deviation_reversion_signals as _fn

    return _fn(df, ma_window=ma_window, entry_dev=entry_dev, exit_dev=exit_dev)


def timing_ma_signals(df: pd.DataFrame, fast: int = 20, slow: int = 60) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Moving average timing strategy for index/ETF.

    Uses MA crossover to switch between full long and flat.
    """
    # 与 ma_cross_signals 复用同一信号逻辑；区别只在于语义：用于“择时是否持有”。
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
    # MACD 指标默认常用参数是 (12, 26, 9)，这里允许自定义窗口，
    # 并用“MACD 线与 signal 线的交叉事件”作为入场/出场信号。
    macd_ind = vbt.MACD.run(close, fast_window=fast, slow_window=slow, signal_window=signal)
    entries = macd_ind.macd_crossed_above(macd_ind.signal)
    exits = macd_ind.macd_crossed_below(macd_ind.signal)
    return close, entries, exits


def donchian_breakout_signals(
    df: pd.DataFrame,
    entry_n: int = 20,
    exit_n: int = 10,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Donchian channel breakout (turtle-style).

    - Entry: today's close breaks above the *previous* N-day high (use shift(1) to avoid lookahead).
    - Exit: today's close breaks below the *previous* M-day low.
    """
    if entry_n <= 1 or exit_n <= 1:
        raise ValueError("entry_n and exit_n must be > 1")
    ohlc = _prepare_ohlc(df)
    close = ohlc["close"]
    prev_high = ohlc["high"].rolling(entry_n).max().shift(1)
    prev_low = ohlc["low"].rolling(exit_n).min().shift(1)
    entries = close > prev_high
    exits = close < prev_low
    return close, entries, exits


def momentum_roc_signals(
    df: pd.DataFrame,
    lookback: int = 60,
    enter_th: float = 0.0,
    exit_th: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Momentum trend strategy using ROC (rate of change).

    ROC = close / close.shift(lookback) - 1
    - Entry: ROC crosses above enter_th
    - Exit: ROC crosses below exit_th
    """
    if lookback <= 1:
        raise ValueError("lookback must be > 1")
    close = _prepare_close(df)
    roc = close / close.shift(lookback) - 1.0
    entries = roc.vbt.crossed_above(enter_th)
    exits = roc.vbt.crossed_below(exit_th)
    return close, entries, exits


def ma_slope_signals(
    df: pd.DataFrame,
    window: int = 60,
    slope_window: int = 5,
    enter_slope: float = 0.0,
    exit_slope: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Trend strength via moving-average slope.

    - Compute MA(window)
    - Slope approx: (ma - ma.shift(slope_window)) / slope_window
    - Entry: slope crosses above enter_slope AND close > MA
    - Exit: slope crosses below exit_slope OR close < MA
    """
    if window <= 1 or slope_window <= 0:
        raise ValueError("window must be > 1 and slope_window must be > 0")
    close = _prepare_close(df)
    ma = vbt.MA.run(close, window=window).ma
    slope = (ma - ma.shift(slope_window)) / float(slope_window)
    entries = slope.vbt.crossed_above(enter_slope) & (close > ma)
    exits = slope.vbt.crossed_below(exit_slope) | (close < ma)
    return close, entries, exits


def bb_squeeze_breakout_signals(
    df: pd.DataFrame,
    window: int = 20,
    n_std: float = 2.0,
    squeeze_q: float = 0.2,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Band squeeze -> breakout strategy.

    - Define bandwidth = (upper - lower) / middle
    - "Squeeze" when bandwidth <= rolling quantile(squeeze_q) over the same window
    - Entry: after a squeeze, close breaks above upper band
    - Exit: close falls below middle band
    """
    if not (0.0 < squeeze_q < 1.0):
        raise ValueError("squeeze_q must be between 0 and 1")
    close = _prepare_close(df)
    bb = vbt.BBANDS.run(close, window=window, std=n_std)
    bandwidth = (bb.upper - bb.lower) / bb.middle.replace(0.0, pd.NA)
    squeeze_th = bandwidth.rolling(window).quantile(squeeze_q)
    squeeze_on = bandwidth <= squeeze_th
    entries = squeeze_on.shift(1).fillna(False) & (close > bb.upper)
    exits = close < bb.middle
    return close, entries, exits


def supertrend_signals(
    df: pd.DataFrame,
    atr_window: int = 10,
    multiplier: float = 3.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """SuperTrend (ATR-band) trend-following strategy.

    Uses HL2 +/- multiplier * ATR bands and an iterative trend state.
    Entry when trend flips to up; exit when flips to down.
    """
    if atr_window <= 1:
        raise ValueError("atr_window must be > 1")
    ohlc = _prepare_ohlc(df)
    high = ohlc["high"]
    low = ohlc["low"]
    close = ohlc["close"]

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(atr_window).mean()

    hl2 = (high + low) / 2.0
    upper_basic = hl2 + multiplier * atr
    lower_basic = hl2 - multiplier * atr

    upper_final = upper_basic.copy()
    lower_final = lower_basic.copy()
    for i in range(1, len(close)):
        idx = close.index[i]
        prev_idx = close.index[i - 1]
        if pd.notna(upper_final.loc[prev_idx]) and pd.notna(upper_basic.loc[idx]):
            upper_final.loc[idx] = (
                min(upper_basic.loc[idx], upper_final.loc[prev_idx])
                if close.loc[prev_idx] <= upper_final.loc[prev_idx]
                else upper_basic.loc[idx]
            )
        if pd.notna(lower_final.loc[prev_idx]) and pd.notna(lower_basic.loc[idx]):
            lower_final.loc[idx] = (
                max(lower_basic.loc[idx], lower_final.loc[prev_idx])
                if close.loc[prev_idx] >= lower_final.loc[prev_idx]
                else lower_basic.loc[idx]
            )

    trend_up = pd.Series(False, index=close.index, dtype=bool)
    for i in range(1, len(close)):
        idx = close.index[i]
        prev_idx = close.index[i - 1]
        if not trend_up.loc[prev_idx]:
            trend_up.loc[idx] = close.loc[idx] > upper_final.loc[idx] if pd.notna(upper_final.loc[idx]) else False
        else:
            trend_up.loc[idx] = close.loc[idx] >= lower_final.loc[idx] if pd.notna(lower_final.loc[idx]) else False

    # Use shift(..., fill_value=False) to keep dtype stable (avoid future downcasting warnings)
    prev_trend = trend_up.shift(1, fill_value=False)
    entries = trend_up & (~prev_trend)
    exits = (~trend_up) & prev_trend
    return close, entries, exits


def dispatch_signals(
    df: pd.DataFrame,
    strategy: str,
    *,
    fast: int = 10,
    slow: int = 30,
    window: int = 20,
    n_std: float = 2.0,
    rsi_window: int = 14,
    rsi_low: float = 30.0,
    rsi_high: float = 70.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    entry_n: int = 20,
    exit_n: int = 10,
    lookback: int = 60,
    enter_th: float = 0.0,
    exit_th: float = 0.0,
    slope_window: int = 5,
    enter_slope: float = 0.0,
    exit_slope: float = 0.0,
    squeeze_q: float = 0.2,
    atr_window: int = 10,
    multiplier: float = 3.0,
    # Z-score mean reversion params
    z_window: int = 60,
    z_k: float = 2.0,
    z_exit: float = 0.0,
    # Deviation (close/MA) mean reversion params
    dev_ma_window: int = 20,
    dev_entry: float = 0.05,
    dev_exit: float = 0.0,
    # EMA slope-trend params
    buy_ema: int = 2,
    slope_n: int = 21,
    slope_scale: float = 20.0,
    sell_ema: int = 42,
    confirm: bool = True,
    guide_ema2: int = 2,
    boundary_ma: int = 27,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Dispatch to the correct signal function by strategy name.

    Returns (close, entries, exits).
    Supported strategy names: ma_cross, boll_breakout, boll_reversion,
    rsi_reversion, zscore_reversion, deviation_reversion, timing_ma, macd,
    donchian, momentum, ma_slope, bb_squeeze, supertrend, ema_slope_trend.
    """
    # 统一入口：方便 CLI/一键脚本按字符串策略名调用，并集中管理各策略参数默认值。
    if strategy == "ma_cross":
        return ma_cross_signals(df, fast=fast, slow=slow)
    if strategy == "boll_breakout":
        return bollinger_breakout_signals(df, window=window, n_std=n_std)
    if strategy == "boll_reversion":
        return bollinger_reversion_signals(df, window=window, n_std=n_std)
    if strategy == "rsi_reversion":
        return rsi_reversion_signals(df, window=rsi_window, low=rsi_low, high=rsi_high)
    if strategy == "timing_ma":
        return timing_ma_signals(df, fast=fast, slow=slow)
    if strategy == "macd":
        return macd_trend_signals(df, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    if strategy == "ema_slope_trend":
        return ema_slope_trend_signals(
            df,
            buy_ema=buy_ema,
            slope_n=slope_n,
            slope_scale=slope_scale,
            sell_ema=sell_ema,
            confirm=confirm,
            guide_ema2=guide_ema2,
            boundary_ma=boundary_ma,
        )
    if strategy == "donchian":
        return donchian_breakout_signals(df, entry_n=entry_n, exit_n=exit_n)
    if strategy == "momentum":
        return momentum_roc_signals(df, lookback=lookback, enter_th=enter_th, exit_th=exit_th)
    if strategy == "ma_slope":
        return ma_slope_signals(
            df,
            window=window,
            slope_window=slope_window,
            enter_slope=enter_slope,
            exit_slope=exit_slope,
        )
    if strategy == "bb_squeeze":
        return bb_squeeze_breakout_signals(df, window=window, n_std=n_std, squeeze_q=squeeze_q)
    if strategy == "supertrend":
        return supertrend_signals(df, atr_window=atr_window, multiplier=multiplier)
    if strategy == "zscore_reversion":
        return zscore_reversion_signals(df, window=z_window, k=z_k, exit_z=z_exit)
    if strategy == "deviation_reversion":
        return deviation_reversion_signals(
            df,
            ma_window=dev_ma_window,
            entry_dev=dev_entry,
            exit_dev=dev_exit,
        )
    raise ValueError(
        "Unknown strategy: "
        f"{strategy!r}. Choose from: ma_cross, boll_breakout, boll_reversion, rsi_reversion, zscore_reversion, deviation_reversion, "
        "timing_ma, macd, ema_slope_trend, donchian, momentum, ma_slope, bb_squeeze, supertrend"
    )

