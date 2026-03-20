# -*- coding: utf-8 -*-
"""
完整交易系统 v3 - ETF 专用版
==================================================

一、与「流程图 10 步」的对应关系
--------------------------------
  01 辨趋势  → get_trend()：20/60 双均线偏离，分 up / down / flat
  02 判方向  → 只做多：明确 down 则不买；flat/up 可参与（与 v3 放宽一致）
  03 找位置 → get_support()：上涨用近期前低，震荡用短均线作止损参考
  04 看信号 → calc_momentum_score()：突破 + RSI 区间 + 均线偏离 合成 0～100 分（非二元 K 线）
  05 定止损 → calc_stop()：max(支撑-ATR, 入场-3ATR, 入场×92%) 取「最贵」止损价 = 最紧风控
  06 定仓位 → calc_trade_value()：单笔风险=净值×risk_pct，且不超过「每槽上限×市场环境系数」
  07 看空间 → check_space()：前高与入场距离 ≥ 1.5×止损距离才开仓
  08 开仓    → rebalance：每周按得分选前 N 只，order_target_value
  09 平仓    → check_exit_one()：硬止损 或 浮盈≥3% 后从最高价回撤 10% 离场
  10 加仓    → rebalance 末尾：浮盈≥3%、趋势非 down、得分≥30，补到目标槽位市值

二、整体策略分析（定性）
--------------------------------
**策略类型**：多标的 ETF 轮动 + 趋势/动量过滤 + 以损定量仓位 + 大盘（沪深300）分档降仓。

**核心思想**：
  - 在较大 ETF 池里，每周筛选「趋势非空头 + 动量评分≥30」的标的；
  - 用较宽止损（3×ATR 与 8% 兜底）减少 ETF 日噪声扫损；
  - 用沪深300 相对 MA60 划分牛/震/熊：熊市最多 1 只且仓位系数 0.4，控制系统性风险暴露；
  - 周频调仓降低换手与佣金侵蚀（相对日频）。

**优势**：
  - 分散行业主题，单只黑天鹅影响有限；大盘差时自动缩仓、减槽位。
  - 信号可解释（突破、RSI 健康区、均线多头），适合与回测报告对照。
  - 出场规则简单：止损 + 盈利后跟踪止盈，无复杂分批减仓状态机。

**风险与局限**：
  - 周频可能错过周内急涨急跌；涨停/流动性差的 ETF 实盘与回测有差异。
  - 动量评分阈值、权重（40/30/30）与参数存在过拟合可能，需样本外或多区间验证。
  - JoinQuant 注释已说明：当日发出平仓后 positions 仍可能计到收盘，open_slots 计算偏保守。
  - set_order_cost 使用股票印花税模型，ETF 实盘通常无印花税，回测偏悲观或需按平台改费用。

**适用场景**：中长期趋势与结构行情、愿意承担一定回撤以换取行业轮动暴露；不适合要求日内精确进出的策略。

三、v2 → v3 核心改进（摘要）
--------------------------------
  ① 信号：K 线形态 → 20 日突破 + MA + RSI 合成评分
  ② 止损：更宽（3×ATR、8% 兜底）
  ③ 出场：固定止损 + 盈利达标后回撤 10% 跟踪止盈
  ④ 频率：日度 → 每周一 open
  ⑤ 均线：10/30 → 20/60
  ⑥ 持仓槽位：最多 2，且熊市降为 1

四、ETF 池（与 g.etf_pool 一致）
--------------------------------
  银行/国防/央企创新/恒生科技/A50/煤炭/游戏/科创50/科创板/中证1000/
  半导体/人工智能/酒/新能源/军工/消费/医疗 等（代码见 initialize）。

适用于聚宽 JoinQuant 平台回测。
"""


# ======================================================
# 初始化
# ======================================================
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    # 费用按股票模板：含卖出印花税。纯 ETF 回测若需更贴近实盘可关闭或调低 close_tax（见模块说明）
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001,
                  open_commission=0.0003, close_commission=0.0003,
                  min_commission=5),
        type='stock'
    )

    # ---------- ETF 池（行业/主题分散，单票流动性上市日期以聚宽数据为准）----------
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
    # 短均线高于长均线超过该比例判为 up；低于负阈值判 down；否则 flat（震荡也可交易）
    g.trend_threshold = 0.003

    # ---------- 04 看信号：动量评分三要素（突破 / RSI 健康区 / 均线多头强度）----------
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
    # 单票「满槽」名义资金≈净值/2×0.95，再乘 regime_factor；实际最多几只由 get_market_regime 返回的 max_open_positions 限制
    g.max_positions = 2

    # ---------- 07 看空间：潜在止盈空间相对止损腿的长度 ----------
    g.min_reward_ratio = 1.5  # 恢复为 1.5:1，保证盈亏比质量

    # ---------- 09 平仓：简化出场逻辑 ----------
    g.trailing_pct   = 0.10   # 跟踪止盈：从持仓最高点回撤10%离场
    g.profit_trigger = 0.03   # 达到3%浮盈后启动跟踪止盈（更早锁利）

    # ---------- 10 加仓 ----------
    g.max_add_times = 1

    # 每标的独立状态：止损价、持仓期最高价（跟踪止盈用）、已加仓次数
    g.state = {}

    # weekday=1：每周一开盘逻辑；年内调仓次数远少于日频，注意与「周线收盘确认」类定义的差异
    run_weekly(rebalance, weekday=1, time='open')


