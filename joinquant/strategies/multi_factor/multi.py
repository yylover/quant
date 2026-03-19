# -*- coding: utf-8 -*-
'''
多因子选股策略 (PB+ROE + RSRS择时)
===================================

策略思路：
--------
选股：财务指标选股（PB+ROE 综合打分）
择时：RSRS 斜率择时（标准分+右偏修正）
持仓：有开仓信号时持有10只股票，不满足时保持空仓
运行环境：JoinQuant / 聚宽（Python3）

策略架构：
---------
1. 选股阶段（基本面因子）：
   - PB（市净率）：价值因子，低PB表示估值便宜
   - ROE（净资产收益率）：质量因子，高ROE表示盈利能力强
   - 综合打分：PB排名 + (1/ROE)排名，越小越好

2. 择时阶段（技术面因子）：
   - RSRS（相对强弱回归斜率）：衡量市场强弱
   - Z-score标准化：将RSRS标准化处理
   - 右偏修正：Z-score × 斜率 × R²，增强信号可靠性

3. 风险控制：
   - 只在RSRS买入信号时持有仓位
   - RSRS卖出信号时清仓离场
   - 等权重分散持仓10只股票

策略优势：
---------
- 基本面选股：PB和ROE都是经典的价值投资指标
- 技术面择时：RSRS有效过滤市场下跌风险
- 分散持仓：10只股票降低单票风险
- 逻辑清晰：价值投资 + 动量择时

策略风险：
---------
- 大熊市风险：RSRS可能滞后于市场急跌
- 价值陷阱：低PB低ROE可能持续低迷
- 行业集中：可能选入同一行业股票
- 换手率：调仓频率较高，增加交易成本
'''

# 导入函数库
import numpy as np  # 数值计算库，用于Z-score标准化
import statsmodels.api as sm  # 统计建模库，用于OLS线性回归

# 初始化函数
def initialize(context):
    """策略初始化，只执行一次"""
    set_option('use_real_price', True)  # 使用真实价格
    set_parameter(context)  # 设置策略参数

    # 交易手续费设置
    # 卖出印花税：0.1%（仅卖出）
    # 开仓佣金：0.03%（万分之三）
    # 平仓佣金：0.03%（万分之三）
    # 最低佣金：5元
    set_order_cost(OrderCost(
        close_tax=0.001,
        open_commission=0.0003,
        close_commission=0.0003,
        min_commission=5
    ), type='stock')

    # 每日定时任务
    # before_open: 开盘前运行，用于计算和预热数据
    # open: 开盘时运行，用于交易决策
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_open, time='open', reference_security='000300.XSHG')

'''
==============================参数设置==============================
'''
def set_parameter(context):
    """
    设置策略全局参数

    核心参数说明：
    -------------
    g.N = 18: RSRS回归窗口（日）
        - 计算高低价回归关系的滑动窗口
        - 18个交易日约等于1个月的交易日数
        - 较短窗口反应灵敏，较长窗口更稳定

    g.M = 1100: Z-score标准化历史窗口（日）
        - 用于计算Z-score的历史数据长度
        - 1100日约等于4.5年
        - 足够长的时间窗口保证统计意义

    g.stock_num = 10: 持股数量
        - 等权重分散持仓
        - 10只股票平衡分散度和换手成本

    g.buy = 0.7: RSRS买入阈值
        - 右偏修正后的RSRS高于0.7时买入
        - 表示市场处于强势状态

    g.sell = -0.7: RSRS卖出阈值
        - 右偏修正后的RSRS低于-0.7时清仓
        - 表示市场处于弱势状态

    g.security = '000300.XSHG': 基准指数
        - 沪深300指数
        - 用于计算RSRS择时信号
    """
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    g.init = True  # 初始化标志
    g.stock_num = 10  # 持股数量
    g.security = '000300.XSHG'  # 基准：沪深300指数
    set_benchmark(g.security)  # 设置基准
    g.days = 0  # 运行天数计数器
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.ans = []  # 存储历史RSRS斜率值
    g.ans_rightdev = []  # 存储历史R²值
    
    # ===================== 历史RSRS数据预热 =====================
    # 在策略初始化时计算历史RSRS斜率和R²
    # 避免回测初期因数据不足导致无法进行Z-score标准化
    prices = get_price(g.security, '2005-01-05', context.previous_date, '1d', ['high', 'low'])
    prices = prices.dropna()  # 去除空值行
    if len(prices) < g.N:
        return

    highs = prices.high
    lows = prices.low

    # 滑动计算RSRS回归斜率和R²
    # 对每个滚动窗口进行线性回归：High = a + b × Low
    # 斜率b表示价格波动强度，R²表示回归拟合度
    for i in range(len(highs))[g.N:]:
        data_high = highs.iloc[i-g.N+1:i+1]
        data_low = lows.iloc[i-g.N+1:i+1]

        # 去除空值，避免回归报错
        if data_high.isna().any() or data_low.isna().any():
            continue

        # 线性回归：High ~ Low
        # 斜率beta反映高低价关系强度
        # R²反映拟合质量，值越高说明高低价关系越稳定
        X = sm.add_constant(data_low, has_constant='add')
        model = sm.OLS(data_high, X)
        results = model.fit()
        g.ans.append(results.params[1])  # 斜率beta
        g.ans_rightdev.append(results.rsquared)  # R²

