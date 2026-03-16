# -*- coding: utf-8 -*-
"""
完整交易系统 - 基于「最完善的交易流程图」10 步
01 辨趋势 02 判方向 03 找位置 04 看信号 05 定止损 06 定仓位 07 看空间
08 开仓 09 平仓 10 加仓
适用于聚宽 JoinQuant 平台回测。
"""


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock'
    )
    g.security = '510300.XSHG'
    # 01 辨趋势：均线周期
    g.short_ma = 10
    g.long_ma = 30
    g.trend_threshold = 0.02   # 均线偏离在此内视为震荡
    # 04 看信号：K线形态与 RSI
    g.rsi_period = 14
    g.rsi_oversold = 30
    g.rsi_overbought = 70
    g.engulf_ratio = 0.01      # 旭日东升/阴包阳 实体比例
    # 05 定止损：总风险 = 本金 * 1.5%
    g.risk_pct = 0.015
    g.stop_atr_mult = 1.5     # 止损也可用 ATR 倍数
    g.atr_period = 14
    # 07 看空间：至少 2:1 盈亏比
    g.min_reward_ratio = 2.0
    # 09 平仓：2:1 减半仓、跟踪止盈
    g.trailing_atr_mult = 1.0  # 跟踪止盈用 ATR
    # 10 加仓：浮盈且再次满足买点
    g.add_only_if_profit = True
    g.max_add_times = 1        # 最多加仓 1 次

    run_daily(rebalance, time='open')


# ---------- 01 辨趋势 ----------
def get_trend(prices):
    """上涨/下跌/震荡"""
    close = prices['close']
    if len(close) < g.long_ma:
        return None, None, None
    short = close.iloc[-g.short_ma:].mean()
    long_ = close.iloc[-g.long_ma:].mean()
    if long_ <= 0:
        return None, None, None
    diff_pct = (short - long_) / long_
    if diff_pct > g.trend_threshold:
        return 'up', short, long_
    if diff_pct < -g.trend_threshold:
        return 'down', short, long_
    return 'flat', short, long_


# ---------- 02 判方向 + 03 找位置 ----------
def get_direction_and_location(prices, trend):
    """主多/主空；顺势延续用均线/前低，转折用前低前高"""
    high = prices['high']
    low = prices['low']
    close = prices['close']
    n = min(20, len(close) - 1)
    if n < 5:
        return None, None
    prev_high = high.iloc[-n-1:-1].max()
    prev_low = low.iloc[-n-1:-1].min()
    current = close.iloc[-1]
    # 找位置：前高前低、均线
    if trend == 'up':
        direction = 'long'
        support = prev_low
    elif trend == 'down':
        direction = 'short'
        support = prev_high  # 做空时用前高作阻力
    else:
        direction = 'long'   # 震荡默认偏多
        support = prev_low
    return direction, support


# ---------- 04 看信号：止跌/滞涨 ----------
def calc_rsi(close_series, period=14):
    delta = close_series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def has_bullish_engulfing(prices):
    """旭日东升/阳包阴：前阴后阳且后实体吞前实体"""
    open_ = prices['open']
    close = prices['close']
    if len(close) < 3:
        return False
    c1, o1 = close.iloc[-2], open_.iloc[-2]
    c2, o2 = close.iloc[-1], open_.iloc[-1]
    if c1 <= o1 and c2 > o2 and c2 > o1 and o2 < c1:
        if (c2 - o2) / (o2 or 1e-6) >= g.engulf_ratio:
            return True
    return False


def has_bearish_engulfing(prices):
    """阴包阳"""
    open_ = prices['open']
    close = prices['close']
    if len(close) < 3:
        return False
    c1, o1 = close.iloc[-2], open_.iloc[-2]
    c2, o2 = close.iloc[-1], open_.iloc[-1]
    if c1 >= o1 and c2 < o2 and c2 < o1 and o2 > c1:
        if (o2 - c2) / (o2 or 1e-6) >= g.engulf_ratio:
            return True
    return False


def get_signal(prices, direction):
    """强/弱 止跌或滞涨信号；本策略只做多，看止跌"""
    close = prices['close']
    if len(close) < g.rsi_period + 2:
        return False, None
    rsi_series = calc_rsi(close, g.rsi_period)
    rsi = rsi_series.iloc[-1]
    if rsi is None or (rsi != rsi):
        rsi = 50
    # 做多：止跌 = 旭日东升 或 RSI 超卖后回升
    strong = has_bullish_engulfing(prices)
    weak = rsi < g.rsi_oversold + 10 and rsi > rsi_series.iloc[-2] if len(rsi_series) >= 2 else False
    if direction == 'long' and (strong or weak):
        return True, 'strong' if strong else 'weak'
    return False, None


# ---------- 05 定止损 ----------
def get_atr(prices):
    """ATR：用 (high-low) 的滚动均简化，避免复杂 True Range 计算"""
    high, low = prices['high'], prices['low']
    if len(high) < g.atr_period:
        return None
    hl = (high - low).rolling(g.atr_period).mean()
    atr = hl.iloc[-1]
    return atr if atr and atr > 0 else None


def set_stop_loss(entry_price, support, prices):
    """左侧：前低；右侧：信号K线低点；兜底：ATR."""
    low = prices['low']
    if len(low) < 2:
        return entry_price * 0.95
    signal_low = low.iloc[-1]
    left_stop = support
    right_stop = signal_low
    stop = min(left_stop, right_stop) if (left_stop and right_stop) else (left_stop or right_stop)
    if stop is None or stop >= entry_price:
        atr = get_atr(prices)
        if atr:
            stop = entry_price - g.stop_atr_mult * atr
        else:
            stop = entry_price * 0.97
    return max(0.01, stop)


