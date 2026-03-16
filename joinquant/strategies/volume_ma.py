# -*- coding: utf-8 -*-
"""
量价策略 (Volume + MA)
放量突破均线时买入：成交量大于近期均量且价格上穿均线。缩量跌破均线或放量滞涨时减仓。
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
    g.ma_period = 20      # 价格均线周期
    g.vol_period = 5      # 量能均线周期
    g.vol_ratio = 1.2     # 放量倍数：当日量 > 均量 * vol_ratio 才确认
    run_daily(rebalance, time='open')


def rebalance(context):
    """每日调仓"""
    need = max(g.ma_period, g.vol_period) + 2
    df = attribute_history(g.security, need, '1d', ['close', 'volume'])
    if df is None or len(df) < need:
        return
    close = df['close']
    volume = df['volume']
    current_price = close.iloc[-1]
    prev_price = close.iloc[-2]
    ma = close.iloc[-g.ma_period - 1:-1].mean()
    prev_ma = close.iloc[-g.ma_period - 2:-2].mean()
    vol_ma = volume.iloc[-g.vol_period - 1:-1].mean()
    current_vol = volume.iloc[-1]

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 放量：当日成交量 > 近期均量 * vol_ratio
    volume_ok = current_vol >= vol_ma * g.vol_ratio
    # 突破：前一日在均线下方，当日收盘站上均线
    break_up = prev_price <= prev_ma and current_price > ma
    # 跌破：价格跌破均线
    break_down = current_price < ma

    if volume_ok and break_up and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)
    elif break_down and hold_amount > 0:
        order_target(g.security, 0)
