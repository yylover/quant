# -*- coding: utf-8 -*-
'''
低波质量策略（低波+质量+防御+RSRS择时）
======================================

策略思路：
---------
选股：基于低波动、高盈利质量、防御性三因子选股
择时：RSRS 斜率择时（标准分+右偏修正）
持仓：有开仓信号时持有15只股票，不满足时保持空仓
运行环境：JoinQuant / 聚宽（Python3）

策略架构：
---------
1. 选股阶段（防御型因子）：
   - 低波因子：历史波动率、Beta、最大回撤
   - 质量因子：ROE、ROIC、毛利率、债务/权益比
   - 防御因子：股息率、现金流/净利润
   
   综合打分 = 低波排名(40%) + 质量排名(30%) + 防御排名(30%)

2. 择时阶段（技术面因子）：
   - RSRS（相对强弱回归斜率）：衡量市场强弱
   - Z-score标准化：将RSRS标准化处理
   - 右偏修正：Z-score × 斜率 × R²

3. 风险控制：
   - 只在RSRS买入信号时持有仓位
   - RSRS卖出信号时清仓离场
   - 分散持仓15只股票
   - 防御性强，回撤小

策略优势：
---------
- 防御性强：低波动+高质量+防御三重保护
- 回撤控制：历史波动率低的股票回撤小
- 现金流好：高股息率提供安全边际
- 适合熊市：防御型策略在下跌市场中表现更好

策略风险：
---------
- 收益有限：低波动股票爆发力不足
- 牛市跑输：在强势牛市中可能跑输大盘
- 因子拥挤：低波策略使用增多导致效果下降
- 防御成本：过度保守可能错失机会
'''

