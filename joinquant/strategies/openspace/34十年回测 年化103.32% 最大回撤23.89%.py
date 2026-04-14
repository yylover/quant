# 克隆自聚宽文章：https://www.joinquant.com/post/47523
# 标题：十年回测  年化103.32%  最大回撤23.89%
# 作者：jason_99

# 克隆自聚宽文章：https://www.joinquant.com/post/47346
# 标题：14-24【年化86%|胜率66%|回撤33%】无未来函数
# 作者：zycash

# 策略收益 648.26%   基准收益 -14.34%   Alpha 1.01   Beta 0.57   Sharpe 3.89   最大回撤  15.83%

## 策略核心逻辑
### 1. 选股逻辑
# - 选股范围 ：从中小综指（399101.XSHE）中选股
# - 市值筛选 ：5-50亿市值，从小到大排列
# - 过滤条件 ：
#   - 过滤次新股（上市不满1年）
#   - 过滤ST及其他具有退市标签的股票
#   - 过滤科创北交所股票，仅保留沪深主板股票
#   - 过滤停牌股票
#   - 过滤昨日涨停/跌停股票（持仓股除外）
#   - 过滤股价过高的股票（单价超过80元）
# - 最终选股 ：选择市值最小的前50只股票，再从中选取前5只作为目标持仓
# ### 2. 交易执行
# - 调仓频率 ：每周二10:00执行调仓
# - 买入逻辑 ：
#   - 每周二更新股票池，选择前5只股票
#   - 卖出不在目标列表且非昨日涨停的股票
#   - 按可用资金平均分配买入目标股票
# - 卖出逻辑 ：
#   - 每周二卖出非目标股票
#   - 每日10:30和14:00检查止损
#   - 每日14:30检查昨日涨停股票是否打开涨停，打开则卖出
# ### 3. 风险控制
# - 止损策略 ：联合止损（策略3）
#   - 个股止损：当股价低于成本价的93%（止损线7%）时止损
#   - 市场趋势止损：当中小综指平均跌幅超过5%时全部清仓
# - 止盈策略 ：当股票收益达到100%时止盈
# - 特殊月份清仓 ：4月5日至4月30日、1月5日至2月5日期间清仓
# - 交易控制 ：止损后隔1天再交易

# 导入函数库
from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd
import random
from datetime import time
from datetime import datetime, timedelta

# 初始化函数
def initialize(context):
    """策略初始化函数，设置交易环境和全局变量"""
    # 开启防未来函数，设定基线，真实价格，滑点及交易成本
    set_option('avoid_future_data', True)
    set_benchmark('000001.XSHG')
    set_option('use_real_price', True)
    set_slippage(FixedSlippage(3/10000))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=2.5/10000, 
        close_commission=2.5/10000, close_today_commission=0, min_commission=5), type='stock')
    
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    log.set_level('system', 'error')
    log.set_level('strategy', 'debug')
    
    # 初始化全局变量 - 布尔型
    g.no_trading_today_signal = False  # 是否为特殊日期（不交易）
    g.pass_april = True  # 是否在四月空仓
    g.run_stoploss = True  # 是否进行止损
    
    # 初始化全局变量 - 列表型
    g.hold_list = []  # 当前持仓的全部股票    
    g.yesterday_HL_list = []  # 记录持仓中昨日涨停的股票
    g.target_list = []  # 准备买入的标的
    g.not_buy_again = []  # 本周内不再买入的标的
    
    # 初始化全局变量 - 数值/字符串型
    g.stock_num = 5  # 目标持仓数量
    g.m_days = 5  # 取值参考天数
    g.up_price = 80  # 股票单价上限
    g.reason_to_sell = ''  # 卖出原因
    g.stoploss_strategy = 3  # 止损策略：1为止损线止损，2为市场趋势止损, 3为联合1、2策略
    g.stoploss_limit = 0.07  # 止损线（7%）
    g.stoploss_market = 0.05  # 市场趋势止损参数（5%）
    g.c = 0  # 止损天数计数器
    
    # 设置交易运行时间
    run_daily(prepare_stock_list, '8:00')  # 每天开盘前更新全局参数，持仓和昨日涨停
    run_weekly(weekly_adjustment, 2, '10:00')  # 每周二上午10点检查并调仓，不会更新卖出原因
    run_daily(sell_stocks, time='10:30')  # 每天10:30检查止损函数，止损会更新卖出原因
    run_daily(sell_stocks, time='14:00')  # 每天14:00检查止损函数，止损会更新卖出原因
    run_daily(trade_afternoon, time='14:30')  # 每天14:30检查涨停股票并处理剩余资金
    run_daily(close_account, '14:30')  # 特殊月份提前清仓
    # run_weekly(print_position_info, 5, time='15:30', reference_security='000300.XSHG')  # 每周5结束后统计持仓盈亏

