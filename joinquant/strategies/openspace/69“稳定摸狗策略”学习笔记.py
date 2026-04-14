# 克隆自聚宽文章：https://www.joinquant.com/post/49290
# 标题：“稳定摸狗策略”学习笔记
# 作者：口袋里的钥匙扣

# 克隆自聚宽文章：https://www.joinquant.com/post/49263
# 标题：安全摸狗策略
# 作者：MarioC

# 克隆自聚宽文章：https://www.joinquant.com/post/42673
# 标题：【回顾3】ETF策略之核心资产轮动
# 作者：wywy1995

import numpy as np
import pandas as pd


#初始化函数 
def initialize(context):
    # 设定基准
    set_benchmark('000300.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 设置滑点 https://www.joinquant.com/view/community/detail/a31a822d1cfa7e83b1dda228d4562a70
    set_slippage(FixedSlippage(0.001))
    # 设置交易成本
    set_order_cost(OrderCost(open_tax=0, close_tax=0, open_commission=0.0002, close_commission=0.0002, close_today_commission=0, min_commission=5), type='fund')
    # 过滤一定级别的日志
    log.set_level('system', 'error')
    # 参数
    g.etf_pool = [
        '518880.XSHG', #黄金ETF（大宗商品）
        '513100.XSHG', #纳指100（海外资产）
        '159915.XSHE', #创业板100（成长股，科技股，中小盘）
        '510180.XSHG', #上证180（价值股，蓝筹股，中大盘）
    ]
    g.m_days = 25 #动量参考天数
    run_daily(trade, '9:30') #每天运行确保即时捕捉动量变化

    
def MOM(etf):
    # 取最近m_days日收盘价，使用对数价格拟合趋势
    df = attribute_history(etf, g.m_days, '1d', ['close'])
    y = np.log(df['close'].values)
    n = len(y)  
    x = np.arange(n)
    # 线性递增权重：越近的价格权重越高
    weights = np.linspace(1,2, n)
    slope, intercept = np.polyfit(x, y, 1, w=weights)
    # 由斜率推导年化收益（近似250个交易日）
    annualized_returns = math.pow(math.exp(slope), 250) - 1
    residuals = y - (slope * x + intercept)
    weighted_residuals = weights * residuals**2
    # 趋势拟合优度，越接近1代表趋势越平滑、线性特征越强
    r_squared = 1 - (np.sum(weighted_residuals) / np.sum(weights * (y - np.mean(y))**2))
    # 最终动量分：收益强度 * 趋势质量
    score = annualized_returns * r_squared
    return score

# 基于年化收益和判定系数打分的动量因子轮动 https://www.joinquant.com/post/26142
def get_rank(etf_pool):
    score_list = []
    for etf in etf_pool:
        score = MOM(etf)
        score_list.append(score)
    df = pd.DataFrame(index=etf_pool, data={'score':score_list})
    # 分数从高到低排序
    df = df.sort_values(by='score', ascending=False)
    #total_score = df['score'].sum() 不告诉你这个怎么用
    # 安全区间过滤：过弱（<=0）或过热（>5）的标的不参与本轮
    df = df[(df['score'] > 0) & (df['score'] <= 5)]
    rank_list = list(df.index)
    if len(rank_list) == 0:
        # 若全部不满足条件，切换到低波动避险ETF
        rank_list=["511880.XSHG"]
    return rank_list

# 交易
def trade(context):
    # 只持有动量最高的一只ETF（单持仓轮动）
    target_num = 1  
    target_list = get_rank(g.etf_pool)[:target_num]
    # 卖出    
    hold_list = list(context.portfolio.positions)
    for etf in hold_list:
        if etf not in target_list:
            # 当前持仓不在目标列表中，清仓
            order_target_value(etf, 0)
            print('卖出' + str(etf))
        else:
            # 仍在目标列表中，继续持有
            print('继续持有' + str(etf))
            pass
    # 买入
    hold_list = list(context.portfolio.positions)
    if len(hold_list) < target_num:
        # 按目标持仓数量等权分配可用现金
        value = context.portfolio.available_cash / (target_num - len(hold_list))
        for etf in target_list:
            if context.portfolio.positions[etf].total_amount == 0:
                # 仅对当前未持有的目标标的下单
                order_target_value(etf, value)
                print('买入' + str(etf))

