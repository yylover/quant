# -*- coding: utf-8 -*-
"""
股债切换策略
用双均线判断沪深300ETF趋势：
  - 价格 > 短期均线 且 短期均线 > 长期均线（多头排列）-> 满仓股票ETF
  - 否则（空头或震荡）-> 满仓债券ETF

双均线过滤比单均线少很多假信号，适合趋势不明显的震荡市。

交易标的：
    510300.XSHG  沪深300ETF（权益）
    511010.XSHG  国债ETF（债券，下跌市避险）

适用于聚宽 JoinQuant 平台回测。
"""


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003,
                  close_commission=0.0003, min_commission=5),
        type='stock'
    )

    g.stock_etf = '510300.XSHG'  # 权益资产
    g.bond_etf  = '511010.XSHG'  # 债券资产
    g.ma_short  = 20              # 短期均线（快线）
    g.ma_long   = 60              # 长期均线（慢线）
    # 防止频繁来回切换：当前持仓方向
    g.current_side = None         # 'stock' / 'bond' / None

    run_daily(rebalance, time='open')


def _calc_trend(context):
    """
    返回 'stock'（股票趋势向上）或 'bond'（趋势向下/震荡）。
    判据：当日价格 > 短均线 且 短均线 > 长均线。
    """
    need = g.ma_long + 2
    prices = attribute_history(g.stock_etf, need, '1d', ['close'])
    if prices is None or len(prices) < g.ma_long + 1:
        return None
    close = prices['close']
    current   = close.iloc[-1]
    ma_short  = close.iloc[-g.ma_short:].mean()
    ma_long   = close.iloc[-g.ma_long:].mean()

    if current > ma_short and ma_short > ma_long:
        return 'stock'
    return 'bond'


def rebalance(context):
    side = _calc_trend(context)
    if side is None:
        return
    # 信号未变化，不操作（减少无效换手）
    if side == g.current_side:
        return

    total = context.portfolio.portfolio_value

    if side == 'stock':
        # 先卖债券，再买股票
        if context.portfolio.positions.get(g.bond_etf):
            order_target(g.bond_etf, 0)
        order_target_value(g.stock_etf, total * 0.95)
    else:
        # 先卖股票，再买债券
        if context.portfolio.positions.get(g.stock_etf):
            order_target(g.stock_etf, 0)
        order_target_value(g.bond_etf, total * 0.95)

    g.current_side = side
