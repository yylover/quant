from __future__ import annotations

import pandas as pd
import vectorbt as vbt


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str:
    """从候选列名中查找第一个存在的列名

    Args:
        df: 输入的 DataFrame
        candidates: 候选列名列表,按优先级顺序排列

    Returns:
        找到的第一个存在的列名

    Raises:
        KeyError: 如果所有候选列名都不存在

    """
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of columns found: {candidates}. Available: {list(df.columns)}")


def _prepare_close(df: pd.DataFrame) -> pd.Series:
    """将 AkShare 日线 DataFrame 标准化为以日期为索引的收盘价 Series

    该函数处理不同来源的数据格式,统一输出格式:
    - 支持中文和英文列名(日期/date, 收盘/close)
    - 确保日期列为 datetime 类型并按时间排序
    - 收盘价转换为 float 类型

    Args:
        df: 包含日期和收盘价的原始 DataFrame

    Returns:
        以日期为索引的收盘价 Series,名称为 "close"

    """
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
    """布林带均值回归策略信号生成

    策略逻辑:
    1. 计算布林带(中轨=移动平均线,上下轨=中轨±n_std倍标准差)
    2. 当价格首次跌破下轨时买入(入场)
    3. 当价格回到中轨或以上时卖出(出场)

    原理: 价格在正常情况下会在布林带通道内波动,
    当价格触及下轨时通常处于超卖状态,预计会回归均值。

    Args:
        df: 包含日期和收盘价的原始 DataFrame
        window: 移动平均窗口期,默认20天
        n_std: 标准差倍数,用于计算布林带上下轨,默认2.0

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    close = _prepare_close(df)
    bb = vbt.BBANDS.run(close, window=window, std=n_std)

    # 仅在价格首次跌破下轨的当天触发入场信号
    # prev_above: 前一日价格在上轨或以上
    # now_below: 当日价格跌破下轨
    # 两者同时为True时产生买入信号,避免重复买入
    prev_above = close.shift(1) >= bb.lower.shift(1)
    now_below = close < bb.lower
    entries = prev_above & now_below

    # 当价格回归均值(回到中轨或以上)时出场
    exits = close >= bb.middle
    return close, entries, exits


def rsi_reversion_signals(
    df: pd.DataFrame,
    window: int = 14,
    low: float = 30.0,
    high: float = 70.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """RSI 均值回归策略信号生成

    策略逻辑:
    1. 计算相对强弱指数(RSI)
    2. 当 RSI < low(超卖区)时买入
    3. 当 RSI > high(超买区)时卖出

    原理: RSI 指标衡量价格变动的速度和变化,
    RSI 低于 30 通常表示超卖,高于 70 表示超买,
    预期价格会向中间区域回归。

    Args:
        df: 包含日期和收盘价的原始 DataFrame
        window: RSI 计算窗口期,默认14天
        low: 超卖阈值,低于此值时买入,默认30
        high: 超买阈值,高于此值时卖出,默认70

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

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
    """Z-Score 均值回归策略信号生成

    策略逻辑:
    1. 计算价格相对于滚动均值的标准化得分(Z-Score)
       z = (close - rolling_mean) / rolling_std
    2. 当 z 从 -k 以上跌破 -k 时买入(价格显著低于均值)
    3. 当 z 从 exit_z 以下突破 exit_z 时卖出(价格回归均值)

    原理: Z-Score 衡量价格偏离均值的程度(以标准差为单位),
    当 Z-Score 绝对值较大时,价格偏离均值较远,
    预期会向均值回归。

    Args:
        df: 包含日期和收盘价的原始 DataFrame
        window: 滚动均值和标准差的计算窗口期,默认60天
        k: 入场阈值,Z-Score 跌破 -k 时买入,默认2.0
        exit_z: 出场阈值,Z-Score 突破此值时卖出,默认0(回归均值)

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    close = _prepare_close(df)
    rolling_mean = close.rolling(window).mean()
    rolling_std = close.rolling(window).std()
    # 计算 Z-Score,将标准差为0的情况替换为NA避免除零错误
    z = (close - rolling_mean) / rolling_std.replace(0.0, pd.NA)

    prev_z = z.shift(1)
    # 入场: Z-Score 从 -k 以上跌破 -k,避免在持续低位重复买入
    entries = (prev_z >= -k) & (z < -k)
    # 出场: Z-Score 从 exit_z 以下突破 exit_z
    exits = (prev_z <= exit_z) & (z > exit_z)
    return close, entries, exits


def deviation_reversion_signals(
    df: pd.DataFrame,
    ma_window: int = 20,
    entry_dev: float = 0.05,
    exit_dev: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """移动平均偏离度均值回归策略信号生成

    策略逻辑:
    1. 计算价格相对于移动平均线的偏离度
       dev = close / MA(ma_window) - 1
    2. 当偏离度从 -entry_dev 以上跌破 -entry_dev 时买入
    3. 当偏离度从 exit_dev 以下突破 exit_dev 时卖出

    原理: 价格在正常情况下会在移动平均线附近波动,
    当价格显著低于均线时(偏离度为负且绝对值较大),
    预期会向均线回归。

    Args:
        df: 包含日期和收盘价的原始 DataFrame
        ma_window: 移动平均线计算窗口期,默认20天
        entry_dev: 入场偏离度阈值,低于 -entry_dev 时买入,默认0.05(即5%)
        exit_dev: 出场偏离度阈值,高于此值时卖出,默认0.0(回归均线)

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    close = _prepare_close(df)
    ma = close.rolling(ma_window).mean()
    # 计算偏离度: 正值表示高于均线,负值表示低于均线
    dev = close / ma - 1.0

    prev_dev = dev.shift(1)
    # 入场: 偏离度从 -entry_dev 以上跌破 -entry_dev,避免在持续低位重复买入
    entries = (prev_dev >= -entry_dev) & (dev < -entry_dev)
    # 出场: 偏离度从 exit_dev 以下突破 exit_dev
    exits = (prev_dev <= exit_dev) & (dev > exit_dev)
    return close, entries, exits


