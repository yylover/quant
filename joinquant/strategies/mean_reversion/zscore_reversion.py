# -*- coding: utf-8 -*-
"""
Z-Score均值回归策略 (Z-Score Mean Reversion)
=============================================

策略原理：
Z-Score（标准分数）是统计学中衡量数据偏离均值程度的标准指标。
公式：Z = (当前价格 - 均值) / 标准差

核心逻辑：
- 当价格偏离均值超过k倍标准差时，认为价格会回归均值
- Z-Score过大（如>2）表示超买，做空或卖出
- Z-Score过小（如<-2）表示超卖，做多或买入

交易规则：
- 买入条件：Z-Score <= -k（价格低于均值k倍标准差）
- 卖出条件：Z-Score >= k（价格高于均值k倍标准差）
- 平仓条件：Z-Score回到 ±k/2 范围内

参数说明：
- g.window = 60: 计算周期，使用60日数据（中长期均值）
- g.k = 2.0: Z-Score阈值，偏离2倍标准差触发交易
- g.revert_threshold = 1.0: 回归阈值，回到1倍标准差内平仓

适用场景：
- 中期震荡行情
- 价格围绕均值波动的市场
- 需要较长时间的数据来建立稳定的统计特征

优势：
- 理论基础扎实，统计显著性高
- 参数可量化，容易优化
- 适合捕捉较大的偏离机会

风险：
- 在趋势市中持续亏损
- 需要较长的暖机期积累数据
- 均值可能随时间漂移

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
    g.window = 60          # 计算周期
    g.k = 2.0              # Z-Score阈值
    g.revert_threshold = 1.0  # 回归阈值

    run_daily(rebalance, time='open')


def rebalance(context):
    """每日调仓"""
    need = g.window + 5
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < g.window:
        return

    close = prices['close']
    current = close.iloc[-1]

    ma = close.iloc[-g.window:].mean()
    std = close.iloc[-g.window:].std()

    if std is None or std <= 0:
        return

    z_score = (current - ma) / std

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：Z-Score <= -k
    if z_score <= -g.k and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买或回归：Z-Score >= k 或回到阈值内
    elif (z_score >= g.k or abs(z_score) <= g.revert_threshold) and hold_amount > 0:
        order_target(g.security, 0)