# ======================================================
# 01 辨趋势
# ======================================================
def get_trend(prices):
    """根据短/长均线相对位置划分 up / down / flat（无价格，仅用均线差）。"""
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
# 市场环境分档（大盘过滤）
# ======================================================
def get_market_regime():
    """
    以沪深300（000300.XSHG）MA60 为基准，判断市场环境。
    返回 (max_open_positions, regime_factor)：
      牛市（偏差 > +2%）：(2, 1.00)
      震荡（偏差 ±2%）  ：(2, 0.70)
      熊市（偏差 < -2%）：(1, 0.40)
    fallback（数据不足）：(2, 0.70)
    """
    data = attribute_history('000300.XSHG', 65, '1d', ['close'])
    if data is None or len(data) < 60:
        return 2, 0.70  # 数据不足，默认按震荡档处理

    close = data['close']
    current = close.iloc[-1]
    ma60 = close.iloc[-60:].mean()

    if ma60 <= 0:
        return 2, 0.70

    diff = (current - ma60) / ma60
    if diff > 0.02:
        return 2, 1.00   # 牛市
    elif diff < -0.02:
        return 1, 0.40   # 熊市
    else:
        return 2, 0.70   # 震荡


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
# 04 看信号（ETF专用）→ 动量评分
# ======================================================
def _calc_rsi(close_series, period):
    delta    = close_series.diff()
    gain     = delta.where(delta > 0, 0.0)
    loss     = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


