# 克隆自聚宽文章：https://www.joinquant.com/post/44699
# 标题：10年52倍，年化59%，全新因子方法超稳定
# 作者：小白F


# 策略收益 19.77% 基准收益 39.16% Alpha -0.03 Beta 0.57 Sharpe 0.46 最大回撤 16.61%
## 策略概述
# 这是一个基于因子选股的量化策略，通过ARBR因子筛选股票，结合市值和EPS指标进行二次筛选，实现了10年52倍的收益（年化59%）。

# ## 核心逻辑
# ### 1. 初始化设置
# - 基准选择 ：中证500指数（000905.XSHG）
# - 交易成本 ：万分之三
# - 持仓数量 ：3只股票
# - 交易频率 ：每周调整一次（每月第一个交易日）
# - 特殊时间窗口 ：4月5日至4月30日为资金再平衡期，不进行交易
# ### 2. 选股逻辑
# 第一步：股票池过滤

# - 过滤掉次新股（上市时间超过1年）
# - 排除创业板、科创板、北交所股票
# - 排除停牌、ST、退市股票
# - 排除涨停或跌停开盘的股票
# 第二步：ARBR因子筛选

# - 计算ARBR因子值
# - 对因子值进行标准化处理
# - 筛选ARBR因子值在特定范围内的股票（-0.9996444781983547 至 0.9986148448690932）
# 第三步：二次筛选

# - 按流通市值从小到大排序
# - 筛选EPS>0的股票
# - 选择市值最小的前3只股票
# ### 3. 交易策略
# 买入策略

# - 每月第一个交易日执行调仓
# - 计算可用资金，平均分配给新买入的股票
# - 只买入不在当前持仓中的目标股票
# 卖出策略

# - 卖出不在目标列表中的股票
# - 保留昨日涨停的股票（即使不在目标列表中）
# - 14:00检查昨日涨停股票，如涨停打开则卖出
# 特殊处理

# - 4月5日至4月30日期间清仓所有股票，进行资金再平衡
# ### 4. 因子处理
# 数据预处理流程

# 1. 去极值 ：使用中位数去极值法，scale=5
# 2. 缺失值处理 ：
#    - 用行业平均值代替缺失值
#    - 行业缺失值用所有行业平均值代替
# 3. 标准化 ：对因子值进行标准化处理
# ### 5. 风险控制
# - 持仓限制 ：最多持有3只股票，分散风险
# - 止损机制 ：对涨停打开的股票及时卖出
# - 定期清仓 ：每年4月进行资金再平衡，避免风险累积
# - 股票过滤 ：严格过滤ST、退市等风险股票

# ARBR因子是由两个部分组成的市场情绪指标：

# - AR（人气指标） ：衡量市场的买卖人气
# - BR（意愿指标） ：衡量市场的买卖意愿强度

# EPS（Earnings Per Share） 即每股收益，是指公司净利润除以发行在外的普通股股数所得的比率。它是衡量公司盈利能力的重要指标，也是投资者评估公司价值的关键指标之一。

#导入函数库
from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd

# 行业代码列表，用于因子处理时的行业分类
industry_code = ['HY001', 'HY002', 'HY003', 'HY004', 'HY005', 'HY006', 'HY007', 'HY008', 'HY009', 'HY010', 'HY011']

#初始化函数 
def initialize(context):
    """初始化函数，设置策略基本参数和运行时间"""
    # 设定基准：中证500指数
    set_benchmark('000905.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数，避免使用未来数据
    set_option("avoid_future_data", True)
    # 将滑点设置为0，简化回测
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5),type='stock')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    log.set_level('system', 'error') 
    
    # 初始化全局变量
    g.no_trading_today_signal = False  # 是否为资金再平衡期
    g.stock_num = 3  # 持仓股票数量
    g.hold_list = []  # 当前持仓的全部股票    
    g.yesterday_HL_list = []  # 记录持仓中昨日涨停的股票
    
    # 因子列表，包含ARBR因子的取值范围
    g.factor_list = [
        {'ARBR': (-0.9996444781983547, 0.9986148448690932)}
        ]
   
    g.chosen_factor = ['ARBR']  # 选择使用的因子
    g.month_day = 1  # 每月调仓日（每月第一个交易日）

    # 设置交易运行时间
    run_daily(prepare_stock_list, '9:05')  # 每日9:05准备股票池
    run_weekly(weekly_adjustment, g.month_day, '9:30')  # 每月第一个交易日9:30调仓
    run_daily(check_limit_up, '14:00')  # 每日14:00检查涨停股
    run_daily(close_account, '14:30')  # 每日14:30检查是否需要清仓
    # run_daily(print_position_info, '15:10')  # 每日15:10打印持仓信息


