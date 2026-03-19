# -*- coding: utf-8 -*-
'''
行业轮动多因子策略（行业动量+估值+景气度+RSRS择时）
==================================================

策略思路：
---------
选股：基于行业动量、行业估值、行业景气度多因子选股
择时：RSRS 斜率择时（标准分+右偏修正）
持仓：配置2-3个优势行业，每个行业选3-5只股票
运行环境：JoinQuant / 聚宽（Python3）

策略架构：
---------
1. 行业评分（多因子）：
   - 行业动量因子：行业指数收益率、RSI突破
   - 行业估值因子：行业PE分位数、PB分位数
   - 行业景气度因子：行业营收增长、订单增速
   
   综合打分 = 动量排名(40%) + 估值排名(30%) + 景气度排名(30%)

2. 个股选股（行业内）：
   - 在优势行业内选股
   - 使用PB、ROE等基本面因子
   - 每个行业选3-5只股票

3. 择时阶段（技术面因子）：
   - RSRS（相对强弱回归斜率）：衡量市场强弱
   - Z-score标准化：将RSRS标准化处理
   - 右偏修正：Z-score × 斜率 × R²

4. 风险控制：
   - 只在RSRS买入信号时持有仓位
   - RSRS卖出信号时清仓离场
   - 配置2-3个行业，降低行业集中风险

策略优势：
---------
- 捕捉行业轮动：根据行业表现动态配置
- 动量驱动：顺势而为，配置强势行业
- 估值保护：避免追高，选择估值合理行业
- 景气度验证：选择基本面向好行业

策略风险：
---------
- 行业轮动失败：强势行业可能突然回调
- 滞后性：行业信号可能滞后于个股表现
- 行业集中：虽然配置多个行业，但仍可能集中
- 切换成本：行业切换频繁会增加交易成本

策略收益
17.42%
 
基准收益
36.08%
 
Alpha
-0.03
 
Beta
0.63
 
Sharpe
0.27
 
最大回撤 
15.96%

'''

# 导入函数库
import numpy as np  # 数值计算库，用于Z-score标准化
import statsmodels.api as sm  # 统计建模库，用于OLS线性回归

# 定义行业ETF池（使用申万一级行业ETF或行业龙头ETF）
SECTOR_ETFS = {
    '金融': ['510230.XSHG', '512880.XSHG'],  # 金融ETF、证券ETF
    '科技': ['512760.XSHG', '159915.XSHE'],  # 半导体ETF、创业板ETF
    '消费': ['159928.XSHE', '512170.XSHG'],  # 消费ETF、医药ETF
    '军工': ['512660.XSHG', '512810.XSHG'],  # 军工ETF、上海国企ETF
    '周期': ['510820.XSHG', '510520.XSHG'],  # 有色ETF、煤炭ETF
    '新能源': ['516160.XSHG', '159783.XSHE'],  # 新能车ETF、新能源ETF
    '医药': ['512010.XSHG', '159938.XSHE'],  # 医药ETF、生物医药ETF
    '地产': ['512200.XSHG', '512080.XSHG'],  # 地产ETF、红利ETF
}

