'''
策略思路：
选股：财务指标选股（PB+ROE 综合打分）
择时：RSRS 斜率择时（标准分+右偏修正）
持仓：有开仓信号时持有10只股票，不满足时保持空仓
运行环境：JoinQuant / 聚宽（Python3）


策略收益
426.40%
策略年化收益
15.04%
超额收益
162.69%
基准收益
100.39%
阿尔法
0.101
贝塔
0.455
夏普比率
0.610
胜率
0.653
盈亏比
1.726
最大回撤 
34.62%
索提诺比率
0.843
日均超额收益
0.04%
超额收益最大回撤
35.84%
超额收益夏普比率
0.232
日胜率
0.493
盈利次数
1583
亏损次数
840
信息比率
0.469
策略波动率
0.181
基准波动率
0.213
最大回撤区间
2021/03/16,2023/06/26
'''

# 导入函数库
import numpy as np
import statsmodels.api as sm

# 初始化函数
def initialize(context):
    set_option('use_real_price', True)
    set_parameter(context)
    
    # 交易手续费
    set_order_cost(OrderCost(
        close_tax=0.001,
        open_commission=0.0003,
        close_commission=0.0003,
        min_commission=5
    ), type='stock')
    
    # 每日运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_open, time='open', reference_security='000300.XSHG')

'''
==============================参数设置==============================
'''
def set_parameter(context):
    g.N = 18
    g.M = 1100
    g.init = True
    g.stock_num = 10
    g.security = '000300.XSHG'
    set_benchmark(g.security)
    g.days = 0
    g.buy = 0.7
    g.sell = -0.7
    g.ans = []
    g.ans_rightdev = []
    
    # ===================== 修复点：数据清洗 + 异常防护 =====================
    prices = get_price(g.security, '2005-01-05', context.previous_date, '1d', ['high', 'low'])
    prices = prices.dropna()  # 去除空值行
    if len(prices) < g.N:
        return
    
    highs = prices.high
    lows = prices.low

    for i in range(len(highs))[g.N:]:
        data_high = highs.iloc[i-g.N+1:i+1]
        data_low = lows.iloc[i-g.N+1:i+1]
        
        # 去除空值，避免回归报错
        if data_high.isna().any() or data_low.isna().any():
            continue
            
        X = sm.add_constant(data_low, has_constant='add')
        model = sm.OLS(data_high, X)
        results = model.fit()
        g.ans.append(results.params[1])
        g.ans_rightdev.append(results.rsquared)

## 开盘前运行
def before_market_open(context):
    g.days += 1
    send_message(f'策略正常运行，当前第{g.days}天~')

## 开盘时运行
def market_open(context):
    security = g.security
    beta = 0
    r2 = 0
    
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

    # 安全计算标准化RSRS
    if len(g.ans) < g.M:
        return
        
    section = g.ans[-g.M:]
    mu = np.mean(section)
    sigma = np.std(section)
    
    if sigma == 0:
        return
        
    zscore = (section[-1] - mu) / sigma
    zscore_rightdev = zscore * beta * r2

    # 买入信号
    if zscore_rightdev > g.buy:
        trade_func(context)
        
    # 卖出信号
    elif zscore_rightdev < g.sell:
        for stock in list(context.portfolio.positions.keys()):
            order_target(stock, 0)

# 选股 + 交易
def trade_func(context):
    try:
        df = get_fundamentals(query(
            valuation.code,
            valuation.pb_ratio,
            indicator.roe
        ))
        
        # 过滤无效数据
        df = df[(df['roe'] > 0.01) & (df['pb_ratio'] > 0.01)]
        df = df.dropna()
        
        if len(df) == 0:
            return
            
        df.index = df['code'].values
        df['1/roe'] = 1 / df['roe']
        df['point'] = df[['pb_ratio', '1/roe']].rank().sum(axis=1)
        df = df.sort_values(by='point').head(g.stock_num)
        
        pool = df.index.tolist()
        cash_per = context.portfolio.total_value / len(pool)
        
        # 调仓
        for s in list(context.portfolio.positions.keys()):
            if s not in pool:
                order_target(s, 0)
                
        for s in pool:
            order_target_value(s, cash_per)
            
    except:
        return

# 打分函数
def f_sum(x):
    return sum(x)