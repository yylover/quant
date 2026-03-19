# -*- coding: utf-8 -*-
"""
乖离率均值回归策略 (BIAS Mean Reversion)
=========================================

策略原理：
乖离率（BIAS）是衡量当前价格相对于移动平均线偏离程度的指标，
反映了价格偏离均线的程度。

计算公式：
BIAS = (当前价格 - N日移动平均价) / N日移动平均价 × 100%

取值范围：可以是正数或负数
- BIAS > 0：价格在均线上方（正乖离）
- BIAS < 0：价格在均线下方（负乖离）
- BIAS = 0：价格与均线重合

核心逻辑：
- 乖离率过大表示价格偏离均线过多，预期会回归
- 正乖离过大可能回调（超买）
- 负乖离过大可能反弹（超卖）
- 基于价格会围绕均线波动的假设

交易规则：
- 买入条件：BIAS <= low（负乖离过大）
- 卖出条件：BIAS >= high（正乖离过大）
- 平仓条件：乖离率回到正常区间

参数说明：
- g.window = 20: 移动平均线周期
- g.low = -0.05: 超卖阈值（-5%）
- g.high = 0.05: 超买阈值（5%）
- g.exit_dev = 0.01: 离场阈值（±1%）

适用场景：
- 短中期震荡行情
- 价格围绕均线波动
- 适合捕捉乖离率回归机会

优势：
- 计算简单，直观易懂
- 参数可量化，容易优化
- 适合短线波段操作

风险：
- 在趋势市中乖离率可能持续极端
- 频繁交易增加成本
- 需要合理的离场机制

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
    g.window = 20          # 移动平均线周期
    g.low = -0.05          # 超卖阈值（-5%）
    g.high = 0.05          # 超买阈值（5%）
    g.exit_dev = 0.01      # 离场阈值（±1%）

    run_daily(rebalance, time='open')


def calc_bias(close_series, window):
    """计算乖离率"""
    ma = close_series.rolling(window, min_periods=window).mean()

    # 避免除零
    ma = ma.replace(0, 1)

    # BIAS = (当前价 - 均线) / 均线
    bias = (close_series - ma) / ma

    return bias


def rebalance(context):
    """每日调仓"""
    need = g.window + 5
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < g.window:
        return

    bias = calc_bias(prices['close'], g.window)
    bias_val = bias.iloc[-1]

    if bias_val is None or (bias_val != bias_val):
        return

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：乖离率 <= -5%
    if bias_val <= g.low and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买或回归：乖离率 >= 5% 或回到 ±1% 范围内
    elif (bias_val >= g.high or abs(bias_val) <= g.exit_dev) and hold_amount > 0:
        order_target(g.security, 0)
