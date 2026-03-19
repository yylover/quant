"""
趋势跟踪策略模块

本模块包含各类趋势跟踪策略，适用于单边上涨或下跌行情。
趋势策略的核心思想是：顺势而为，在趋势形成后跟进，在趋势反转时退出。

策略分类：
1. 均线类：双均线交叉、均线斜率、EMA斜率趋势
2. 动量类：ROC动量、唐奇安通道突破
3. 指标类：MACD、SuperTrend、布林带突破/挤压
4. 择时类：均线择时（专用于指数/ETF）

作者：ShareCode Quant Team
"""

from __future__ import annotations

import pandas as pd
import vectorbt as vbt


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str:
    """从候选列名中查找第一个存在的列名

    Args:
        df: 输入的 DataFrame
        candidates: 候选列名列表，按优先级顺序排列

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
    """将日线 DataFrame 标准化为以日期为索引的收盘价 Series

    该函数处理不同来源的数据格式，统一输出格式：
    - 支持中文和英文列名（日期/date, 收盘/close）
    - 确保日期列为 datetime 类型并按时间排序
    - 收盘价转换为 float 类型

    Args:
        df: 包含日期和收盘价的原始 DataFrame

    Returns:
        以日期为索引的收盘价 Series，名称为 "close"
    """
    df = df.copy()
    date_col = _first_col(df, ["日期", "date"])
    close_col = _first_col(df, ["收盘", "close"])
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    close = df.set_index(date_col)[close_col].astype(float)
    close.name = "close"
    return close


def _prepare_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """标准化为 OHLC DataFrame，以日期为索引

    支持 AkShare 中文列名和通用英文列名。
    返回列：open, high, low, close

    Args:
        df: 包含日期和 OHLC 信息的原始 DataFrame

    Returns:
        标准化的 OHLC DataFrame
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


# ============================================================================
# 均线类趋势策略
# ============================================================================

