# -*- coding: utf-8 -*-
"""
布林带均值回归策略 (Bollinger Bands Mean Reversion)
==================================================

策略原理：
布林带是基于移动平均线和标准差的技术指标，由三条线组成：
- 中轨：N日移动平均线（MA）
- 上轨：中轨 + k × 标准差
- 下轨：中轨 - k × 标准差

均值回归交易逻辑：
- 价格触及下轨（超卖）：买入
- 价格触及上轨（超买）：卖出
- 基于价格会在中轨（均值）附近波动的假设

参数说明：
- g.window = 20: 布林带周期，使用20日数据
- g.num_std = 2.0: 标准差倍数，上下轨距离中轨2倍标准差

适用场景：
- 震荡市，价格在布林带通道内反复波动
- 适合捕捉超卖反弹和超买回调的机会

与趋势版本的区别：
- 均值回归版：低买高卖，在通道内做波段
- 趋势突破版：突破上轨追涨，跌破中轨止损

适用于聚宽 JoinQuant 平台回测。
"""

from jqdata import *


def initialize(context):
    """
    初始化函数
    """
    # 设置基准为沪深300指数
    set_benchmark('000300.XSHG')

    # 使用真实价格
    set_option('use_real_price', True)

    # 设置交易手续费
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock'
    )

    # 交易标的：沪深300ETF
    g.security = '510300.XSHG'

    # 布林带参数
    g.window = 20   # 中轨/标准差计算周期
    g.num_std = 2.0  # 上下轨标准差倍数

    # 每个交易日开盘时执行调仓
    run_daily(rebalance, time='open')


def rebalance(context):
    """
    每日调仓函数
    根据价格相对于布林带的位置决定买卖
    """
    # 获取历史价格数据
    prices = attribute_history(g.security, g.window + 1, '1d', ['close'])

    # 数据不足则跳过
    if prices is None or len(prices) < g.window:
        return

    close = prices['close']

    # 计算布林带
    mid = close.iloc[-g.window:].mean()      # 中轨：移动平均
    std = close.iloc[-g.window:].std()        # 标准差

    # 标准差无效则跳过
    if std is None or std <= 0:
        return

    # 上轨和下轨
    upper = mid + g.num_std * std    # 上轨
    lower = mid - g.num_std * std    # 下轨

    # 当前价格
    current = close.iloc[-1]

    # 获取当前持仓
    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 买入信号：价格接近或跌破下轨（超卖）
    # 使用 1.01 倍容忍度，避免小幅波动导致频繁交易
    if current <= lower * 1.01:
        if hold_amount <= 0:
            # 全仓买入（留5%现金）
            order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 卖出信号：价格接近或突破上轨（超买）
    elif current >= upper * 0.99:
        if hold_amount > 0:
            # 清仓卖出
            order_target(g.security, 0)
