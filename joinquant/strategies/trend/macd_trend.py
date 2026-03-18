# -*- coding: utf-8 -*-
"""
MACD 趋势交易策略（趋势状态机版）
================================

目标：把 MACD 当作“趋势是否向上”的状态，而不是只在金叉/死叉当日交易。

默认逻辑（推荐）：
  - 入场/持有（多头趋势）：
      DIF > DEA 且 柱状图 MACD_BAR >= min_hist
  - 离场（空头/趋势结束）：
      DIF < DEA 或  柱状图 MACD_BAR <  min_hist_exit

这样做的好处：
  - 在红柱/多头状态持续期间保持持仓，提高 beta；
  - 避免只靠“交叉那一天”的触发导致踏空。

标的：默认 510300.XSHG（沪深300ETF，可改）
频率：日频开盘执行。
"""


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001,
                  open_commission=0.0003, close_commission=0.0003,
                  min_commission=5),
        type='stock'
    )

    g.security = '000300.XSHG'

    # MACD 参数（默认经典 12/26/9）
    g.fast = 12
    g.slow = 26
    g.signal = 9

    # 趋势判定阈值
    g.min_hist = 0.0           # 多头至少柱状图 >= 0
    g.min_hist_exit = 0.0     # 离场阈值（可设成 -0.0~0.0 来增加鲁棒性）

    # 资金使用比例
    g.order_pct = 0.95

    run_daily(rebalance, time='open')


def calc_ema(series, n):
    return series.ewm(span=n, adjust=False).mean()


def get_macd(close, fast=12, slow=26, signal=9):
    """
    返回：
      dif, dea, macd_bar
    其中 macd_bar = (dif - dea) * 2（与常见柱状图定义一致）
    """
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    dif = ema_fast - ema_slow
    dea = calc_ema(dif, signal)
    macd_bar = (dif - dea) * 2
    return dif, dea, macd_bar


def rebalance(context):
    sec = g.security
    need = g.slow + g.signal + 10
    prices = attribute_history(sec, need, '1d', ['close'])
    if prices is None or len(prices) < need:
        return

    close = prices['close']
    dif, dea, bar = get_macd(close, g.fast, g.slow, g.signal)

    d_now = dif.iloc[-1]
    e_now = dea.iloc[-1]
    b_now = bar.iloc[-1]

    position = context.portfolio.positions.get(sec)
    has_pos = position is not None and position.total_amount > 0

    # --- 趋势状态机 ---
    bullish = (d_now > e_now) and (b_now >= g.min_hist)
    bearish = (d_now < e_now) or (b_now < g.min_hist_exit)

    # 入场/持有
    if bullish:
        if not has_pos:
            order_target_value(sec, context.portfolio.available_cash * g.order_pct)
        return

    # 离场
    if bearish and has_pos:
        order_target(sec, 0)
        return

