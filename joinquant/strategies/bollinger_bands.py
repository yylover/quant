# -*- coding: utf-8 -*-
"""
布林带策略 (Bollinger Bands)
价格触及下轨做多，触及上轨减仓/平仓；或突破上轨做多（趋势）、跌破下轨平仓。
此处采用：下轨附近买入，上轨附近卖出。
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
    g.window = 20   # 均线/标准差周期
    g.num_std = 2.0  # 上下轨标准差倍数
    run_daily(rebalance, time='open')


def rebalance(context):
    """每日调仓：中轨=MA，上轨=中轨+k*std，下轨=中轨-k*std"""
    prices = attribute_history(g.security, g.window + 1, '1d', ['close'])
    if prices is None or len(prices) < g.window:
        return
    close = prices['close']
    mid = close.iloc[-g.window:].mean()
    std = close.iloc[-g.window:].std()
    if std is None or std <= 0:
        return
    upper = mid + g.num_std * std
    lower = mid - g.num_std * std
    current = close.iloc[-1]

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 价格接近或跌破下轨 -> 买入
    if current <= lower * 1.01:
        if hold_amount <= 0:
            order_target_value(g.security, context.portfolio.available_cash * 0.95)
    # 价格接近或突破上轨 -> 卖出
    elif current >= upper * 0.99:
        if hold_amount > 0:
            order_target(g.security, 0)