def kdj_reversion_signals(
    df: pd.DataFrame,
    window: int = 9,
    m1: int = 3,
    m2: int = 3,
    low: float = 20.0,
    high: float = 80.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """KDJ 均值回归策略信号生成

    策略逻辑:
    1. 计算 KDJ 指标(随机指标)
       - RSV = (收盘价 - N日最低价) / (N日最高价 - N日最低价) × 100
       - K = EMA(RSV, m1)
       - D = EMA(K, m2)
       - J = 3*K - 2*D
    2. 当 K 值从 low 以上跌破 low 时买入(超卖)
    3. 当 K 值从 high 以下突破 high 时卖出(超买)

    原理: KDJ 指标比 RSI 对价格变化更敏感,
    K 值低于 20 表示超卖,高于 80 表示超买,
    预期价格会向中间区域回归。适合短期波动行情。

    Args:
        df: 包含日期、开盘价、最高价、最低价、收盘价的原始 DataFrame
        window: RSV 计算窗口期,默认9天
        m1: K 值平滑周期,默认3天
        m2: D 值平滑周期,默认3天
        low: 超卖阈值,K 值低于此值时买入,默认20
        high: 超买阈值,K 值高于此值时卖出,默认80

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    df = df.copy()
    date_col = _first_col(df, ["日期", "date"])
    open_col = _first_col(df, ["开盘", "open"])
    high_col = _first_col(df, ["最高", "high"])
    low_col = _first_col(df, ["最低", "low"])
    close_col = _first_col(df, ["收盘", "close"])

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    df = df.set_index(date_col)

    high = df[high_col].astype(float)
    low = df[low_col].astype(float)
    close = df[close_col].astype(float)
    close.name = "close"

    # 计算 RSV
    low_n = low.rolling(window).min()
    high_n = high.rolling(window).max()
    rsv = ((close - low_n) / (high_n - low_n).replace(0.0, pd.NA)) * 100

    # 计算 K、D、J
    k = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d = k.ewm(com=m2 - 1, adjust=False).mean()
    j = 3 * k - 2 * d

    # KDJ 均值回归策略:
    # 当 K 值低于超卖线时买入(不要求交叉,更激进)
    # 当 K 值高于超买线时卖出(不要求交叉,更激进)
    entries = k < low
    exits = k > high

    return close, entries, exits


def williams_r_reversion_signals(
    df: pd.DataFrame,
    window: int = 14,
    low: float = -80.0,
    high: float = -20.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Williams %R 均值回归策略信号生成

    策略逻辑:
    1. 计算 Williams %R 指标
       %R = (最高价 - 收盘价) / (最高价 - 最低价) × (-100)
    2. 当 %R 从 low 以上跌破 low 时买入(超卖,如 -80)
    3. 当 %R 从 high 以下突破 high 时卖出(超买,如 -20)

    原理: Williams %R 衡量收盘价在最近 N 日高低价区间中的位置,
    取值范围 [-100, 0],-100 表示收盘价在区间最低点,
    0 表示收盘价在区间最高点。
    %R < -80 表示超卖,%R > -20 表示超买,
    预期价格会向中间区域回归。

    Args:
        df: 包含日期、最高价、最低价、收盘价的原始 DataFrame
        window: 计算窗口期,默认14天
        low: 超卖阈值,%R 低于此值时买入,默认-80
        high: 超买阈值,%R 高于此值时卖出,默认-20

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    df = df.copy()
    date_col = _first_col(df, ["日期", "date"])
    high_col = _first_col(df, ["最高", "high"])
    low_col = _first_col(df, ["最低", "low"])
    close_col = _first_col(df, ["收盘", "close"])

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    df = df.set_index(date_col)

    high = df[high_col].astype(float)
    low = df[low_col].astype(float)
    close = df[close_col].astype(float)
    close.name = "close"

    # 计算 Williams %R
    high_n = high.rolling(window).max()
    low_n = low.rolling(window).min()
    williams_r = ((high_n - close) / (high_n - low_n).replace(0.0, pd.NA)) * -100

    # Williams %R 均值回归策略:
    # 当 %R 低于超卖线时买入(不要求交叉,更激进)
    # 当 %R 高于超买线时卖出(不要求交叉,更激进)
    entries = williams_r < low
    exits = williams_r > high

    return close, entries, exits


def cci_reversion_signals(
    df: pd.DataFrame,
    window: int = 20,
    low: float = -100.0,
    high: float = 100.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """CCI (商品通道指数) 均值回归策略信号生成

    策略逻辑:
    1. 计算 CCI 指标
       TP = (最高价 + 最低价 + 收盘价) / 3
       MA_TP = TP 的移动平均
       MD = TP 与 MA_TP 绝对偏差的移动平均
       CCI = (TP - MA_TP) / (0.015 * MD)
    2. 当 CCI 从 low 以上跌破 low 时买入(超卖,如 -100)
    3. 当 CCI 从 high 以下突破 high 时卖出(超买,如 100)

    原理: CCI 专门用于识别循环性超买超卖,
    取值范围通常在 -100 到 +100 之间,
    超过 ±100 表示价格偏离统计均值较多,
    预期会向均值回归。对震荡行情特别有效。

    Args:
        df: 包含日期、最高价、最低价、收盘价的原始 DataFrame
        window: 计算窗口期,默认20天
        low: 超卖阈值,CCI 低于此值时买入,默认-100
        high: 超买阈值,CCI 高于此值时卖出,默认100

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    df = df.copy()
    date_col = _first_col(df, ["日期", "date"])
    high_col = _first_col(df, ["最高", "high"])
    low_col = _first_col(df, ["最低", "low"])
    close_col = _first_col(df, ["收盘", "close"])

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    df = df.set_index(date_col)

    high = df[high_col].astype(float)
    low = df[low_col].astype(float)
    close = df[close_col].astype(float)
    close.name = "close"

    # 计算 TP (典型价格)
    tp = (high + low + close) / 3

    # 计算 CCI
    ma_tp = tp.rolling(window).mean()
    md = tp.rolling(window).apply(lambda x: abs(x - x.mean()).mean())
    cci = (tp - ma_tp) / (0.015 * md).replace(0.0, pd.NA)

    # CCI 均值回归策略:
    # 当 CCI 低于超卖线时买入(不要求交叉,更激进)
    # 当 CCI 高于超买线时卖出(不要求交叉,更激进)
    entries = cci < low
    exits = cci > high

    return close, entries, exits


def macd_reversion_signals(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    hist_threshold: float = 0.5,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD 均值回归策略信号生成

    策略逻辑:
    1. 计算 MACD 指标
       - DIF = EMA(收盘价, fast) - EMA(收盘价, slow)
       - DEA = EMA(DIF, signal)
       - MACD柱 = (DIF - DEA) × 2
    2. 当 MACD 柱从 hist_threshold 以上跌破 hist_threshold 时买入
    3. 当 MACD 柱从 -hist_threshold 以下突破 -hist_threshold 时卖出

    原理: MACD 柱状图反映价格动能的变化,
    柱状图偏离零轴过大表示动能过强,预期会回归。
    结合了趋势跟踪和均值回归的特性。

    Args:
        df: 包含日期和收盘价的原始 DataFrame
        fast: 快线周期,默认12天
        slow: 慢线周期,默认26天
        signal: 信号线周期,默认9天
        hist_threshold: 柱状图阈值,默认0.5

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    close = _prepare_close(df)
    # 手动计算 MACD 以避免 vectorbt 版本兼容性问题
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = dif - dea

    # 计算 MACD 柱状图(已经计算完成)

    # MACD 均值回归策略:
    # 当柱状图从正阈值以上跌破阈值时买入(动能从强转弱)
    # 当柱状图从负阈值以下突破负阈值时卖出(动能从弱转强)
    prev_hist = hist.shift(1)
    entries = (prev_hist >= hist_threshold) & (hist < hist_threshold)
    exits = (prev_hist <= -hist_threshold) & (hist > -hist_threshold)

    return close, entries, exits


def bias_reversion_signals(
    df: pd.DataFrame,
    window: int = 20,
    low: float = -0.05,
    high: float = 0.05,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """乖离率 (BIAS) 均值回归策略信号生成

    策略逻辑:
    1. 计算乖离率指标
       BIAS = (收盘价 - MA(window)) / MA(window) × 100%
    2. 当 BIAS 从 low 以上跌破 low 时买入(价格显著低于均值)
    3. 当 BIAS 从 high 以下突破 high 时卖出(价格显著高于均值)

    原理: 乖离率衡量收盘价偏离移动平均线的程度,
    BIAS 过大表示价格偏离均线过多,预期会回归。
    正值表示超买,负值表示超卖。中国股市常用指标。

    Args:
        df: 包含日期和收盘价的原始 DataFrame
        window: 移动平均线计算窗口期,默认20天
        low: 超卖阈值,BIAS 低于此值时买入,默认-0.05(即-5%)
        high: 超买阈值,BIAS 高于此值时卖出,默认0.05(即5%)

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    close = _prepare_close(df)
    ma = close.rolling(window).mean()

    # 计算乖离率
    bias = (close - ma) / ma

    # BIAS 均值回归策略:
    # 当乖离率从低阈值以上跌破低阈值时买入(超卖)
    # 当乖离率从高阈值以下突破高阈值时卖出(超买)
    prev_bias = bias.shift(1)
    entries = (prev_bias >= low) & (bias < low)
    exits = (prev_bias <= high) & (bias > high)

    return close, entries, exits


def bb_width_reversion_signals(
    df: pd.DataFrame,
    window: int = 20,
    n_std: float = 2.0,
    width_percentile: float = 0.1,
    exit_percentile: float = 0.5,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """布林带宽度 (BB Width) 均值回归策略信号生成

    策略逻辑:
    1. 计算布林带宽度
       Width = (上轨 - 下轨) / 中轨
    2. 当布林带宽度从历史 width_percentile 分位以上跌破该分位时买入
    3. 当布林带宽度突破 exit_percentile 分位时卖出

    原理: 布林带宽度反映市场波动率,
    宽度压缩到历史低位表示市场进入平静期,
    预期波动率会回归均值,价格将出现突破。
    适合捕捉波动率压缩后的行情爆发。

    Args:
        df: 包含日期和收盘价的原始 DataFrame
        window: 移动平均窗口期,默认20天
        n_std: 标准差倍数,用于计算布林带上下轨,默认2.0
        width_percentile: 入场分位数,低于此历史分位时买入,默认0.1(10%分位)
        exit_percentile: 出场分位数,高于此历史分位时卖出,默认0.5(50%分位)

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    close = _prepare_close(df)
    # 手动计算布林带以避免 vectorbt 版本兼容性问题
    middle = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = middle + n_std * std
    lower = middle - n_std * std

    # 计算布林带宽度,避免除零错误
    bb_width = (upper - lower) / middle.replace(0.0, pd.NA)

    # 计算布林带宽度的历史分位数
    width_threshold = bb_width.rolling(window * 2).quantile(width_percentile)
    exit_threshold = bb_width.rolling(window * 2).quantile(exit_percentile)

    # BB Width 均值回归策略:
    # 当布林带宽度从阈值以上跌破阈值时买入(波动率压缩)
    # 当布林带宽度突破出场阈值时卖出(波动率回归)
    prev_width = bb_width.shift(1)
    entries = (prev_width >= width_threshold) & (bb_width < width_threshold)
    exits = bb_width > exit_threshold

    return close, entries, exits


def atr_reversion_signals(
    df: pd.DataFrame,
    window: int = 14,
    atr_multiplier: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """ATR (平均真实波幅) 均值回归策略信号生成

    策略逻辑:
    1. 计算 ATR 指标(衡量波动率)
       TR = max(最高-最低, abs(最高-前收盘), abs(最低-前收盘))
       ATR = TR 的移动平均
    2. 当价格从 ATR 上轨以上跌破上轨时买入(超卖)
    3. 当价格从 ATR 下轨以下突破下轨时卖出(超买)

    原理: ATR 衡量市场波动率,
    使用 ATR 的倍数构建动态通道,
    价格偏离通道时预期会回归。
    相比固定带宽的布林带,ATR 通道能自适应市场波动率。

    Args:
        df: 包含日期、最高价、最低价、收盘价的原始 DataFrame
        window: ATR 计算窗口期,默认14天
        atr_multiplier: ATR 倍数,用于构建通道宽度,默认2.0

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    df = df.copy()
    date_col = _first_col(df, ["日期", "date"])
    high_col = _first_col(df, ["最高", "high"])
    low_col = _first_col(df, ["最低", "low"])
    close_col = _first_col(df, ["收盘", "close"])

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    df = df.set_index(date_col)

    high = df[high_col].astype(float)
    low = df[low_col].astype(float)
    close = df[close_col].astype(float)
    close.name = "close"

    # 计算 TR (真实波幅)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        abs(high - prev_close),
        abs(low - prev_close)
    ], axis=1).max(axis=1)

    # 计算 ATR
    atr = tr.rolling(window).mean()

    # 使用 ATR 构建通道
    middle = close.rolling(window).mean()
    upper = middle + atr_multiplier * atr
    lower = middle - atr_multiplier * atr

    # ATR 均值回归策略:
    # 当价格从上轨以上跌破上轨时买入(超卖)
    # 当价格从下轨以下突破下轨时卖出(超买)
    prev_close = close.shift(1)
    prev_upper = upper.shift(1)
    prev_lower = lower.shift(1)
    entries = (prev_close >= prev_upper) & (close < upper)
    exits = (prev_close <= prev_lower) & (close > lower)

    return close, entries, exits


def roc_reversion_signals(
    df: pd.DataFrame,
    window: int = 12,
    low: float = -0.08,
    high: float = 0.08,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """ROC (变动率) 均值回归策略信号生成

    策略逻辑:
    1. 计算 ROC 指标
       ROC = (当前收盘价 - N日前收盘价) / N日前收盘价
    2. 当 ROC 从 low 以上跌破 low 时买入(超卖)
    3. 当 ROC 从 high 以下突破 high 时卖出(超买)

    原理: ROC 衡量价格在 N 日内的变化率,
    ROC 绝对值过大表示价格变动过快,
    预期会回归正常水平。适合捕捉超涨超跌行情。

    Args:
        df: 包含日期和收盘价的原始 DataFrame
        window: ROC 计算窗口期,默认12天
        low: 超卖阈值,ROC 低于此值时买入,默认-0.08(即-8%)
        high: 超买阈值,ROC 高于此值时卖出,默认0.08(即8%)

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    close = _prepare_close(df)

    # 计算 ROC
    roc = close.pct_change(window)

    # ROC 均值回归策略:
    # 当 ROC 从低阈值以上跌破低阈值时买入(超卖)
    # 当 ROC 从高阈值以下突破高阈值时卖出(超买)
    prev_roc = roc.shift(1)
    entries = (prev_roc >= low) & (roc < low)
    exits = (prev_roc <= high) & (roc > high)

    return close, entries, exits


def psar_reversion_signals(
    df: pd.DataFrame,
    af: float = 0.02,
    max_af: float = 0.2,
    lookback: int = 3,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """PSAR (抛物线转向) 逆向均值回归策略信号生成

    策略逻辑:
    1. 计算 PSAR 指标(趋势跟踪指标)
    2. 当价格远离 PSAR 线超过 N 日移动标准差的 lookback 倍时反向交易
       - 价格显著低于 PSAR 线时买入(超卖)
       - 价格显著高于 PSAR 线时卖出(超买)
    3. 当价格回归到 PSAR 线附近时平仓

    原理: PSAR 通常用于趋势跟踪,
    本策略逆向使用:当价格远离 PSAR 时,
    表示趋势过度,预期会回归。
    结合了趋势强度和均值回归的概念。

    Args:
        df: 包含日期、最高价、最低价、收盘价的原始 DataFrame
        af: 初始加速因子,默认0.02
        max_af: 最大加速因子,默认0.2
        lookback: 回望窗口期,用于计算偏离程度,默认3天

    Returns:
        元组包含三个 Series:
        - close: 标准化的收盘价序列
        - entries: 买入信号序列(True表示买入点)
        - exits: 卖出信号序列(True表示卖出点)

    """
    df = df.copy()
    date_col = _first_col(df, ["日期", "date"])
    high_col = _first_col(df, ["最高", "high"])
    low_col = _first_col(df, ["最低", "low"])
    close_col = _first_col(df, ["收盘", "close"])

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    df = df.set_index(date_col)

    high = df[high_col].astype(float)
    low = df[low_col].astype(float)
    close = df[close_col].astype(float)
    close.name = "close"

    # 计算 PSAR (简化实现)
    psar = close.copy()
    trend = pd.Series(1, index=close.index)  # 1=上涨趋势, -1=下跌趋势
    ep = high.iloc[0]  # 极值点
    af_value = af
    is_long = True

    for i in range(1, len(close)):
        if is_long:
            psar.iloc[i] = psar.iloc[i-1] + af_value * (ep - psar.iloc[i-1])
            if low.iloc[i] < psar.iloc[i]:
                psar.iloc[i] = low.iloc[i]
                is_long = False
                trend.iloc[i] = -1
                ep = low.iloc[i]
                af_value = af
            else:
                trend.iloc[i] = 1
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af_value = min(af_value + af, max_af)
        else:
            psar.iloc[i] = psar.iloc[i-1] + af_value * (ep - psar.iloc[i-1])
            if high.iloc[i] > psar.iloc[i]:
                psar.iloc[i] = high.iloc[i]
                is_long = True
                trend.iloc[i] = 1
                ep = high.iloc[i]
                af_value = af
            else:
                trend.iloc[i] = -1
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af_value = min(af_value + af, max_af)

    # 计算价格与 PSAR 的偏离度(用移动标准差衡量)
    deviation = (close - psar) / close.rolling(lookback * 2).std().replace(0.0, pd.NA)

    # PSAR 逆向均值回归策略:
    # 当价格显著低于 PSAR 时买入(下跌趋势过度)
    # 当价格显著高于 PSAR 时卖出(上涨趋势过度)
    entries = deviation < -1.5  # 价格低于 PSAR 超过1.5倍标准差
    exits = deviation > 1.5  # 价格高于 PSAR 超过1.5倍标准差

    return close, entries, exits

