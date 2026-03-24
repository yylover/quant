"""
策略收益
491.77%
策略年化收益
42.26%
超额收益
575.25%
基准收益
-12.36%
阿尔法
0.421
贝塔
0.578
夏普比率
1.642
胜率
0.643
盈亏比
3.020
最大回撤 
23.16%
索提诺比率
2.220
日均超额收益
0.16%
超额收益最大回撤
19.35%
超额收益夏普比率
1.891
日胜率
0.549
盈利次数
236
亏损次数
131
信息比率
2.019
策略波动率
0.233
基准波动率
0.178
最大回撤区间
2024/12/12,2025/01/10



下面是对 **`strategies/cases/zeshi_yitiaolong.py`**（文件头带一段回测收益展示）的策略拆解，基于当前代码。

---

## 1. 策略定位（一句话）

**月度择时 + 大小盘风格轮动 + 基本面筛选**：每月初根据 **沪深300大票** 与 **中小盘指数成分** 近 **10 日平均涨跌** 判断「偏大」「偏小」或「行情弱则配外盘 ETF」；再在对应股票池里用 **ROE/ROIC/估值/成长** 等条件选出 **约 3 只** 持仓。  
日常用 **涨停持有规则**、**尾盘涨停打开则卖**、**-8% 止损**，以及一段 **「补跌加仓」** 逻辑（见下文注意点）。

- **基准**：沪深300（`000300.XSHG`）  
- **滑点**：`FixedSlippage(0)`（回测偏理想）  
- **防未来数据**：`avoid_future_data` 已开  

---

## 2. 时间与主流程

| 时间 | 函数 | 作用 |
|------|------|------|
| **每月 1 日 9:30** | `monthly_adjustment` | **核心**：大小盘强弱 → 选股池 → 调仓买卖。 |
| **每日 9:05** | `prepare_stock_list` | 更新持仓列表、**昨日涨停**持仓列表（用于后面「涨停不卖」等）。 |
| **每日 14:00** | `stop_loss` | 涨停打开则卖；**跌破成本约 92%** 止损；另有 `for-else` 分支（见第 6 节）。 |

---

## 3. 月度择时逻辑（`monthly_adjustment`）

1. **两个股票池**（均用 **上一交易日** `dt_last` 成分）：  
   - **B**：`000300` 沪深300  
   - **S**：`399101` 中小板综（名称上以代码为准）  
   - 统一 **剔除** 科创/北交/创业板等（`filter_kcbj_stock` 会去掉 `3` 开头等）、ST、次新股等。

2. **代表大/小的样本**：  
   - 在 **300 成分**里按 **流通市值从大到小** 取前 **20** 只 → `Blst`  
   - 在 **399101 成分**里按 **流通市值从小到大** 取前 **20** 只 → `Slst`

3. **算近 N=10 日** 这 20+20 只的 **平均涨跌幅** → `B_mean`、`S_mean`（先分别对 20 只算区间涨跌再取均值）。

4. **风格分支**（与注释「开大 / 开小 / 开外盘」对应）：  
   - **「无敌好行情」**：`B_mean>10` 或 `S_mean>10`（单位可理解为百分比量级）  
     - 若 `B_mean > S_mean`：**偏大** → 在 **300 全成分**上用 `ROIC_BIG`、`BIG`、`BM` 合并去重得 `target_list`  
     - 否则：**偏小** → `SMALL` 取前 `g.stock_num*3`  
   - **否则若** `B_mean>S_mean` 且 `B_mean>0`：**偏大**（同上三类合并）  
   - **否则若** `B_mean<S_mean` 且 `S_mean>0`：**偏小** → `SMALL`  
   - **否则**：**`target_list = g.foreign_ETF`**（黄金、德股、纳指、石油等 **5 只** 跨境/商品 ETF）

5. **再过滤**：`filter_limitup_stock`、`filter_limitdown_stock`、`filter_paused_stock`（避免买在涨跌停板价上）。

6. **调仓**：  
   - 若持仓 **不在** `target_list` 且 **不在** `g.yesterday_HL_list`（昨日涨停的持仓保护），则 **平仓**。  
   - 若目标数量 **多于** 当前持仓数，用 **现金 / 需新增只数** 作为每只买入金额，**逐个 `open_position`** 直到满仓或目标只数。

---

## 4. 三套选股函数（含义摘要）

| 函数 | 思路 |
|------|------|
| **`SMALL`** | ROE>15%、ROA>10%，再按 **总市值升序**（偏小盘）。 |
| **`BIG`** | PE/PS/PCF、EPS、ROE、净利率、毛利率、营收增速等，按 **总市值降序** 取 **`g.stock_num`（3）**。 |
| **`ROIC_BIG`** | 总市值、PE、负债率、营收增长等 + **`filter_roic`**（`roic_ttm>8%`），按 **留存收益** 排序取前 3。 |
| **`BM`** | 市值 100–900 亿、PB/PCF、ROE、利润增速等，按市值升序取 3。 |

另有 **`filter_roic`**：对列表逐只拉 **`jqfactor` 的 `roic_ttm`**。

---

## 5. 日度风控（`prepare_stock_list` + `stop_loss`）

- **`prepare_stock_list`**：对当前持仓，看 **昨日** 是否 **收盘涨停**（`close == high_limit`），记入 **`g.yesterday_HL_list`**。  
- **`stop_loss`（14:00）**：  
  - 对 **昨日涨停** 标的：用 **1 分钟线** 看当前价是否 **仍封涨停**；若 **低于涨停价** → **卖出**（涨停打开即走）；仍涨停则 **继续持有**。  
  - 对其余持仓：若现价 **< 成本 × 0.92** → **清仓**（约 **-8%** 止损）。

---

## 6. 代码层面需警惕的问题

1. **`stop_loss` 里 `for ... else`（约 123–143 行）**  
   - 在 Python 中，`for` 的 **`else`** 会在 **循环正常结束（未 break）时执行**。  
   - 这里 **`else` 会与「补跌最多的 N 支加仓」** 绑在一起，**每个交易日 14:00 在循环跑完后都可能进入 `else`**，逻辑极易 **不符合「仅止损后补仓」** 的设计意图，更像是 **缩进/结构错误**。实盘/回测前建议人工核对或重写该段。

2. **`filter_highprice_stock` / `filter_highprice_stock2`**  
   - 在文中 **未被 `monthly_adjustment` 调用**，若策略意图是限制高价股，则当前 **可能未生效**。

3. **`get_recent_limit_up_stock` / `get_recent_down_up_stock`**  
   - 同样 **未见在主流程调用**，可能是预留或复制遗留。

4. **`filter_kcbj_stock`**  
   - 去掉 **`3` 开头**，会 **排除创业板（300）**，选股范围与「中小盘」表述需一致理解。

5. **回测假设**  
   - **零滑点**、涨跌停过滤、月度调仓，收益片段（文件头 **491%** 等）**强依赖区间**，且 **≠ 实盘**。  

6. **依赖**  
   - `jqfactor`、`get_factor_values`、`talib` 等需在聚宽环境可用。

---

## 7. 一句话总结

**`zeshi_yitiaolong.py` = 每月用「沪深300代表的大票 vs 中小板综代表的小票」近 10 日强弱，在「价值/成长/中盘」等基本面规则里选 **3 只** 左右；弱市则切到 **5 只外盘 ETF**；日度对 **涨停股** 做 **开板卖**，对其余持仓做 **约 8% 止损**，并依赖 **`prepare_stock_list` 的昨日涨停列表** 避免轻易卖掉连板仓位。**

若你希望，我可以只针对 **`stop_loss` 那一段** 画出「当前解释器实际执行顺序」的流程说明，便于你决定是否改缩进。

"""


