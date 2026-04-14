# 克隆自聚宽文章：https://www.joinquant.com/post/48789
# 标题：低风险中等收益策略
# 作者：Gyro^.^

# 策略收益 37.86% 基准收益 18.08% Alpha 0.20 Beta 0.59 Sharpe 1.88 最大回撤 11.12%

# ## 策略概述
# 这是一个低风险中等收益的量化策略，通过投资小市值优质股票和基金组合，实现风险分散和稳健收益。策略核心思想是"小而美"——选择小市值但基本面良好的股票，同时配置部分基金作为现金管理工具。

# ## 核心逻辑
# ### 1. 初始化设置
# - 防未来数据 ：启用 avoid_future_data ，确保不使用未来数据
# - 真实价格交易 ：使用真实价格进行交易
# - 日志级别 ：只记录error级别以上的日志
# - 运行时间 ：
#   - 开盘前更新股票池（ before_open ）
#   - 9:35执行交易（ 9:35 ）
#   - 收盘后生成报告（ after_close ）
# ### 2. 每日更新（iUpdate）
# 参数设置 ：

# - nposition = 100 ：目标持仓数量（100只）
# - nchoice = 30 ：选择的小市值股票数量
# 更新内容 ：

# - 计数器加1
# - 选择小市值优质股票（30只）
# - 选择基金（现金管理工具）
# - 计算每只股票的仓位大小： 1.0/nposition * 总资金
# ### 3. 交易执行（iTrader）
# 卖出逻辑 ：

# - 遍历当前持仓
# - 如果股票不在目标列表中，且未停牌，则卖出
# - 使用市价单，价格设置为最新价的99%
# 买入股票逻辑 ：

# - 遍历目标股票列表
# - 如果现金不足，停止买入
# - 如果股票未停牌且不在持仓中，则买入
# - 买入金额取 max(position_size, 100*最新价) ，确保至少买入1手
# - 使用市价单，价格设置为最新价的101%
# 买入基金逻辑 ：

# - 遍历目标基金列表
# - 如果现金不足，停止买入
# - 如果基金未停牌，则买入
# - 买入金额为 position_size
# - 使用市价单，价格设置为最新价
# ### 4. 选股逻辑（_choice_small）
# 股票池构建 ：

# - 基准指数：国证A指（399317.XSHE）
# - 获取指数成分股
# - 过滤ST股票
# 小市值筛选 ：

# - 按市值从小到大排序
# - 选择前10%的股票（ m = int(0.1*len(stocks)) ）
# 基本面筛选（三正原则） ：

# - pb_ratio > 0 ：市净率为正
# - inc_return > 0 ：收益增长率为正
# - ocf_to_revenue > 0 ：经营现金流与收入比为正
# 最终选择 ：

# - 选择前 1.2 * nchoice 只股票作为缓冲（36只）
# - 优先保留已在持仓中的股票
# - 最终选择30只股票
# ### 5. 基金选择（_choice_funds）
# 基金池 ：

# - 默认基金： ['511220.XSHG', '518880.XSHG', '513500.XSHG']
#   - 511220.XSHG：国债ETF
#   - 518880.XSHG：黄金ETF
#   - 513500.XSHG：标普500ETF
# 过滤条件 ：

# - 排除停牌基金
# - 如果所有基金都停牌，默认使用 000012.XSHG （上证180金融指数）

import pandas as pd
import json

def initialize(context):
    # setting system
    log.set_level('order', 'error')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    # setting strategy
    run_daily(iUpdate, 'before_open')
    run_daily(iTrader, '9:35')
    run_daily(iReport, 'after_close')
    g.days = 0 # day counter

def iUpdate(context):
    # parameters
    nposition = 100 # number of positions
    nchoice = 30
    # daily update
    g.days = g.days + 1
    g.stocks = _choice_small(context, nchoice)
    g.funds = _choice_funds(context)
    g.position_size = 1.0/nposition * context.portfolio.total_value