# 1-1 更新全局参数，每天开盘前运行
def prepare_stock_list(context):
    """每天开盘前更新全局参数，包括持仓列表和昨日涨停股票"""
    # 更新已持有列表
    g.hold_list = list(context.portfolio.positions.keys())
    
    # 更新持有股票中昨日涨停的股票
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', 
            fields=['close', 'high_limit', 'low_limit'], count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.yesterday_HL_list = list(df.code)
    else:
        g.yesterday_HL_list = []
    
    # 判断今天是否为特殊日期（不交易）
    g.no_trading_today_signal = today_is_between(context)

# 1-2 选股模块，每周运行一遍
def get_stock_list(context):
    """选股函数，从中小综指中筛选符合条件的股票"""
    final_list = []
    
    # 从中小综指中选股
    initial_list = get_index_stocks('399101.XSHE')
    
    # 过滤次新股（上市不满1年）
    initial_list = filter_new_stock(context, initial_list)
    
    # 过滤科创北交所股票，仅保留沪深主板股票
    initial_list = filter_kcbj_stock(initial_list)
    
    # 过滤ST及其他具有退市标签的股票
    initial_list = filter_st_stock(initial_list)
    
    # 筛选5-50亿市值的股票，按市值从小到大排列
    q = query(valuation.code, valuation.market_cap).filter(
        valuation.code.in_(initial_list),
        valuation.market_cap.between(5, 50)
    ).order_by(valuation.market_cap.asc())
    df_fun = get_fundamentals(q)[:100]
    
    # 更新股票列表
    initial_list = list(df_fun.code)
    
    # 过滤停牌股票
    initial_list = filter_paused_stock(initial_list)
    
    # 过滤昨日涨停股票（持仓股除外）
    initial_list = filter_limitup_stock(context, initial_list)
    
    # 过滤昨日跌停股票（持仓股除外）
    initial_list = filter_limitdown_stock(context, initial_list)
    
    # 过滤股价过高的股票（持仓股除外）
    initial_list = filter_highprice_stock(context, initial_list)
    
    # 再次按市值排序，选取前50只股票
    q = query(valuation.code, valuation.market_cap).filter(
        valuation.code.in_(initial_list)
    ).order_by(valuation.market_cap.asc())
    df_fun = get_fundamentals(q)[:50]
    final_list = list(df_fun.code)
    
    return final_list  # 返回前50只股票

