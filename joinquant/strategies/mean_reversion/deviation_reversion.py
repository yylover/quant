# -*- coding: utf-8 -*-
"""
偏离度均值回归策略 (Deviation Mean Reversion)
==============================================

策略原理：
衡量价格相对于移动平均线的偏离程度，当偏离超过一定比例时，
预期价格会回归到均线附近。

核心逻辑：
- 计算价格相对于N日移动平均线的偏离度
- 偏离度 = (当前价格 - 均值) / 均值
- 当偏离度超过阈值时进行反向交易

交易规则：
- 买入条件：偏离度 <= -entry_dev（价格低于均线5%）
- 卖出条件：偏离度 >= entry_dev（价格高于均线5%）
- 平仓条件：偏离度回到 ±exit_dev 范围内

参数说明：
- g.ma_window = 20: 移动平均线周期
- g.entry_dev = 0.05: 入场偏离阈值（5%）
- g.exit_dev = 0.01: 出场偏离阈值（1%）

适用场景：
- 短中期震荡行情
- 价格围绕均线波动的市场
- 波动率相对稳定的市场

优势：
- 计算简单，易于理解
- 响应速度快，适合短线操作
- 参数直观，容易调整

风险：
- 在单边趋势中会持续亏损
- 频繁交易导致高手续费
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
    g.ma_window = 20       # 移动平均线周期
    g.entry_dev = 0.05     # 入场偏离阈值（5%）
    g.exit_dev = 0.01      # 出场偏离阈值（1%）

    run_daily(rebalance, time='open')


def rebalance(context):
    """每日调仓"""
    need = g.ma_window + 2
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < g.ma_window:
        return

    close = prices['close']
    current = close.iloc[-1]
    ma = close.iloc[-g.ma_window:].mean()

    if ma <= 0:
        return

    # 计算偏离度
    deviation = (current - ma) / ma

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：偏离度 <= -5%
    if deviation <= -g.entry_dev and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买或回归：偏离度 >= 5% 或回到 ±1% 范围内
    elif (deviation >= g.entry_dev or abs(deviation) <= g.exit_dev) and hold_amount > 0:
        order_target(g.security, 0)