def iTrader(context):
    # load data
    stocks = g.stocks
    funds = g.funds 
    position_size = g.position_size
    cash_size = 5 * position_size
    cdata = get_current_data()
    # sell
    choice = stocks + funds
    for s in context.portfolio.positions:
        if cdata[s].paused:
            continue
        if s not in choice:
            log.info('sell', s, cdata[s].name)
            order_target(s, 0, MarketOrderStyle(0.99*cdata[s].last_price))
    # buy stocks
    for s in stocks:
        if context.portfolio.available_cash < position_size:
            break # 现金耗尽，中止
        if cdata[s].paused:
            continue
        if s not in context.portfolio.positions:
            log.info('buy', s, cdata[s].name)
            value = max(position_size, 100*cdata[s].last_price)
            order_value(s, value, MarketOrderStyle(1.01*cdata[s].last_price))
    # buy funds
    for s in funds:
        if context.portfolio.available_cash < cash_size:
            break # 现金耗尽，中止
        if not cdata[s].paused:
            log.info('save', s, cdata[s].name)
            order_value(s, position_size, MarketOrderStyle(cdata[s].last_price))

def iReport(context):
    # table of positions
    cdata = get_current_data()
    tvalue = context.portfolio.total_value
    ptable = pd.DataFrame(columns=['amount', 'value', 'weight', 'name'])
    for s in context.portfolio.positions:
        ps = context.portfolio.positions[s]
        ptable.loc[s] = [ps.total_amount, int(ps.value), 100*ps.value/tvalue, cdata[s].name]
    ptable = ptable.sort_values(by='weight', ascending=False)
    # daily report
    pd.set_option('display.max_rows', None)
    log.info('  positions', len(ptable), '\n', ptable.head())
    log.info('  total win %i, return %.2f%%', \
            int(tvalue - context.portfolio.inout_cash), 100*context.portfolio.returns)
    log.info('  total value %.2f, cash %.2f', \
            context.portfolio.total_value/10000, context.portfolio.available_cash/10000)
    log.info('running days', g.days)

def _choice_small(context, nchoice):
    # parameters
    index = '399317.XSHE'
    # stocks
    dt_now = context.current_dt.date()
    stocks = get_index_stocks(index, dt_now)
    # non-ST
    cdata = get_current_data()
    stocks = [s for s in stocks if not cdata[s].is_st]
    # small stocks, 10%
    m = int(0.1*len(stocks))
    df = get_fundamentals(query(
            valuation.code,
            valuation.market_cap,
            valuation.pb_ratio,
            indicator.inc_return,
            indicator.ocf_to_revenue,
        ).filter(
            valuation.code.in_(stocks),
        ).order_by(valuation.market_cap.asc()
        ).limit(m)
        ).dropna().set_index('code')
    # qualify, 三正
    df = df[(df.pb_ratio > 0) & (df.inc_return > 0) & (df.ocf_to_revenue > 0)]
    # choice
    n = int(1.2 * nchoice) # buffer 20%
    stocks = df.head(n).index.tolist()
    # united
    stocks_0 = [s for s in stocks if s in context.portfolio.positions]
    stocks_1 = [s for s in stocks if s not in context.portfolio.positions]
    choice = (stocks_0 + stocks_1)[:nchoice]
    # report
    df = df[['market_cap']].loc[choice]
    df['name'] = [cdata[s].name for s in df.index]
    log.info('small-quality stocks', len(choice), '\n', df.head())
    # reuslt
    return choice

def _choice_funds(context):
    # load funds
    #funds = json.loads(read_file('funds'))
    funds = ['511220.XSHG', '518880.XSHG', '513500.XSHG']
    # filter
    cdata = get_current_data()
    funds = [s for s in funds if not cdata[s].paused]
    if len(funds) == 0:
        funds = ['000012.XSHG'] # default
    # results
    return funds
# end