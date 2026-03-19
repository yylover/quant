# -*- coding: utf-8 -*-
"""
均值回归策略 (Mean Reversion Strategy)
=====================================

策略原理：
价格在短期内会围绕均值波动，当价格偏离均值超过一定阈值时，预期价格会回归均值。

核心逻辑：
1. 计算 N 日移动平均线（MA）作为均值
2. 计算 N 日标准差（Std）
3. 计算当前价格的 Z-score（偏离程度）：(当前价 - MA) / Std
4. 交易规则：
   - 当 Z <= -k 倍标准差时（超卖）：买入
   - 当 Z >= k 倍标准差时（超买）：卖出
   - 当偏离缩小到阈值内时可平仓

参数说明：
- g.window = 20: 均线周期，用于计算MA和标准差
- g.num_std = 2.0: 触发阈值，偏离均值2倍标准差时触发交易
- g.revert_ratio = 0.5: 回归系数，偏离缩小到0.5倍标准差内可平仓

适用场景：
- 震荡市，价格在一定区间内反复波动
- 不适用于单边趋势行情（会持续亏损）

风险提示：
- 在单边牛市中会错过上涨机会
- 在单边熊市中会不断接飞刀
- 建议配合其他指标（如趋势判断）使用

适用于聚宽 JoinQuant 平台回测。
"""

from jqdata import *


def initialize(context):
    """
    初始化函数
    设置基准、手续费、标的和策略参数
    """
    # 设置基准为沪深300指数
    set_benchmark('000300.XSHG')

    # 使用真实价格
    set_option('use_real_price', True)

    # 设置交易手续费：买入0.03%，卖出0.103%（含印花税0.1%）
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock'
    )

    # 交易标的：沪深300ETF
    g.security = '510300.XSHG'

    # 策略参数
    g.window = 20      # 均线周期：使用20日移动平均
    g.num_std = 2.0    # 触发阈值：偏离均线2倍标准差时触发交易
    g.revert_ratio = 0.5  # 回归系数：偏离缩小到0.5倍标准差内可平仓

    # 每个交易日开盘时执行调仓
    run_daily(rebalance, time='open')


def rebalance(context):
    """
    每日调仓函数
    根据价格偏离程度决定买入或卖出
    """
    # 获取历史价格数据，需要 window+2 天数据以确保计算准确
    need = g.window + 2
    prices = attribute_history(g.security, need, '1d', ['close'])

    # 数据不足则跳过
    if prices is None or len(prices) < g.window:
        return

    close = prices['close']
    current = close.iloc[-1]

    # 计算均线和标准差
    ma = close.iloc[-g.window:].mean()
    std = close.iloc[-g.window:].std()

    # 标准差为0或无效则跳过
    if std is None or std <= 0:
        return

    # 计算当前价格的 Z-score（偏离程度）
    # z > 0 表示价格高于均值，z < 0 表示价格低于均值
    z = (current - ma) / std

    # 获取当前持仓
    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 交易信号判断
    # 超卖：价格低于均值超过 k 倍标准差 -> 买入信号
    oversold = z <= -g.num_std

    # 超买：价格高于均值超过 k 倍标准差 -> 卖出信号
    overbought = z >= g.num_std

    # 回归：偏离回到阈值内可平多（价格向均值回归）
    reverted = abs(z) <= g.revert_ratio * g.num_std

    # 执行交易
    # 情况1：超卖且无持仓 -> 买入
    if oversold and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 情况2：超买或价格已回归，且有持仓 -> 卖出
    elif (overbought or (hold_amount > 0 and reverted)):
        if hold_amount > 0:
            order_target(g.security, 0)
