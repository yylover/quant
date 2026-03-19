# -*- coding: utf-8 -*-
"""
ATR均值回归策略 (ATR Mean Reversion)
====================================

策略原理：
ATR（Average True Range，平均真实波幅）衡量市场波动率，
基于价格的真实范围（考虑跳空）。

计算公式：
1. TR = max(最高价-最低价, |最高价-前收盘|, |最低价-前收盘|)
2. ATR = TR的N日移动平均

核心逻辑：
- 价格突破ATR通道表示过度延伸，可能反转
- ATR通道：均线 ± k × ATR
- 当价格突破上轨可能回调，突破下轨可能反弹

交易规则：
- 买入条件：价格 <= 均线 - k × ATR（跌破下轨）
- 卖出条件：价格 >= 均线 + k × ATR（突破上轨）
- 平仓条件：价格回到通道内

参数说明：
- g.window = 14: ATR计算周期
- g.ma_window = 20: 均线周期
- g.atr_multiplier = 2.0: ATR倍数
- g.exit_multiplier = 0.5: 离场ATR倍数

适用场景：
- 波动率适中的市场
- 价格围绕通道波动
- 适合捕捉超买超卖反转

优势：
- 考虑了跳空情况
- 基于真实波动幅度
- 适应市场波动率变化

风险：
- 在高波动期通道过宽，信号减少
- 在低波动期通道过窄，假信号增多
- 需要合理设置ATR倍数

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
    g.window = 14             # ATR计算周期
    g.ma_window = 20          # 均线周期
    g.atr_multiplier = 2.0    # 入场ATR倍数
    g.exit_multiplier = 0.5   # 离场ATR倍数

    run_daily(rebalance, time='open')


def calc_atr(high_series, low_series, close_series, window):
    """计算ATR指标"""
    # 前一日收盘价
    prev_close = close_series.shift(1)

    # 计算真实范围TR
    tr1 = high_series - low_series
    tr2 = abs(high_series - prev_close)
    tr3 = abs(low_series - prev_close)

    # TR = max(TR1, TR2, TR3)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR = TR的N日移动平均
    atr = tr.rolling(window, min_periods=window).mean()

    return atr


def rebalance(context):
    """每日调仓"""
    need = max(g.window, g.ma_window) + 10
    data = attribute_history(g.security, need, '1d', ['close', 'high', 'low'])
    if data is None or len(data) < need:
        return

    close = data['close']
    high = data['high']
    low = data['low']

    # 计算ATR
    atr = calc_atr(high, low, close, g.window)
    atr_val = atr.iloc[-1]

    if atr_val is None or (atr_val != atr_val):
        return

    # 计算均线
    ma = close.iloc[-g.ma_window:].mean()

    if ma is None or (ma != ma):
        return

    # ATR通道
    upper_band = ma + g.atr_multiplier * atr_val
    lower_band = ma - g.atr_multiplier * atr_val
    exit_upper = ma + g.exit_multiplier * atr_val
    exit_lower = ma - g.exit_multiplier * atr_val

    current = close.iloc[-1]

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 超卖：价格跌破下轨
    if current <= lower_band and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 超买或回归：价格突破上轨或回到通道内
    elif (current >= upper_band or (exit_lower <= current <= exit_upper)) and hold_amount > 0:
        order_target(g.security, 0)
