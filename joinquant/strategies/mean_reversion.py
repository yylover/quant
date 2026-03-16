# -*- coding: utf-8 -*-
"""
均值回归策略 (Mean Reversion)
价格偏离均线超过 k 倍标准差时认为超买/超卖：向下偏离买入，向上偏离卖出。
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
    g.window = 20      # 均线周期
    g.num_std = 2.0    # 触发阈值：偏离均线 k 倍标准差
    g.revert_ratio = 0.5  # 回归到均线附近（偏离缩小到 0.5 倍标准差内）可平仓
    run_daily(rebalance, time='open')


def rebalance(context):
    """每日调仓"""
    need = g.window + 2
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < g.window:
        return
    close = prices['close']
    current = close.iloc[-1]
    ma = close.iloc[-g.window:].mean()
    std = close.iloc[-g.window:].std()
    if std is None or std <= 0:
        return
    # 当前偏离（正数=高于均线，负数=低于均线）
    z = (current - ma) / std

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：价格低于均线超过 k 倍标准差 -> 买入
    oversold = z <= -g.num_std
    # 超买：价格高于均线超过 k 倍标准差 -> 卖出
    overbought = z >= g.num_std
    # 回归：偏离回到阈值内可平多
    reverted = abs(z) <= g.revert_ratio * g.num_std

    if oversold and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)
    elif (overbought or (hold_amount > 0 and reverted)):
        if hold_amount > 0:
            order_target(g.security, 0)