def ma_cross_signals(
    df: pd.DataFrame,
    fast: int = 10,
    slow: int = 30,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """双均线交叉趋势策略

    策略逻辑：
    1. 计算短期均线（fast）和长期均线（slow）
    2. 当短期均线从下向上突破长期均线时买入（金叉）
    3. 当短期均线从上向下跌破长期均线时卖出（死叉）

    原理：短期均线代表近期价格趋势，长期均线代表长期价格趋势。
    金叉表示短期动能转强，死叉表示短期动能转弱。
    这是趋势跟踪的经典策略，简单但有效。

    适用场景：
    - 明显的上涨或下跌趋势
    - 不适合震荡市（会产生较多假信号）

    参数建议：
    - 快速交易：fast=5, slow=20
    - 中期趋势：fast=10, slow=30（默认）
    - 长期趋势：fast=20, slow=60

    Args:
        df: 包含日期和收盘价的 DataFrame
        fast: 短期均线周期，默认 10 天
        slow: 长期均线周期，默认 30 天（必须大于 fast）

    Returns:
        (close, entries, exits) 元组：
        - close: 标准化的收盘价序列
        - entries: 买入信号序列（True 表示买入点）
        - exits: 卖出信号序列（True 表示卖出点）

    Raises:
        ValueError: 当 fast >= slow 时抛出异常
    """
    if fast >= slow:
        raise ValueError("fast window must be smaller than slow window")

    close = _prepare_close(df)

    # 使用 VectorBT 的 MA 指标计算均线
    fast_ma = vbt.MA.run(close, window=fast)
    slow_ma = vbt.MA.run(close, window=slow)

    # 交叉事件作为入场/出场触发点
    # 使用 crossed_above/crossed_below 避免重复信号
    entries = fast_ma.ma_crossed_above(slow_ma)  # 金叉：买入
    exits = fast_ma.ma_crossed_below(slow_ma)    # 死叉：卖出

    return close, entries, exits


def timing_ma_signals(
    df: pd.DataFrame,
    fast: int = 20,
    slow: int = 60,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """均线择时策略（专用于指数/ETF）

    策略逻辑：
    与双均线交叉策略完全相同，但语义上用于"择时是否持有"。

    适用场景：
    - 宽基指数（沪深300、中证500等）
    - 行业 ETF
    - 用于决定何时满仓、何时空仓

    参数建议：
    - 指数择时：fast=20, slow=60（默认）
    - 更保守：fast=20, slow=120
    - 更激进：fast=10, slow=40

    Args:
        df: 包含日期和收盘价的 DataFrame
        fast: 短期均线周期，默认 20 天
        slow: 长期均线周期，默认 60 天

    Returns:
        (close, entries, exits) 元组
    """
    return ma_cross_signals(df, fast=fast, slow=slow)


def ma_slope_signals(
    df: pd.DataFrame,
    window: int = 60,
    slope_window: int = 5,
    enter_slope: float = 0.0,
    exit_slope: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """均线斜率趋势策略

    策略逻辑：
    1. 计算 N 日移动平均线
    2. 计算均线的变化率（斜率）：
       slope = (MA - MA.shift(slope_window)) / slope_window
    3. 入场条件：斜率突破阈值 且 价格在均线之上
    4. 出场条件：斜率跌破阈值 或 价格跌破均线

    原理：通过均线的斜率判断趋势强度。
    - 斜率为正且上升 → 趋势向上加强
    - 斜率为负或下降 → 趋势减弱
    - 价格在均线之上 → 处于多头状态

    优势：
    - 比单纯交叉策略更早发现趋势转折
    - 结合趋势强度和价格位置双重确认

    参数建议：
    - 中期趋势：window=60, slope_window=5（默认）
    - 短期趋势：window=20, slope_window=3
    - 长期趋势：window=120, slope_window=10

    Args:
        df: 包含日期和收盘价的 DataFrame
        window: 移动平均线周期，默认 60 天
        slope_window: 计算斜率的窗口期，默认 5 天
        enter_slope: 入场斜率阈值，默认 0.0（任何正斜率）
        exit_slope: 出场斜率阈值，默认 0.0（任何负斜率）

    Returns:
        (close, entries, exits) 元组

    Raises:
        ValueError: 当 window <= 1 或 slope_window <= 0 时抛出异常
    """
    if window <= 1 or slope_window <= 0:
        raise ValueError("window must be > 1 and slope_window must be > 0")

    close = _prepare_close(df)
    ma = vbt.MA.run(close, window=window).ma

    # 计算均线斜率：单位时间内均线的平均变化量
    slope = (ma - ma.shift(slope_window)) / float(slope_window)

    # 入场：斜率向上突破 且 价格在均线之上
    entries = slope.vbt.crossed_above(enter_slope) & (close > ma)

    # 出场：斜率向下突破 或 价格跌破均线
    exits = slope.vbt.crossed_below(exit_slope) | (close < ma)

    return close, entries, exits


# ============================================================================
# 动量类趋势策略
# ============================================================================

def momentum_roc_signals(
    df: pd.DataFrame,
    lookback: int = 60,
    enter_th: float = 0.0,
    exit_th: float = 0.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """ROC 动量趋势策略

    策略逻辑：
    1. 计算价格变动率（Rate of Change, ROC）：
       ROC = (当前价格 - N日前价格) / N日前价格
    2. 当 ROC 突破入场阈值时买入（正动量）
    3. 当 ROC 跌破出场阈值时卖出（负动量）

    原理：ROC 衡量价格在一段时间内的涨跌幅度。
    - ROC > 0 表示上涨动能
    - ROC < 0 表示下跌动能
    - ROC 突破阈值表示动能增强，趋势可能持续

    优势：
    - 直接衡量价格动能，不受均线滞后影响
    - 可通过阈值过滤噪音
    - 适合捕捉中期趋势

    参数建议：
    - 中期动量：lookback=60, enter_th=0.05, exit_th=0.0（上涨 5% 以上买入）
    - 短期动量：lookback=20, enter_th=0.03
    - 长期动量：lookback=120, enter_th=0.10

    Args:
        df: 包含日期和收盘价的 DataFrame
        lookback: 动量回看周期，默认 60 天
        enter_th: 入场 ROC 阈值，默认 0.0（任何正 ROC）
        exit_th: 出场 ROC 阈值，默认 0.0（任何负 ROC）

    Returns:
        (close, entries, exits) 元组

    Raises:
        ValueError: 当 lookback <= 1 时抛出异常
    """
    if lookback <= 1:
        raise ValueError("lookback must be > 1")

    close = _prepare_close(df)

    # 计算 ROC：N 日涨跌幅
    roc = close / close.shift(lookback) - 1.0

    # ROC 突破阈值时入场/出场
    entries = roc.vbt.crossed_above(enter_th)
    exits = roc.vbt.crossed_below(exit_th)

    return close, entries, exits


def donchian_breakout_signals(
    df: pd.DataFrame,
    entry_n: int = 20,
    exit_n: int = 10,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """唐奇安通道突破策略（Turtle Trading 原型）

    策略逻辑：
    1. 计算过去 N 天的最高价和最低价，形成通道
    2. 入场：今日收盘价突破过去 entry_n 天的最高价
    3. 出场：今日收盘价跌破过去 exit_n 天的最低价

    原理：价格突破历史高点表明新的上涨趋势开始，
    价格跌破历史低点表明趋势反转。
    这是海龟交易系统的基础策略。

    优势：
    - 捕捉大级别趋势的突破
    - 风险可控（通道宽度决定止损距离）
    - 经典策略，长期有效性经过验证

    适用场景：
    - 趋势明确的行情
    - 波动性适中的品种
    - 不适合震荡市（频繁假突破）

    参数建议：
    - 标准海龟：entry_n=20, exit_n=10（默认）
    - 更保守：entry_n=40, exit_n=20
    - 更激进：entry_n=10, exit_n=5

    Args:
        df: 包含日期、开盘价、最高价、最低价、收盘价的 DataFrame
        entry_n: 入场通道周期（突破几日新高），默认 20 天
        exit_n: 出场通道周期（跌破几日新低），默认 10 天

    Returns:
        (close, entries, exits) 元组

    Raises:
        ValueError: 当 entry_n <= 1 或 exit_n <= 1 时抛出异常
    """
    if entry_n <= 1 or exit_n <= 1:
        raise ValueError("entry_n and exit_n must be > 1")

    ohlc = _prepare_ohlc(df)
    close = ohlc["close"]

    # 计算通道边界（用 shift(1) 避免未来数据泄露）
    prev_high = ohlc["high"].rolling(entry_n).max().shift(1)
    prev_low = ohlc["low"].rolling(exit_n).min().shift(1)

    # 突破高点买入，跌破低点卖出
    entries = close > prev_high
    exits = close < prev_low

    return close, entries, exits


# ============================================================================
# 指标类趋势策略
# ============================================================================

def macd_trend_signals(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD 趋势策略

    策略逻辑：
    1. 计算 MACD 指标：
       - DIF (快线) = EMA(收盘价, fast) - EMA(收盘价, slow)
       - DEA (信号线) = EMA(DIF, signal)
       - MACD柱 = (DIF - DEA) × 2
    2. 当 DIF 从下向上突破 DEA 时买入（金叉）
    3. 当 DIF 从上向下跌破 DEA 时卖出（死叉）

    原理：MACD 是最常用的趋势指标之一。
    - DIF 反映短期价格动能
    - DEA 反映长期价格动能
    - 金叉表示短期动能转强，死叉表示短期动能转弱

    优势：
    - 结合了快慢均线，比单纯交叉更稳定
    - MACD 柱状图可辅助判断动能强弱
    - 适用性广，适合各种周期

    参数说明：
    - 标准参数：fast=12, slow=26, signal=9（默认）
    - 短期：fast=6, slow=13, signal=5
    - 长期：fast=24, slow=52, signal=18

    Args:
        df: 包含日期和收盘价的 DataFrame
        fast: 快线 EMA 周期，默认 12 天
        slow: 慢线 EMA 周期，默认 26 天（必须大于 fast）
        signal: 信号线 EMA 周期，默认 9 天

    Returns:
        (close, entries, exits) 元组

    Raises:
        ValueError: 当 fast >= slow 时抛出异常
    """
    if fast >= slow:
        raise ValueError("fast window must be smaller than slow window")

    close = _prepare_close(df)

    # 使用 VectorBT 计算 MACD
    macd_ind = vbt.MACD.run(
        close,
        fast_window=fast,
        slow_window=slow,
        signal_window=signal
    )

    # MACD 线与信号线的交叉作为入场/出场信号
    entries = macd_ind.macd_crossed_above(macd_ind.signal)  # 金叉
    exits = macd_ind.macd_crossed_below(macd_ind.signal)   # 死叉

    return close, entries, exits


def supertrend_signals(
    df: pd.DataFrame,
    atr_window: int = 10,
    multiplier: float = 3.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """SuperTrend 超级趋势策略

    策略逻辑：
    1. 计算 ATR（平均真实波幅）
    2. 基于 HL2（高低价中点）和 ATR 构建动态通道：
       上轨 = HL2 + multiplier × ATR
       下轨 = HL2 - multiplier × ATR
    3. 迭代计算趋势状态（上升/下降）
    4. 趋势从下跌转为上升时买入
    5. 趋势从上升转为下跌时卖出

    原理：SuperTrend 是一种自适应趋势跟踪指标，
    - 价格在上轨之上时为上升趋势
    - 价格在下轨之下时为下跌趋势
    - 通道宽度根据市场波动率动态调整

    优势：
    - 自适应波动率，在震荡市中更紧凑，趋势市中更宽松
    - 可视化效果好，直观显示趋势方向
    - 可直接用作移动止损线

    适用场景：
    - 各种趋势市场
    - 可作为主策略，也可用于止损

    参数建议：
    - 标准：atr_window=10, multiplier=3.0（默认）
    - 更灵敏：atr_window=7, multiplier=2.0
    - 更稳健：atr_window=14, multiplier=4.0

    Args:
        df: 包含日期、开盘价、最高价、最低价、收盘价的 DataFrame
        atr_window: ATR 计算窗口，默认 10 天
        multiplier: ATR 倍数，默认 3.0

    Returns:
        (close, entries, exits) 元组

    Raises:
        ValueError: 当 atr_window <= 1 时抛出异常
    """
    if atr_window <= 1:
        raise ValueError("atr_window must be > 1")

    ohlc = _prepare_ohlc(df)
    high = ohlc["high"]
    low = ohlc["low"]
    close = ohlc["close"]

    # 计算真实波幅（True Range, TR）
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # 计算 ATR
    atr = tr.rolling(atr_window).mean()

    # 计算基础上下轨
    hl2 = (high + low) / 2.0
    upper_basic = hl2 + multiplier * atr
    lower_basic = hl2 - multiplier * atr

    # 迭代计算最终上下轨（考虑趋势状态）
    upper_final = upper_basic.copy()
    lower_final = lower_basic.copy()
    for i in range(1, len(close)):
        idx = close.index[i]
        prev_idx = close.index[i - 1]
        if pd.notna(upper_final.loc[prev_idx]) and pd.notna(upper_basic.loc[idx]):
            # 上升趋势中，上轨只能下调
            upper_final.loc[idx] = (
                min(upper_basic.loc[idx], upper_final.loc[prev_idx])
                if close.loc[prev_idx] <= upper_final.loc[prev_idx]
                else upper_basic.loc[idx]
            )
        if pd.notna(lower_final.loc[prev_idx]) and pd.notna(lower_basic.loc[idx]):
            # 下降趋势中，下轨只能上调
            lower_final.loc[idx] = (
                max(lower_basic.loc[idx], lower_final.loc[prev_idx])
                if close.loc[prev_idx] >= lower_final.loc[prev_idx]
                else lower_basic.loc[idx]
            )

    # 判断趋势方向
    trend_up = pd.Series(False, index=close.index, dtype=bool)
    for i in range(1, len(close)):
        idx = close.index[i]
        prev_idx = close.index[i - 1]
        if not trend_up.loc[prev_idx]:
            # 从下跌转为上升：价格突破上轨
            trend_up.loc[idx] = close.loc[idx] > upper_final.loc[idx] if pd.notna(upper_final.loc[idx]) else False
        else:
            # 上升趋势继续：价格保持在下轨之上
            trend_up.loc[idx] = close.loc[idx] >= lower_final.loc[idx] if pd.notna(lower_final.loc[idx]) else False

    # 趋势转折点为入场/出场点
    prev_trend = trend_up.shift(1, fill_value=False)
    entries = trend_up & (~prev_trend)   # 趋势向上转折
    exits = (~trend_up) & prev_trend      # 趋势向下转折

    return close, entries, exits


def bollinger_breakout_signals(
    df: pd.DataFrame,
    window: int = 20,
    n_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """布林带突破趋势策略

    策略逻辑：
    1. 计算布林带：
       - 中轨 = N 日移动平均线
       - 上轨 = 中轨 + n_std × N 日标准差
       - 下轨 = 中轨 - n_std × N 日标准差
    2. 入场：价格从下向上突破上轨（强突破）
    3. 出场：价格跌破中轨

    原理：布林带反映价格波动范围。
    - 上轨代表统计学上的显著高位
    - 突破上轨通常意味着强势上涨
    - 回到中轨表示趋势转弱

    与布林带均值回归的区别：
    - 均值回归：价格触及下轨买入（超卖反弹）
    - 趋势突破：价格突破上轨买入（趋势加速）

    适用场景：
    - 价格快速上涨的强势行情
    - 配合成交量确认效果更好
    - 不适合震荡市

    参数建议：
    - 标准：window=20, n_std=2.0（默认）
    - 更紧凑：window=10, n_std=1.5
    - 更宽松：window=30, n_std=2.5

    Args:
        df: 包含日期和收盘价的 DataFrame
        window: 移动平均线周期，默认 20 天
        n_std: 标准差倍数，默认 2.0

    Returns:
        (close, entries, exits) 元组
    """
    close = _prepare_close(df)

    # 计算布林带
    bb = vbt.BBANDS.run(close, window=window, std=n_std)

    # 仅在"从下向上突破上轨"时触发入场
    # 用 shift(1) 判断"昨天还在上轨下方"，避免持续在上轨上方时重复入场
    prev_below = close.shift(1) <= bb.upper.shift(1)
    now_above = close > bb.upper
    entries = prev_below & now_above

    # 跌破中轨作为出场（趋势转弱）
    exits = close < bb.middle

    return close, entries, exits


def bb_squeeze_breakout_signals(
    df: pd.DataFrame,
    window: int = 20,
    n_std: float = 2.0,
    squeeze_q: float = 0.2,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """布林带挤压突破策略

    策略逻辑：
    1. 计算布林带带宽：
       bandwidth = (上轨 - 下轨) / 中轨
    2. 定义"挤压"：带宽 <= 历史分位数
    3. 入场：在挤压状态后，价格突破上轨
    4. 出场：价格跌破中轨

    原理：市场波动率呈现周期性变化。
    - 挤压：波动率低，市场平静，积蓄能量
    - 突破：积蓄的能量释放，大行情开始
    - 经典名言："安静的市场孕育大行情"

    优势：
    - 捕捉波动率爆发后的趋势行情
    - 过滤震荡市场的假突破
    - 结合了波动率和趋势两个维度

    适用场景：
    - 波动率周期性变化的品种
    - 趋势启动前的蓄势阶段

    参数建议：
    - 标准：window=20, n_std=2.0, squeeze_q=0.2（默认，20%分位）
    - 更严格：squeeze_q=0.1（更极端的挤压）
    - 更宽松：squeeze_q=0.3

    Args:
        df: 包含日期和收盘价的 DataFrame
        window: 移动平均线周期，默认 20 天
        n_std: 标准差倍数，默认 2.0
        squeeze_q: 挤压阈值分位数，默认 0.2（20%分位）

    Returns:
        (close, entries, exits) 元组

    Raises:
        ValueError: 当 squeeze_q 不在 (0, 1) 范围内时抛出异常
    """
    if not (0.0 < squeeze_q < 1.0):
        raise ValueError("squeeze_q must be between 0 and 1")

    close = _prepare_close(df)

    # 计算布林带和带宽
    bb = vbt.BBANDS.run(close, window=window, std=n_std)
    bandwidth = (bb.upper - bb.lower) / bb.middle.replace(0.0, pd.NA)

    # 定义挤压：带宽低于历史分位数
    squeeze_th = bandwidth.rolling(window).quantile(squeeze_q)
    squeeze_on = bandwidth <= squeeze_th

    # 挤压后突破上轨入场
    entries = squeeze_on.shift(1).fillna(False) & (close > bb.upper)

    # 跌破中轨出场
    exits = close < bb.middle

    return close, entries, exits


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
    """EMA 斜率调整趋势策略

    策略逻辑：
    1. 构建买入线：快速 EMA
       buy_line = EMA(收盘价, buy_ema)

    2. 构建卖出线：基于价格斜率调整的 EMA
       斜率 = (收盘价 - 收盘价.shift(slope_n)) / slope_n
       斜率调整后的价格 = 斜率 × slope_scale + 收盘价
       sell_line = EMA(斜率调整后的价格, sell_ema)

    3. 基本信号：
       - 入场：买入线从下向上突破卖出线
       - 出场：卖出线从上向下跌破买入线

    4. 可选确认（confirm=True）：
       - 引导线 = EMA(四条 EMA 的平均, guide_ema2)
       - 边界线 = MA(收盘价, boundary_ma)
       - 额外入场条件：引导线 >= 边界线
       - 额外出场条件：边界线突破引导线

    原理：这是对经典双均线策略的改进。
    - 买入线是快速响应的价格线
    - 卖出线是考虑了价格变化率的趋势线（上涨时抬高，下跌时降低）
    - 二次确认用于过滤假信号

    优势：
    - 比传统均线策略更敏感
    - 斜率调整使卖出线能够自适应价格动能
    - 二次确认减少震荡市中的假信号

    参数说明：
    - buy_ema=2：买入线是极快的 EMA（2日）
    - sell_ema=42：卖出线是中期的 EMA（42日）
    - slope_n=21：计算21日斜率（约一个月）
    - slope_scale=20：斜率放大倍数
    - guide_emas=(4,6,12,24)：用于引导线的四条 EMA 周期
    - boundary_ma=27：边界线是27日简单均线
    - confirm=True：开启二次确认

    Args:
        df: 包含日期和收盘价的 DataFrame
        buy_ema: 买入线 EMA 周期，默认 2
        slope_n: 计算斜率的窗口期，默认 21 天
        slope_scale: 斜率放大倍数，默认 20.0
        sell_ema: 卖出线 EMA 周期，默认 42
        confirm: 是否使用二次确认，默认 True
        guide_emas: 引导线的 EMA 周期组合，默认 (4, 6, 12, 24)
        guide_ema2: 引导线的平滑周期，默认 2
        boundary_ma: 边界线 MA 周期，默认 27

    Returns:
        (close, entries, exits) 元组
    """
    close = _prepare_close(df)

    # 构建买入线
    buy_line = vbt.MA.run(close, window=buy_ema, ewm=True).ma

    # 构建卖出线：基于价格斜率调整
    slope = (close - close.shift(slope_n)) / float(slope_n)
    sell_src = slope * float(slope_scale) + close
    sell_line = vbt.MA.run(sell_src, window=sell_ema, ewm=True).ma

    # 基本交叉信号
    bu = buy_line.vbt.crossed_above(sell_line)
    sel = sell_line.vbt.crossed_above(buy_line)

    if not confirm:
        # 不使用二次确认
        entries = bu
        exits = sel
        return close, entries.fillna(False), exits.fillna(False)

    # 二次确认
    e1, e2, e3, e4 = guide_emas
    guide_raw = (
        vbt.MA.run(close, window=e1, ewm=True).ma +
        vbt.MA.run(close, window=e2, ewm=True).ma +
        vbt.MA.run(close, window=e3, ewm=True).ma +
        vbt.MA.run(close, window=e4, ewm=True).ma
    ) / 4.0
    guide = vbt.MA.run(guide_raw, window=guide_ema2, ewm=True).ma
    boundary = vbt.MA.run(close, window=boundary_ma).ma

    # 结合确认条件
    entries = bu & (guide >= boundary)
    exits = sel | boundary.vbt.crossed_above(guide)

    return close, entries.fillna(False), exits.fillna(False)


# ============================================================================
# 策略分发器
# ============================================================================

def dispatch_signals(
    df: pd.DataFrame,
    strategy: str,
    **kwargs,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """趋势策略分发器

    根据策略名称调用对应的信号生成函数。

    支持的策略名称：
    - ma_cross: 双均线交叉
    - timing_ma: 均线择时（指数/ETF）
    - ma_slope: 均线斜率
    - ema_slope_trend: EMA 斜率调整趋势
    - momentum: ROC 动量
    - donchian: 唐奇安通道突破
    - macd: MACD 趋势
    - supertrend: 超级趋势
    - boll_breakout: 布林带突破
    - bb_squeeze: 布林带挤压突破

    Args:
        df: 包含价格数据的 DataFrame
        strategy: 策略名称（字符串）
        **kwargs: 策略参数，根据不同策略传入不同参数

    Returns:
        (close, entries, exits) 元组

    Raises:
        ValueError: 当策略名称不支持时抛出异常

    示例：
        >>> close, entries, exits = dispatch_signals(
        ...     df,
        ...     strategy="ma_cross",
        ...     fast=10,
        ...     slow=30
        ... )
    """
    if strategy == "ma_cross":
        return ma_cross_signals(df, fast=kwargs.get("fast", 10), slow=kwargs.get("slow", 30))
    if strategy == "timing_ma":
        return timing_ma_signals(df, fast=kwargs.get("fast", 20), slow=kwargs.get("slow", 60))
    if strategy == "ma_slope":
        return ma_slope_signals(
            df,
            window=kwargs.get("window", 60),
            slope_window=kwargs.get("slope_window", 5),
            enter_slope=kwargs.get("enter_slope", 0.0),
            exit_slope=kwargs.get("exit_slope", 0.0),
        )
    if strategy == "ema_slope_trend":
        return ema_slope_trend_signals(
            df,
            buy_ema=kwargs.get("buy_ema", 2),
            slope_n=kwargs.get("slope_n", 21),
            slope_scale=kwargs.get("slope_scale", 20.0),
            sell_ema=kwargs.get("sell_ema", 42),
            confirm=kwargs.get("confirm", True),
            guide_emas=kwargs.get("guide_emas", (4, 6, 12, 24)),
            guide_ema2=kwargs.get("guide_ema2", 2),
            boundary_ma=kwargs.get("boundary_ma", 27),
        )
    if strategy == "momentum":
        return momentum_roc_signals(
            df,
            lookback=kwargs.get("lookback", 60),
            enter_th=kwargs.get("enter_th", 0.0),
            exit_th=kwargs.get("exit_th", 0.0),
        )
    if strategy == "donchian":
        return donchian_breakout_signals(
            df,
            entry_n=kwargs.get("entry_n", 20),
            exit_n=kwargs.get("exit_n", 10),
        )
    if strategy == "macd":
        return macd_trend_signals(
            df,
            fast=kwargs.get("fast", 12),
            slow=kwargs.get("slow", 26),
            signal=kwargs.get("signal", 9),
        )
    if strategy == "supertrend":
        return supertrend_signals(
            df,
            atr_window=kwargs.get("atr_window", 10),
            multiplier=kwargs.get("multiplier", 3.0),
        )
    if strategy == "boll_breakout":
        return bollinger_breakout_signals(
            df,
            window=kwargs.get("window", 20),
            n_std=kwargs.get("n_std", 2.0),
        )
    if strategy == "bb_squeeze":
        return bb_squeeze_breakout_signals(
            df,
            window=kwargs.get("window", 20),
            n_std=kwargs.get("n_std", 2.0),
            squeeze_q=kwargs.get("squeeze_q", 0.2),
        )

    raise ValueError(
        f"Unknown strategy: {strategy!r}. "
        f"Supported strategies: ma_cross, timing_ma, ma_slope, ema_slope_trend, "
        f"momentum, donchian, macd, supertrend, boll_breakout, bb_squeeze"
    )


# ============================================================================
# 策略参数优化建议
# ============================================================================

"""
趋势策略参数优化建议：

1. 双均线交叉（ma_cross）
   - 快速交易：fast=5, slow=20（信号多，假信号多）
   - 中期趋势：fast=10, slow=30（平衡）
   - 长期趋势：fast=20, slow=60（信号少，稳健）

2. 均线择时（timing_ma）
   - 指数择时：fast=20, slow=60（默认）
   - 更保守：fast=20, slow=120（减少交易频率）
   - 更激进：fast=10, slow=40（更快响应）

3. MACD（macd）
   - 标准参数：fast=12, slow=26, signal=9（推荐）
   - 短期：fast=6, slow=13, signal=5
   - 长期：fast=24, slow=52, signal=18

4. 唐奇安通道（donchian）
   - 标准海龟：entry_n=20, exit_n=10（推荐）
   - 更保守：entry_n=40, exit_n=20
   - 更激进：entry_n=10, exit_n=5

5. SuperTrend（supertrend）
   - 标准：atr_window=10, multiplier=3.0（推荐）
   - 更灵敏：atr_window=7, multiplier=2.0
   - 更稳健：atr_window=14, multiplier=4.0

6. 布林带突破（boll_breakout）
   - 标准：window=20, n_std=2.0（推荐）
   - 更紧凑：window=10, n_std=1.5
   - 更宽松：window=30, n_std=2.5

7. 布林带挤压（bb_squeeze）
   - 标准：window=20, n_std=2.0, squeeze_q=0.2（推荐）
   - 更严格：squeeze_q=0.1（等待更极端的挤压）
   - 更宽松：squeeze_q=0.3（更容易触发）

8. 动量策略（momentum）
   - 中期：lookback=60, enter_th=0.05（推荐）
   - 短期：lookback=20, enter_th=0.03
   - 长期：lookback=120, enter_th=0.10

优化建议：
- 使用回测框架测试不同参数组合
- 考虑市场特性（波动率、流动性）
- 平衡交易频率和胜率
- 注意过拟合风险
"""
