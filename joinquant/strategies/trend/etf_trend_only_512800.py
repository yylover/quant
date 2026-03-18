# -*- coding: utf-8 -*-
"""
单 ETF 纯趋势交易系统（标的：512800.XSHG 银行 ETF）
=====================================================

目标：作为「买入并持有」的简化替代方案，只用一个非常直观的趋势过滤：

  - 价格站上 MA60 且 MA60 向上 → 在市（全仓持有 512800）
  - 价格跌破 MA60 且 MA60 向下 → 空仓（持现金）
  - 其他时间 → 保持原有状态，不频繁切换

不做任何网格、高抛低吸，也不做复杂的止损/止盈逻辑，
只控制「在不在市场里」，用来和：
  1）简单买入并持有 512800
  2）趋势 + 网格 版本
进行直接对比。

适用于聚宽 JoinQuant 平台回测。
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

    # 只交易 512800
    g.symbol = '512800.XSHG'

    # 趋势参数：长期均线 MA60
    g.long_ma = 20

    # 最大单标的仓位 = 100% 资产
    g.max_pos_pct = 1.0

    # 使用日频，在开盘时根据前一日收盘价和 MA60 决定是否持仓
    run_daily(handle, time='open')


def get_trend(prices):
    """
    基于价格与 MA60 的简洁趋势判定：
      - close > MA60 且 MA60 向上 → up
      - close < MA60 且 MA60 向下 → down
      - 其他情况 → flat
    """
    close = prices['close']
    if len(close) < g.long_ma + 2:
        return None

    ma_long_now = close.iloc[-g.long_ma:].mean()
    ma_long_prev = close.iloc[-g.long_ma-1:-1].mean()
    if ma_long_now <= 0 or ma_long_prev <= 0:
        return None

    price_now = close.iloc[-1]

    slope_up = ma_long_now > ma_long_prev
    slope_down = ma_long_now < ma_long_prev

    if price_now > ma_long_now and slope_up:
        return 'up'
    if price_now < ma_long_now and slope_down:
        return 'down'
    return 'flat'


def handle(context):
    symbol = g.symbol

    # 取足够历史数据用于 MA60 计算
    need = g.long_ma + 5
    prices = attribute_history(symbol, need, '1d', ['open', 'high', 'low', 'close'])
    if prices is None or len(prices) < need:
        return

    trend = get_trend(prices)
    if trend is None:
        return

    position = context.portfolio.positions.get(symbol)
    has_position = position is not None and position.total_amount > 0

    portfolio_value = context.portfolio.portfolio_value
    target_value = portfolio_value * g.max_pos_pct

    # --- 趋势向上：希望在市（全仓持有） ---
    if trend == 'up':
        # 若当前仓位明显不足目标，则调仓到满仓附近
        current_value = position.value if has_position else 0
        if current_value < target_value * 0.9:
            order_target_value(symbol, target_value)
            log.info('[入场] 趋势向上，买入 {} 至满仓'.format(symbol))
        # 若已经接近满仓，则不动作，减少换手
        return

    # --- 趋势向下：希望空仓 ---
    if trend == 'down':
        if has_position:
            order_target(symbol, 0)
            log.info('[离场] 趋势向下，清仓 {}'.format(symbol))
        return

    # --- 趋势不明朗（flat）：观望，保持当前状态 ---
    # 不强制进出，避免在震荡区间频繁 whipsaw
    return