from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd
import pickle
import talib
import warnings
warnings.filterwarnings("ignore")
# 初始化函数
def initialize(context):
    # 设定基准
    set_benchmark('000300.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置为0https://cdn.joinquant.com/std/algorithm/img/mdpush.png
    set_slippage(FixedSlippage(0))
    # 设置交易成本万分之三，不同滑点影响可在归因分析中查看
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), type='stock')
    # 过滤order中低于error级别的日志https://cdn.joinquant.com/std/algorithm/img/mdpush.png
    log.set_level('order', 'error')
    # 初始化全局变量
    g.no_trading_today_signal = False
    g.stock_num = 3
    g.hold_list = []  # 当前持仓的全部股票
    g.yesterday_HL_list = []  # 记录持仓中昨日涨停的股票
    g.foreign_ETF = [
        '518880.XSHG',
        '513030.XSHG',
        '513100.XSHG',
        '164824.XSHE',
        '159866.XSHE',
        ]
    # 设置交易运行时间
    run_daily(prepare_stock_list, '9:05')
    run_monthly(monthly_adjustment, 1, '9:30')
    run_daily(stop_loss, '14:00')

def prepare_stock_list(context):
    # 获取已持有列表
    g.hold_list = []
    for position in list(context.portfolio.positions.values()):
        stock = position.security
        g.hold_list.append(stock)
    # 获取昨日涨停列表
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', fields=['close', 'high_limit'],
                       count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.yesterday_HL_list = list(df.code)
    else:
        g.yesterday_HL_list = []
        
