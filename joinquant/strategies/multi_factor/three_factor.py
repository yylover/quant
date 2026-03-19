# -*- coding: utf-8 -*-
'''
三因子扩展策略（市值+价值+动量+RSRS择时）
=========================================

策略思路：
---------
选股：基于Fama-French三因子模型，使用市值、价值、动量三因子选股
择时：RSRS 斜率择时（标准分+右偏修正）
持仓：有开仓信号时持有15只股票，不满足时保持空仓
运行环境：JoinQuant / 聚宽（Python3）

策略架构：
---------
1. 选股阶段（多因子）：
   - 市值因子（SMB）：小盘股往往有超额收益
   - 价值因子（HML）：低估值股票收益更好
   - 动量因子（MOM）：过去强势股票延续强势
   
   综合打分 = 市值排名(30%) + 价值排名(30%) + 动量排名(40%)

2. 择时阶段（技术面因子）：
   - RSRS（相对强弱回归斜率）：衡量市场强弱
   - Z-score标准化：将RSRS标准化处理
   - 右偏修正：Z-score × 斜率 × R²

3. 风险控制：
   - 只在RSRS买入信号时持有仓位
   - RSRS卖出信号时清仓离场
   - 分散持仓15只股票

策略优势：
---------
- 因子分散：市值、价值、动量三个维度
- 理论扎实：基于Fama-French三因子模型
- 择时风控：RSRS有效过滤市场下跌风险
- 分散持仓：15只股票降低单票风险

策略风险：
---------
- 小盘股风险：流动性差，波动大
- 价值陷阱：低估值可能持续低迷
- 动量失效：熊市动量策略可能失效
- 因子拥挤：多因子策略使用增多导致效果下降
'''

