# -*- coding: utf-8 -*-
"""
网格策略 (Grid Trading)
在设定价格区间内等分网格，价格每下跌一档加仓、每上涨一档减仓，赚取波动价差。
适用于聚宽 JoinQuant 平台回测。
"""


def initialize(context):
    """初始化"""
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock'
    )
    g.security = '510300.XSHG'
    # 网格参数：用近期高低点估计区间，或手动设固定区间
    g.use_adaptive_range = True   # True=用过去 N 日高低点动态算区间
    g.range_days = 60             # 动态区间回溯天数
    g.grid_num = 5                # 网格档数
    g.position_per_grid = 0.2     # 每档仓位占比（总资金的 20% 一档）
    run_daily(rebalance, time='open')


def get_grid_range(context):
    """获取网格上下界"""
    if g.use_adaptive_range:
        prices = attribute_history(g.security, g.range_days, '1d', ['high', 'low'])
        if prices is None or len(prices) < 10:
            return None, None
        low = prices['low'].min()
        high = prices['high'].max()
        return low, high
    # 固定区间示例（可按标的修改）
    return 3.5, 5.5


def rebalance(context):
    """每日调仓：按当前价落在哪一档决定目标仓位"""
    low, high = get_grid_range(context)
    if low is None or high is None or high <= low:
        return
    prices = attribute_history(g.security, 1, '1d', ['close'])
    if prices is None or len(prices) == 0:
        return
    current = prices['close'].iloc[-1]
    total_value = context.portfolio.portfolio_value
    step = (high - low) / g.grid_num
    # 当前价在第几格（0=最低格，越跌格越小，越买越多）
    if current <= low:
        grid_index = 0
    elif current >= high:
        grid_index = g.grid_num
    else:
        grid_index = int((current - low) / step)
        if grid_index >= g.grid_num:
            grid_index = g.grid_num - 1
    # 目标仓位：格越低（价格越低）仓位越高
    target_ratio = (g.grid_num - grid_index) / (g.grid_num + 1)
    target_ratio = min(0.95, max(0, target_ratio))
    target_value = total_value * target_ratio
    order_target_value(g.security, target_value)