#1-1 准备股票池
def prepare_stock_list(context):
    """准备股票池，获取当前持仓和昨日涨停股票列表"""
    # 获取已持有列表
    g.hold_list = []
    for position in list(context.portfolio.positions.values()):
        stock = position.security
        g.hold_list.append(stock)
    
    # 获取昨日涨停列表
    if g.hold_list != []:
        # 获取昨日收盘价和涨停价
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', 
                      fields=['close', 'high_limit'], count=1, panel=False, fill_paused=False)
        # 筛选收盘价等于涨停价的股票
        df = df[df['close'] == df['high_limit']]
        g.yesterday_HL_list = list(df.code)
    else:
        g.yesterday_HL_list = []
    
    # 判断今天是否为账户资金再平衡的日期（4月5日至4月30日）
    g.no_trading_today_signal = today_is_between(context, '04-05', '04-30')
    
#1-2 选股模块
def get_stock_list(context):
    """选股模块，通过ARBR因子和基本面指标筛选股票"""
    # 指定日期防止未来数据
    yesterday = context.previous_date
    today = context.current_dt
    
    # 获取初始列表
    initial_list = get_all_securities('stock', today).index.tolist()
    # 过滤股票池
    initial_list = filter_all_stock2(context, initial_list)
    
    final_list = []
    # 获取因子列表
    factor_list = list(g.factor_list[0].keys())
    
    # 获取因子数据
    factor_data = get_factor_values(initial_list, factor_list, end_date=yesterday, count=1)
    # 构建因子数据框
    df_jq_factor_value = pd.DataFrame(index=initial_list, columns=factor_list)
    for factor in factor_list:
        df_jq_factor_value[factor] = list(factor_data[factor].T.iloc[:, 0])

    # 数据预处理：去极值、缺失值处理、标准化
    df_jq_factor_value = data_preprocessing(df_jq_factor_value, initial_list, industry_code, yesterday)

    # 因子筛选
    df = df_jq_factor_value
    df = df.dropna()  # 删除缺失值
    
    # 根据ARBR因子范围筛选股票
    for factor in g.chosen_factor:
        df = df[(df[factor] >= g.factor_list[0][factor][0]) & (df[factor] <= g.factor_list[0][factor][1])]
        print(f'过滤完 {factor} ，剩余：{len(df)}')
    
    # 获取筛选后的股票列表
    postive_list = list(df.index)
    log.info(f'因子筛选后的数量：{len(postive_list)}/{len(df)}')
    
    # 基本面筛选：按流通市值排序，选择EPS>0的股票
    q = query(valuation.code, valuation.circulating_market_cap, indicator.eps).filter(
        valuation.code.in_(postive_list)).order_by(valuation.circulating_market_cap.asc())
    
    df2 = get_fundamentals(q)
    df2 = df2[df2['eps'] > 0]  # 筛选EPS>0的股票
    lst = list(df2.code)

    # 选择市值最小的前g.stock_num只股票
    lst = lst[:min(g.stock_num, len(lst))]
    
    # 构建最终股票列表
    for stock in lst:
        if stock not in final_list:
            final_list.append(stock)
    
    return final_list

