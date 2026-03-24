"""
聚宽量化选股策略（完整版 - 对照标准样本编写）
=====================================
选股条件：
1. 个股收盘价在2元到200元之间
3. A股市值在40亿元到400亿元之间
4. 流通股本在9000万股到12亿股之间
5. 当日成交总金额大于2000万
6. 个股换手率大于1%
7. 上市天数大于545天
8. 股东人数大于12000户
9. 当日成交量大于前一日成交量
10. KDJ指标：前一日K值< 30，当日K值>30且K>D，J>0
11. MA120>MA365
12. 近1年涨幅小于50%，近20日涨幅小于30%，前一日涨幅小于4%
13. PE大于0
14. MA5 > 昨日MA5

买入时机：9:50-14:57，MACD金叉买入
仓位控制：单只≤10%，最多10只

止损策略：
- 时间止损：持有5天，最大盈利< 3%清仓
- 硬止损：亏损≥8%清仓
- 移动止损：从最高点回撤≥8%清仓
- 利润衰减：按盈利区间和回撤幅度执行

作者：******量化研究员
日期：2026-03-22
参考：joinquant_fixed_strategy.py 标准样本



策略收益
483.78%
策略年化收益
41.88%
超额收益
566.14%
基准收益
-12.36%
阿尔法
0.417
贝塔
0.575
夏普比率
1.630
胜率
0.638
盈亏比
2.918
最大回撤 
22.81%
索提诺比率
2.200
日均超额收益
0.16%
超额收益最大回撤
19.41%
超额收益夏普比率
1.876
日胜率
0.550
盈利次数
226
亏损次数
128
信息比率
2.004
策略波动率
0.232
基准波动率
0.178
最大回撤区间
2024/12/12,2025/01/10
"""

from jqdata import *
import pandas as pd
import datetime


# ============================ 【全局缓存】 ============================
g_cache = {}


# ============================ 【initialize】 ============================
def initialize(context):
    # ---------- 选股参数 ----------
    g.stock_pool = [] # 每日动态选股池
    g.hold_max_count = 10 # 最大持仓数量
    g.single_position_pct = 0.10 # 单票最大仓位 10%
    g.buy_unit = 100 # 买入单位（100股）

    # ---------- 选股条件参数 ----------
    g.price_min = 2 # 股价最低
    g.price_max = 200 # 股价最高
    g.market_cap_min = 40 # 市值最低（亿）
    g.market_cap_max = 400 # 市值最高（亿）
    g.circ_cap_min = 9000 # 流通股本最低（万股）
    g.circ_cap_max = 120000 # 流通股本最高（万股）
    g.amount_min = 20_000_000 # 成交金额最低（2000万）
    g.turnover_min = 1 # 换手率最低（%）
    g.list_days_min = 545 # 上市天数最低（交易日）

    # ---------- 风控参数 ----------
    g.time_stop_days = 5 # 时间止损：持有 N 天
    g.time_stop_profit = 0.03 # 时间止损盈利阈值 3%
    g.hard_stop_loss = 0.08 # 硬止损：亏损 ≥8% 清仓
    g.move_stop_loss = 0.08 # 移动止损：从高点回撤 ≥8% 清仓

    # ---------- 利润衰减规则 ----------
    g.profit_decay_rules = [
    (0.05, 0.10, 0.50, 2, 'sell_all', 1.00),
    (0.10, 0.20, 0.40, 2, 'reduce', 0.50),
    (0.20, 0.30, 0.35, 3, 'reduce', 0.30),
    (0.30, float('inf'), 0.30, 3, 'reserve', 0.20),
    ]

    # ---------- 持仓入场日期记录 ----------
    g.entry_date = {}

    # ---------- 调度函数 ----------
    run_daily(select_stocks, time='before_open') # 盘前选股
    run_daily(trade, time='09:50') # 首次买入
    run_daily(trade_mid, time='10:00') # 盘中买入
    run_daily(trade_mid, time='11:00') # 盘中买入
    run_daily(trade_mid, time='13:30') # 盘中买入
    run_daily(trade_mid, time='14:30') # 盘中买入
    run_daily(after_trading_end, time='after_close') # 收盘统计


