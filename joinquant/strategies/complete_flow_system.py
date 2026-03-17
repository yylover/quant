# -*- coding: utf-8 -*-
"""
完整交易系统 v3 - ETF 专用版
==================================================
基于「最完善的交易流程图」10 步，针对 ETF 特性全面重构：

  01 辨趋势  02 判方向  03 找位置  04 看信号  05 定止损
  06 定仓位  07 看空间  08 开仓    09 平仓    10 加仓

v2 → v3 核心改进：
  ① 信号（Step04）：放弃旭日东升/阴包阳（K线形态对ETF无效）
                    → 改为「20日突破」+「MA多头排列+RSI健康区间」
  ② 止损（Step05）：1.5×ATR → 3×ATR / 8% 固定止损（减少噪声止损）
  ③ 出场（Step09）：去掉复杂的减半仓逻辑
                    → 固定止损 + 从盈利高点回撤 10% 跟踪离场
  ④ 频率：日度 → 周度（每周一检查），每年最多 ~50 次信号，
           大幅减少交易成本侵蚀
  ⑤ 均线周期：10/30 → 20/60（更适合 ETF 的中期趋势）
  ⑥ 最多持仓：3 → 2（集中持仓，减少分散摩擦）

ETF 池：
  512800.XSHG 银行ETF       159208.XSHE 国防ETF
  515880.XSHG 央企创新ETF   513120.XSHG 恒生科技ETF
  562500.XSHG 中证A50ETF    515220.XSHG 煤炭ETF
  159755.XSHE 游戏ETF       588460.XSHG 科创50ETF
  588050.XSHG 科创板ETF     515400.XSHG 中证1000ETF
  512480.XSHG 半导体ETF     159819.XSHE 人工智能ETF
  512690.XSHG 酒ETF         159869.XSHE 新能源ETF
  512660.XSHG 军工ETF       159928.XSHE 消费ETF
  512170.XSHG 医疗ETF

适用于聚宽 JoinQuant 平台回测。
"""


# ======================================================
# 初始化
# ======================================================
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001,
                  open_commission=0.0003, close_commission=0.0003,
                  min_commission=5),
        type='stock'
    )

    # ---------- ETF 池 ----------
    g.etf_pool = [
        '512800.XSHG',  # 银行ETF
        '159208.XSHE',  # 国防ETF
        '515880.XSHG',  # 央企创新ETF
        '513120.XSHG',  # 恒生科技ETF
        '562500.XSHG',  # 中证A50ETF
        '515220.XSHG',  # 煤炭ETF
        '159755.XSHE',  # 游戏ETF
        '588460.XSHG',  # 科创50ETF
        '588050.XSHG',  # 科创板ETF
        '515400.XSHG',  # 中证1000ETF
        '512480.XSHG',  # 半导体ETF
        '159819.XSHE',  # 人工智能ETF
        '512690.XSHG',  # 酒ETF
        '159869.XSHE',  # 新能源ETF
        '512660.XSHG',  # 军工ETF
        '159928.XSHE',  # 消费ETF
        '512170.XSHG',  # 医疗ETF
    ]

    # ---------- 01 辨趋势：均线周期 ----------
    g.short_ma        = 20    # 短期均线（20日，约1个月）
    g.long_ma         = 60    # 长期均线（60日，约3个月）
    g.trend_threshold = 0.003  # 均线偏差阈值（降低，震荡期也可参与）

    # ---------- 04 看信号：ETF适用信号 ----------
    g.breakout_days = 20      # 突破信号：价格突破N日最高价
    g.rsi_period    = 14
    g.rsi_low       = 45      # RSI健康区间下限（ETF不常跌到超卖区）
    g.rsi_high      = 70      # RSI健康区间上限（未过热）

    # ---------- 05 定止损：宽止损减少噪声止损 ----------
    g.atr_period      = 14
    g.stop_atr_mult   = 3.0   # 止损宽度：3×ATR
    g.fixed_stop_pct  = 0.08  # 兜底：固定8%止损

    # ---------- 06 定仓位 ----------
    g.risk_pct      = 0.015   # 单笔最大风险：净值1.5%
    g.max_positions = 2       # slot_cap 计算基准（固定为2，不随大盘变化；实际持仓数由 get_market_regime() 动态决定）

    # ---------- 07 看空间 ----------
    g.min_reward_ratio = 1.5  # 最低盈亏比1.5:1（ETF波动幅度较小）

    # ---------- 09 平仓：简化出场逻辑 ----------
    g.trailing_pct   = 0.10   # 跟踪止盈：从持仓最高点回撤10%离场
    g.profit_trigger = 0.03   # 达到3%浮盈后启动跟踪止盈（更早锁利）

    # ---------- 10 加仓 ----------
    g.max_add_times = 1

    # 每个标的独立状态：{security: {'stop': float, 'highest': float, 'add_count': int}}
    g.state = {}

    # 每周一检查信号（大幅降低交易频率和手续费）
    run_weekly(rebalance, weekday=1, time='open')


