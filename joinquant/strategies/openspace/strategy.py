# 聚宽风格代码
def initialize(context):
    # 初始化
    context.security = '000300.XSHG'  # 沪深300
    context.short_ma = 5
    context.long_ma = 20
    set_benchmark('000300.XSHG')
    set_slippage(PriceSlippage(0.002))  # 滑点0.2%
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013))  # 佣金+印花税

def handle_data(context, data):
    # 每日运行
    security = context.security
    # 获取历史价格
    df = history(60, '1d', 'close', [security])
    # 计算均线
    ma_short = df[security].rolling(context.short_ma).mean()[-1]
    ma_long = df[security].rolling(context.long_ma).mean()[-1]
    # 持仓
    pos = context.portfolio.positions[security].total_amount
    # 金叉买入
    if ma_short > ma_long and pos == 0:
        order_target_percent(security, 1.0)  # 满仓
    # 死叉卖出
    elif ma_short < ma_long and pos > 0:
        order_target(security, 0)