# 导入函数库
import numpy as np  # 数值计算库，用于Z-score标准化
import statsmodels.api as sm  # 统计建模库，用于OLS线性回归
from scipy import stats  # 统计库，用于计算Beta

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
    g.stock_num = 15: 持股数量
    g.buy = 0.5: RSRS买入阈值（更低，更保守）
    g.sell = -0.5: RSRS卖出阈值（更低，更保守）

    g.vol_window = 60: 波动率计算窗口（日）
        - 计算60日历史波动率
        - 衡量股票波动风险

    g.beta_window = 252: Beta计算窗口（日）
        - 计算252日Beta
        - 衡量相对市场波动

    g.drawdown_window = 252: 最大回撤计算窗口（日）
        - 计算252日最大回撤
        - 衡量历史最大风险

    g.factor_weights: 因子权重
        - 低波因子：40%
        - 质量因子：30%
        - 防御因子：30%
    """
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    g.init = True  # 初始化标志
    g.stock_num = 15  # 持股数量
    g.security = '000300.XSHG'  # 基准：沪深300指数
    set_benchmark(g.security)  # 设置基准
    g.days = 0  # 运行天数计数器
    g.buy = 0.5  # RSRS买入阈值（更保守）
    g.sell = -0.5  # RSRS卖出阈值（更保守）
    g.ans = []  # 存储历史RSRS斜率值
    g.ans_rightdev = []  # 存储历史R²值

    # 多因子参数
    g.vol_window = 60  # 波动率计算窗口
    g.beta_window = 252  # Beta计算窗口
    g.drawdown_window = 252  # 最大回撤计算窗口
    g.factor_weights = {'low_vol': 0.4, 'quality': 0.3, 'defensive': 0.3}  # 因子权重

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
    核心逻辑：RSRS择时 + 低波质量防御三因子选股交易
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

# 计算Beta（相对于基准）
def calculate_beta(stock_prices, market_prices):
    """
    计算股票相对于市场的Beta值
    
    Beta = Cov(stock, market) / Var(market)
    - Beta > 1: 股票波动大于市场
    - Beta < 1: 股票波动小于市场（低波）
    - Beta = 1: 股票波动等于市场
    """
    try:
        # 计算收益率
        stock_returns = np.diff(stock_prices) / stock_prices[:-1]
        market_returns = np.diff(market_prices) / market_prices[:-1]
        
        # 计算协方差和方差
        covariance = np.cov(stock_returns, market_returns)[0, 1]
        market_variance = np.var(market_returns)
        
        if market_variance == 0:
            return 1.0
        
        beta = covariance / market_variance
        return beta
    except:
        return 1.0

# 计算最大回撤
def calculate_max_drawdown(prices):
    """
    计算价格序列的最大回撤
    
    最大回撤 = max(峰值 - 当前值) / 峰值
    """
    try:
        if len(prices) < 2:
            return 0.0
        
        # 计算累计峰值
        cummax = np.maximum.accumulate(prices)
        
        # 计算回撤
        drawdown = (prices - cummax) / cummax
        
        # 最大回撤（负值）
        max_drawdown = drawdown.min()
        
        return abs(max_drawdown)  # 返回正数
    except:
        return 0.0

# 低波质量防御三因子选股 + 交易
def trade_func(context):
    """
    低波质量防御三因子选股并执行调仓

    选股逻辑：
    1. 低波因子：历史波动率、Beta、最大回撤
    2. 质量因子：ROE、ROIC、毛利率、债务/权益比
    3. 防御因子：股息率、现金流/净利润

    综合打分 = 低波排名×0.4 + 质量排名×0.3 + 防御排名×0.3
    排名越小，得分越高

    持仓数量：15只
    仓位分配：等权重分散
    """
    try:
        # 获取基本面数据
        df = get_fundamentals(query(
            valuation.code,  # 股票代码
            valuation.pb_ratio,  # 市净率
            indicator.roe,  # 净资产收益率
            indicator.roa,  # 总资产收益率
            indicator.gross_profit_margin,  # 毛利率
            indicator.inc_revenue_year_on_year,  # 营收增长率
            balance.total_owner_equities,  # 股东权益
            balance.total_liability,  # 总负债
            cash_flow.net_operate_cash_flow,  # 经营现金流
            income.net_profit  # 净利润
        ))

        # 过滤无效数据
        # PB > 0: 估值合理
        # ROE > 0.08: 盈利能力强（8%以上）
        # 营收增长 > -0.2: 避免大幅下滑
        df = df[(df['pb_ratio'] > 0) & (df['roe'] > 0.08) & 
                (df['inc_revenue_year_on_year'] > -0.2)]
        df = df.dropna()

        if len(df) == 0:
            return

        # 设置索引为股票代码
        df.index = df['code'].values

        # ===================== 计算低波因子 =====================
        volatility_scores = []
        beta_scores = []
        drawdown_scores = []

        # 获取基准指数价格
        market_prices = get_price(g.security, end_date=context.previous_date, 
                                  frequency='daily', fields=['close'], 
                                  count=g.beta_window)
        market_prices = market_prices['close'].values

        for stock in df.index:
            try:
                # 获取股票价格
                stock_prices = get_price(stock, end_date=context.previous_date, 
                                        frequency='daily', fields=['close'], 
                                        count=g.beta_window)
                stock_prices = stock_prices['close'].values

                # 计算波动率
                if len(stock_prices) >= g.vol_window:
                    recent_prices = stock_prices[-g.vol_window:]
                    returns = np.diff(recent_prices) / recent_prices[:-1]
                    volatility = np.std(returns)
                else:
                    volatility = 0.3  # 默认值

                # 计算Beta
                beta = calculate_beta(stock_prices, market_prices)

                # 计算最大回撤
                if len(stock_prices) >= g.drawdown_window:
                    recent_prices = stock_prices[-g.drawdown_window:]
                    max_dd = calculate_max_drawdown(recent_prices)
                else:
                    max_dd = 0.5  # 默认值

                volatility_scores.append(volatility)
                beta_scores.append(beta)
                drawdown_scores.append(max_dd)

            except:
                volatility_scores.append(0.3)  # 默认值
                beta_scores.append(1.0)  # 默认值
                drawdown_scores.append(0.5)  # 默认值

        df['volatility'] = volatility_scores
        df['beta'] = beta_scores
        df['max_drawdown'] = drawdown_scores

        # 低波综合得分：波动率、Beta、最大回撤，越小越好
        df['low_vol_score'] = (
            df['volatility'].rank() + 
            df['beta'].rank() + 
            df['max_drawdown'].rank()
        ) / 3

        # ===================== 计算质量因子 =====================
        # 质量因子：ROE、ROA、毛利率
        # 财务健康度：负债权益比
        df['debt_equity'] = df['total_liability'] / df['total_owner_equities']
        # 剔除极端值
        df.loc[df['debt_equity'] > 5, 'debt_equity'] = 5

        df['quality_score'] = (
            df['roe'].rank(ascending=False) +  # ROE越高越好
            df['roa'].rank(ascending=False) +  # ROA越高越好
            df['gross_profit_margin'].rank(ascending=False) +  # 毛利率越高越好
            (1 / df['debt_equity']).rank(ascending=False)  # 负债越低越好
        ) / 4

        # ===================== 计算防御因子 =====================
        # 防御因子：股息率、现金流质量
        # 股息率 = 股息 / 股价（这里用ROE/PB近似）
        df['dividend_yield'] = df['roe'] / df['pb_ratio']
        # 现金流质量 = 经营现金流 / 净利润
        df['cash_flow_quality'] = df['net_operate_cash_flow'] / df['net_profit']
        # 剔除极端值
        df.loc[df['cash_flow_quality'] < -2, 'cash_flow_quality'] = -2
        df.loc[df['cash_flow_quality'] > 5, 'cash_flow_quality'] = 5

        df['defensive_score'] = (
            df['dividend_yield'].rank(ascending=False) +  # 股息率越高越好
            df['cash_flow_quality'].rank(ascending=False)  # 现金流越好越好
        ) / 2

        # ===================== 综合打分 =====================
        df['low_vol_rank'] = df['low_vol_score'].rank()  # 低波越好，排名靠前
        df['quality_rank'] = df['quality_score'].rank(ascending=False)  # 质量越好，排名靠前
        df['defensive_rank'] = df['defensive_score'].rank(ascending=False)  # 防御越好，排名靠前

        # 综合得分：加权排名
        df['total_score'] = (
            df['low_vol_rank'] * g.factor_weights['low_vol'] +
            df['quality_rank'] * g.factor_weights['quality'] +
            df['defensive_rank'] * g.factor_weights['defensive']
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