# ---------- 06 定仓位（以损定量）----------
def calc_position_size(capital, entry_price, stop_price):
    """总风险 = 本金 * 1.5%；仓位 = 总风险 / 单手风险（每股止损空间）"""
    if entry_price <= stop_price or entry_price <= 0:
        return 0
    risk_amount = capital * g.risk_pct
    risk_per_share = entry_price - stop_price
    shares = int(risk_amount / risk_per_share)
    return max(0, shares)


# ---------- 07 看空间（至少 2:1 盈亏比）----------
def check_space(entry_price, stop_price, prices):
    """目标位：前高或 入场+2*止损距离；空间不足不开仓"""
    high = prices['high']
    n = min(30, len(high) - 1)
    if n < 5:
        return True
    target = high.iloc[-n-1:-1].max()
    stop_dist = entry_price - stop_price
    need_target = entry_price + g.min_reward_ratio * stop_dist
    return target >= need_target or (target - entry_price) >= g.min_reward_ratio * stop_dist


# ---------- 08 开仓 / 10 加仓 ----------
def try_open_or_add(context, entry_price, stop_price, position_value, is_add=False):
    """开仓或加仓：以损定量"""
    capital = context.portfolio.portfolio_value
    if is_add:
        capital = context.portfolio.available_cash
    shares = calc_position_size(capital, entry_price, stop_price)
    if shares <= 0:
        return
    target_value = shares * entry_price
    if target_value > capital * 0.95:
        target_value = capital * 0.95
    if is_add:
        order_target_value(g.security, position_value + target_value)
    else:
        order_target_value(g.security, target_value)


# ---------- 09 平仓 ----------
def check_exit(context, prices, position):
    """打止损、2:1 减半仓、跟踪止盈"""
    if not position or position.total_amount <= 0:
        return
    entry = position.avg_cost
    stop = getattr(g, 'stop_loss', None)
    if stop is None:
        return
    close = prices['close']
    low = prices['low']
    if len(low) < 1:
        return
    last_low = low.iloc[-1]
    last_close = close.iloc[-1]
    # 1) 打止损
    if last_low <= stop:
        order_target(g.security, 0)
        g.stop_loss = None
        g.trailing_stop = None
        g.reduced_half = False
        g.add_count = 0
        return
    # 2) 盈亏比 2:1 减半仓
    if not getattr(g, 'reduced_half', False):
        profit_ratio = (last_close - entry) / (entry - stop) if (entry - stop) > 0 else 0
        if profit_ratio >= g.min_reward_ratio:
            half_value = context.portfolio.positions[g.security].value / 2
            order_target_value(g.security, half_value)
            g.reduced_half = True
            g.trailing_stop = last_low  # 跟踪止盈起点
            return
    # 3) 跟踪止盈（用 ATR）
    trailing = getattr(g, 'trailing_stop', None)
    if trailing is not None and last_low <= trailing:
        order_target(g.security, 0)
        g.stop_loss = None
        g.trailing_stop = None
        g.reduced_half = False
        g.add_count = 0
        return
    # 上移跟踪止盈
    if getattr(g, 'reduced_half', False) and last_close > (entry + (entry - stop)):
        atr = get_atr(prices) if 'high' in prices and len(prices) >= g.atr_period + 1 else None
        if atr:
            new_trail = last_close - g.trailing_atr_mult * atr
            if new_trail > getattr(g, 'trailing_stop', 0):
                g.trailing_stop = new_trail


def rebalance(context):
    security = g.security
    need = max(g.long_ma, g.rsi_period, g.atr_period) + 5
    prices = attribute_history(security, need, '1d', ['open', 'high', 'low', 'close'])
    if prices is None or len(prices) < need:
        return

    position = context.portfolio.positions.get(security)
    hold_amount = position.total_amount if position else 0
    current_price = prices['close'].iloc[-1]

    # ---------- 09 平仓优先 ----------
    if hold_amount > 0:
        check_exit(context, prices, position)
        position = context.portfolio.positions.get(security)
        hold_amount = position.total_amount if position else 0

    # ---------- 01 辨趋势 ----------
    trend, short_ma, long_ma = get_trend(prices)
    if trend is None:
        return

    # ---------- 02 判方向 + 03 找位置 ----------
    direction, support = get_direction_and_location(prices, trend)
    if direction is None:
        return

    # 只做多
    if direction != 'long':
        return

    # ---------- 04 看信号 ----------
    has_sig, sig_type = get_signal(prices, direction)
    if not has_sig:
        return

    # ---------- 05 定止损 ----------
    entry_price = current_price
    stop_price = set_stop_loss(entry_price, support, prices)

    # ---------- 07 看空间 ----------
    if not check_space(entry_price, stop_price, prices):
        return

    # ---------- 06 定仓位 + 08 开仓 / 10 加仓 ----------
    if hold_amount <= 0:
        try_open_or_add(context, entry_price, stop_price, 0, is_add=False)
        g.stop_loss = stop_price
        g.reduced_half = False
        g.add_count = 0
    else:
        # 10 加仓：浮盈且再次满足买点，且未超过加仓次数
        add_count = getattr(g, 'add_count', 0)
        if g.add_only_if_profit and add_count < g.max_add_times:
            entry = position.avg_cost
            if current_price > entry:
                pos_value = context.portfolio.positions[security].value
                try_open_or_add(context, entry_price, stop_price, pos_value, is_add=True)
                g.add_count = add_count + 1
