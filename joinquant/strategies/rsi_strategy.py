# -*- coding: utf-8 -*-
"""
RSI 策略 (Relative Strength Index)
RSI < 超卖线 买入，RSI > 超买线 卖出。
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
    g.period = 14   # RSI 周期
    g.oversold = 30  # 超卖阈值，低于此值考虑买入
    g.overbought = 70  # 超买阈值，高于此值考虑卖出
    run_daily(rebalance, time='open')


def calc_rsi(close_series, period=14):
    """计算 RSI：RS = 平均涨幅/平均跌幅, RSI = 100 - 100/(1+RS)"""
    delta = close_series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rs = rs.replace([float('inf'), -float('inf')], 0).fillna(0)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def rebalance(context):
    """每日调仓"""
    need = g.period + 2
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < need:
        return
    close = prices['close']
    rsi_series = calc_rsi(close, g.period)
    rsi = rsi_series.iloc[-1]
    if rsi is None or (rsi != rsi):  # NaN check
        return

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    if rsi < g.oversold:
        if hold_amount <= 0:
            order_target_value(g.security, context.portfolio.available_cash * 0.95)
    elif rsi > g.overbought:
        if hold_amount > 0:
            order_target(g.security, 0)