# 1-3 每周调整持仓
def weekly_adjustment(context):
    """每周二执行调仓操作，卖出非目标股票，买入目标股票"""
    if g.no_trading_today_signal == False:  # 非特殊日期才交易
        # 重置不再买入列表
        g.not_buy_again = []
        
        # 获取股票池，选取50只符合条件的股票
        g.target_list = get_stock_list(context)
        
        # 选择前5只股票作为目标持仓
        target_list = g.target_list[:g.stock_num]
        # target_list = random.sample(target_list[:8], g.stock_num)  # 前8个中随机选5
        
        log.info(str(target_list))
        
        # 调仓卖出：卖出非目标且非昨日涨停的股票
        for stock in g.hold_list:
            if (stock not in target_list) and (stock not in g.yesterday_HL_list):
                position = context.portfolio.positions[stock]
                if close_position(position):  # 卖出股票操作
                    log.info("卖出[%s]" % (stock))
                else:
                    log.info("！！！卖出失败[%s]" % (stock))
            else:
                log.info("已持有[%s]" % (stock))
        
        # 调仓买入
        buy_security(context, target_list)
        
        # 记录已买入股票，本周内不再重复买入
        for stock in list(context.portfolio.positions.keys()):
            g.not_buy_again.append(stock)

# 1-7 每天定点检查止损
def sell_stocks(context):
    """每天检查止损和止盈条件，执行相应操作"""
    if g.run_stoploss == True:
        if g.stoploss_strategy == 1:  # 仅个股止损
            for stock in context.portfolio.positions.keys():
                # 股票盈利大于等于100%则止盈
                if context.portfolio.positions[stock].price >= context.portfolio.positions[stock].avg_cost * 2:
                    order_target_value(stock, 0)
                    log.debug("收益100%止盈,卖出{}".format(stock))
                # 个股止损：当股价低于成本价的93%时止损
                elif context.portfolio.positions[stock].price < context.portfolio.positions[stock].avg_cost * (1 - g.stoploss_limit):
                    order_target_value(stock, 0)
                    log.debug("收益止损,卖出{}".format(stock))
                    g.reason_to_sell = 'stoploss'
        
        elif g.stoploss_strategy == 2:  # 仅市场趋势止损
            # 获取中小综指成分股前一天的开盘价和收盘价
            stock_df = get_price(security=get_index_stocks('399101.XSHE'), end_date=context.previous_date, 
                frequency='daily', fields=['close', 'open'], count=1, panel=False)
            # 计算平均跌幅
            down_ratio = abs((stock_df['close'] / stock_df['open'] - 1).mean())
            
            # 当市场平均跌幅超过5%时全部清仓
            if down_ratio >= g.stoploss_market:
                g.reason_to_sell = 'stoploss'
                log.debug("大盘惨跌,平均降幅{:.2%}".format(down_ratio))
                for stock in context.portfolio.positions.keys():
                    order_target_value(stock, 0)
        
        elif g.stoploss_strategy == 3:  # 联合止损策略
            # 获取中小综指成分股前一天的开盘价和收盘价
            stock_df = get_price(security=get_index_stocks('399101.XSHE'), end_date=context.previous_date, 
                frequency='daily', fields=['close', 'open'], count=1, panel=False)
            # 计算平均跌幅
            down_ratio = abs((stock_df['close'] / stock_df['open'] - 1).mean())
            
            # 当市场平均跌幅超过5%时全部清仓
            if down_ratio >= g.stoploss_market:
                g.reason_to_sell = 'stoploss'
                log.debug("基准指数暴跌,平均降幅{:.2%},全部清仓".format(down_ratio))
                for stock in context.portfolio.positions.keys():
                    order_target_value(stock, 0)
            else:
                # 否则执行个股止损
                for stock in context.portfolio.positions.keys():
                    if context.portfolio.positions[stock].price < context.portfolio.positions[stock].avg_cost * (1 - g.stoploss_limit):
                        order_target_value(stock, 0)
                        log.debug("达到止损,卖出{}".format(stock))
                        g.reason_to_sell = 'stoploss'

