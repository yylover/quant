# -*- coding: utf-8 -*-
"""
MACD 策略 (Moving Average Convergence Divergence)
DIF 上穿 DEA 且柱状图由负转正时买入，下穿时卖出。可选：柱状图过滤（红柱才持有多头）。
适用于聚宽 JoinQuant 平台回测。
"""


def initialize(context):
    """初始化"""
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock'
    )
    g.security = '510300.XSHG'
    g.fast = 12   # 快线周期
    g.slow = 26   # 慢线周期
    g.signal = 9  # 信号线周期
    run_daily(rebalance, time='open')


def calc_ema(series, n):
    """指数移动平均"""
    return series.ewm(span=n, adjust=False).mean()


def get_macd(close, fast=12, slow=26, signal=9):
    """计算 DIF, DEA, MACD 柱"""
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    dif = ema_fast - ema_slow
    dea = calc_ema(dif, signal)
    macd_bar = (dif - dea) * 2  # 柱状图
    return dif, dea, macd_bar


def rebalance(context):
    """每日调仓"""
    need = g.slow + g.signal + 5
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < need:
        return
    close = prices['close']
    dif, dea, bar = get_macd(close, g.fast, g.slow, g.signal)

    d_now, d_prev = dif.iloc[-1], dif.iloc[-2]
    e_now, e_prev = dea.iloc[-1], dea.iloc[-2]
    b_now, b_prev = bar.iloc[-1], bar.iloc[-2]

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 金叉：DIF 上穿 DEA（前一日 DIF<=DEA，当日 DIF>DEA）
    golden = (d_prev <= e_prev) and (d_now > e_now)
    # 死叉：DIF 下穿 DEA
    death = (d_prev >= e_prev) and (d_now < e_now)

    if golden and b_now >= 0:
        if hold_amount <= 0:
            order_target_value(g.security, context.portfolio.available_cash * 0.95)
    elif death or b_now < 0:
        if hold_amount > 0:
            order_target(g.security, 0)
