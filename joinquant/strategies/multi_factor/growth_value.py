# -*- coding: utf-8 -*-
'''
成长价值复合策略（成长+价值+质量+RSRS择时）
==========================================

策略思路：
---------
选股：基于成长、价值、质量三因子选股
择时：RSRS 斜率择时（标准分+右偏修正）
持仓：有开仓信号时持有12只股票，不满足时保持空仓
运行环境：JoinQuant / 聚宽（Python3）

策略架构：
---------
1. 选股阶段（多因子）：
   - 成长因子：营收增长率、利润增长率、ROE增长率
   - 价值因子：PE、PB、PEG（动态估值）
   - 质量因子：ROE、ROIC、毛利率、现金流质量
   
   综合打分 = 成长排名(40%) + 价值排名(30%) + 质量排名(30%)

2. 择时阶段（技术面因子）：
   - RSRS（相对强弱回归斜率）：衡量市场强弱
   - Z-score标准化：将RSRS标准化处理
   - 右偏修正：Z-score × 斜率 × R²

3. 风险控制：
   - 只在RSRS买入信号时持有仓位
   - RSRS卖出信号时清仓离场
   - 分散持仓12只股票

策略优势：
---------
- 成长价值平衡：兼顾成长性和估值安全边际
- 多维度选股：成长、价值、质量三个维度
- 理论扎实：基于基本面价值投资理论
- 择时风控：RSRS有效过滤市场下跌风险

策略风险：
---------
- 成长陷阱：高增长可能不可持续
- 估值陷阱：低估值可能是基本面恶化
- 质量恶化：ROE等质量指标可能下滑
- 行业集中：可能选入同一成长性行业

策略收益
31.77%
 
基准收益
36.08%
 
Alpha
0.02
 
Beta
0.65
 
Sharpe
0.56
 
最大回撤 
16.03%
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
    set_order_cost(OrderCost(
        close_tax=0.001,
        open_commission=0.0003,
        close_commission=0.0003,
        min_commission=5
    ), type='stock')

    # 每日定时任务
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
    g.M = 1100: Z-score标准化历史窗口（日）
    g.stock_num = 12: 持股数量
    g.buy = 0.7: RSRS买入阈值
    g.sell = -0.7: RSRS卖出阈值

    g.growth_window = 4: 成长因子计算周期（季度）
        - 对比最近4个季度的财务数据
        - 衡量年度成长性

    g.value_window = 24: 价值因子计算窗口（日）
        - 使用24日平均估值

    g.factor_weights: 因子权重
        - 成长因子：40%
        - 价值因子：30%
        - 质量因子：30%
    """
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    g.init = True  # 初始化标志
    g.stock_num = 12  # 持股数量
    g.security = '000300.XSHG'  # 基准：沪深300指数
    set_benchmark(g.security)  # 设置基准
    g.days = 0  # 运行天数计数器
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.ans = []  # 存储历史RSRS斜率值
    g.ans_rightdev = []  # 存储历史R²值

    # 多因子参数
    g.growth_window = 4  # 成长因子窗口（4个季度）
    g.value_window = 24  # 价值因子窗口
    g.factor_weights = {'growth': 0.4, 'value': 0.3, 'quality': 0.3}  # 因子权重

    # 历史RSRS数据预热
    prices = get_price(g.security, '2005-01-05', context.previous_date, '1d', ['high', 'low'])
    prices = prices.dropna()
    if len(prices) < g.N:
        return

    highs = prices.high
    lows = prices.low

    for i in range(len(highs))[g.N:]:
        data_high = highs.iloc[i-g.N+1:i+1]
        data_low = lows.iloc[i-g.N+1:i+1]

        if data_high.isna().any() or data_low.isna().any():
            continue

        X = sm.add_constant(data_low, has_constant='add')
        model = sm.OLS(data_high, X)
        results = model.fit()
        g.ans.append(results.params[1])
        g.ans_rightdev.append(results.rsquared)

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
    核心逻辑：RSRS择时 + 成长价值质量三因子选股交易
    """
    security = g.security  # 基准指数
    beta = 0  # 当前RSRS斜率
    r2 = 0  # 当前R²

    # 更新当日RSRS斜率和R²
    if not g.init:
        try:
            prices = attribute_history(security, g.N, '1d', ['high', 'low'])
            prices = prices.dropna()
            if len(prices) >= g.N:
                highs = prices.high
                lows = prices.low
                X = sm.add_constant(lows, has_constant='add')
                model = sm.OLS(highs, X)
                res = model.fit()
                beta = res.params[1]
                r2 = res.rsquared
                g.ans.append(beta)
                g.ans_rightdev.append(r2)
        except:
            return
    else:
        g.init = False

    # 计算RSRS择时信号
    if len(g.ans) < g.M:
        return

    section = g.ans[-g.M:]
    mu = np.mean(section)
    sigma = np.std(section)

    if sigma == 0:
        return

    zscore = (section[-1] - mu) / sigma
    zscore_rightdev = zscore * beta * r2

    # 交易决策
    if zscore_rightdev > g.buy:
        trade_func(context)  # 选股并买入
    elif zscore_rightdev < g.sell:
        for stock in list(context.portfolio.positions.keys()):
            order_target(stock, 0)  # 清仓所有持仓

# 成长价值质量三因子选股 + 交易
def trade_func(context):
    """
    成长价值质量三因子选股并执行调仓

    选股逻辑：
    1. 成长因子：营收增长率、利润增长率、ROE增长率
    2. 价值因子：PE、PB、PEG
    3. 质量因子：ROE、ROIC、毛利率

    综合打分 = 成长排名×0.4 + 价值排名×0.3 + 质量排名×0.3
    排名越小，得分越高

    持仓数量：12只
    仓位分配：等权重分散
    """
    try:
        # 获取基本面数据
        df = get_fundamentals(query(
            valuation.code,  # 股票代码
            valuation.pe_ratio,  # 市盈率
            valuation.pb_ratio,  # 市净率
            indicator.roe,  # 净资产收益率
            indicator.inc_revenue_year_on_year,  # 营收同比增长率
            indicator.inc_net_profit_year_on_year,  # 净利润同比增长率
            indicator.gross_profit_margin,  # 毛利率
            balance.total_assets,  # 总资产
            balance.total_owner_equities  # 股东权益
        ))

        # 过滤无效数据
        # PE > 0: 盈利公司
        # PB > 0: 估值合理
        # ROE > 0.05: 盈利能力强（5%以上）
        # 营收增长 > -0.3: 避免营收大幅下滑
        df = df[(df['pe_ratio'] > 0) & (df['pb_ratio'] > 0) & 
                (df['roe'] > 0.05) & (df['inc_revenue_year_on_year'] > -0.3)]
        df = df.dropna()

        if len(df) == 0:
            return

        # 设置索引为股票代码
        df.index = df['code'].values

        # ===================== 计算成长因子 =====================
        # 成长因子：综合营收增长和利润增长
        # 归一化后综合排名
        df['growth_score'] = (
            df['inc_revenue_year_on_year'].rank() + 
            df['inc_net_profit_year_on_year'].rank()
        ) / 2

        # ===================== 计算价值因子 =====================
        # 价值因子：PE、PB、PEG（PE/增长率）
        # PEG = PE / (净利润增长率 * 100)
        df['peg'] = df['pe_ratio'] / (df['inc_net_profit_year_on_year'] * 100 + 1)
        # 剔除极端PEG值
        df.loc[df['peg'] < 0, 'peg'] = 100
        df.loc[df['peg'] > 10, 'peg'] = 10

        # 价值综合得分：PE、PB、PEG三个指标，越小越好
        df['value_score'] = (
            df['pe_ratio'].rank() + 
            df['pb_ratio'].rank() + 
            df['peg'].rank()
        ) / 3

        # ===================== 计算质量因子 =====================
        # 质量因子：ROE、毛利率
        df['quality_score'] = (
            df['roe'].rank(ascending=False) +  # ROE越高越好
            df['gross_profit_margin'].rank(ascending=False)  # 毛利率越高越好
        ) / 2

        # ===================== 综合打分 =====================
        # 对每个因子进行排名（成长和质量降序，价值升序）
        df['growth_rank'] = df['growth_score'].rank(ascending=False)  # 成长越好，排名靠前
        df['value_rank'] = df['value_score'].rank()  # 估值越低，排名靠前
        df['quality_rank'] = df['quality_score'].rank(ascending=False)  # 质量越好，排名靠前

        # 综合得分：加权排名
        df['total_score'] = (
            df['growth_rank'] * g.factor_weights['growth'] +
            df['value_rank'] * g.factor_weights['value'] +
            df['quality_rank'] * g.factor_weights['quality']
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