def stop_loss(context):
    num = 0
    now_time = context.current_dt
    if g.yesterday_HL_list != []:
        # 对昨日涨停股票观察到尾盘如不涨停则提前卖出，如果涨停即使不在应买入列表仍暂时持有
        for stock in g.yesterday_HL_list:
            current_data = get_price(stock, end_date=now_time, frequency='1m', fields=['close', 'high_limit'],
                                     skip_paused=False, fq='pre', count=1, panel=False, fill_paused=True)
            if current_data.iloc[0, 0] < current_data.iloc[0, 1]:
                log.info("[%s]涨停打开，卖出" % (stock))
                position = context.portfolio.positions[stock]
                close_position(position)
                num = num+1
            else:
                log.info("[%s]涨停，继续持有" % (stock))
    SS=[]
    S=[]
    for stock in g.hold_list:
        if stock in list(context.portfolio.positions.keys()):
            if context.portfolio.positions[stock].price < context.portfolio.positions[stock].avg_cost * 0.92:
                order_target_value(stock, 0)
                log.debug("止损 Selling out %s" % (stock))
                num = num+1
            else:
                S.append(stock)
                NOW = (context.portfolio.positions[stock].price - context.portfolio.positions[stock].avg_cost)/context.portfolio.positions[stock].avg_cost
                SS.append(np.array(NOW))
    else:
        if num >=1:
            if len(SS) > 0:
                num=3
                min_values = sorted(SS)[:num]
                min_indices = [SS.index(value) for value in min_values]
                min_strings = [S[index] for index in min_indices]
                cash = context.portfolio.cash/num
                for ss in min_strings:
                    order_value(ss, cash)
                    log.debug("补跌最多的N支 Order %s" % (ss))

def filter_roic(context,stock_list):
    yesterday = context.previous_date
    list=[]
    for stock in stock_list:
        roic=get_factor_values(stock, 'roic_ttm', end_date=yesterday,count=1)['roic_ttm'].iloc[0,0]
        if roic>0.08:
            list.append(stock)
    return list
def filter_highprice_stock(context,stock_list):
	last_prices = history(1, unit='1m', field='close', security_list=stock_list)
	return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
			or last_prices[stock][-1] < 10]
def filter_highprice_stock2(context,stock_list):
	last_prices = history(1, unit='1m', field='close', security_list=stock_list)
	return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
			or last_prices[stock][-1] < 300]