# 行业龙头股票池（每行业3-5只龙头）
SECTOR_STOCKS = {
    '金融': ['601318.XSHG', '600036.XSHG', '601166.XSHG', '600030.XSHG'],
    '科技': ['000858.XSHE', '300750.XSHE', '002415.XSHE', '688981.XSHG'],
    '消费': ['600519.XSHG', '000858.XSHE', '603288.XSHG', '002304.XSHE'],
    '军工': ['600760.XSHG', '002025.XSHE', '600893.XSHG', '601798.XSHG'],
    '周期': ['600019.XSHG', '600547.XSHG', '601899.XSHG', '600585.XSHG'],
    '新能源': ['300750.XSHE', '300274.XSHE', '002594.XSHE', '601012.XSHG'],
    '医药': ['600276.XSHG', '000661.XSHE', '300015.XSHE', '002007.XSHE'],
    '地产': ['000002.XSHE', '600048.XSHG', '000001.XSHE', '001979.XSHE'],
}

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
    g.buy = 0.7: RSRS买入阈值
    g.sell = -0.7: RSRS卖出阈值

    g.momentum_window = 60: 行业动量计算窗口（日）
        - 计算60日行业指数收益率
        - 衡量行业短期动量

    g.valuation_window = 252: 行业估值历史窗口（日）
        - 计算252日行业PE/PB分位数
        - 衡量行业估值水平

    g.sector_num = 3: 配置行业数量
        - 选择排名前3的行业
        - 降低行业集中风险

    g.stocks_per_sector = 4: 每个行业选股数量
        - 每个行业选4只龙头股
        - 总持仓：12只股票

    g.factor_weights: 行业因子权重
        - 动量因子：40%
        - 估值因子：30%
        - 景气度因子：30%
    """
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    g.init = True  # 初始化标志
    g.security = '000300.XSHG'  # 基准：沪深300指数
    set_benchmark(g.security)  # 设置基准
    g.days = 0  # 运行天数计数器
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.ans = []  # 存储历史RSRS斜率值
    g.ans_rightdev = []  # 存储历史R²值

    # 行业轮动参数
    g.momentum_window = 60  # 行业动量计算窗口
    g.valuation_window = 252  # 行业估值历史窗口
    g.sector_num = 3  # 配置行业数量
    g.stocks_per_sector = 4  # 每个行业选股数量
    g.factor_weights = {'momentum': 0.4, 'valuation': 0.3, 'fundamental': 0.3}  # 因子权重

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
    核心逻辑：RSRS择时 + 行业轮动多因子选股交易
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

# 计算行业评分
def calculate_sector_scores(context):
    """
    计算各行业的综合评分

    返回：行业评分字典 {行业名: 综合得分}
    """
    sector_scores = {}

    for sector_name, etf_list in SECTOR_ETFS.items():
        try:
            # 使用第一个ETF作为行业代表
            etf = etf_list[0]

            # 获取行业ETF价格
            etf_prices = get_price(etf, end_date=context.previous_date, 
                                   frequency='daily', fields=['close'], 
                                   count=g.momentum_window)
            etf_prices = etf_prices['close'].values

            # ===================== 计算动量因子 =====================
            if len(etf_prices) >= g.momentum_window:
                momentum = (etf_prices[-1] / etf_prices[0]) - 1
            else:
                momentum = 0

            # ===================== 计算估值因子 =====================
            # 使用行业代表股票的PE、PB作为行业估值
            sector_stock = SECTOR_STOCKS[sector_name][0]  # 取第一个龙头股
            stock_pe = get_current_data().get_stock(sector_stock).day_pe_ratio
            stock_pb = get_current_data().get_stock(sector_stock).day_pb_ratio

            # 估值得分：PE、PB越低越好
            valuation_score = (stock_pe + stock_pb) / 2

            # ===================== 计算景气度因子 =====================
            # 获取行业龙头股票的营收增长率
            df = get_fundamentals(query(
                valuation.code,
                indicator.inc_revenue_year_on_year,
                indicator.inc_net_profit_year_on_year
            ).filter(valuation.code.in_(SECTOR_STOCKS[sector_name])))

            if len(df) > 0:
                revenue_growth = df['inc_revenue_year_on_year'].mean()
                profit_growth = df['inc_net_profit_year_on_year'].mean()
                fundamental_score = (revenue_growth + profit_growth) / 2
            else:
                fundamental_score = 0

            # ===================== 综合打分 =====================
            # 动量排名（越高越好）
            momentum_rank = momentum  # 动量越高越好
            # 估值排名（越低越好）
            valuation_rank = -valuation_score  # 估值越低，排名越高
            # 景气度排名（越高越好）
            fundamental_rank = fundamental_score  # 景气度越高越好

            # 综合得分
            total_score = (
                momentum_rank * g.factor_weights['momentum'] +
                valuation_rank * g.factor_weights['valuation'] +
                fundamental_rank * g.factor_weights['fundamental']
            )

            sector_scores[sector_name] = total_score

        except:
            sector_scores[sector_name] = -999  # 异常时给最低分

    return sector_scores

# 行业内选股
def select_stocks_in_sector(context, sector_name):
    """
    在指定行业内选股

    选股逻辑：
    1. 获取行业内所有股票
    2. 使用PB、ROE等基本面因子选股
    3. 选择得分最高的N只股票

    返回：股票列表
    """
    try:
        # 获取行业内股票的基本面数据
        df = get_fundamentals(query(
            valuation.code,
            valuation.pb_ratio,
            indicator.roe,
            indicator.inc_revenue_year_on_year
        ).filter(valuation.code.in_(SECTOR_STOCKS[sector_name])))

        # 过滤无效数据
        df = df[(df['pb_ratio'] > 0) & (df['roe'] > 0.05)]
        df = df.dropna()

        if len(df) == 0:
            return SECTOR_STOCKS[sector_name][:g.stocks_per_sector]  # 返回默认股票

        # 设置索引为股票代码
        df.index = df['code'].values

        # 综合打分
        df['1/roe'] = 1 / df['roe']
        df['score'] = df[['pb_ratio', '1/roe']].rank().sum(axis=1)

        # 按得分排序，选取前N只股票
        df = df.sort_values(by='score').head(g.stocks_per_sector)

        return df.index.tolist()

    except:
        return SECTOR_STOCKS[sector_name][:g.stocks_per_sector]  # 返回默认股票

# 行业轮动选股 + 交易
def trade_func(context):
    """
    行业轮动多因子选股并执行调仓

    选股逻辑：
    1. 计算各行业综合评分（动量+估值+景气度）
    2. 选择评分最高的3个行业
    3. 在每个行业内选4只股票
    4. 等权重分散持仓

    持仓数量：12只（3行业×4股/行业）
    仓位分配：等权重分散
    """
    try:
        # ===================== 计算行业评分 =====================
        sector_scores = calculate_sector_scores(context)

        # ===================== 选择优势行业 =====================
        # 按评分排序，选择前N个行业
        sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
        top_sectors = [item[0] for item in sorted_sectors[:g.sector_num]]

        # ===================== 在行业内选股 =====================
        pool = []
        for sector in top_sectors:
            stocks = select_stocks_in_sector(context, sector)
            pool.extend(stocks)

        # 去重
        pool = list(set(pool))

        if len(pool) == 0:
            return

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
