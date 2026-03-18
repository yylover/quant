# -*- coding: utf-8 -*-
"""
布林带突破趋势策略 (Bollinger Breakout, Trend-Following)
==========================================================

与原来的布林带“均值回归”版不同，这里实现的是**顺势突破**版本：

  - 当价格**有效上穿上轨**时视为趋势启动 → 做多持有
  - 当价格**跌回中轨或下轨**时视为趋势结束/大幅回撤 → 平仓离场

适合单边趋势行情（如阶段性牛市），本质是一个通道突破 CTA 的布林带实现。

默认标的：510300.XSHG（沪深300ETF），可在 initialize 中修改。
"""


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001,
                  open_commission=0.0003, close_commission=0.0003,
                  min_commission=5),
        type='stock'
    )

    g.security = '000300.XSHG'
    g.window = 20        # 布林带窗口长度
    g.num_std = 2.0      # 上下轨标准差倍数
    g.use_mid_exit = True  # True: 跌破中轨就离场；False: 跌破下轨才离场（更宽）

    run_daily(rebalance, time='open')


def rebalance(context):
    """
    趋势版布林带逻辑：
      - 入场：前一日收盘在上轨下方，当前收盘 > 上轨（上轨突破）
      - 离场：
          use_mid_exit=True  时：收盘 < 中轨
          use_mid_exit=False 时：收盘 < 下轨
    """
    sec = g.security
    window = g.window

    # 需要 window+2 根数据来判断“前一日位置 + 当日突破”
    need = window + 2
    df = attribute_history(sec, need, '1d', ['close'])
    if df is None or len(df) < need:
        return

    close = df['close']

    # 关键修正：布林带的中轨/上轨/下轨用“上一天的数据”计算（shift(1)）
    # 否则上轨会把当前收盘价一起吃进去，导致 current > upper_now 很难触发。
    ma = close.rolling(window).mean().shift(1)
    std = close.rolling(window).std().shift(1)

    mid_prev = ma.iloc[-2]
    upper_prev = mid_prev + g.num_std * std.iloc[-2]
    lower_prev = mid_prev - g.num_std * std.iloc[-2]

    mid_now = ma.iloc[-1]
    upper_now = mid_now + g.num_std * std.iloc[-1]
    lower_now = mid_now - g.num_std * std.iloc[-1]

    # 若仍有 NaN（初期数据不足）则不交易
    if any(x != x for x in [mid_prev, upper_prev, lower_prev, mid_now, upper_now, lower_now]):
        return

    prev_close = close.iloc[-2]
    current = close.iloc[-1]

    position = context.portfolio.positions.get(sec)
    hold_amount = position.total_amount if position else 0

    # --- 入场条件：上轨突破 ---
    # 用“跨越”方式更稳：昨天 <= 上轨 && 今天 > 上轨
    breakout_up = (prev_close <= upper_prev) and (current > upper_now)

    # --- 离场条件 ---
    if g.use_mid_exit:
        exit_line = mid_now
    else:
        exit_line = lower_now
    exit_signal = current < exit_line

    # 入场：无持仓且发生突破
    if breakout_up and hold_amount <= 0:
        order_target_value(sec, context.portfolio.available_cash * 0.95)
        log.info('[布林突破买入] {} 收盘={:.3f} 上轨={:.3f}'.format(sec, current, upper_now))
        return

    # 离场：有持仓且触发出场条件
    if exit_signal and hold_amount > 0:
        order_target(sec, 0)
        log.info('[布林突破卖出] {} 收盘={:.3f} 退出线={:.3f}'.format(sec, current, exit_line))
        return