## 开盘前运行
def before_market_open(context):
    """
    开盘前运行函数，每日执行一次
    用途：计数器更新、消息推送等非交易任务
    """
    g.days += 1  # 运行天数计数
    send_message(f'策略正常运行，当前第{g.days}天~')  # 消息推送

## 开盘时运行
def market_open(context):
    """
    开盘时运行函数，每日执行一次
    核心逻辑：RSRS择时 + 选股交易
    """
    security = g.security  # 基准指数
    beta = 0  # 当前RSRS斜率
    r2 = 0  # 当前R²

    # ===================== 更新当日RSRS斜率和R² =====================
    if not g.init:
        try:
            # 获取最近N日的高低价数据
            prices = attribute_history(security, g.N, '1d', ['high', 'low'])
            prices = prices.dropna()
            if len(prices) >= g.N:
                highs = prices.high
                lows = prices.low
                # 线性回归：High ~ Low
                X = sm.add_constant(lows, has_constant='add')
                model = sm.OLS(highs, X)
                res = model.fit()
                beta = res.params[1]  # 当前斜率
                r2 = res.rsquared  # 当前R²
                g.ans.append(beta)  # 存入历史
                g.ans_rightdev.append(r2)  # 存入历史
        except:
            return
    else:
        g.init = False  # 首次运行后跳过预热

    # ===================== 计算RSRS择时信号 =====================
    # 安全检查：确保有足够的历史数据进行标准化
    if len(g.ans) < g.M:
        return

    # Z-score标准化：将当前RSRS斜率转换为标准分数
    section = g.ans[-g.M:]  # 取最近M个历史值
    mu = np.mean(section)  # 历史均值
    sigma = np.std(section)  # 历史标准差

    if sigma == 0:
        return

    # 当前RSRS的Z-score：衡量当前斜率偏离历史均值的程度
    zscore = (section[-1] - mu) / sigma

    # 右偏修正：增强信号可靠性
    # 逻辑：
    # - Z-score > 0 且 beta > 0 且 R² > 0：趋势向上且拟合好，加强买入信号
    # - Z-score < 0 且 beta < 0 且 R² > 0：趋势向下且拟合好，加强卖出信号
    # - R² 越高，信号越可靠
    zscore_rightdev = zscore * beta * r2

    # ===================== 交易决策 =====================
    # 买入信号：RSRS强势，市场处于上升通道
    if zscore_rightdev > g.buy:
        trade_func(context)  # 选股并买入

    # 卖出信号：RSRS弱势，市场处于下降通道
    elif zscore_rightdev < g.sell:
        for stock in list(context.portfolio.positions.keys()):
            order_target(stock, 0)  # 清仓所有持仓

# 选股 + 交易
def trade_func(context):
    """
    多因子选股并执行调仓

    选股逻辑：
    1. 过滤条件：ROE > 0.01 且 PB > 0.01（剔除异常值和亏损股）
    2. 打分公式：综合排名 = PB排名 + (1/ROE)排名
       - PB排名：越小越好（低估值）
       - 1/ROE排名：越小越好（高ROE对应低1/ROE）
    3. 选股数量：前g.stock_num只股票（默认10只）
    4. 仓位分配：等权重分散

    调仓逻辑：
    1. 卖出不在新选股池中的持仓股票
    2. 买入新选股池中的股票，目标金额 = 总资产 / 持股数量
    """
    try:
        # 获取基本面数据：股票代码、PB、ROE
        df = get_fundamentals(query(
            valuation.code,  # 股票代码
            valuation.pb_ratio,  # 市净率
            indicator.roe  # 净资产收益率
        ))

        # 过滤无效数据
        # ROE > 0.01：盈利公司，剔除亏损股
        # PB > 0.01：估值合理，剔除异常值
        df = df[(df['roe'] > 0.01) & (df['pb_ratio'] > 0.01)]
        df = df.dropna()  # 去除空值

        if len(df) == 0:
            return

        # 设置索引为股票代码
        df.index = df['code'].values

        # 计算反向ROE（1/ROE）
        # ROE越高，1/ROE越低，排名越靠前
        df['1/roe'] = 1 / df['roe']

        # 综合打分：PB排名 + (1/ROE)排名
        # rank()：默认升序排名，越小越好
        # point越小，表示估值越低、盈利能力越强
        df['point'] = df[['pb_ratio', '1/roe']].rank().sum(axis=1)

        # 按打分排序，选取前N只股票
        df = df.sort_values(by='point').head(g.stock_num)

        # 获取最终选股池
        pool = df.index.tolist()

        # 计算每只股票的目标持仓金额（等权重）
        cash_per = context.portfolio.total_value / len(pool)

        # ===================== 调仓操作 =====================
        # 第一步：卖出不在新选股池中的持仓
        for s in list(context.portfolio.positions.keys()):
            if s not in pool:
                order_target(s, 0)  # 清仓

        # 第二步：买入/调仓新选股池中的股票
        for s in pool:
            order_target_value(s, cash_per)  # 目标持仓金额

    except:
        return  # 异常时跳过本次交易

# 打分函数（未使用，保留备用）
def f_sum(x):
    """
    计算打分总和（备用函数）

    当前代码中直接使用pandas的sum(axis=1)，
    该函数暂未被调用，保留以备将来扩展。
    """
    return sum(x)