#1-3 整体调整持仓
def weekly_adjustment(context):
    """整体调整持仓，卖出不在目标列表的股票，买入新的目标股票"""
    # 如果不是资金再平衡期，则执行调仓
    if g.no_trading_today_signal == False:
        # 获取应买入列表 
        target_list = get_stock_list(context)
        
        # 调仓卖出：卖出不在目标列表且不是昨日涨停的股票
        for stock in g.hold_list:
            if (stock not in target_list) and (stock not in g.yesterday_HL_list):
                log.info("卖出[%s]" % (stock))
                position = context.portfolio.positions[stock]
                close_position(position)
            else:
                log.info("已持有[%s]" % (stock))
        
        # 调仓买入：计算可用资金，平均分配给新买入的股票
        position_count = len(context.portfolio.positions)
        target_num = len(target_list)
        if target_num > position_count:
            # 计算每只新股票的买入金额
            value = context.portfolio.cash / (target_num - position_count)
            for stock in target_list:
                # 只买入不在当前持仓的股票
                if context.portfolio.positions[stock].total_amount == 0:
                    if open_position(stock, value):
                        # 如果已达到目标持仓数量，停止买入
                        if len(context.portfolio.positions) == target_num:
                            break

#1-4 调整昨日涨停股票
def check_limit_up(context):
    """检查昨日涨停股票，如涨停打开则卖出"""
    now_time = context.current_dt
    if g.yesterday_HL_list != []:
        # 对昨日涨停股票观察到尾盘如不涨停则提前卖出
        for stock in g.yesterday_HL_list:
            # 获取当前价格和涨停价
            current_data = get_price(stock, end_date=now_time, frequency='1m', 
                                  fields=['close', 'high_limit'], skip_paused=False, 
                                  fq='pre', count=1, panel=False, fill_paused=True)
            
            # 如果当前价格低于涨停价，说明涨停打开，卖出
            if current_data.iloc[0, 0] < current_data.iloc[0, 1]:
                log.info("[%s]涨停打开，卖出" % (stock))
                position = context.portfolio.positions[stock]
                close_position(position)
            else:
                log.info("[%s]涨停，继续持有" % (stock))


# 过滤股票，过滤停牌退市ST股票，选股时使用
def filter_all_stock2(context, stock_list):
    """过滤股票，排除次新股、创业板、科创板、北交所、停牌、ST、退市等股票"""
    # 过滤次新股：上市时间超过1年（252个交易日）
    by_date = get_trade_days(end_date=context.previous_date, count=252)[0]
    all_stocks = get_all_securities(date=by_date).index.tolist()
    # 只保留上市超过1年的股票
    stock_list = list(set(stock_list).intersection(set(all_stocks)))

    # 获取当前股票数据
    curr_data = get_current_data()
    
    # 过滤条件：
    # 1. 排除创业板（3开头）、科创板（68开头）、北交所（4、8开头）
    # 2. 排除停牌股票
    # 3. 排除ST股票
    # 4. 排除名称中包含ST、*、退的股票（退市风险）
    # 5. 排除涨停或跌停开盘的股票
    return [stock for stock in stock_list if not (
            stock.startswith(('3', '68', '4', '8')) or  # 创业，科创，北交所
            curr_data[stock].paused or # 停牌
            curr_data[stock].is_st or  # ST
            ('ST' in curr_data[stock].name) or # ST
            ('*' in curr_data[stock].name) or # 退市 
            ('退' in curr_data[stock].name) or # 退市
            (curr_data[stock].day_open == curr_data[stock].high_limit) or  # 涨停开盘
            (curr_data[stock].day_open == curr_data[stock].low_limit)  # 跌停开盘
    )]


#3-1 交易模块-自定义下单
def order_target_value_(security, value):
    """自定义下单函数，设置目标市值"""
    if value == 0:
        log.debug("Selling out %s" % (security))
    else:
        log.debug("Order %s to value %f" % (security, value))
    return order_target_value(security, value)

#3-2 交易模块-开仓
def open_position(security, value):
    """开仓函数，买入指定市值的股票"""
    order = order_target_value_(security, value)
    # 如果下单成功且有成交，则返回True
    if order != None and order.filled > 0:
        return True
    return False

#3-3 交易模块-平仓
def close_position(position):
    """平仓函数，卖出指定持仓"""
    security = position.security
    # 下单卖出全部持仓
    order = order_target_value_(security, 0)  # 可能会因停牌失败
    if order != None:
        # 检查订单状态是否为已成交且成交量等于订单量
        if order.status == OrderStatus.held and order.filled == order.amount:
            return True
    return False



