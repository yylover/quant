# -*- coding: utf-8 -*-
"""
PE 估值择时策略
每月计算沪深300指数成分股的市值加权PE，与历史PE分位数比较，动态调整仓位：
    PE分位数 <= 20%（极度低估）-> 95% 满仓
    PE分位数 <= 40%（低估）    -> 75% 重仓
    PE分位数 <= 60%（合理）    -> 50% 半仓
    PE分位数 <= 80%（偏贵）    -> 25% 轻仓
    PE分位数 >  80%（高估）    ->  0% 空仓

数据不足24个月时采用绝对阈值兜底（见 _get_position_ratio）。

交易标的：
    510300.XSHG  沪深300ETF
    PE计算来源：000300.XSHG 成分股 get_fundamentals

适用于聚宽 JoinQuant 平台回测。
"""

from jqdata import *


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003,
                  close_commission=0.0003, min_commission=5),
        type='stock'
    )

    g.index    = '000300.XSHG'  # PE 来源指数
    g.etf      = '510300.XSHG'  # 实际交易标的
    g.pe_history = []            # 滚动存储历史月度 PE
    g.pe_window  = 60            # 分位数回看窗口（月），约 5 年

    # 每月第一个交易日调仓
    run_monthly(rebalance, monthday=1, time='open')


def _get_index_pe(index_code, date):
    """
    获取指数市值加权 PE。
    返回 float 或 None（数据异常时）。
    """
    stocks = get_index_stocks(index_code, date=date)
    if not stocks:
        return None

    q = query(
        valuation.code,
        valuation.pe_ratio,
        valuation.market_cap
    ).filter(
        valuation.code.in_(stocks),
        valuation.pe_ratio > 0,
        valuation.pe_ratio < 500      # 过滤极端值（亏损股/重组股）
    )
    df = get_fundamentals(q, date=date)
    if df is None or len(df) == 0:
        return None

    total_mcap = df['market_cap'].sum()
    if total_mcap <= 0:
        return None

    weighted_pe = (df['pe_ratio'] * df['market_cap']).sum() / total_mcap
    return float(weighted_pe)


def _get_position_ratio(pe, pe_list):
    """
    根据 PE 历史分位数返回目标仓位比例。
    数据不足 24 个月时，用绝对 PE 阈值兜底（沪深300历史均值约 13–16 倍）。
    """
    if len(pe_list) < 24:
        # 暖机期：用绝对阈值
        if pe <= 11:   return 0.95
        if pe <= 14:   return 0.75
        if pe <= 18:   return 0.50
        if pe <= 24:   return 0.25
        return 0.0

    # 数据充足：用历史分位数
    sorted_pe = sorted(pe_list)
    n = len(sorted_pe)
    rank = sum(1 for x in sorted_pe if x <= pe)
    percentile = rank / n  # 越低 = PE 越便宜

    if percentile <= 0.20:  return 0.95
    if percentile <= 0.40:  return 0.75
    if percentile <= 0.60:  return 0.50
    if percentile <= 0.80:  return 0.25
    return 0.0


def rebalance(context):
    current_date = context.current_dt.date()

    # 计算本月 PE
    pe = _get_index_pe(g.index, current_date)
    if pe is None:
        log.warn('PE 获取失败，跳过本月调仓')
        return

    # 更新历史，保留最近 pe_window 个月
    g.pe_history.append(pe)
    if len(g.pe_history) > g.pe_window:
        g.pe_history = g.pe_history[-g.pe_window:]

    # 计算目标仓位
    target_ratio  = _get_position_ratio(pe, g.pe_history)
    target_value  = context.portfolio.portfolio_value * target_ratio

    log.info('PE={:.2f}  分位数样本={:d}  目标仓位={:.0%}'.format(
        pe, len(g.pe_history), target_ratio))

    order_target_value(g.etf, target_value)