def get_recent_limit_up_stock(context, stock_list, recent_days):
    stat_date = context.previous_date
    new_list = []
    for stock in stock_list:
        df = get_price(stock, end_date=stat_date, frequency='daily', fields=['close','high_limit'], count=recent_days, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        if len(df) > 0:
            new_list.append(stock)
    return new_list
def get_recent_down_up_stock(context, stock_list, recent_days):
    stat_date = context.previous_date
    new_list = []
    for stock in stock_list:
        df = get_price(stock, end_date=stat_date, frequency='daily', fields=['close','low_limit'], count=recent_days, panel=False, fill_paused=False)
        df = df[df['close'] == df['low_limit']]
        if len(df) > 0:
            new_list.append(stock)
    return new_list
def SMALL(context,choice):
    df = get_fundamentals(query(
        valuation.code,
        indicator.roe,
        indicator.roa,
    ).filter(
        valuation.code.in_(choice),
        indicator.roe > 0.15,
        indicator.roa > 0.10,
    )).set_index('code').index.tolist()

    q = query(
    valuation.code
    ).filter(
	valuation.code.in_(df)
	).order_by(
         valuation.market_cap.asc())
    final_list = list(get_fundamentals(q).code)
    return final_list
    
def BIG(context,choice):
    BIG_stock_list = get_fundamentals(query(
        valuation.code,
    ).filter(
        valuation.code.in_(choice),
        valuation.pe_ratio_lyr.between(0,30),#市盈率
        valuation.ps_ratio.between(0,8),#市销率TTM
        valuation.pcf_ratio<10,#市现率TTM
        indicator.eps>0.3,#每股收益
        indicator.roe>0.1,#净资产收益率
        indicator.net_profit_margin>0.1,#销售净利率
        indicator.gross_profit_margin>0.3,#销售毛利率
        indicator.inc_revenue_year_on_year>0.25,#营业收入同比增长率
    ).order_by(
    valuation.market_cap.desc()).limit(g.stock_num)).set_index('code').index.tolist()
    
    return BIG_stock_list
def ROIC_BIG(context,choice):
    df = get_fundamentals(query(
            valuation.code,
        ).filter(
            valuation.code.in_(choice),
            valuation.market_cap>300,#总市值（亿元）
            valuation.pe_ratio.between(0,50),#市盈率TTM
            indicator.eps>0.12,#每股收益
            indicator.roa>0.15,  #总资产收益
            (balance.total_liability/balance.total_sheet_owner_equities)<0.5,
            indicator.inc_total_revenue_year_on_year>0.3,#营业总收入同比增长率
            indicator.inc_revenue_year_on_year>0.2,#营业收入同比增长率
            balance.retained_profit>0,#未分配利润
        )).set_index('code').index.tolist()
    df=filter_roic(context,df)
    q = query(
    valuation.code
    ).filter(
	valuation.code.in_(df)
	).order_by(
         balance.retained_profit.desc())

    final_list = list(get_fundamentals(q).code)[:g.stock_num]
    return final_list
def BM(context,choice):
    BM_list = get_fundamentals(query(
            valuation.code,
        ).filter(
            valuation.code.in_(choice),
            valuation.market_cap.between(100,900),#总市值（亿元）
            valuation.pb_ratio.between(0,10),#市净率
            valuation.pcf_ratio<4,#市现率TTM
            indicator.eps>0.3,#每股收益
            indicator.roe>0.2,#净资产收益率
            indicator.net_profit_margin>0.1,#销售净利率
            indicator.inc_revenue_year_on_year>0.2,#营业收入同比增长率
            indicator.inc_operation_profit_year_on_year>0.1,#营业利润同比增长率
        ).order_by(
        valuation.market_cap.asc()).limit(g.stock_num)).set_index('code').index.tolist()
    return BM_list
# 1-3 整体调整持仓
def monthly_adjustment(context):
    today = context.current_dt
    dt_last = context.previous_date
    N=10
    B_stocks = get_index_stocks('000300.XSHG', dt_last)
    B_stocks = filter_kcbj_stock(B_stocks)
    B_stocks = filter_st_stock(B_stocks)
    B_stocks = filter_new_stock(context, B_stocks)
    
    S_stocks = get_index_stocks('399101.XSHE', dt_last)
    S_stocks = filter_kcbj_stock(S_stocks)
    S_stocks = filter_st_stock(S_stocks)
    S_stocks = filter_new_stock(context, S_stocks)
    
    q = query(
        valuation.code, valuation.circulating_market_cap
    ).filter(
        valuation.code.in_(B_stocks)
    ).order_by(
        valuation.circulating_market_cap.desc()
    )
    df = get_fundamentals(q, date=dt_last)
    Blst = list(df.code)[:20]
    
    q = query(
        valuation.code, valuation.circulating_market_cap
    ).filter(
        valuation.code.in_(S_stocks)
    ).order_by(
        valuation.circulating_market_cap.asc()
    )
    df = get_fundamentals(q, date=dt_last)
    Slst = list(df.code)[:20]
    #
    B_ratio = get_price(Blst, end_date=dt_last, frequency='1d', fields=['close'], count=N, panel=False
                        ).pivot(index='time', columns='code', values='close')
    change_BIG = (B_ratio.iloc[-1] / B_ratio.iloc[0] - 1) * 100
    A1 = np.array(change_BIG)
    A1 = np.nan_to_num(A1)  
    B_mean = np.mean(A1)

    
    S_ratio = get_price(Slst, end_date=dt_last, frequency='1d', fields=['close'], count=N, panel=False
                        ).pivot(index='time', columns='code', values='close')
    change_SMALL = (S_ratio.iloc[-1] / S_ratio.iloc[0] - 1) * 100
    A1 = np.array(change_SMALL)
    A1 = np.nan_to_num(A1)
    S_mean = np.mean(A1)


    if B_mean > 10 or S_mean > 10:
        print('无敌好行情')
        if B_mean > S_mean:
            print('开大')
            choice = B_stocks
            target_list1 = ROIC_BIG(context,choice)
            target_list2 = BIG(context,choice)
            target_list3 = BM(context,choice)
            target_list = target_list3+target_list1+target_list2
            target_list = list(set(target_list))
        else:
            print('开小')
            choice = S_stocks
            target_list = SMALL(context,choice)[:g.stock_num*3]
    elif B_mean>S_mean and B_mean>0:
        print('开大')
        choice = B_stocks
        target_list2 = ROIC_BIG(context,choice)
        target_list1 = BIG(context,choice)
        target_list3 = BM(context,choice)
        target_list = target_list1+target_list2+target_list3
        target_list = list(set(target_list))

    elif B_mean < S_mean and S_mean > 0:
        print('开小')
        choice = S_stocks
        target_list = SMALL(context,choice)[:g.stock_num*3]
    else:
        print('开外盘')
        target_list = g.foreign_ETF

    target_list = filter_limitup_stock(context,target_list)
    target_list = filter_limitdown_stock(context,target_list)
    target_list = filter_paused_stock(target_list)
    for stock in g.hold_list:
        if (stock not in target_list) and (stock not in g.yesterday_HL_list):
            position = context.portfolio.positions[stock]
            close_position(position)
    position_count = len(context.portfolio.positions)
    target_num = len(target_list)
    if target_num > position_count:
        value = context.portfolio.cash / (target_num - position_count)
        for stock in target_list:
            if stock not in list(context.portfolio.positions.keys()):
                if open_position(stock, value):
                    if len(context.portfolio.positions) == target_num:
                        break


# 3-1 交易模块-自定义下单
def order_target_value_(security, value):
    if value == 0:
        log.debug("Selling out %s" % (security))
    else:
        log.debug("Order %s to value %f" % (security, value))
    return order_target_value(security, value)

# 3-2 交易模块-开仓
def open_position(security, value):
    order = order_target_value_(security, value)
    if order != None and order.filled > 0:
        return True
    return False

# 3-3 交易模块-平仓
def close_position(position):
    security = position.security
    order = order_target_value_(security, 0)  # 可能会因停牌失败
    if order != None:
        if order.status == OrderStatus.held and order.filled == order.amount:
            return True
    return False


def filter_paused_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].paused]

# 2-2 过滤ST及其他具有退市标签的股票
def filter_st_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list
            if not current_data[stock].is_st
            and 'ST' not in current_data[stock].name
            and '*' not in current_data[stock].name
            and '退' not in current_data[stock].name]


# 2-3 过滤科创北交股票
def filter_kcbj_stock(stock_list):
    for stock in stock_list[:]:
        if stock[0] == '4' or stock[0] == '8' or stock[:2] == '68' or stock[0] == '3':
            stock_list.remove(stock)
    return stock_list


# 2-4 过滤涨停的股票
def filter_limitup_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] < current_data[stock].high_limit]


# 2-5 过滤跌停的股票
def filter_limitdown_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] > current_data[stock].low_limit]


# 2-6 过滤次新股
def filter_new_stock(context, stock_list):
    yesterday = context.previous_date
    return [stock for stock in stock_list if
            not yesterday - get_security_info(stock).start_date < datetime.timedelta(days=375)]

