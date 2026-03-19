# -*- coding: utf-8 -*-
"""
布林带宽度回归策略 (Bollinger Band Width Mean Reversion)
=========================================================

策略原理：
布林带宽度（Band Width）衡量市场波动率，计算公式：
带宽 = (上轨 - 下轨) / 中轨

核心逻辑：
- 当带宽压缩到历史低点时，表示波动率极低
- 低波动率后往往伴随高波动率（波动率聚类）
- 压缩突破后，价格往往向某个方向大幅移动
- 本策略在带宽压缩时买入，等待突破

交易规则：
- 买入条件：带宽 <= 历史分位数（如10%，表示波动率压缩）
- 卖出条件：带宽 > 历史分位数（如50%，波动率恢复）
- 或达到盈利目标后平仓

参数说明：
- g.window = 20: 布林带周期
- g.n_std = 2.0: 标准差倍数
- g.width_percentile = 0.1: 带宽分位数（10%）
- g.width_lookback = 60: 带宽历史回看期

适用场景：
- 波动率压缩后的突破
- 低波动率后的高波动
- 适合捕捉暴涨机会

优势：
- 捕捉波动率扩张机会
- 在横盘震荡后寻找爆发点
- 可以结合方向判断提高胜率

风险：
- 突破方向不确定，可能反向突破
- 需要止损保护
- 长期低波动期机会少

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
    g.window = 20             # 布林带周期
    g.n_std = 2.0             # 标准差倍数
    g.width_percentile = 0.1  # 带宽分位数
    g.width_lookback = 60     # 带宽历史回看期
    g.exit_width_percentile = 0.5  # 出场分位数

    run_daily(rebalance, time='open')


def calc_bollinger_width(close_series, window, n_std):
    """计算布林带宽度"""
    ma = close_series.rolling(window, min_periods=window).mean()
    std = close_series.rolling(window, min_periods=window).std()

    # 避免除零
    ma = ma.replace(0, 1)

    # 上轨和下轨
    upper = ma + n_std * std
    lower = ma - n_std * std

    # 带宽 = (上轨 - 下轨) / 中轨
    width = (upper - lower) / ma

    return width


def rebalance(context):
    """每日调仓"""
    need = g.window + g.width_lookback + 10
    prices = attribute_history(g.security, need, '1d', ['close'])
    if prices is None or len(prices) < need:
        return

    close = prices['close']

    # 计算布林带宽度
    width = calc_bollinger_width(close, g.window, g.n_std)
    current_width = width.iloc[-1]

    if current_width is None or (current_width != current_width):
        return

    # 获取历史带宽分位数
    width_history = width.iloc[-g.width_lookback:]
    width_threshold = width_history.quantile(g.width_percentile)
    width_exit_threshold = width_history.quantile(g.exit_width_percentile)

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 波动率压缩：带宽 <= 历史分位数10%
    if current_width <= width_threshold and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 波动率恢复：带宽 >= 历史分位数50%
    elif current_width >= width_exit_threshold and hold_amount > 0:
        order_target(g.security, 0)
