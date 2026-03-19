# -*- coding: utf-8 -*-
"""
威廉指标均值回归策略 (Williams %R Mean Reversion)
==================================================

策略原理：
威廉指标（Williams %R）是一种动量指标，用于衡量当前收盘价
在最近N日价格区间中的位置。

计算公式：
%R = (最高价 - 收盘价) / (最高价 - 最低价) × (-100)

取值范围：0 到 -100
- 0 到 -20：超买区
- -80 到 -100：超卖区
- -20 到 -80：正常区间

核心逻辑：
- %R 接近 -100 表示价格接近区间最低位，可能反弹
- %R 接近 0 表示价格接近区间最高位，可能回调
- 基于价格会从极端位置回归的假设

交易规则：
- 买入条件：%R <= -80（进入超卖区）
- 卖出条件：%R >= -20（进入超买区）

参数说明：
- g.window = 14: 计算周期
- g.low = -80: 超卖阈值
- g.high = -20: 超买阈值

适用场景：
- 短期震荡行情
- 价格在一定区间内波动
- 适合捕捉短期反转

优势：
- 反应灵敏，适合短线操作
- 计算简单，容易理解
- 在震荡市中表现良好

风险：
- 在趋势市中容易产生假信号
- 可能持续停留在超买或超卖区域
- 需要结合其他指标过滤

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
    g.window = 14       # 计算周期
    g.low = -80         # 超卖阈值
    g.high = -20        # 超买阈值

    run_daily(rebalance, time='open')


def calc_williams_r(high_series, low_series, close_series, window):
    """计算威廉指标"""
    highest = high_series.rolling(window, min_periods=window).max()
    lowest = low_series.rolling(window, min_periods=window).min()

    # 避免除零
    high_low_diff = highest - lowest
    high_low_diff = high_low_diff.replace(0, 1)

    # %R = (最高价 - 收盘价) / (最高价 - 最低价) × (-100)
    williams_r = (highest - close_series) / high_low_diff * (-100)

    return williams_r


def rebalance(context):
    """每日调仓"""
    need = g.window + 5
    data = attribute_history(g.security, need, '1d', ['close', 'high', 'low'])
    if data is None or len(data) < need:
        return

    williams_r = calc_williams_r(data['high'], data['low'], data['close'], g.window)
    wr_val = williams_r.iloc[-1]

    if wr_val is None or (wr_val != wr_val):
        return

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：%R <= -80
    if wr_val <= g.low and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买：%R >= -20
    elif wr_val >= g.high and hold_amount > 0:
        order_target(g.security, 0)
