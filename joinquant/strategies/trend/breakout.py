# -*- coding: utf-8 -*-
"""
突破策略 (Breakout / 唐奇安类简化版)
====================================

**入场**：收盘价 **突破过去 N 日最高价**（不含当日 K 线），视为盘整后向上启动，做多。

**出场**（二选一）：
  - `exit_days > 0`：收盘价 **跌破过去 M 日最低价**（不含当日），时间止损/结构破位。
  - `exit_days == 0`：**移动止损**——从持仓以来净值最高价回撤超过 `trailing_stop_pct` 则清仓。

属于经典 **趋势跟随 / 通道突破** 思路；震荡市假突破多，需接受回撤与换手。

适用于聚宽 JoinQuant；默认标的 `510300.XSHG`（沪深300ETF）。
"""


def initialize(context):
    """初始化：基准、真实价格、手续费、参数与调度。"""
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock'
    )
    g.security = '510300.XSHG'
    # 突破窗口：用「不含最新一根 K 线」的前 N 日最高价作阻力线，最新收盘上破则买入
    g.breakout_days = 20
    # 出场窗口：>0 时用前 M 日（不含当日）最低价作支撑跌破则卖；=0 则改用下方移动止损
    g.exit_days = 10
    # 仅当 exit_days==0 时生效：相对持仓期最高价回撤超过该比例则平仓（如 0.05=5%）
    g.trailing_stop_pct = 0.05
    run_daily(rebalance, time='open')


def rebalance(context):
    """
    每日逻辑（日频、开盘调度）：
    - 取足够长的 high/low/close，保证 N 日、M 日切片有效。
    - prev_high / prev_low 的切片 **不包含 iloc[-1]**，避免把「当天」算进极值里再和当天收盘比（未来函数）。
    """
    need = max(g.breakout_days, g.exit_days or 1) + 2
    prices = attribute_history(g.security, need, '1d', ['high', 'low', 'close'])
    if prices is None or len(prices) < need:
        return
    high = prices['high']
    low = prices['low']
    close = prices['close']
    # 最近一根 K 线的收盘价（在 run_daily open 下通常为昨日收盘）
    current = close.iloc[-1]

    # 前 breakout_days 个「完整历史区间」的最高价：切片为 iloc[-(N+1):-1]，共 N 根，不含最后一根
    prev_high = high.iloc[-g.breakout_days - 1:-1].max()
    prev_low = low.iloc[-g.exit_days - 1:-1].min() if g.exit_days > 0 else None

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 移动止损需要记录持仓以来的价格峰值；空仓时清空，避免沿用上一次的峰值
    if hold_amount > 0:
        if not hasattr(g, 'highest_since_entry'):
            g.highest_since_entry = current
        g.highest_since_entry = max(g.highest_since_entry, current)
    else:
        g.highest_since_entry = None

    # 入场：今日收盘创出「昨日为止」的 N 日新高
    breakout_buy = current > prev_high

    # 出场：结构破位（跌破 M 日低）或 从持仓最高价回撤超阈值
    if g.exit_days > 0:
        exit_signal = current < prev_low
    else:
        exit_signal = g.highest_since_entry and current < g.highest_since_entry * (1 - g.trailing_stop_pct)

    if breakout_buy and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)
    elif exit_signal and hold_amount > 0:
        order_target(g.security, 0)