# 导入函数库
import numpy as np  # 数值计算库，用于Z-score标准化
import statsmodels.api as sm  # 统计建模库，用于OLS线性回归
import pandas as pd  # 数据处理库

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

    g.M = 1100: Z-score标准化历史窗口（日）
        - 用于计算Z-score的历史数据长度
        - 1100日约等于4.5年

    g.stock_num = 15: 持股数量
        - 等权重分散持仓
        - 15只股票平衡分散度和换手成本

    g.buy = 0.7: RSRS买入阈值
        - 右偏修正后的RSRS高于0.7时买入

    g.sell = -0.7: RSRS卖出阈值
        - 右偏修正后的RSRS低于-0.7时清仓

    g.momentum_window = 252: 动量因子计算窗口（日）
        - 252日约等于1年
        - 经典的12个月动量因子

    g.size_window = 12: 市值因子计算窗口（日）
        - 使用12日平均市值
        - 避免单日市值波动影响

    g.value_window = 24: 价值因子计算窗口（日）
        - 使用24日平均估值
        - 平滑估值数据

    g.factor_weights: 因子权重
        - 市值因子：30%
        - 价值因子：30%
        - 动量因子：40%
    """
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    g.init = True  # 初始化标志
    g.stock_num = 15  # 持股数量
    g.security = '000300.XSHG'  # 基准：沪深300指数
    set_benchmark(g.security)  # 设置基准
    g.days = 0  # 运行天数计数器
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.ans = []  # 存储历史RSRS斜率值
    g.ans_rightdev = []  # 存储历史R²值

    # 多因子参数
    g.momentum_window = 252  # 动量因子窗口（1年）
    g.size_window = 12  # 市值因子窗口
    g.value_window = 24  # 价值因子窗口
    g.factor_weights = {'size': 0.3, 'value': 0.3, 'momentum': 0.4}  # 因子权重

    # ===================== 历史RSRS数据预热 =====================
    # 在策略初始化时计算历史RSRS斜率和R²
    prices = get_price(g.security, '2005-01-05', context.previous_date, '1d', ['high', 'low'])
    prices = prices.dropna()  # 去除空值行
    if len(prices) < g.N:
        return

    highs = prices.high
    lows = prices.low

    # 滑动计算RSRS回归斜率和R²
    for i in range(len(highs))[g.N:]:
        data_high = highs.iloc[i-g.N+1:i+1]
        data_low = lows.iloc[i-g.N+1:i+1]

        # 去除空值，避免回归报错
        if data_high.isna().any() or data_low.isna().any():
            continue

        # 线性回归：High ~ Low
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
    核心逻辑：RSRS择时 + 三因子选股交易
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
    zscore_rightdev = zscore * beta * r2

    # ===================== 交易决策 =====================
    # 买入信号：RSRS强势，市场处于上升通道
    if zscore_rightdev > g.buy:
        trade_func(context)  # 选股并买入

    # 卖出信号：RSRS弱势，市场处于下降通道
    elif zscore_rightdev < g.sell:
        for stock in list(context.portfolio.positions.keys()):
            order_target(stock, 0)  # 清仓所有持仓

# 三因子选股 + 交易
def trade_func(context):
    """
    三因子选股并执行调仓

    选股逻辑：
    1. 市值因子（SMB）：小盘股因子，倾向于选择中小盘股
    2. 价值因子（HML）：低估值因子，倾向于选择低PB、低PE股票
    3. 动量因子（MOM）：过去12个月收益高的股票

    综合打分 = 市值排名×0.3 + 价值排名×0.3 + 动量排名×0.4
    排名越小，得分越高

    持仓数量：15只
    仓位分配：等权重分散
    """
    try:
        # 获取基本面数据：股票代码、市值、PB、PE
        df = get_fundamentals(query(
            valuation.code,  # 股票代码
            valuation.market_cap,  # 总市值
            valuation.pb_ratio,  # 市净率
            valuation.pe_ratio  # 市盈率
        ))

        # 过滤无效数据
        # PE > 0: 盈利公司
        # PB > 0: 估值合理
        # 市值 > 0: 有效市值
        df = df[(df['pe_ratio'] > 0) & (df['pb_ratio'] > 0) & (df['market_cap'] > 0)]
        df = df.dropna()  # 去除空值

        if len(df) == 0:
            return

        # 设置索引为股票代码
        df.index = df['code'].values

        # ===================== 计算市值因子（SMB）=====================
        # 小盘股因子：市值越小，排名越靠前
        # 使用倒数使小市值排名靠前
        df['size_score'] = 1 / df['market_cap']

        # ===================== 计算价值因子（HML）=====================
        # 价值因子：低PB、低PE，排名越靠前
        # 综合PB和PE两个估值指标
        df['value_score'] = (df['pb_ratio'].rank() + df['pe_ratio'].rank()) / 2

        # ===================== 计算动量因子（MOM）=====================
        # 动量因子：过去12个月收益率
        momentum_scores = []
        for stock in df.index:
            try:
                # 获取过去252日的收盘价
                prices = get_price(stock, end_date=context.previous_date, 
                                 frequency='daily', fields=['close'], 
                                 count=g.momentum_window)
                if len(prices) >= 2:
                    # 计算12个月收益率
                    momentum = (prices['close'][-1] / prices['close'][0]) - 1
                    momentum_scores.append(momentum)
                else:
                    momentum_scores.append(0)
            except:
                momentum_scores.append(0)

        df['momentum_score'] = momentum_scores

        # ===================== 综合打分 =====================
        # 对每个因子进行排名（升序，越小越好）
        df['size_rank'] = df['size_score'].rank(ascending=False)  # 倒数越大，市值越小，排名靠前
        df['value_rank'] = df['value_score'].rank()  # 估值越低，排名靠前
        df['momentum_rank'] = df['momentum_score'].rank(ascending=False)  # 动量越高，排名靠前

        # 综合得分：加权排名
        df['total_score'] = (
            df['size_rank'] * g.factor_weights['size'] +
            df['value_rank'] * g.factor_weights['value'] +
            df['momentum_rank'] * g.factor_weights['momentum']
        )

        # 按综合得分排序，选取前N只股票
        df = df.sort_values(by='total_score').head(g.stock_num)

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