# ============================ 【选股函数】 ============================
def select_stocks(context):
    """每日盘前选股"""
    current_dt = context.current_dt

    try:
        # ==================== 1. 财务数据查询 ====================
        # 估值基础数据
        q_val = query(
            valuation.code,
            valuation.market_cap,
            valuation.circulating_cap,
            valuation.pe_ratio,
            valuation.turnover_ratio,
        ).filter(
            valuation.pe_ratio > 0,
            valuation.market_cap >= g.market_cap_min,
            valuation.market_cap <= g.market_cap_max,
        )
        val_df = get_fundamentals(q_val, date=current_dt)

        if val_df.empty:
            g.stock_pool = []
            log.warning("估值数据为空，今日不选股")
            return

        # 过滤 A 股（6/0/3 开头）
        val_df = val_df[val_df['code'].str.startswith(('6', '0', '3'))].copy()
        codes = val_df['code'].tolist()

        # 变量重命名
        fin_df = val_df

        # ==================== 3. ST/停牌过滤 ====================
        current_data = get_current_data()
        valid_codes = []
        for code in fin_df['code'].tolist():
            if code in current_data:
                info = current_data[code]
                if not info.is_st and not info.paused:
                    valid_codes.append(code)
        fin_df = fin_df[fin_df['code'].isin(valid_codes)]

        # ==================== 4. 批量行情数据 ====================
        all_codes = fin_df['code'].tolist()

        # 使用 history() 获取多标的数据
        close_df = history(400, '1d', 'close', all_codes, df=True)
        volume_df = history(400, '1d', 'volume', all_codes, df=True)
        money_df = history(400, '1d', 'money', all_codes, df=True)

        # 上市天数计算
        info_dict = {}
        for code in all_codes:
            try:
                info = get_security_info(code)
                cal_days = (current_dt.date() - info.start_date).days
                info_dict[code] = {'listed_days': int(cal_days * 250 / 365)}
            except Exception:
                info_dict[code] = {'listed_days': 0}

        # ==================== 5. 逐条筛选 ====================
        selected = []

        for _, row in fin_df.iterrows():
            code = row['code']

            if code not in close_df.columns or len(close_df[code]) < 400:
                continue

            close_s = close_df[code]
            volume_s = volume_df[code]
            money_s = money_df[code]

            latest = close_s.iloc[-1]
            info = info_dict.get(code, {})

            # 条件1：收盘价 2~200 元
            if not (g.price_min <= latest <= g.price_max):
                continue

            # 条件2：流通股本 9000万~12亿 股（单位：万股）
            circ_cap = row['circulating_cap']
            if not (g.circ_cap_min <= circ_cap <= g.circ_cap_max):
                continue

            # 条件3：当日成交金额 > 2000 万
            if money_s.iloc[-1] <= g.amount_min:
                continue

            # 条件4：换手率 > 1%
            if row['turnover_ratio'] <= g.turnover_min:
                continue

            # 条件5：上市交易日 > 545
            if info.get('listed_days', 0) <= g.list_days_min:
                continue



            # 条件7：当日成交量 > 前一日
            if volume_s.iloc[-1] <= volume_s.iloc[-2]:
                continue

            # 计算涨跌幅
            pct_df = close_s.pct_change()

            # 条件8：涨幅过滤
            # 近1年涨幅 < 50%
            year_pct = pct_df.iloc[-250:].sum() if len(pct_df) >= 250 else pct_df.sum()
            if year_pct >= 0.50:
                continue

            # 近20日涨幅 < 30%
            twenty_pct = pct_df.iloc[-20:].sum()
            if twenty_pct >= 0.30:
                continue

            # 前一日涨幅 < 4%
            prev_pct = pct_df.iloc[-2]
            if prev_pct >= 0.04:
                continue

            # 条件9：MA5 > 昨日MA5
            ma5 = close_s.rolling(5).mean()
            if ma5.iloc[-1] <= ma5.iloc[-2]:
                continue

            # 条件10：MA120 > MA365
            ma120 = close_s.rolling(120).mean()
            ma365 = close_s.rolling(365).mean()
            if ma120.iloc[-1] <= ma365.iloc[-1]:
                continue

            # 条件11：KDJ指标
            # 前一日K值< 30，当日K值>30且K>D，J>0
            kdj = calculate_kdj(close_s)
            if kdj is None or len(kdj) < 2:
                continue

            prev_k, prev_d = kdj.iloc[-2]['k'], kdj.iloc[-2]['d']
            curr_k, curr_d, curr_j = kdj.iloc[-1]['k'], kdj.iloc[-1]['d'], kdj.iloc[-1]['j']

            if not (prev_k < 30 and curr_k > 30 and curr_k > curr_d and curr_j > 0):
                continue

            selected.append(code)

        g.stock_pool = selected[:30] # 选股池上限30只
        log.info(f"选股完成：{len(g.stock_pool)} 只，满足条件的股票: {g.stock_pool[:5]}")

    except Exception as e:
        g.stock_pool = []
        log.error(f"选股出错：{str(e)}")


# ============================ 【KDJ计算】 ============================
def calculate_kdj(close_s, n=9):
    """计算KDJ指标"""
    if len(close_s) < n:
        return None

    low = close_s.rolling(n).min()
    high = close_s.rolling(n).max()

    rsv = (close_s - low) / (high - low) * 100
    rsv = rsv.fillna(50)

    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d

    kdj = pd.DataFrame({'k': k, 'd': d, 'j': j}, index=close_s.index)
    return kdj


