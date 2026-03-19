# -*- coding: utf-8 -*-
"""
KDJ均值回归策略 (KDJ Mean Reversion)
====================================

策略原理：
KDJ指标是一种常用的超买超卖指标，由K线、D线、J线三条线组成。
K值和D值在0-100之间波动，J值可以超出这个范围。

核心逻辑：
- K值或D值低于20表示超卖，预期上涨
- K值或D值高于80表示超买，预期下跌
- J值更敏感，可用于提前预警

计算方法：
1. 计算RSV（未成熟随机值）：(收盘价 - N日最低价) / (N日最高价 - N日最低价) × 100
2. K = (2/3) × 前一日K + (1/3) × 当日RSV
3. D = (2/3) × 前一日D + (1/3) × 当日K
4. J = 3 × 当日K - 2 × 当日D

交易规则：
- 买入条件：K <= 20 且 D <= 20（超卖）
- 卖出条件：K >= 80 且 D >= 80（超买）

参数说明：
- g.window = 9: RSV计算周期
- g.m1 = 3: K值平滑系数
- g.m2 = 3: D值平滑系数
- g.low = 20: 超卖阈值
- g.high = 80: 超买阈值

适用场景：
- 短期震荡行情
- 超买超卖反转明显
- 适合做短线波段

优势：
- 反应灵敏，适合捕捉短期反转
- 三条线交叉提供确认信号
- 在震荡市中表现良好

风险：
- 在强趋势中容易产生假信号
- 参数敏感，需要针对不同标的优化
- 高频交易增加成本

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
    g.window = 9          # RSV计算周期
    g.m1 = 3              # K值平滑系数
    g.m2 = 3              # D值平滑系数
    g.low = 20            # 超卖阈值
    g.high = 80           # 超买阈值

    run_daily(rebalance, time='open')


def calc_kdj(high_series, low_series, close_series, window, m1, m2):
    """计算KDJ指标"""
    # 计算RSV
    lowest = low_series.rolling(window, min_periods=window).min()
    highest = high_series.rolling(window, min_periods=window).max()

    # 避免除零
    high_low_diff = highest - lowest
    high_low_diff = high_low_diff.replace(0, 1)

    rsv = (close_series - lowest) / high_low_diff * 100

    # K值平滑
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()

    # D值平滑
    d = k.ewm(alpha=1/m2, adjust=False).mean()

    # J值
    j = 3 * k - 2 * d

    return k, d, j


def rebalance(context):
    """每日调仓"""
    need = g.window + max(g.m1, g.m2) + 10
    data = attribute_history(g.security, need, '1d', ['close', 'high', 'low'])
    if data is None or len(data) < need:
        return

    k, d, j = calc_kdj(data['high'], data['low'], data['close'],
                      g.window, g.m1, g.m2)

    k_val = k.iloc[-1]
    d_val = d.iloc[-1]

    if k_val is None or d_val is None or (k_val != k_val) or (d_val != d_val):
        return

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：K <= 20 且 D <= 20
    if k_val <= g.low and d_val <= g.low and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买：K >= 80 且 D >= 80
    elif k_val >= g.high and d_val >= g.high and hold_amount > 0:
        order_target(g.security, 0)
