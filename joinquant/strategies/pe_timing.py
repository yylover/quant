# -*- coding: utf-8 -*-
"""
PE 估值择时策略 v2（PE × 趋势双因子）
=====================================
v1 问题：单独使用 PE 分位数，A 股牛市中 PE 长期处于高分位，策略持续轻仓踏空。

v2 改进：
  1. 双因子决策矩阵：PE 分位数 × 价格趋势（MA），两者共同决定仓位
     - PE 便宜 + 趋势向上 → 满仓（最强信号）
     - PE 便宜 + 趋势向下 → 半仓（便宜但还在跌，谨慎）
     - PE 偏贵 + 趋势向上 → 轻仓（贵但趋势在，不完全空仓）
     - PE 偏贵 + 趋势向下 → 极轻或空仓（最弱信号，保护资金）
  2. 最低保底仓位 10%（暖机期不会因阈值过保守而完全踏空）
  3. 暖机期缩短至 12 个月（之前 24 个月太长）
  4. 趋势信号用 60 日均线（月度策略匹配中长期趋势）

交易标的：510300.XSHG（沪深300ETF）
PE 来源：000300.XSHG 成分股市值加权 PE

适用于聚宽 JoinQuant 平台回测。
"""

from jqdata import *


# ---------- 仓位决策矩阵 ----------
# pe_bucket: 'low'(<40%) / 'mid'(40-60%) / 'high'(60-80%) / 'top'(>80%)
# trend:     'up' / 'down'
_POSITION_MATRIX = {
    ('low',  'up'):   0.95,
    ('low',  'down'): 0.50,
    ('mid',  'up'):   0.65,
    ('mid',  'down'): 0.25,
    ('high', 'up'):   0.35,
    ('high', 'down'): 0.10,
    ('top',  'up'):   0.15,
    ('top',  'down'): 0.00,
}
_MIN_POSITION = 0.10   # 暖机期最低保底仓位


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003,
                  close_commission=0.0003, min_commission=5),
        type='stock'
    )

    g.index          = '000300.XSHG'  # PE 来源指数
    g.etf            = '510300.XSHG'  # 实际交易标的
    g.pe_history     = []             # 滚动历史 PE（月度）
    g.pe_window      = 60             # 分位数回看窗口（月），约 5 年
    g.pe_warmup      = 12             # 暖机：至少 12 个月后才用分位数
    g.ma_days        = 60             # 趋势判断均线周期（交易日）

    run_monthly(rebalance, monthday=1, time='open')


# ---------- PE 获取 ----------
def _get_index_pe(index_code, date):
    """市值加权 PE，过滤亏损股和极端值"""
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
        valuation.pe_ratio < 500
    )
    df = get_fundamentals(q, date=date)
    if df is None or len(df) == 0:
        return None
    total_mcap = df['market_cap'].sum()
    if total_mcap <= 0:
        return None
    return float((df['pe_ratio'] * df['market_cap']).sum() / total_mcap)


# ---------- 趋势判断 ----------
def _get_trend(etf, ma_days):
    """价格在 ma_days 日均线上方返回 'up'，否则 'down'"""
    prices = attribute_history(etf, ma_days + 2, '1d', ['close'])
    if prices is None or len(prices) < ma_days + 1:
        return 'up'   # 数据不足时保守默认上涨
    close = prices['close']
    ma = close.iloc[-ma_days:].mean()
    return 'up' if close.iloc[-1] > ma else 'down'


# ---------- PE 分档 ----------
def _pe_bucket(pe, pe_list):
    """
    数据充足时用历史分位数分档；不足时用 A 股经验绝对阈值。
    返回: 'low' / 'mid' / 'high' / 'top'
    """
    if len(pe_list) < g.pe_warmup:
        # 暖机期：沪深300历史 PE 经验区间
        if pe <= 12:   return 'low'
        if pe <= 16:   return 'mid'
        if pe <= 22:   return 'high'
        return 'top'

    sorted_pe = sorted(pe_list)
    n = len(sorted_pe)
    pct = sum(1 for x in sorted_pe if x <= pe) / n

    if pct <= 0.40:  return 'low'
    if pct <= 0.60:  return 'mid'
    if pct <= 0.80:  return 'high'
    return 'top'


# ---------- 主调仓 ----------
def rebalance(context):
    current_date = context.current_dt.date()

    # 1. 获取本月 PE
    pe = _get_index_pe(g.index, current_date)
    if pe is None:
        log.warn('PE 获取失败，跳过本月调仓')
        return

    # 2. 更新历史
    g.pe_history.append(pe)
    if len(g.pe_history) > g.pe_window:
        g.pe_history = g.pe_history[-g.pe_window:]

    # 3. PE 分档
    bucket = _pe_bucket(pe, g.pe_history)

    # 4. 趋势判断
    trend = _get_trend(g.etf, g.ma_days)

    # 5. 查矩阵得目标仓位
    target_ratio = _POSITION_MATRIX[(bucket, trend)]

    # 暖机期保底：不低于 _MIN_POSITION
    if len(g.pe_history) < g.pe_warmup:
        target_ratio = max(target_ratio, _MIN_POSITION)

    target_value = context.portfolio.portfolio_value * target_ratio
    order_target_value(g.etf, target_value)

    log.info(
        'PE={:.2f}  分档={}  趋势={}  目标仓位={:.0%}  '
        '样本数={:d}'.format(pe, bucket, trend, target_ratio, len(g.pe_history))
    )
