# -*- coding: utf-8 -*-
"""
动量策略 (Momentum)
根据过去 N 日收益率排序，买入强势标的、卖出弱势标的。
单标的版本：价格相对自身均线动量，突破则买入/跌破则卖出。
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
    g.lookback = 20   # 动量 lookback 天数
    g.ma_window = 10  # 均线过滤：价格在均线上方才做多
    run_daily(rebalance, time='open')


def rebalance(context):
    """每日调仓：动量 = 当前价 / N日前价 - 1，配合均线过滤"""
    prices = attribute_history(g.security, g.lookback + g.ma_window + 1, '1d', ['close'])
    if prices is None or len(prices) < g.lookback + g.ma_window:
        return
    close = prices['close']
    current = close.iloc[-1]
    past = close.iloc[-(g.lookback + 1)]
    momentum = (current / past) - 1.0 if past > 0 else 0
    ma = close.iloc[-g.ma_window:].mean()

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 动量为正且价格在均线上方 -> 做多
    if momentum > 0 and current > ma:
        if hold_amount <= 0:
            order_target_value(g.security, context.portfolio.available_cash * 0.95)
    # 动量转负或价格跌破均线 -> 平仓
    elif momentum <= 0 or current < ma:
        if hold_amount > 0:
            order_target(g.security, 0)