# 1-4 昨日涨停股票确定是否止盈，卖出时会记录卖出原因
def check_limit_up(context):
    """检查昨日涨停股票是否打开涨停，打开则卖出"""
    now_time = context.current_dt  # 当前时间
    if g.yesterday_HL_list != []:
        # 对昨日涨停股票观察到尾盘如不涨停则提前卖出，如果涨停即使不在应买入列表仍暂时持有
        for stock in g.yesterday_HL_list:
            current_data = get_price(stock, end_date=now_time, frequency='1m', fields=['close', 'high_limit'], 
                skip_paused=False, fq='pre', count=1, panel=False, fill_paused=True)
            
            # 如果当前价格低于涨停价，说明涨停打开，卖出股票
            if current_data.iloc[0, 0] < current_data.iloc[0, 1]:
                position = context.portfolio.positions[stock]
                if close_position(position):
                    log.info("[%s]涨停打开，卖出" % (stock))
                    g.reason_to_sell = 'limitup'
            else:
                log.info("[%s]涨停，继续持有" % (stock))

# 1-5 如果账户还有金额则执行此操作，会重置卖出原因
def check_remain_amount(context):
    """检查账户剩余资金，如果是因涨停卖出则可以再次买入，止损卖出则隔1天再交易"""
    if g.reason_to_sell == 'limitup':  # 判断售出原因，如果是涨停售出则可以再次交易
        g.hold_list = list(context.portfolio.positions.keys())
        if len(g.hold_list) < g.stock_num:  # 如果持仓数量不足目标数量
            target_list = g.target_list  # 每周更新的股票池
            target_list = filter_not_buy_again(target_list)  # 排除本周调仓时已经持仓的股票
            target_list = target_list[:min(g.stock_num, len(target_list))]  # 确保不超过目标持仓数量
            
            log.info('有余额可用' + str(round((context.portfolio.cash), 2)) + '元。' + str(target_list))
            buy_security(context, target_list)  # 买入股票
        
        g.reason_to_sell = ''  # 重置卖出原因
    else:
        g.c += 1  # 止损天数计数
        log.info('刚刚止损，隔1天再交易')
        if g.c % 2 == 0:  # 隔1天后重置卖出原因
            g.reason_to_sell = ''

# 1-6 下午检查交易
def trade_afternoon(context):
    """每天下午检查涨停股票并处理剩余资金"""
    if g.no_trading_today_signal == False:  # 非特殊日期才交易
        check_limit_up(context)  # 检查涨停股票
        check_remain_amount(context)  # 处理剩余资金

# 2-1 过滤停牌股票
def filter_paused_stock(stock_list):
    """过滤停牌股票"""
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].paused]

# 2-2 过滤ST及其他具有退市标签的股票
def filter_st_stock(stock_list):
    """过滤ST及其他具有退市标签的股票"""
    current_data = get_current_data()
    return [stock for stock in stock_list
            if not current_data[stock].is_st
            and 'ST' not in current_data[stock].name
            and '*' not in current_data[stock].name
            and '退' not in current_data[stock].name]

# 2-3 过滤科创北交股票，改为仅保留沪深主板股票
def filter_kcbj_stock(stock_list):
    """过滤科创北交股票，仅保留沪深主板股票"""
    for stock in stock_list[:]:
        # 过滤科创板（688开头）、创业板（300开头）、北交所（4或8开头）股票
        if stock[0] == '4' or stock[0] == '8' or stock[:3] == '688' or stock[:3] == '300':
            stock_list.remove(stock)
    return stock_list

# 2-4 过滤除持仓外涨停的股票
def filter_limitup_stock(context, stock_list):
    """过滤除持仓外涨停的股票"""
    # 获取股票前一天的收盘价和涨停价
    df = get_price(stock_list, end_date=context.previous_date, frequency='daily', 
        fields=['close', 'high_limit', 'low_limit'], count=1, panel=False, fill_paused=False)
    # 筛选前一天涨停的股票
    df = df[df['close'] == df['high_limit']]
    # 保留持仓股票，过滤其他涨停股票
    return [stock for stock in stock_list if stock in g.hold_list or stock not in list(df.code)]

