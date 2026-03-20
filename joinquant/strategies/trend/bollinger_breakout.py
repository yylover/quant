# -*- coding: utf-8 -*-
"""
布林带突破趋势策略 (Bollinger Breakout, Trend-Following)
==========================================================

与「均值回归」版布林带（触下轨买、触上轨卖）相反，本文件是**顺势突破**：

  - **入场**：收盘价**有效上破上轨**（前一日在上轨下方或贴轨，当日明确站上）。
  - **离场**：收盘价跌回**中轨**（`use_mid_exit=True`）或**下轨**（`False`），视为趋势结束或深度回撤。

实现要点：通道用 `rolling(...).shift(1)`，避免当日收盘参与当日上下轨计算导致突破条件失真。

适合单边趋势；震荡市假突破多。默认代码里 `g.security` 为沪深300指数代码，
聚宽回测若不能交易指数请改为 `510300.XSHG` 等 ETF（见 initialize 内注释）。
"""


def initialize(context):
    # 回测对比基准（沪深300指数）；与交易标的可不同
    set_benchmark('000300.XSHG')
    # 用真实成交价回测，避免前复权等导致委托价失真，
    ## 真实成交价有没有问题？
    set_option('use_real_price', True)
    # A 股：卖出印花税 + 双边佣金；ETF 无印花税时 close_tax 仍可按股票设或按平台说明调整
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001,
                  open_commission=0.0003, close_commission=0.0003,
                  min_commission=5),
        type='stock'
    )

    # 交易标的：000300 为指数不可直接买卖，实盘/回测常改为 510300.XSHG 等 ETF
    g.security = '510300.XSHG'
    g.window = 20        # 中轨 = N 日收盘均值；N 越大通道越平滑、信号越少
    g.num_std = 2.0      # 上下轨 = 中轨 ± k×标准差；k 越大通道越宽、突破越少
    # 离场线：True=收盘跌破「当日中轨」即平（敏感）；False=跌破下轨才平（更扛回撤）
    g.use_mid_exit = True

    # 每日开盘后不久执行：用截至前一交易日的收盘价序列算信号，符合日频回测习惯
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

    # 至少 window+2 根 K 线：倒数第 2 根判断「昨日是否在上轨下」，倒数第 1 根判断「今日是否突破」
    need = window + 2
    df = attribute_history(sec, need, '1d', ['close'])
    if df is None or len(df) < need:
        return

    close = df['close']

    # 关键：rolling 后再 shift(1)，使「用于判定 t 日」的上下轨只用到 t-1 及更早收盘
    # 若不用 shift，当日收盘会参与当日上轨计算，上轨被抬高，突破条件几乎难触发（未来信息/定义问题）
    ma = close.rolling(window).mean().shift(1)
    std = close.rolling(window).std().shift(1)

    # 昨日（iloc[-2]）对应的通道：与 prev_close 同一天，用于判断昨日是否在上轨下方
    mid_prev = ma.iloc[-2]
    upper_prev = mid_prev + g.num_std * std.iloc[-2]
    lower_prev = mid_prev - g.num_std * std.iloc[-2]

    # 今日（iloc[-1]）对应的通道：与 current 同一天，用于判断今日是否站上上轨、是否跌破离场线
    mid_now = ma.iloc[-1]
    upper_now = mid_now + g.num_std * std.iloc[-1]
    lower_now = mid_now - g.num_std * std.iloc[-1]

    # 暖机期 rolling/shift 会产生 NaN，任一为 NaN 则跳过（NaN != NaN）
    if any(x != x for x in [mid_prev, upper_prev, lower_prev, mid_now, upper_now, lower_now]):
        return

    prev_close = close.iloc[-2]  # 前一交易日收盘
    current = close.iloc[-1]     # 最近一个收盘（在 run_daily open 时通常为「昨日收盘」）

    position = context.portfolio.positions.get(sec)
    hold_amount = position.total_amount if position else 0

    # --- 入场：顺势突破上轨 ---
    # 「上穿」定义：昨日收盘不高于昨日上轨，今日收盘高于今日上轨（真突破，非持续悬在上轨外重复买）
    breakout_up = (prev_close <= upper_prev) and (current > upper_now)

    # --- 离场：跌回通道内（趋势跟随止损）---
    # 中轨离场：趋势减弱即走；下轨离场：容忍更大回撤，少震出但可能回吐更多浮盈
    if g.use_mid_exit:
        exit_line = mid_now
    else:
        exit_line = lower_now
    exit_signal = current < exit_line

    # 仅空仓时开仓；满仓约 95% 留余量应对手续费等
    if breakout_up and hold_amount <= 0:
        order_target_value(sec, context.portfolio.available_cash * 0.95)
        log.info('[布林突破买入] {} 收盘={:.3f} 上轨={:.3f}'.format(sec, current, upper_now))
        return

    # 仅持仓时平仓；order_target(0) 表示清仓该标的
    if exit_signal and hold_amount > 0:
        order_target(sec, 0)
        log.info('[布林突破卖出] {} 收盘={:.3f} 退出线={:.3f}'.format(sec, current, exit_line))
        return