# ======================================================
# 动量评分（替代二元信号）
# ======================================================
def calc_momentum_score(prices):
    """
    综合动量评分，返回 0.0～100.0。
    数据不足（< g.long_ma + 1 条）或 RSI 为 NaN 时返回 0.0。

    子项（各自独立上限，三项之和最大为100）：
      突破强度（40分）：收盘突破近 g.breakout_days 日高点的幅度，5%→满分
      RSI强度  （30分）：RSI 在 45～70 线性映射；RSI > 70 强制为 0
      均线斜率  （30分）：短均线高于长均线的偏差，3%→满分；负偏差为 0
    """
    close = prices['close']
    high  = prices['high']

    if len(close) < g.long_ma + 1:
        return 0.0

    current = close.iloc[-1]

    # --- 突破强度（40 分）：最近一日收盘相对「不含当日的 breakout_days 日最高价」的超额幅度 ---
    recent_high = high.iloc[-g.breakout_days - 1:-1].max()
    if recent_high > 0:
        breakout_ratio = (current - recent_high) / recent_high
        breakout_score = min(max(breakout_ratio, 0) / 0.05, 1.0) * 40
    else:
        breakout_score = 0.0

    # --- RSI（30 分）：45～70 线性给分；>70 视为过热，避免追高 ---
    rsi_series = _calc_rsi(close, g.rsi_period)
    rsi = rsi_series.iloc[-1]
    if rsi != rsi:  # NaN check
        return 0.0
    if rsi <= 70:
        rsi_score = max((rsi - 45) / 25, 0) * 30
    else:
        rsi_score = 0.0  # 过热，避免追高

    # --- 均线多头强度（30 分）：短均高于长均的相对幅度，最大按 3% 饱和 ---
    ma_short = close.iloc[-g.short_ma:].mean()
    ma_long  = close.iloc[-g.long_ma:].mean()
    if ma_long > 0:
        slope_ratio = (ma_short - ma_long) / ma_long
        slope_score = min(max(slope_ratio, 0) / 0.03, 1.0) * 30
    else:
        slope_score = 0.0

    return breakout_score + rsi_score + slope_score


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
    在多个候选止损价中取 max（数值最大 = 离入场价最近的止损线 = 单笔亏损相对最紧）。
    候选含：支撑下修 1ATR、入场下 3×ATR、入场下 8%。
    """
    atr = _get_atr(prices)
    stops = []
    if atr:
        stops.append(entry_price - g.stop_atr_mult * atr)
        if support:
            stops.append(support - atr)
    stops.append(entry_price * (1 - g.fixed_stop_pct))
    return max(0.01, max(stops))


# ======================================================
# 06 定仓位（以损定量，每槽独立）
# ======================================================
def calc_trade_value(portfolio_value, entry_price, stop_price, regime_factor=1.0):
    """以损定量：目标市值 = (净值×单笔风险比例) / 每股止损空间 × 入场价，且不超过单槽上限×环境系数。"""
    if entry_price <= stop_price or entry_price <= 0:
        return 0
    slot_cap    = portfolio_value / g.max_positions * 0.95 * regime_factor
    risk_amount = portfolio_value * g.risk_pct
    risk_share  = entry_price - stop_price
    value       = (risk_amount / risk_share) * entry_price
    return min(value, slot_cap)


# ======================================================
# 07 看空间（盈亏比 >= min_reward_ratio）
# ======================================================
def check_space(entry_price, stop_price, prices):
    """用不含当日的近 n 日最高价近似「上方空间」，需 ≥ min_reward_ratio × 止损距离才允许开仓。"""
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
    """
    每周主流程：先大盘分档 → 逐标的检查出场 → 算剩余槽位 →
    扫描池内未持仓 ETF → 过滤趋势/评分/止损/空间 → 按分排序开仓 → 最后处理加仓。
    """
    need = max(g.long_ma, g.rsi_period, g.atr_period, g.breakout_days) + 5

    # -------- 大盘环境：决定最多几只 + 单槽资金缩放系数 --------
    max_open_positions, regime_factor = get_market_regime()
    log.info('[市场环境] max_open_positions={} regime_factor={:.0%}'.format(
        max_open_positions, regime_factor))

    # -------- 09 平仓优先（有仓的标的先跑止损/跟踪止盈）--------
    for sec in list(context.portfolio.positions.keys()):
        prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
        if prices is None or len(prices) < need:
            continue
        check_exit_one(context, sec, prices)

    # -------- 剩余可开新仓槽位 --------
    # 注意：若本交易日已发平仓，部分环境下 positions 仍可能计到收盘，open_slots 可能暂时为 0（偏保守）
    open_slots = max_open_positions - len(context.portfolio.positions)
    if open_slots <= 0:
        return

    # -------- 扫描池子：未持仓标的 → 趋势/评分/支撑止损/空间 → 候选列表 --------
    candidates = []  # 元素 (score, security, entry_price, stop_price)

    for sec in g.etf_pool:
        if sec in context.portfolio.positions:
            continue  # 已持有，留给后段加仓逻辑

        prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
        if prices is None or len(prices) < need:
            continue

        trend = get_trend(prices)
        if trend == 'down':
            continue  # 02/01：明确空头不参与（只做多）

        score = calc_momentum_score(prices)
        if score < 30:
            continue  # 04：动量不足不进场

        entry_price = prices['close'].iloc[-1]

        support = get_support(prices, trend)

        stop_price = calc_stop(entry_price, support, prices)

        if not check_space(entry_price, stop_price, prices):
            continue  # 07：上方空间不够盈亏比要求

        candidates.append((score, sec, entry_price, stop_price))

    if not candidates:
        return

    # 08：高分优先，填满 open_slots 个新仓
    candidates.sort(key=lambda x: x[0], reverse=True)
    portfolio_value = context.portfolio.portfolio_value

    for score, sec, entry_price, stop_price in candidates[:open_slots]:
        trade_val = calc_trade_value(portfolio_value, entry_price, stop_price, regime_factor)
        if trade_val <= 0:
            continue
        avail = context.portfolio.available_cash * 0.95
        if trade_val > avail:
            trade_val = avail
        if trade_val <= 0:
            continue

        order_target_value(sec, trade_val)
        g.state[sec] = {
            'stop':      stop_price,
            'highest':   entry_price,
            'add_count': 0,
        }
        log.info('[开仓] {} 得分={:.1f} 入场={:.3f} 止损={:.3f} 风险={:.1%} 环境系数={:.0%}'.format(
            sec, score, entry_price, stop_price,
            (entry_price - stop_price) / entry_price,
            regime_factor
        ))

    # -------- 10 加仓：已有仓、未超加仓次数、浮盈≥3%、趋势与评分仍达标 --------
    for sec in list(context.portfolio.positions.keys()):
        state = g.state.get(sec)
        if not state or state.get('add_count', 0) >= g.max_add_times:
            continue
        position = context.portfolio.positions.get(sec)
        if not position or position.total_amount <= 0:
            continue

        current = context.portfolio.positions[sec].price
        if current <= position.avg_cost * 1.03:
            continue  # 与 g.profit_trigger 对齐：无浮盈不加

        prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
        if prices is None or len(prices) < need:
            continue

        if get_trend(prices) == 'down':
            continue
        if calc_momentum_score(prices) < 30:
            continue

        support    = get_support(prices, 'up')
        stop_price = calc_stop(current, support, prices)

        # 目标总市值 ≈ 按当前价重算的槽位目标，add_val = 目标 − 现仓，避免一步加过头
        pos_val    = position.value
        target_val = calc_trade_value(portfolio_value, current, stop_price, regime_factor)
        add_val    = max(0, target_val - pos_val)
        avail      = context.portfolio.available_cash * 0.95
        add_val    = min(add_val, avail)
        if add_val <= 0:
            continue

        order_target_value(sec, pos_val + add_val)
        state['add_count'] = state.get('add_count', 0) + 1
        log.info('[加仓] {} 浮盈={:.1%} 加仓量={:.0f}'.format(
            sec, (current - position.avg_cost) / position.avg_cost, add_val))