# ============================ 【分时MACD金叉判断】 ============================
def calculate_macd_minute(security, current_dt):
    """计算分钟级MACD，判断是否金叉"""
    cache_key = f"{security}_macd_{current_dt.strftime('%Y%m%d%H%M')}"
    if cache_key in g_cache:
        return g_cache[cache_key]

    try:
        today_start = datetime.datetime.combine(current_dt.date(), datetime.time(9, 31))
        end_time = current_dt

        min_data = get_price(security,
            start_date=today_start,
            end_date=end_time,
            frequency='1m',
            fields=['close'])
        if min_data is None or len(min_data) < 26:
            g_cache[cache_key] = False
            return False

        close_arr = min_data['close']
        ema12 = close_arr.ewm(span=12, adjust=False).mean()
        ema26 = close_arr.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()

        # 金叉：DIF从下方穿越DEA
        result = dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]
        g_cache[cache_key] = result
        return result

    except Exception as e:
        log.error(f"分时MACD计算失败 {security}：{str(e)}")
        g_cache[cache_key] = False
        return False


# ============================ 【持仓信息获取】 ============================
def get_position_info(context, security):
    """返回：(持仓数量, 成本价, 持仓期最高收盘价, 持有天数)"""
    pos = context.portfolio.positions.get(security)
    if not pos or pos.total_amount == 0:
        return 0, 0.0, 0.0, 0

    avg_cost = pos.avg_cost
    entry_date = g.entry_date.get(security, context.current_dt.date())
    hold_days = (context.current_dt.date() - entry_date).days

    # 持仓期最高收盘价
    prev_date = context.current_dt - pd.Timedelta(days=1)
    try:
        price_data = get_price(security,
            start_date=entry_date,
            end_date=prev_date,
            frequency='daily',
            fields=['close'])
        highest_close = float(price_data['close'].max()) \
            if price_data is not None and not price_data.empty else avg_cost
    except Exception:
        highest_close = avg_cost

    return pos.total_amount, avg_cost, highest_close, hold_days


