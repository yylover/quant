# -*- coding: utf-8 -*-
"""
突破策略 (Breakout)
价格突破 N 日最高价时买入，跌破 N 日最低价（或 M 日移动止损）时卖出。
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
    g.breakout_days = 20   # 突破周期：突破 N 日新高买入
    g.exit_days = 10       # 出场：跌破 N 日新低卖出（0 表示用移动止损）
    g.trailing_stop_pct = 0.05  # 移动止损：从最高点回撤 5% 卖出（当 exit_days=0 时可用）
    run_daily(rebalance, time='open')


def rebalance(context):
    """每日调仓"""
    need = max(g.breakout_days, g.exit_days or 1) + 2
    prices = attribute_history(g.security, need, '1d', ['high', 'low', 'close'])
    if prices is None or len(prices) < need:
        return
    high = prices['high']
    low = prices['low']
    close = prices['close']
    current = close.iloc[-1]
    # 前 N 日最高/最低（不含当日）
    prev_high = high.iloc[-g.breakout_days - 1:-1].max()
    prev_low = low.iloc[-g.exit_days - 1:-1].min() if g.exit_days > 0 else None

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 记录持仓期间最高价（用于移动止损）
    if hold_amount > 0:
        if not hasattr(g, 'highest_since_entry'):
            g.highest_since_entry = current
        g.highest_since_entry = max(g.highest_since_entry, current)
    else:
        g.highest_since_entry = None

    # 突破：当日收盘价 > 前 N 日最高价
    breakout_buy = current > prev_high
    # 出场：跌破 N 日新低 或 移动止损
    if g.exit_days > 0:
        exit_signal = current < prev_low
    else:
        exit_signal = g.highest_since_entry and current < g.highest_since_entry * (1 - g.trailing_stop_pct)

    if breakout_buy and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)
    elif exit_signal and hold_amount > 0:
        order_target(g.security, 0)