# 2-5 过滤除了持仓外跌停的股票
def filter_limitdown_stock(context, stock_list):
    """过滤除了持仓外跌停的股票"""
    # 获取股票前一天的收盘价和跌停价
    df = get_price(stock_list, end_date=context.previous_date, frequency='daily', 
        fields=['close', 'high_limit', 'low_limit'], count=1, panel=False, fill_paused=False)
    # 筛选前一天跌停的股票
    df = df[df['close'] == df['low_limit']]
    # 保留持仓股票，过滤其他跌停股票
    return [stock for stock in stock_list if stock in g.hold_list or stock not in list(df.code)]

# 2-6 过滤次新股
def filter_new_stock(context, stock_list):
    """过滤上市不满1年的次新股"""
    yesterday = context.previous_date
    return [stock for stock in stock_list if not yesterday - get_security_info(stock).start_date < timedelta(days=375)]

# 2-6.5 过滤除持仓外股价过高的
def filter_highprice_stock(context, stock_list):
    """过滤除持仓外股价过高的股票"""
    last_prices = history(1, unit='1d', field='close', security_list=stock_list)
    return [stock for stock in stock_list if stock in g.hold_list or
            last_prices[stock][-1] <= g.up_price]

# 2-7 删除本周一买入的股票
def filter_not_buy_again(stock_list):
    """过滤本周内已经买入过的股票"""
    return [stock for stock in stock_list if stock not in g.not_buy_again]
 
# 3-1 交易模块-自定义下单
def order_target_value_(security, value):
    """自定义下单函数，添加日志记录"""
    if value == 0:
        pass
        # log.debug("Selling out %s" % (security))
    else:
        log.debug("Order %s to value %f" % (security, value))
    return order_target_value(security, value)

# 3-2 交易模块-开仓
def open_position(security, value):
    """开仓函数，返回开仓是否成功"""
    order = order_target_value_(security, value)
    if order is not None and order.filled > 0:
        return True
    return False

# 3-3 交易模块-平仓，调仓，止盈，特殊月份卖出用这个函数，止损不是这个
def close_position(position):
    """平仓函数，返回平仓是否成功"""
    security = position.security
    order = order_target_value_(security, 0)  # 可能会因停牌失败
    if order is not None:
        if order.status == OrderStatus.held and order.filled == order.amount:
            return True
    return False

# 3-4 买入模块
def buy_security(context, target_list):
    """买入股票模块，按可用资金平均分配买入目标股票"""
    # 持仓股数量
    position_count = len(context.portfolio.positions)
    # 目标股数量
    target_num = len(target_list)
    
    if target_num > position_count:  # 如果目标数量大于当前持仓数量
        # 计算每只股票的买入金额
        value = context.portfolio.cash / (target_num - position_count)
        
        for stock in target_list:
            # 如果股票尚未持仓
            if context.portfolio.positions[stock].total_amount == 0:
                # 执行买入操作
                if open_position(stock, value):
                    log.info("买入[%s]（%s元）" % (stock, value))
                    g.not_buy_again.append(stock)  # 记录已买入股票，本周内不再买入
                    
                    # 如果已经达到目标持仓数量，停止买入
                    if len(context.portfolio.positions) == target_num:
                        break

# 4-1 判断今天是否为特殊时间段
def today_is_between(context):
    """判断今天是否为特殊时间段（1月5日至2月5日或4月5日至4月30日）"""
    today = context.current_dt.strftime('%m-%d')
    if g.pass_april is True:
        if (('04-05' <= today) and (today <= '04-30')) or (('01-05' <= today) and (today <= '02-05')):
            return True
        else:
            return False
    else:
        return False

# 4-2 特殊月份清仓
def close_account(context):
    """特殊月份清仓函数"""
    if g.no_trading_today_signal == True:  # 如果是特殊日期
        if len(g.hold_list) != 0:  # 如果有持仓
            for stock in g.hold_list:
                position = context.portfolio.positions[stock]
                if close_position(position):  # 执行平仓操作
                    log.info("卖出[%s]" % (stock))

