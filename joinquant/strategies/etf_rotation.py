# -*- coding: utf-8 -*-
"""
ETF 多品种动量轮动策略 v3
==========================
v1 问题：没有熊市保护，2015/2018 大跌时仍在权益 ETF 之间轮动，最大回撤 47.75%。
v2 问题：绝对动量要求（MA过滤 + 正动量）双重限制过严，策略始终持有国债，从未入场。

v3 核心修正：
  - MA 过滤已经隐含趋势判断（价格 > MA60 = 中期向上），不再额外要求正动量
  - 动量只用于排名，不用于"能否买入"的判断
  - 没有任何权益 ETF 通过 MA 过滤 → 全仓债券（熊市保护保留）
  - 有权益 ETF 通过 MA 过滤 → 按动量选 Top-K 等权持有

策略逻辑：
  每月调仓，从权益池中筛选价格在 MA60 上方的 ETF，
  按 20 日动量排名取前 K 名等权持有；
  若无权益 ETF 上穿 MA60，则全仓切入国债 ETF 防御。

ETF 池：
    510300.XSHG  沪深300ETF   大盘价值
    510500.XSHG  中证500ETF   中盘成长
    159915.XSHE  创业板ETF    小盘成长
    512880.XSHG  证券ETF      金融弹性（2013年上市，回测不早于2014年）
    511010.XSHG  国债ETF      熊市防御仓（仅在无权益 ETF 合格时持有）

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

    g.equity_pool    = [
        '510300.XSHG',  # 沪深300ETF
        '510500.XSHG',  # 中证500ETF
        '159915.XSHE',  # 创业板ETF
        '512880.XSHG',  # 证券ETF
    ]
    g.safe_etf       = '511010.XSHG'  # 国债ETF：无权益 ETF 合格时的防御仓
    g.momentum_days  = 20             # 动量排名周期（短期，用于相对强弱比较）
    g.ma_filter_days = 60             # 趋势过滤均线（中期，决定能否入场）
    g.top_k          = 2              # 每月持有权益 ETF 数量

    run_monthly(rebalance, monthday=1, time='open')


def _calc_momentum(security, mom_days, ma_days):
    """
    计算动量并做均线趋势过滤。
    价格 < MA → 返回 None（不参与排名）。
    价格 >= MA → 返回 mom_days 日收益率（可正可负，仅用于排名）。
    """
    need = max(mom_days, ma_days) + 2
    prices = attribute_history(security, need, '1d', ['close'])
    if prices is None or len(prices) < max(mom_days, ma_days) + 1:
        return None
    close = prices['close']
    current = close.iloc[-1]

    # 趋势过滤：价格须在 MA 上方才可入场
    ma = close.iloc[-ma_days:].mean()
    if current < ma:
        return None

    # 动量得分（仅排名用，不作入场门槛）
    past = close.iloc[-(mom_days + 1)]
    if past <= 0:
        return None
    return (current / past) - 1.0


def rebalance(context):
    """
    月度调仓：
      1. 计算各权益 ETF 动量（含 MA 过滤）
      2. 无合格 ETF → 全仓国债（熊市防御）
      3. 有合格 ETF → 按动量取 Top-K，等权持有
    """
    scores = {}
    for etf in g.equity_pool:
        m = _calc_momentum(etf, g.momentum_days, g.ma_filter_days)
        if m is not None:
            scores[etf] = m

    # 熊市防御：无权益 ETF 在均线上方 → 全仓国债
    if not scores:
        target_etfs = [g.safe_etf]
        log.info('[防御] 无权益ETF通过MA过滤，切换至国债ETF')
    else:
        # 按动量降序，取 Top-K（动量值可正可负，只比较相对强弱）
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        target_etfs = [etf for etf, _ in ranked[:g.top_k]]
        log.info('持仓: {}  动量得分: {}'.format(
            target_etfs,
            {etf: round(m, 4) for etf, m in ranked[:g.top_k]}
        ))

    # 先平掉不在目标列表的持仓，再买入目标
    for etf in list(context.portfolio.positions.keys()):
        if etf not in target_etfs:
            order_target(etf, 0)

    weight = 0.95 / len(target_etfs)
    total_value = context.portfolio.portfolio_value
    for etf in target_etfs:
        order_target_value(etf, total_value * weight)
