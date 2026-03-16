# -*- coding: utf-8 -*-
"""
ETF 多品种动量轮动策略 v2（加入绝对动量保护）
========================================
核心改进（相比 v1）：
  1. 绝对动量保护：若权益 ETF 的最高动量仍为负，全仓切至国债ETF（熊市逃顶）
  2. 动量回看期延长至 60 日（减少噪声，更适合月度调仓）
  3. 均线过滤保留 60 日（只有在均线上方的 ETF 才参与竞选）

策略逻辑：
  相对动量：选池内动量最高的 Top-K ETF
  绝对动量：若入选的权益 ETF 动量均 <= 0，视为市场整体下跌，全切国债ETF

ETF 池：
    510300.XSHG  沪深300ETF   大盘价值
    510500.XSHG  中证500ETF   中盘成长
    159915.XSHE  创业板ETF    小盘成长
    512880.XSHG  证券ETF      金融弹性（2013年上市，回测不早于2014年）
    511010.XSHG  国债ETF      避险资产（绝对动量触发时的避风港）

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

    # 权益 ETF 池（不含国债，国债作为独立避险仓）
    g.equity_pool = [
        '510300.XSHG',  # 沪深300ETF
        '510500.XSHG',  # 中证500ETF
        '159915.XSHE',  # 创业板ETF
        '512880.XSHG',  # 证券ETF
    ]
    g.safe_etf       = '511010.XSHG'  # 国债ETF：绝对动量保护时全仓切入
    g.momentum_days  = 60             # 动量回看周期（交易日）；60日=约3个月
    g.ma_filter_days = 60             # 均线过滤周期
    g.top_k          = 2              # 每月持有权益 ETF 数量

    run_monthly(rebalance, monthday=1, time='open')


def _calc_momentum(security, mom_days, ma_days):
    """
    计算动量值（过去 mom_days 日收益率）并做均线过滤。
    价格在均线下方 -> 返回 None（不参与选拔）。
    """
    need = max(mom_days, ma_days) + 2
    prices = attribute_history(security, need, '1d', ['close'])
    if prices is None or len(prices) < max(mom_days, ma_days) + 1:
        return None
    close = prices['close']
    current = close.iloc[-1]
    ma = close.iloc[-ma_days:].mean()

    # 均线过滤
    if current < ma:
        return None

    past = close.iloc[-(mom_days + 1)]
    if past <= 0:
        return None
    return (current / past) - 1.0


def rebalance(context):
    """
    月度调仓逻辑：
      1. 计算权益 ETF 池各标的动量（含均线过滤）
      2. 按相对动量选 Top-K
      3. 绝对动量检查：若所有候选动量 <= 0，全切国债ETF
      4. 否则等权持有 Top-K 权益ETF
    """
    # --- 1. 计算各权益 ETF 动量 ---
    scores = {}
    for etf in g.equity_pool:
        m = _calc_momentum(etf, g.momentum_days, g.ma_filter_days)
        if m is not None:
            scores[etf] = m

    # 按动量降序排名，选 Top-K
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    candidates = ranked[:g.top_k]  # [(etf, momentum), ...]

    # --- 2. 绝对动量保护 ---
    # 所有候选 ETF 动量均 <= 0（或根本没有候选），视为熊市，全切国债
    all_negative = (len(candidates) == 0 or all(m <= 0 for _, m in candidates))

    if all_negative:
        # 全仓切至国债 ETF
        target_etfs = [g.safe_etf]
        log.info('[绝对动量触发] 权益ETF动量全负，切换至国债ETF')
    else:
        # 只保留动量为正的候选（正动量才值得持有）
        target_etfs = [etf for etf, m in candidates if m > 0]
        if not target_etfs:
            target_etfs = [g.safe_etf]

    # --- 3. 调仓 ---
    # 先平掉不在目标列表的持仓
    for etf in list(context.portfolio.positions.keys()):
        if etf not in target_etfs:
            order_target(etf, 0)

    # 等权买入目标 ETF
    weight = 0.95 / len(target_etfs)
    total_value = context.portfolio.portfolio_value
    for etf in target_etfs:
        order_target_value(etf, total_value * weight)

    log.info('本月持仓: {}  动量得分: {}'.format(
        target_etfs,
        {etf: round(m, 4) for etf, m in ranked[:g.top_k]}
    ))
