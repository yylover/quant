# -*- coding: utf-8 -*-
"""
RSI均值回归策略 (RSI Mean Reversion Strategy)
===============================================

策略原理：
RSI（Relative Strength Index，相对强弱指标）是一种动量震荡指标，
用于衡量价格变动的速度和变化幅度，取值范围在0-100之间。

核心逻辑：
1. RSI > 70（超买区）：价格可能过高，预期回调 → 卖出信号
2. RSI < 30（超卖区）：价格可能过低，预期反弹 → 买入信号
3. 基于价格会从极端位置回归到正常区间的假设

计算方法：
- RS = 平均涨幅 / 平均跌幅（N日内）
- RSI = 100 - 100/(1 + RS)

参数说明：
- g.period = 14: RSI计算周期，默认14日
- g.oversold = 30: 超卖阈值，RSI低于此值时考虑买入
- g.overbought = 70: 超买阈值，RSI高于此值时考虑卖出

适用场景：
- 震荡市，价格在超买超卖区间反复波动
- 适合捕捉短期反弹和回调机会
- 在强趋势行情中容易产生假信号（持续超买超卖）

改进建议：
- 可结合趋势判断（如均线）过滤趋势市中的假信号
- 可根据波动率动态调整超买超卖阈值

适用于聚宽 JoinQuant 平台回测。
"""

from jqdata import *
import numpy as np


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

    # RSI参数
    g.period = 14       # RSI计算周期，标准值为14日
    g.oversold = 30     # 超卖阈值，低于此值认为超卖
    g.overbought = 70   # 超买阈值，高于此值认为超买

    # 每个交易日开盘时执行调仓
    run_daily(rebalance, time='open')


def calc_rsi(close_series, period=14):
    """
    计算RSI指标

    计算步骤：
    1. 计算每日价格变化（delta）
    2. 分离涨幅和跌幅
    3. 计算N日平均涨幅和平均跌幅
    4. 计算RS（相对强度）
    5. 计算RSI = 100 - 100/(1+RS)

    参数：
    - close_series: 收盘价序列
    - period: RSI周期

    返回：
    - RSI序列
    """
    # 计算每日价格变化
    delta = close_series.diff()

    # 分离涨幅和跌幅
    gain = delta.where(delta > 0, 0.0)    # 涨幅，非涨则置0
    loss = (-delta).where(delta < 0, 0.0) # 跌幅，非跌则置0

    # 计算N日平均涨幅和平均跌幅
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()

    # 计算RS（相对强度）
    rs = avg_gain / avg_loss

    # 处理无穷大和NaN值
    rs = rs.replace([float('inf'), -float('inf')], 0).fillna(0)

    # 计算RSI
    rsi = 100 - (100 / (1 + rs))

    return rsi


def rebalance(context):
    """
    每日调仓函数
    根据RSI值判断超买超卖状态并执行交易
    """
    # 获取历史价格数据，需要 period+2 天数据
    need = g.period + 2
    prices = attribute_history(g.security, need, '1d', ['close'])

    # 数据不足则跳过
    if prices is None or len(prices) < need:
        return

    close = prices['close']

    # 计算RSI序列
    rsi_series = calc_rsi(close, g.period)

    # 获取最新的RSI值
    rsi = rsi_series.iloc[-1]

    # RSI值无效则跳过
    if rsi is None or (rsi != rsi):  # NaN检查
        return

    # 获取当前持仓
    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 买入信号：RSI < 超卖阈值（超卖）
    if rsi < g.oversold:
        if hold_amount <= 0:
            # 全仓买入（留5%现金）
            order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 卖出信号：RSI > 超买阈值（超买）
    elif rsi > g.overbought:
        if hold_amount > 0:
            # 清仓卖出
            order_target(g.security, 0)
