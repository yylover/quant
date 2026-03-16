# -*- coding: utf-8 -*-
"""
双均线策略 (MA Crossover)
当短期均线上穿长期均线时买入，下穿时卖出。
适用于聚宽 JoinQuant 平台回测。
"""


def initialize(context):
    """初始化：设置基准、标的、均线周期与交易参数"""
    # 设置基准
    set_benchmark('000300.XSHG')
    # 用真实价格交易（避免未来数据）
    set_option('use_real_price', True)
    # 设置滑点与手续费
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock'
    )
    # 策略参数
    g.security = '510300.XSHG'  # 沪深300ETF，可改为 000300.XSHG 仅作基准时用指数
    g.short_window = 5   # 短期均线周期
    g.long_window = 20  # 长期均线周期
    g.threshold = 0.01  # 上穿需超过长期均线 1% 才开仓，减少假信号
    # 定时每日开盘后执行
    run_daily(rebalance, time='open')


def rebalance(context):
    """每日调仓逻辑"""
    # 获取历史收盘价
    prices = attribute_history(g.security, g.long_window + 1, '1d', ['close'])
    if prices is None or len(prices) < g.long_window + 1:
        return
    close = prices['close']
    short_ma = close.iloc[-g.short_window:].mean()
    long_ma = close.iloc[-g.long_window:].mean()
    prev_short = close.iloc[-(g.short_window + 1):-1].mean()
    prev_long = close.iloc[-(g.long_window + 1):-1].mean()

    # 当前持仓
    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 金叉：短期上穿长期，且短期 > 长期 * (1 + threshold)
    if prev_short <= prev_long and short_ma > long_ma * (1 + g.threshold):
        if hold_amount <= 0:
            order_target_value(g.security, context.portfolio.available_cash * 0.95)
    # 死叉：短期下穿长期
    elif prev_short >= prev_long and short_ma < long_ma:
        if hold_amount > 0:
            order_target(g.security, 0)
