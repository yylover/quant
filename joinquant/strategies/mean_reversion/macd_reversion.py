# -*- coding: utf-8 -*-
"""
MACD均值回归策略 (MACD Mean Reversion)
=======================================

策略原理：
MACD（Moving Average Convergence Divergence）是一种趋势跟踪指标，
但也可以用于均值回归策略。

计算公式：
1. EMA_12 = 12日指数移动平均
2. EMA_26 = 26日指数移动平均
3. DIF = EMA_12 - EMA_26（快线）
4. DEA = DIF的9日指数移动平均（慢线）
5. MACD柱状图 = (DIF - DEA) × 2

均值回归应用：
- MACD柱状图正向过大表示超买，预期回落
- MACD柱状图负向过大表示超卖，预期反弹
- 基于动量会回归到均值附近的假设

交易规则：
- 买入条件：MACD柱状图 <= -threshold（负向过大）
- 卖出条件：MACD柱状图 >= threshold（正向过大）
- 平仓条件：柱状图回归到正常区间

参数说明：
- g.fast = 12: 快线周期
- g.slow = 26: 慢线周期
- g.signal = 9: 信号线周期
- g.threshold = 0.5: 触发阈值

适用场景：
- 中短期震荡行情
- 动量过大后的反转
- 适合捕捉动量回归机会

优势：
- 结合趋势和动量信息
- MACD柱状图反映动能强弱
- 可以识别过度拉升或砸盘

风险：
- 在强趋势中柱状图可能持续极端
- 需要根据标的特性调整阈值
- 柱状图波动较大，容易误触发

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
    g.fast = 12            # 快线周期
    g.slow = 26            # 慢线周期
    g.signal = 9           # 信号线周期
    g.threshold = 0.5      # 触发阈值

    run_daily(rebalance, time='open')


def calc_macd(close_series, fast, slow, signal):
    """计算MACD指标"""
    # 计算EMA
    ema_fast = close_series.ewm(span=fast, adjust=False).mean()
    ema_slow = close_series.ewm(span=slow, adjust=False).mean()

    # DIF（快线）
    dif = ema_fast - ema_slow

    # DEA（信号线）
    dea = dif.ewm(span=signal, adjust=False).mean()

    # MACD柱状图
    macd = (dif - dea) * 2

    return macd


def rebalance(context):
    """每日调仓"""
    need = g.slow + g.signal + 10
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < need:
        return

    macd = calc_macd(prices['close'], g.fast, g.slow, g.signal)
    macd_val = macd.iloc[-1]

    if macd_val is None or (macd_val != macd_val):
        return

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：MACD柱状图负向过大
    if macd_val <= -g.threshold and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买：MACD柱状图正向过大
    elif macd_val >= g.threshold and hold_amount > 0:
        order_target(g.security, 0)
