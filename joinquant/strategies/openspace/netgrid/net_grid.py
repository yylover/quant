# 克隆自聚宽文章：https://www.joinquant.com/post/539
# 标题：【网格交易策略-年化30%+】-网格大法好，熊市不用跑~

import numpy
import pandas as pd
from pandas import Series
def initialize(context):
    g.cash = 1000000
    g.buy_stock = ['000300.XSHG']
    g.initial_price = {'000300.XSHG': 0}
    g.has_initial_position = {'000300.XSHG': False}
    g.last_adjust_price = {'000300.XSHG': 0}
    set_universe(g.buy_stock)

# 计算股票累计收益率（从建仓至今）
def security_accumulate_return(context,data,stock):
    current_price = data[stock].price
    if stock in context.portfolio.positions:
        cost = context.portfolio.positions[stock].avg_cost
        if cost != 0:
            return (current_price-cost)/cost
    return None

# 个股止损，根据累计收益
def conduct_accumulate_stoploss(context,data,stock,bench):
    if security_accumulate_return(context,data,stock) != None\
    and security_accumulate_return(context,data,stock) < bench:
        order_target_value(stock,0)
        log.info("Sell %s for stoploss" %stock)
        return True
    else:
        return False


# 初始底仓选择，判断没有initial_price，则建立基准价
def initial_price(context,data,stock):
    if g.initial_price[stock]==0:
        g.initial_price[stock]=data[stock].price
        g.last_adjust_price[stock]=data[stock].price
    return None

# 动态调整基准价
def adjust_benchmark_price(context, data, stock):
    current_price = data[stock].price
    last_adjust = g.last_adjust_price[stock]
    
    # 如果价格相对于上次调整价变化超过15%，则调整基准价
    if last_adjust > 0:
        price_change = (current_price - last_adjust) / last_adjust
        if abs(price_change) > 0.15:
            g.initial_price[stock] = current_price
            g.last_adjust_price[stock] = current_price
            log.info("Adjust benchmark price to: %.2f for %s" % (current_price, stock))
    return None

# 补仓、空仓：分n买入/卖出
def setup_position(context,data,stock,bench,status):
    bottom_price= g.initial_price[stock]
    if bottom_price == 0:
        return
    cash = context.portfolio.cash
    current_price = data[stock].price
    # 检查股票是否在持仓中
    if stock in context.portfolio.positions:
        amount = context.portfolio.positions[stock].total_amount
        current_value = current_price*amount
    else:
        amount = 0
        current_value = 0
    unit_value = g.cash/20
    returns = (current_price-bottom_price)/bottom_price
    #卖出
    if (status == 'short'):
        if returns > bench and current_value > 4*unit_value:
            order_target_value(stock,4*unit_value)
        if returns > 2*bench and current_value > 2*unit_value:
            order_target_value(stock,2*unit_value)
        if returns > 3*bench and current_value >1*unit_value :
            order_target_value(stock,1*unit_value)
        if returns > 4*bench and current_value >0:
            order_target_value(stock,0)
    # 买入
    if (status == 'long') and cash >0:
        # 指数交易最小单位为1股
        min_shares = 1
        min_value = current_price * min_shares
        
        if returns < bench and current_value < 3*unit_value:
            target_value = 3*unit_value
            if cash >= min_value:
                order_target_value(stock, target_value)
        if returns < 2*bench and current_value < 5*unit_value:
            target_value = 5*unit_value
            if cash >= min_value:
                order_target_value(stock, target_value)
        if returns < 3*bench and current_value <7*unit_value :
            target_value = 7*unit_value
            if cash >= min_value:
                order_target_value(stock, target_value)
        if returns < 4*bench and current_value < 8*unit_value:
            target_value = 8*unit_value
            if cash >= min_value:
                order_target_value(stock, target_value)
    return True 

# 每个单位时间(如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次)调用一次
def handle_data(context, data):
    for stock in g.buy_stock:
    
        #初始设置底仓
        initial_price(context,data,stock)
        
        # 初始建仓
        if not g.has_initial_position[stock]:
            unit_value = g.cash/20
            current_price = data[stock].price
            min_shares = 1
            min_value = current_price * min_shares
            cash = context.portfolio.cash
            if cash >= min_value:
                target_value = 2*unit_value
                order_target_value(stock, target_value)
                g.has_initial_position[stock] = True
                log.info("Initial position established: %.2f for %s" % (target_value, stock))
        
        # 动态调整基准价
        adjust_benchmark_price(context, data, stock)
        
        #补仓步长：更频繁的网格
        setup_position(context,data,stock,-0.05,'long')
        #空仓步长：更频繁的网格
        setup_position(context,data,stock,0.08,'short')
    
    # 计算并绘制仓位
    total_value = context.portfolio.total_value
    # 计算持股市值
    market_value = 0
    for stock in context.portfolio.positions:
        position = context.portfolio.positions[stock]
        market_value += position.total_amount * position.price
    position_ratio = market_value / total_value if total_value > 0 else 0
    # 绘制仓位曲线
    if 'plot' in dir():
        plot('position_ratio', position_ratio)

