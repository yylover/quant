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
    # MACD 柱状图阈值：用“上穿/下穿”而不是只看当前值
    # 目的：减少在 0 附近反复波动导致的来回切换
    g.min_hist = 0.0           # 多头入场：柱状图从 <= 该值 上穿
    g.min_hist_exit = 0.0     # 离场：柱状图从 >= 该值 下穿

    # 只有在 DIF 上穿 DEA 且柱状图上穿时入场（更贴近趋势启动）
    g.require_dif_cross_for_entry = True

    # 离场：DIF 死叉 或 柱状图下穿（两者满足任一即可）
    g.exit_on_death_or_hist_cross = True

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

    d_prev, d_now = dif.iloc[-2], dif.iloc[-1]
    e_prev, e_now = dea.iloc[-2], dea.iloc[-1]
    b_prev, b_now = bar.iloc[-2], bar.iloc[-1]

    position = context.portfolio.positions.get(sec)
    has_pos = position is not None and position.total_amount > 0

    # --- 趋势状态机（触发用交叉，持有用状态） ---
    dif_up = d_now > e_now
    dif_down = d_now < e_now

    hist_cross_up = (b_prev <= g.min_hist) and (b_now > g.min_hist)
    hist_cross_down = (b_prev >= g.min_hist_exit) and (b_now < g.min_hist_exit)

    golden = (d_prev <= e_prev) and (d_now > e_now)   # DIF 上穿 DEA
    death = (d_prev >= e_prev) and (d_now < e_now)    # DIF 下穿 DEA

    # 入场：优先使用“趋势启动”条件，降低噪声切换
    if not has_pos:
        if g.require_dif_cross_for_entry:
            if golden and hist_cross_up:
                order_target_value(sec, context.portfolio.available_cash * g.order_pct)
        else:
            if dif_up and b_now >= g.min_hist:
                order_target_value(sec, context.portfolio.available_cash * g.order_pct)
        return

    # 离场：DIF 死叉 或 柱状图下穿（择一即可）
    if g.exit_on_death_or_hist_cross:
        if death or hist_cross_down:
            order_target(sec, 0)
            return

    # 保底：若不满足离场开关，则用更宽松条件维持趋势
    if dif_down or (b_now < g.min_hist_exit):
        order_target(sec, 0)
        return

