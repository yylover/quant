# -*- coding: utf-8 -*-
"""
单 ETF 趋势 + 网格交易系统（标的：512800.XSHG 银行 ETF）
==========================================================

核心思想：
  1. 只交易 512800，一切从简，专注一个标的；
  2. 用中期均线（MA20 / MA60）做趋势过滤，只在上升趋势参与；
  3. 上升趋势内建立「核心趋势仓位」，长期持有；
  4. 在核心仓位基础上叠加「小网格」高抛低吸，平滑成本、增加收益。

实现要点：
  - 趋势判定：MA20 和 MA60，偏差超过阈值才视为趋势明确；
  - 核心仓位：在上升趋势中，把总资产的一定比例配置到 512800；
  - 网格仓位：在价格围绕近期均价波动时，按固定百分比网格加减仓；
  - 在趋势转为空头时，全部清仓并重置网格状态。

适用于聚宽 JoinQuant 平台回测。


策略收益
9.17%
策略年化收益
0.97%
超额收益
-22.00%
基准收益
39.95%
阿尔法
-0.029
贝塔
0.367
夏普比率
-0.221
胜率
0.675
盈亏比
1.209
最大回撤 
27.17%
索提诺比率
-0.277
日均超额收益
-0.01%
超额收益最大回撤
41.81%
超额收益夏普比率
-0.402
日胜率
0.493
盈利次数
54
亏损次数
26
信息比率
-0.168
策略波动率
0.137
基准波动率
0.183
最大回撤区间
2021/02/18,2023/06/26
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

    # -------- 交易标的，仅 512800 --------
    g.symbol = '512800.XSHG'

    # -------- 趋势参数（单 ETF 经典趋势过滤） --------
    # 使用更经典的「价格相对长期均线」趋势判定，而不是 MA 差值：
    #   close > MA60 且 MA60 向上 → up
    #   close < MA60 且 MA60 向下 → down
    #   其余视为 flat
    g.long_ma = 60

    # -------- 仓位与网格参数 --------
    # 单 ETF 趋势策略，以趋势为主：上升趋势时尽量满仓持有
    g.core_pos_pct = 1.0        # 上升趋势内的核心仓位占比（占总资产）
    # 网格作为增强收益的小辅助，轻量化处理
    g.grid_unit_pct = 0.02      # 每一档网格交易占总资产的比例（2% 资产高抛低吸）
    g.grid_step_pct = 0.02      # 网格间距：价格变动 2% 触发一档
    g.max_grid_up = 5           # 单个趋势周期内，最多「高抛」几档
    g.max_grid_down = 5         # 单个趋势周期内，最多「低吸」几档

    # 网格状态：
    #   ref_price     ：最近一次网格交易价格（或核心仓开仓价）
    #   up_count      ：已完成的向上卖出档数
    #   down_count    ：已完成的向下买入档数
    g.grid_state = {
        'ref_price': None,
        'up_count': 0,
        'down_count': 0,
    }

    # 日频执行，更适合网格细节
    run_daily(handle, time='open')


# ======================================================
# 趋势判定：基于价格与 MA60
# ======================================================
def get_trend(prices):
    """
    返回：
      'up'   : 上升趋势
      'down' : 下降趋势
      'flat' : 震荡 / 不明朗
      None   : 数据不足
    """
    close = prices['close']
    if len(close) < g.long_ma + 2:
        return None

    # 长期均线（MA60）
    ma_long_now = close.iloc[-g.long_ma:].mean()
    ma_long_prev = close.iloc[-g.long_ma-1:-1].mean()
    if ma_long_now <= 0 or ma_long_prev <= 0:
        return None

    slope_up = ma_long_now > ma_long_prev  # MA60 向上
    slope_down = ma_long_now < ma_long_prev  # MA60 向下

    price_now = close.iloc[-1]

    # 价格站上 MA60 且 MA60 向上 → 上升趋势
    if price_now > ma_long_now and slope_up:
        return 'up'
    # 价格跌破 MA60 且 MA60 向下 → 下降趋势
    if price_now < ma_long_now and slope_down:
        return 'down'

    # 其余情况视为震荡 / 不明朗
    return 'flat'


# ======================================================
# 主逻辑：趋势 + 网格
# ======================================================
def handle(context):
    symbol = g.symbol

    # 获取足够的历史数据用于趋势判断
    need = g.long_ma + 5
    prices = attribute_history(symbol, need, '1d', ['open', 'high', 'low', 'close'])
    if prices is None or len(prices) < need:
        return

    trend = get_trend(prices)
    current_price = prices['close'].iloc[-1]

    position = context.portfolio.positions.get(symbol)
    has_position = position is not None and position.total_amount > 0

    # ---------------- 趋势空头 → 清仓 & 重置网格 ----------------
    if trend == 'down':
        if has_position:
            order_target(symbol, 0)
            log.info('[清仓] 趋势转空，卖出全部 {}'.format(symbol))
        reset_grid_state()
        return

    # 趋势不明朗（flat 或 None）→ 不开新仓，但保留已有仓位（可选）
    if trend != 'up':
        # 保留已有仓位，不做网格操作，只是观望
        return

    # ---------------- 上升趋势：建立 / 维持核心仓位 ----------------
    portfolio_value = context.portfolio.portfolio_value
    core_target_value = portfolio_value * g.core_pos_pct

    current_value = position.value if has_position else 0

    # 若当前持仓低于核心仓位 90%，则调整到核心目标仓位
    if current_value < core_target_value * 0.9:
        order_target_value(symbol, core_target_value)
        log.info('[核心仓位] 调整到核心仓位 {:.1f}% 总资产'.format(g.core_pos_pct * 100))
        # 核心仓开仓后，以当前价作为网格参考价起点
        g.grid_state['ref_price'] = current_price
        g.grid_state['up_count'] = 0
        g.grid_state['down_count'] = 0
        return

    # 若当前仓位明显高于核心仓位太多（极端情况），也可以适当回调回核心区域
    if current_value > core_target_value * 1.3:
        order_target_value(symbol, core_target_value)
        log.info('[核心仓位] 回调过高仓位至核心区间')
        g.grid_state['ref_price'] = current_price
        g.grid_state['up_count'] = 0
        g.grid_state['down_count'] = 0
        return

    # ---------------- 上升趋势 + 核心仓已建立：执行网格交易 ----------------
    if g.grid_state['ref_price'] is None:
        g.grid_state['ref_price'] = current_price

    do_grid_trading(context, symbol, current_price)


def reset_grid_state():
    g.grid_state['ref_price'] = None
    g.grid_state['up_count'] = 0
    g.grid_state['down_count'] = 0


def do_grid_trading(context, symbol, current_price):
    """
    在上升趋势且核心仓位已建立的前提下：
      - 价格每跌 1×grid_step_pct，相对上一个 ref_price 低吸一档；
      - 价格每涨 1×grid_step_pct，相对上一个 ref_price 高抛一档；
    每一档交易金额 = 总资产 * grid_unit_pct。
    """
    portfolio_value = context.portfolio.portfolio_value
    position = context.portfolio.positions.get(symbol)
    if position is None or position.total_amount <= 0:
        return

    ref_price = g.grid_state['ref_price']
    if ref_price is None or ref_price <= 0:
        g.grid_state['ref_price'] = current_price
        return

    grid_unit_value = portfolio_value * g.grid_unit_pct
    if grid_unit_value < 1000:  # 太小就不折腾，避免手续费噪音
        return

    # 价格较 ref_price 下跌 → 低吸
    down_threshold = ref_price * (1 - g.grid_step_pct)
    # 价格较 ref_price 上涨 → 高抛
    up_threshold = ref_price * (1 + g.grid_step_pct)

    # --- 低吸网格 ---
    if current_price <= down_threshold and g.grid_state['down_count'] < g.max_grid_down:
        # 可用现金检查
        avail_cash = context.portfolio.available_cash * 0.95
        trade_value = min(grid_unit_value, avail_cash)
        if trade_value > 0:
            order_value(symbol, trade_value)
            g.grid_state['down_count'] += 1
            g.grid_state['ref_price'] = current_price
            log.info('[网格低吸] 价格跌破 {:.2f}，买入约 {:.0f} 元，下档次数={}'.format(
                down_threshold, trade_value, g.grid_state['down_count']))
        return

    # --- 高抛网格 ---
    # 避免把所有仓位都卖光，只在核心仓位以上做高抛
    position_value = position.value
    core_floor_value = portfolio_value * g.core_pos_pct * 0.8  # 保留至少 80% 核心仓

    if current_price >= up_threshold and g.grid_state['up_count'] < g.max_grid_up:
        # 预计卖出一档后仍不低于核心下限
        potential_value = position_value - grid_unit_value
        if potential_value >= core_floor_value:
            order_value(symbol, -grid_unit_value)
            g.grid_state['up_count'] += 1
            g.grid_state['ref_price'] = current_price
            log.info('[网格高抛] 价格突破 {:.2f}，卖出约 {:.0f} 元，上档次数={}'.format(
                up_threshold, grid_unit_value, g.grid_state['up_count']))