#4-1 判断今天是否为账户资金再平衡的日期
def today_is_between(context, start_date, end_date):
    """判断今天是否在指定的日期范围内"""
    # 获取今天的月-日格式
    today = context.current_dt.strftime('%m-%d')
    # 判断是否在指定范围内
    if (start_date <= today) and (today <= end_date):
        return True
    else:
        return False

#4-2 清仓后次日资金可转
def close_account(context):
    """在资金再平衡期清仓所有股票"""
    if g.no_trading_today_signal == True:
        if len(g.hold_list) != 0:
            for stock in g.hold_list:
                position = context.portfolio.positions[stock]
                close_position(position)
                log.info("卖出[%s]" % (stock))

#4-3 打印每日持仓信息
def print_position_info(context):
    """打印每日持仓信息和成交记录"""
    # 打印当天成交记录
    trades = get_trades()
    for _trade in trades.values():
        print('成交记录：'+str(_trade))
    
    # 打印账户信息
    for position in list(context.portfolio.positions.values()):
        securities = position.security
        cost = position.avg_cost
        price = position.price
        ret = 100 * (price / cost - 1)
        value = position.value
        amount = position.total_amount    
        print('代码:{}'.format(securities))
        print('成本价:{}'.format(format(cost, '.2f')))
        print('现价:{}'.format(price))
        print('收益率:{}%'.format(format(ret, '.2f')))
        print('持仓(股):{}'.format(amount))
        print('市值:{}'.format(format(value, '.2f')))
        print('———————————————————————————————————')
    print('———————————————————————————————————————分割线————————————————————————————————————————')
    
    
    #取股票对应行业
def get_industry_name(i_Constituent_Stocks, value):
    """获取股票所属的行业"""
    return [k for k, v in i_Constituent_Stocks.items() if value in v]

#缺失值处理
def replace_nan_indu(factor_data, stockList, industry_code, date):
    """处理因子数据中的缺失值，用行业平均值代替"""
    # 把nan用行业平均值代替，依然会有nan，此时用所有股票平均值代替
    i_Constituent_Stocks = {}
    # 构建行业因子数据框
    data_temp = pd.DataFrame(index=industry_code, columns=factor_data.columns)
    
    # 计算每个行业的因子平均值
    for i in industry_code:
        # 获取行业股票列表
        temp = get_industry_stocks(i, date)
        # 只保留在股票池中的股票
        i_Constituent_Stocks[i] = list(set(temp).intersection(set(stockList)))
        # 计算行业因子平均值
        data_temp.loc[i] = mean(factor_data.loc[i_Constituent_Stocks[i], :])
    
    # 处理每个因子的缺失值
    for factor in data_temp.columns:
        # 行业缺失值用所有行业平均值代替
        null_industry = list(data_temp.loc[pd.isnull(data_temp[factor]), factor].keys())
        for i in null_industry:
            data_temp.loc[i, factor] = mean(data_temp[factor])
        
        # 股票缺失值用所属行业平均值代替，无所属行业则用所有股票平均值
        null_stock = list(factor_data.loc[pd.isnull(factor_data[factor]), factor].keys())
        for i in null_stock:
            industry = get_industry_name(i_Constituent_Stocks, i)
            if industry:
                factor_data.loc[i, factor] = data_temp.loc[industry[0], factor]
            else:
                factor_data.loc[i, factor] = mean(factor_data[factor])
    
    return factor_data

#数据预处理
def data_preprocessing(factor_data, stockList, industry_code, date):
    """数据预处理：去极值、缺失值处理、标准化"""
    # 去极值：使用中位数去极值法，scale=5
    factor_data = winsorize_med(factor_data, scale=5, inf2nan=False, axis=0)
    # 缺失值处理：用行业平均值代替
    factor_data = replace_nan_indu(factor_data, stockList, industry_code, date)
    # 标准化处理
    factor_data = standardlize(factor_data, axis=0)
    
    return factor_data