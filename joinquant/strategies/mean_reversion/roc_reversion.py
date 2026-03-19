# -*- coding: utf-8 -*-
"""
ROC均值回归策略 (ROC Mean Reversion)
===================================

策略原理：
ROC（Rate of Change，变动率）衡量价格在N日内的变化幅度，
反映价格变动的速度和方向。

计算公式：
ROC = (当前价格 - N日前价格) / N日前价格 × 100%

取值范围：
- ROC > 0：价格上涨（正值越大涨幅越大）
- ROC < 0：价格下跌（负值越小跌幅越大）
- ROC = 0：价格无变化

核心逻辑：
- ROC过大表示短期涨幅过大，可能回调（超买）
- ROC过小表示短期跌幅过大，可能反弹（超卖）
- 基于价格涨跌不会永远持续的假设

交易规则：
- 买入条件：ROC <= low（跌幅过大，如-8%）
- 卖出条件：ROC >= high（涨幅过大，如8%）
- 平仓条件：ROC回到正常区间

参数说明：
- g.window = 12: ROC计算周期
- g.low = -0.08: 超卖阈值（-8%）
- g.high = 0.08: 超买阈值（8%）
- g.exit_dev = 0.02: 离场阈值（±2%）

适用场景：
- 短期震荡行情
- 价格快速涨跌后反转
- 适合捕捉短期超买超卖

优势：
- 反应速度极快
- 计算简单直观
- 适合短线交易

风险：
- 在趋势行情中容易产生假信号
- 可能频繁触发交易
- 需要配合止损策略

适用于聚宽 JoinQuant 平台回测。
"""

from jqdata import *


def initialize(context):
    """
    初始化函数
    """
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock'
    )

    g.security = '510300.XSHG'
    g.window = 12          # ROC计算周期
    g.low = -0.08          # 超卖阈值（-8%）
    g.high = 0.08          # 超买阈值（8%）
    g.exit_dev = 0.02      # 离场阈值（±2%）

    run_daily(rebalance, time='open')


def calc_roc(close_series, window):
    """计算ROC指标"""
    # ROC = (当前价 - N日前价格) / N日前价格
    prev_close = close_series.shift(window)

    # 避免除零
    prev_close = prev_close.replace(0, 1)

    roc = (close_series - prev_close) / prev_close

    return roc


def rebalance(context):
    """每日调仓"""
    need = g.window + 5
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < g.window + 1:
        return

    roc = calc_roc(prices['close'], g.window)
    roc_val = roc.iloc[-1]

    if roc_val is None or (roc_val != roc_val):
        return

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：ROC <= -8%
    if roc_val <= g.low and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买或回归：ROC >= 8% 或回到 ±2% 范围内
    elif (roc_val >= g.high or abs(roc_val) <= g.exit_dev) and hold_amount > 0:
        order_target(g.security, 0)