# ======================================================
# 01 辨趋势
# ======================================================
def get_trend(prices):
    """均线多头/空头/震荡"""
    close = prices['close']
    if len(close) < g.long_ma + 1:
        return None
    short = close.iloc[-g.short_ma:].mean()
    long_ = close.iloc[-g.long_ma:].mean()
    if long_ <= 0:
        return None
    diff = (short - long_) / long_
    if diff > g.trend_threshold:
        return 'up'
    if diff < -g.trend_threshold:
        return 'down'
    return 'flat'


# ======================================================
# 03 找位置（支撑/阻力）
# ======================================================
def get_support(prices, trend):
    """用近期低点或短期均线作为支撑，计算止损参考位"""
    close = prices['close']
    low   = prices['low']
    n = min(20, len(close) - 1)
    if n < 5:
        return None
    if trend == 'up':
        # 上涨趋势中，近期低点是支撑
        return low.iloc[-n-1:-1].min()
    return close.iloc[-g.short_ma:].mean()  # 震荡时用短均线


# ======================================================
# 04 看信号（ETF专用）
# ======================================================
def _calc_rsi(close_series, period):
    delta    = close_series.diff()
    gain     = delta.where(delta > 0, 0.0)
    loss     = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def get_signal(prices):
    """
    ETF 适用信号（替代 K 线形态）：
      强信号：收盘价突破近 N 日最高价（动能突破）
      弱信号：均线多头排列 + RSI 在健康区间且上升
    返回 (has_signal, 'strong'/'weak'/None)
    """
    close = prices['close']
    high  = prices['high']

    if len(close) < max(g.breakout_days, g.rsi_period) + 2:
        return False, None

    current = close.iloc[-1]

    # 强信号：突破近 N 日高点（不含当日）
    recent_high = high.iloc[-g.breakout_days-1:-1].max()
    if current > recent_high:
        return True, 'strong'

    # 弱信号：均线多头 + RSI 在健康区间且正在上升
    rsi_series = _calc_rsi(close, g.rsi_period)
    rsi_now    = rsi_series.iloc[-1]
    rsi_prev   = rsi_series.iloc[-2] if len(rsi_series) >= 2 else rsi_now
    if rsi_now != rsi_now:  # NaN check
        return False, None

    ma_short = close.iloc[-g.short_ma:].mean()
    ma_long  = close.iloc[-g.long_ma:].mean()
    ma_ok    = current > ma_short > ma_long
    rsi_ok   = g.rsi_low <= rsi_now <= g.rsi_high and rsi_now > rsi_prev

    if ma_ok and rsi_ok:
        return True, 'weak'

    return False, None


# ======================================================
# 05 定止损
# ======================================================
def _get_atr(prices):
    h, l = prices['high'], prices['low']
    if len(h) < g.atr_period:
        return None
    atr = (h - l).rolling(g.atr_period).mean().iloc[-1]
    return float(atr) if atr and atr > 0 else None


def calc_stop(entry_price, support, prices):
    """
    止损 = max(support - 1ATR, entry - 3ATR, entry × 92%)
    三者取最高（离入场最近），保证止损不会过宽
    """
    atr = _get_atr(prices)
    stops = []
    if atr:
        stops.append(entry_price - g.stop_atr_mult * atr)
        if support:
            stops.append(support - atr)
    stops.append(entry_price * (1 - g.fixed_stop_pct))
    return max(0.01, max(stops))  # 取最近的止损（最高价格）


# ======================================================
# 06 定仓位（以损定量，每槽独立）
# ======================================================
def calc_trade_value(portfolio_value, entry_price, stop_price):
    if entry_price <= stop_price or entry_price <= 0:
        return 0
    slot_cap    = portfolio_value / g.max_positions * 0.95
    risk_amount = portfolio_value * g.risk_pct
    risk_share  = entry_price - stop_price
    value       = (risk_amount / risk_share) * entry_price
    return min(value, slot_cap)


# ======================================================
# 07 看空间（盈亏比 >= min_reward_ratio）
# ======================================================
def check_space(entry_price, stop_price, prices):
    n = min(40, len(prices['high']) - 1)
    if n < 5:
        return True
    target    = prices['high'].iloc[-n-1:-1].max()
    stop_dist = entry_price - stop_price
    if stop_dist <= 0:
        return False
    return (target - entry_price) >= g.min_reward_ratio * stop_dist


