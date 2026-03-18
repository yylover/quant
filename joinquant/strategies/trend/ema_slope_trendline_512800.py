# -*- coding: utf-8 -*-
"""
买卖线（EMA + SLOPE 修正）交易策略 - JoinQuant 实现版
======================================================

公式来源（按你提供的逻辑翻译）：

买线 := EMA(C, 2)
卖线 := EMA(SLOPE(C, 21) * 20 + C, 42)

主信号：
  BU  := CROSS(买线, 卖线)   # 金叉买入
  SEL := CROSS(卖线, 买线)   # 死叉卖出

辅助确认：
  指导线 := EMA((EMA(C,4)+EMA(C,6)+EMA(C,12)+EMA(C,24))/4, 2)
  界     := MA(C, 27)

默认交易规则（贴合“红柱/绿柱”持仓逻辑 + 二次确认）：
  - 多头区间：买线 >= 卖线（红柱）→ 持有/买入
  - 空头区间：买线 <  卖线（绿柱）→ 空仓/卖出
  - 二次确认（可选）：只在确认同向时才执行换仓
    - 多头确认：指导线 >= 界
    - 空头确认：指导线 <  界

重要说明（SLOPE 口径差异）：
  不同平台对 SLOPE(C, N) 的定义可能不同。此实现提供两种常见口径可选：
    - 'linreg'：最近 N 根做线性回归，取斜率
    - 'diff'  ：(C - REF(C, N-1)) / (N-1) 的差分斜率
  你可以通过 g.slope_method 切换，以匹配你原指标平台的表现。

标的：默认 512800.XSHG（可修改 g.security）
频率：日频开盘执行（用昨日收盘数据生成信号）
"""


import numpy as np


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001,
                  open_commission=0.0003, close_commission=0.0003,
                  min_commission=5),
        type='stock'
    )

    # -------- 交易标的（默认单 ETF）--------
    # g.security = '512800.XSHG'
    g.security = '000300.XSHG'

    # -------- 参数（与公式一致）--------
    g.buy_ema_n = 2
    g.slope_n = 21
    g.slope_mult = 20.0
    g.sell_ema_n = 42
    # SLOPE 计算口径：'linreg' 或 'diff'
    g.slope_method = 'linreg'

    g.guide_emas = (4, 6, 12, 24)
    g.guide_smooth_n = 2
    g.boundary_ma_n = 27

    # 二次确认开关：True = 换仓需满足“指导线/界”同向确认
    g.use_confirm = False

    run_daily(rebalance, time='open')


def _ema(series, n):
    # JoinQuant 环境为 pandas Series，使用 ewm 计算 EMA
    return series.ewm(span=n, adjust=False).mean()


def _ma(series, n):
    return series.rolling(n, min_periods=n).mean()


def _rolling_slope(series, n):
    """
    计算 SLOPE(C, n)：用最近 n 个点做线性回归，取斜率。
    返回与 series 等长的序列（前 n-1 位为 NaN）。
    """
    y = series.values.astype(float)
    out = np.full_like(y, fill_value=np.nan, dtype=float)
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_demean = x - x_mean
    denom = np.sum(x_demean ** 2)
    if denom <= 0:
        return series * np.nan

    for i in range(n - 1, len(y)):
        window = y[i - n + 1:i + 1]
        y_mean = window.mean()
        slope = np.sum((window - y_mean) * x_demean) / denom
        out[i] = slope

    # 保持 pandas 索引
    return series.__class__(out, index=series.index)


def _diff_slope(series, n):
    """
    差分斜率口径： (C - REF(C, n-1)) / (n-1)
    与部分指标平台的 SLOPE 更接近（非回归）。
    """
    if n <= 1:
        return series * np.nan
    return (series - series.shift(n - 1)) / float(n - 1)


def _cross(up, down):
    """
    CROSS(up, down)：上一根 up<=down 且 当前 up>down
    up/down 为标量或长度>=2的序列；此处仅使用最后两根。
    """
    return up.iloc[-2] <= down.iloc[-2] and up.iloc[-1] > down.iloc[-1]


def _calc_lines(close):
    # 买线
    buy_line = _ema(close, g.buy_ema_n)

    # 卖线：EMA(SLOPE(C,21)*20 + C, 42)
    if g.slope_method == 'diff':
        slope21 = _diff_slope(close, g.slope_n)
    else:
        slope21 = _rolling_slope(close, g.slope_n)
    sell_raw = slope21 * g.slope_mult + close
    sell_line = _ema(sell_raw, g.sell_ema_n)

    # 指导线：EMA((EMA4+EMA6+EMA12+EMA24)/4, 2)
    ema_sum = None
    for n in g.guide_emas:
        e = _ema(close, n)
        ema_sum = e if ema_sum is None else (ema_sum + e)
    guide_line = _ema(ema_sum / float(len(g.guide_emas)), g.guide_smooth_n)

    # 界：MA(C,27)
    boundary = _ma(close, g.boundary_ma_n)

    return buy_line, sell_line, guide_line, boundary


def rebalance(context):
    # 需要的历史长度：sell_ema(42) + slope(21) + boundary(27) + 余量
    need = max(g.sell_ema_n + g.slope_n, g.boundary_ma_n, max(g.guide_emas)) + 10
    df = attribute_history(g.security, need, '1d', ['close'])
    if df is None or len(df) < need:
        return

    close = df['close']

    buy_line, sell_line, guide_line, boundary = _calc_lines(close)

    # 指标末端若仍为 NaN（数据不足），直接退出
    if np.isnan(buy_line.iloc[-1]) or np.isnan(sell_line.iloc[-1]) or np.isnan(guide_line.iloc[-1]) or np.isnan(boundary.iloc[-1]):
        return

    bu = _cross(buy_line, sell_line)      # 金叉提示
    sel = _cross(sell_line, buy_line)     # 死叉提示

    confirm_long = (guide_line.iloc[-1] >= boundary.iloc[-1])
    confirm_short = (guide_line.iloc[-1] < boundary.iloc[-1])

    position = context.portfolio.positions.get(g.security)
    has_pos = position is not None and position.total_amount > 0

    bull = buy_line.iloc[-1] >= sell_line.iloc[-1]
    bear = not bull

    # --- 多头区间：持有 / 买入 ---
    if bull and (not g.use_confirm or confirm_long):
        if not has_pos:
            order_target_value(g.security, context.portfolio.available_cash * 0.95)
            log.info('[买入] {} 红柱区间（买线>=卖线）；BU={} 确认={}'.format(
                g.security, bu, confirm_long))
        return

    # --- 空头区间：空仓 / 卖出 ---
    if bear and (not g.use_confirm or confirm_short):
        if has_pos:
            order_target(g.security, 0)
            log.info('[卖出] {} 绿柱区间（买线<卖线）；SEL={} 确认={}'.format(
                g.security, sel, confirm_short))
        return

