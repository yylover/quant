# -*- coding: utf-8 -*-
"""
PSAR均值回归策略 (PSAR Mean Reversion)
======================================

策略原理：
PSAR（Parabolic SAR，抛物线转向指标）是一种趋势跟踪指标，
用于确定止损点和趋势反转点。

计算逻辑：
- 上升趋势：SAR位于价格下方，随时间上升
- 下降趋势：SAR位于价格上方，随时间下降
- 当价格突破SAR时，趋势反转

均值回归应用：
- 计算价格相对于PSAR线的偏离程度
- 当偏离过大时，预期价格会向PSAR线回归
- 使用标准差量化偏离程度

交易规则：
- 买入条件：价格 < PSAR - k × std（过度偏离下方）
- 卖出条件：价格 > PSAR + k × std（过度偏离上方）
- 平仓条件：价格回到正常偏离范围内

参数说明：
- g.af = 0.02: 加速因子初始值
- g.max_af = 0.2: 最大加速因子
- g.lookback = 3: 计算偏离度的回看期
- g.k = 1.5: 偏离阈值倍数

适用场景：
- 有明确趋势的市场
- 价格围绕趋势线波动
- 适合捕捉趋势中的均值回归

优势：
- 结合趋势信息
- PSAR自动调整方向
- 可以识别过度延伸

风险：
- 在震荡市中PSAR频繁转向
- 需要合理设置偏离阈值
- 计算相对复杂

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
    g.af = 0.02            # 加速因子初始值
    g.max_af = 0.2         # 最大加速因子
    g.lookback = 3         # 计算偏离度的回看期
    g.k = 1.5              # 偏离阈值倍数

    run_daily(rebalance, time='open')


def calc_psar(high_series, low_series, close_series, af, max_af):
    """计算PSAR指标"""
    n = len(close_series)
    psar = [0] * n
    is_up_trend = True
    ep = high_series.iloc[0]
    af_current = af

    # 初始化PSAR
    psar[0] = low_series.iloc[0]

    for i in range(1, n):
        prev_psar = psar[i-1]

        if is_up_trend:
            # 上升趋势
            psar[i] = prev_psar + af_current * (ep - prev_psar)

            # 检查是否反转
            if low_series.iloc[i] < psar[i]:
                is_up_trend = False
                psar[i] = max(high_series.iloc[i-1], high_series.iloc[i-2], ep)
                ep = low_series.iloc[i]
                af_current = af
            else:
                # 更新EP和AF
                if high_series.iloc[i] > ep:
                    ep = high_series.iloc[i]
                    af_current = min(af_current + af, max_af)

                # 确保PSAR在最低价以下
                psar[i] = min(psar[i], low_series.iloc[i-1], low_series.iloc[i-2] if i > 1 else psar[i])
        else:
            # 下降趋势
            psar[i] = prev_psar - af_current * (prev_psar - ep)

            # 检查是否反转
            if high_series.iloc[i] > psar[i]:
                is_up_trend = True
                psar[i] = min(low_series.iloc[i-1], low_series.iloc[i-2], ep)
                ep = high_series.iloc[i]
                af_current = af
            else:
                # 更新EP和AF
                if low_series.iloc[i] < ep:
                    ep = low_series.iloc[i]
                    af_current = min(af_current + af, max_af)

                # 确保PSAR在最高价以上
                psar[i] = max(psar[i], high_series.iloc[i-1], high_series.iloc[i-2] if i > 1 else psar[i])

    return pd.Series(psar, index=close_series.index)


def rebalance(context):
    """每日调仓"""
    need = 100  # 需要足够数据计算PSAR
    data = attribute_history(g.security, need, '1d', ['close', 'high', 'low'])
    if data is None or len(data) < need:
        return

    close = data['close']
    high = data['high']
    low = data['low']

    # 计算PSAR
    psar = calc_psar(high, low, close, g.af, g.max_af)
    psar_val = psar.iloc[-1]

    if psar_val is None or (psar_val != psar_val):
        return

    # 计算最近偏离度的标准差
    recent_close = close.iloc[-g.lookback:]
    recent_psar = psar.iloc[-g.lookback:]
    deviation = (recent_close - recent_psar) / abs(recent_psar)
    std_dev = deviation.std()

    if std_dev is None or std_dev <= 0:
        return

    # 当前偏离度
    current_dev = (close.iloc[-1] - psar_val) / abs(psar_val)

    position = context.portfolio.positions.get(g.security)
    hold_amount = position.total_amount if position else 0

    # 过度偏离下方：价格 < PSAR - k × std
    if current_dev <= -g.k * std_dev and hold_amount <= 0:
        order_target_value(g.security, context.portfolio.available_cash * 0.95)

    # 过度偏离上方：价格 > PSAR + k × std
    elif current_dev >= g.k * std_dev and hold_amount > 0:
        order_target(g.security, 0)

    # 偏离回归到正常范围内
    elif abs(current_dev) <= 0.5 * std_dev and hold_amount > 0:
        order_target(g.security, 0)