# ======================================================
# 09 平仓：固定止损 + 跟踪止盈（简化版，适合ETF）
# ======================================================
def check_exit_one(context, security, prices):
    """
    出场逻辑：
      1. 固定止损：跌破止损价立即离场
      2. 跟踪止盈：盈利超过 profit_trigger 后，
                   从持仓期最高点回撤 trailing_pct 时离场
    返回 True 表示已平仓。
    """
    state    = g.state.get(security)
    position = context.portfolio.positions.get(security)

    if not position or position.total_amount <= 0:
        g.state.pop(security, None)
        return True
    if not state:
        return False

    current = prices['close'].iloc[-1]
    entry   = position.avg_cost
    stop    = state.get('stop', entry * (1 - g.fixed_stop_pct))

    # 更新持仓期最高价
    state['highest'] = max(state.get('highest', entry), current)

    # 1) 固定止损
    if current <= stop:
        order_target(security, 0)
        g.state.pop(security, None)
        log.info('[止损] {} 现价={:.3f} 止损={:.3f}'.format(security, current, stop))
        return True

    # 2) 跟踪止盈（只有在浮盈超过阈值后才激活）
    profit_pct = (current - entry) / entry
    if profit_pct >= g.profit_trigger:
        trail_line = state['highest'] * (1 - g.trailing_pct)
        if current <= trail_line:
            order_target(security, 0)
            g.state.pop(security, None)
            log.info('[跟踪止盈] {} 现价={:.3f} 跟踪线={:.3f}'.format(
                security, current, trail_line))
            return True

    return False


# ======================================================
# 主调仓逻辑（每周一执行）
# ======================================================
def rebalance(context):
    need = max(g.long_ma, g.rsi_period, g.atr_period, g.breakout_days) + 5

    # -------- 09 平仓优先 --------
    for sec in list(context.portfolio.positions.keys()):
        prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
        if prices is None or len(prices) < need:
            continue
        check_exit_one(context, sec, prices)

    # -------- 检查剩余开仓容量 --------
    open_slots = g.max_positions - len(context.portfolio.positions)
    if open_slots <= 0:
        return

    # -------- 扫描 ETF 池，收集满足 1-7 步的候选标的 --------
    # 结构：(rank, security, entry_price, stop_price)
    # rank: 0=强信号突破, 1=弱信号趋势
    candidates = []

    for sec in g.etf_pool:
        if sec in context.portfolio.positions:
            continue  # 已持有，跳过

        prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
        if prices is None or len(prices) < need:
            continue

        # 01 辨趋势
        trend = get_trend(prices)
        if trend != 'up':
            continue  # 只做上升趋势

        # 04 看信号（ETF化信号）
        has_sig, sig_type = get_signal(prices)
        if not has_sig:
            continue

        entry_price = prices['close'].iloc[-1]

        # 03 找位置（支撑）
        support = get_support(prices, trend)

        # 05 定止损
        stop_price = calc_stop(entry_price, support, prices)

        # 07 看空间
        if not check_space(entry_price, stop_price, prices):
            continue

        rank = 0 if sig_type == 'strong' else 1
        candidates.append((rank, sec, entry_price, stop_price))

    if not candidates:
        return

    # 强信号优先，同级按 ETF 池顺序
    candidates.sort(key=lambda x: x[0])
    portfolio_value = context.portfolio.portfolio_value

    for rank, sec, entry_price, stop_price in candidates[:open_slots]:
        # 06 定仓位
        trade_val = calc_trade_value(portfolio_value, entry_price, stop_price)
        if trade_val <= 0:
            continue
        avail = context.portfolio.available_cash * 0.95
        if trade_val > avail:
            trade_val = avail
        if trade_val <= 0:
            continue

        # 08 开仓
        order_target_value(sec, trade_val)
        g.state[sec] = {
            'stop':      stop_price,
            'highest':   entry_price,
            'add_count': 0,
        }
        log.info('[{}信号开仓] {} 入场={:.3f} 止损={:.3f} 风险={:.1%}'.format(
            '强' if rank == 0 else '弱',
            sec, entry_price, stop_price,
            (entry_price - stop_price) / entry_price
        ))

    # -------- 10 加仓：浮盈且再次满足买点 --------
    for sec in list(context.portfolio.positions.keys()):
        state = g.state.get(sec)
        if not state or state.get('add_count', 0) >= g.max_add_times:
            continue
        position = context.portfolio.positions.get(sec)
        if not position or position.total_amount <= 0:
            continue

        current = context.portfolio.positions[sec].price
        if current <= position.avg_cost * 1.03:  # 至少浮盈3%才考虑加仓
            continue

        prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
        if prices is None or len(prices) < need:
            continue

        if get_trend(prices) != 'up':
            continue
        has_sig, _ = get_signal(prices)
        if not has_sig:
            continue

        support    = get_support(prices, 'up')
        stop_price = calc_stop(current, support, prices)
        add_val    = min(
            portfolio_value / g.max_positions * 0.95,
            context.portfolio.available_cash * 0.95
        )
        if add_val <= 0:
            continue

        pos_val = position.value
        order_target_value(sec, pos_val + add_val)
        state['add_count'] = state.get('add_count', 0) + 1
        log.info('[加仓] {} 浮盈={:.1%}'.format(
            sec, (current - position.avg_cost) / position.avg_cost))