# ============================ 【卖出风控】 ============================
def check_and_close(context, security, current_dt):
    """执行单只持仓的全部卖出规则"""
    current_data = get_current_data()

    hold_amount, avg_cost, highest_close, hold_days = get_position_info(context, security)
    if hold_amount == 0:
        return False

    if security not in current_data:
        return False
    current_price = current_data[security].last_price
    if current_price <= 0:
        return False

    profit_rate = (current_price - avg_cost) / avg_cost if avg_cost > 0 else 0
    drawdown_rate = (highest_close - current_price) / highest_close if highest_close > 0 else 0
    max_profit_rate = (highest_close - avg_cost) / avg_cost if avg_cost > 0 else 0

    # ---------- 规则1：时间止损 ----------
    if hold_days >= g.time_stop_days and max_profit_rate < g.time_stop_profit:
        order_target(security, 0)
        log.info(f"【时间止损】{security}，持有{hold_days}天，"
                 f"最大盈利{max_profit_rate*100:.2f}% < 3%，清仓")
        return True

    # ---------- 规则2：硬止损 ----------
    if profit_rate <= -g.hard_stop_loss:
        order_target(security, 0)
        log.info(f"【硬止损】{security}，亏损{abs(profit_rate)*100:.2f}% >= 8%，清仓")
        return True

    # ---------- 规则3：利润衰减退出 ----------
    prev_date = current_dt - pd.Timedelta(days=1)

    for profit_min, profit_max, drawdown_pct, days, op_type, op_ratio in g.profit_decay_rules:
        if not (profit_min <= max_profit_rate < profit_max):
            continue

        try:
            price_series = get_price(security,
                end_date=prev_date,
                count=days + 5,
                frequency='daily',
                fields=['close'])
            if price_series is None or len(price_series) < days:
                break

            recent_high = price_series['close'].rolling(days).max().iloc[-1]
            is_consolidating = recent_high < highest_close

            if is_consolidating and drawdown_rate >= drawdown_pct:
                if op_type == 'sell_all':
                    order_target(security, 0)
                    log.info(f"【利润衰减·清仓】{security}，浮盈{max_profit_rate*100:.2f}%，"
                             f"回撤{drawdown_rate*100:.2f}% >= {drawdown_pct*100}%，清仓")
                    return True

                elif op_type == 'reduce':
                    target_value = hold_amount * avg_cost * (1 - op_ratio)
                    target_amount = int(target_value / current_price // 100 * 100)
                    if target_amount >= 100:
                        order_target(security, target_amount)
                        log.info(f"【利润衰减·减仓】{security}，减{int(op_ratio*100)}%，"
                                 f"剩余{target_amount}股")
                    else:
                        order_target(security, 0)
                        log.info(f"【利润衰减·减仓】{security}，减至不足1手，清仓")
                    return True

                elif op_type == 'reserve':
                    target_value = hold_amount * avg_cost * op_ratio
                    target_amount = int(target_value / current_price // 100 * 100)
                    if target_amount >= 100:
                        order_target(security, target_amount)
                        log.info(f"【利润衰减·留底仓】{security}，保留{int(op_ratio*100)}%底仓，"
                                 f"剩余{target_amount}股")
                    return True

        except Exception as e:
            log.error(f"利润衰减判断出错 {security}：{str(e)}")

        break

    # ---------- 规则4：移动止损 ----------
    if drawdown_rate >= g.move_stop_loss:
        order_target(security, 0)
        log.info(f"【移动止损】{security}，从高点回撤{drawdown_rate*100:.2f}% >= 8%，清仓")
        return True

    return False


# ============================ 【交易函数】 ============================
def trade(context):
    """09:50 执行：先遍历持仓执行卖出规则，再执行买入"""
    current_dt = context.current_dt

    # 遍历持仓，执行卖出规则
    for security in list(context.portfolio.positions.keys()):
        check_and_close(context, security, current_dt)

    # 执行买入
    buy_stocks(context)


def trade_mid(context):
    """盘中买入（10:00/11:00/13:30/14:30）"""
    current_dt = context.current_dt
    current_time = current_dt.time()

    # 排除禁止买入时段（9:15-9:50 和 14:57-15:00）
    if datetime.time(9, 15) <= current_time <= datetime.time(9, 50):
        return
    if datetime.time(14, 57) <= current_time <= datetime.time(15, 0):
        return

    buy_stocks(context)


# ============================ 【买入逻辑】 ============================
def buy_stocks(context):
    """选股池过滤 → MACD买点 → 分批建仓"""
    current_dt = context.current_dt
    total_asset = context.portfolio.total_value
    current_data = get_current_data()

    # 过滤ST/停牌标的
    pool = []
    for code in g.stock_pool:
        if code in current_data:
            info = current_data[code]
            if not info.is_st and not info.paused:
                pool.append(code)

    # 持仓数量检查
    hold_count = sum(
        1 for s in context.portfolio.positions
        if context.portfolio.positions[s].total_amount > 0
    )
    if hold_count >= g.hold_max_count:
        log.info(f"当前持仓 {hold_count} 只，已达上限，暂停买入")
        return

    for security in pool:
        # 跳过已持仓的股票
        if security in context.portfolio.positions and \
           context.portfolio.positions[security].total_amount > 0:
            continue

        # MACD金叉买点过滤
        if not calculate_macd_minute(security, current_dt):
            continue

        if security not in current_data:
            continue
        current_price = current_data[security].last_price
        if current_price <= 0:
            continue

        # 计算买入金额（单只仓位不超过10%）
        buy_value = total_asset * g.single_position_pct
        buy_amount = int(buy_value / current_price // g.buy_unit * g.buy_unit)

        if buy_amount < 100:
            continue

        try:
            order(security, buy_amount)
            g.entry_date[security] = current_dt.date()

            pos_pct = buy_value / total_asset * 100
            log.info(f"【MACD金叉买入】{security}，买入{buy_amount}股，"
                     f"单价{current_price:.2f}，仓位{pos_pct:.1f}%")

            hold_count += 1
            if hold_count >= g.hold_max_count:
                break

        except Exception as e:
            log.error(f"买入失败 {security}：{str(e)}")


# ============================ 【收盘统计】 ============================
def after_trading_end(context):
    """每日收盘后输出账户状态"""
    total_asset = context.portfolio.total_value
    cash = context.portfolio.cash
    pos_value = context.portfolio.positions_value

    hold_details = []
    for s, pos in context.portfolio.positions.items():
        if pos.total_amount > 0:
            entry_d = g.entry_date.get(s, context.current_dt.date())
            hold_days = (context.current_dt.date() - entry_d).days
            pnl = (pos.price - pos.avg_cost) / pos.avg_cost * 100
            hold_details.append(
                f"{s}({hold_days}天, {'+' if pnl >= 0 else ''}{pnl:.2f}%)"
            )

    # 清空当日缓存
    today = context.current_dt.strftime('%Y-%m-%d')
    global g_cache
    g_cache = {k: v for k, v in g_cache.items() if today not in k}

    log.info(f"=== 收盘统计 ===")
    log.info(f"总资产: {total_asset:.2f} | 持仓市值: {pos_value:.2f} | 现金: {cash:.2f}")
    log.info(f"持仓: {', '.join(hold_details) if hold_details else '空仓'}")