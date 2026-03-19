# -*- coding: utf-8 -*-
"""
CCI均值回归策略 (CCI Mean Reversion)
======================================

策略原理：
CCI（Commodity Channel Index，顺势指标）是一种衡量价格偏离
其统计平均水平的指标。

计算公式：
1. TP = (最高价 + 最低价 + 收盘价) / 3（典型价格）
2. MA_TP = TP的N日移动平均
3. MD = TP的N日平均绝对偏差
4. CCI = (TP - MA_TP) / (0.015 × MD)

取值范围：通常在 -300 到 +300 之间
- CCI > 100：超买，可能回调
- CCI < -100：超卖，可能反弹
- -100 到 100：正常区间

核心逻辑：
- CCI偏离0值越远，表示价格越偏离其统计平均水平
- 当CCI超过±100时，预期价格会回归

交易规则：
- 买入条件：CCI <= -100（进入超卖区）
- 卖出条件：CCI >= 100（进入超买区）
- 平仓条件：CCI回到正常区间

参数说明：
- g.window = 20: 计算周期
- g.low = -100: 超卖阈值
- g.high = 100: 超买阈值

适用场景：
- 中短期震荡行情
- 价格围绕均值波动
- 适合捕捉较大的反转机会

优势：
- 能够识别超买超卖极端情况
- 适用于各种时间周期
- 在震荡市中表现良好

风险：
- 在强趋势中容易产生假信号
- CCI可以长时间停留在极端区域
- 需要足够的数据积累

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
    g.window = 20       # 计算周期
    g.low = -100        # 超卖阈值
    g.high = 100        # 超买阈值

    run_daily(rebalance, time='open')


def calc_cci(high_series, low_series, close_series, window):
    """计算CCI指标"""
    # 典型价格 TP
    tp = (high_series + low_series + close_series) / 3

    # TP的移动平均
    ma_tp = tp.rolling(window, min_periods=window).mean()

    # TP的平均绝对偏差
    mad = tp.rolling(window, min_periods=window).apply(lambda x: abs(x - x.mean()).mean())

    # 避免除零
    mad = mad.replace(0, 1)

    # CCI = (TP - MA_TP) / (0.015 × MD)
    cci = (tp - ma_tp) / (0.015 * mad)

    return cci


def rebalance(context):
    """每日调仓"""
    need = g.window + 5
    data = attribute_history(g.security, need, '1d', ['close', 'high', 'low'])
    if data is None or len(data) < need:
        return

    cci = calc_cci(data['high'], data['low'], data['close'], g.window)
    cci_val = cci.iloc[-1]

    if cci_val is None or (cci_val != cci_val):
        return

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：CCI <= -100
    if cci_val <= g.low and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买：CCI >= 100
    elif cci_val >= g.high and hold_amount > 0:
        order_target(g.security, 0)
