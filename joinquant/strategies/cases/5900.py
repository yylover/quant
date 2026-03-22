
# -*- coding: utf-8 -*-
from jqdata import *
import pandas as pd
import re

# ==================== initialize ====================
def initialize(context):
    set_option('use_real_price', True)
    log.set_level('order', 'error')

    # 盘前粗选
    run_daily(test_logic, time='before_open', reference_security='000300.XSHG')
    
    # 开盘后1分钟精选买入
    run_daily(do_buy, time='09:31', reference_security='000300.XSHG')
    
    # 第二个交易日开盘09:30全仓卖出（完美T+1）
    run_daily(sell_all_next_day, time='09:30', reference_security='000300.XSHG')


# ==================== 原始粗选（一字未改） ====================
def test_logic(context):
    today = context.current_dt.date()
    trade_days = get_trade_days(end_date=today, count=2)
    target_date = trade_days[0]

    log.info(f"开始筛选 {target_date} 满足条件的股票...")

    stocks = list(get_all_securities(['stock'], target_date).index)
    selected = []

    for stock in stocks:
        info = get_security_info(stock)
        name = info.display_name

        if stock.startswith(('300', '301', '302', '688')):
            continue
        if not re.search(u'[\u4e00-\u9fa5]', name):
            continue
        if 'ST' in name or '*ST' in name or '退' in name:
            continue
        if (target_date - info.start_date).days < 60:
            continue

        df = get_price(stock, start_date=target_date, end_date=target_date,
                      fields=['open', 'close', 'pre_close'], skip_paused=False, fq='pre')
        if df is None or df.empty:
            continue

        row = df.iloc[0]
        o, c, pre_c = row['open'], row['close'], row['pre_close']

        if pd.isna(o) or pd.isna(c) or pd.isna(pre_c) or pre_c == 0:
            continue

        if c < pre_c * 1.098:        # 涨停
            continue
        if abs(c - o) / pre_c > 0.02: # 实体 ≤ 2%
            continue

        selected.append(stock)
        log.info(f"{stock} | {name} | open={o:.3f}, close={c:.3f}, pre_close={pre_c:.3f}, 实体涨幅={(abs(c-o)/pre_c*100):.2f}%")

    g.limit_up_pool = selected  
    log.info(f"最终选出 {len(selected)} 只股票: {selected}")


# ==================== 精选买入（终极版：必须前一天也涨停 + 第二天缩量） ====================
def do_buy(context):
    if not hasattr(g, 'limit_up_pool') or len(g.limit_up_pool) == 0:
        log.info("今日无粗选股票，跳过买入")
        return
        
    to_buy = []
    now = context.current_dt
    today = now.date()
    
    pass_vol_smaller = []   # 前天涨停 + 昨天缩量
    pass_open_0_5    = []   # 开盘涨幅 0~5%
    pass_tick_higher = []   # 前10笔拉升
    
    log.info(f"开始精选昨日 {len(g.limit_up_pool)} 只小实体涨停股")
    
    # 昨天 = 粗选涨停日
    yesterday_limit_up_day = get_trade_days(end_date=today, count=2)[0]
    # 前天
    day_before = get_trade_days(end_date=today, count=3)[2]
    
    for stock in g.limit_up_pool:
        name = get_security_info(stock).display_name
        
        # 条件1：前天必须涨停 + 昨天量 < 前天量
        vol_ok = False
        
        # 昨天（涨停日）数据
        df_yest = get_price(stock, start_date=yesterday_limit_up_day, end_date=yesterday_limit_up_day,
                           fields=['close', 'pre_close', 'volume'], frequency='daily')
        if df_yest.empty: continue
        close_yest = df_yest['close'].iloc[0]
        pre_close_yest = df_yest['pre_close'].iloc[0]
        vol_yest = df_yest['volume'].iloc[0]
        
        # 前天数据
        df_before = get_price(stock, start_date=day_before, end_date=day_before,
                             fields=['close', 'pre_close', 'volume'], frequency='daily')
        if df_before.empty: continue
        close_before = df_before['close'].iloc[0]
        pre_close_before = df_before['pre_close'].iloc[0]
        vol_before = df_before['volume'].iloc[0]
        
        # 前天是否涨停
        was_limit_up_before = close_before >= pre_close_before * 1.098 - 0.01
        # 昨天是否缩量
        vol_smaller = vol_yest < vol_before
        
        if was_limit_up_before and vol_smaller:
            vol_ok = True
            pass_vol_smaller.append(stock)
            log.info(f"条件1通过 → {stock} {name} | 前天涨停 + 昨天缩量 "
                     f"（前天量 {vol_before:,.0f} → 昨天量 {vol_yest:,.0f}）")
        
        # 条件2：今日开盘涨幅 0~5%
        price_df = get_price(stock, count=2, end_date=today, fields=['close','open'], fq='pre')
        if len(price_df) < 2: continue
        last_close = price_df['close'].iloc[-2]
        open_today = price_df['open'].iloc[-1]
        open_ret = (open_today - last_close) / last_close
        open_ok = 0 <= open_ret <= 0.05
        if open_ok:
            pass_open_0_5.append(stock)
            log.info(f"条件2通过 → {stock} {name} 开盘涨幅 {open_ret*100:+.2f}%")
        
        # 条件3：前10笔均价 > 开盘价
        tick_ok = False
        try:
            ticks = get_ticks(security=stock, end_dt=now, count=10, fields=['current','volume'])
            if ticks is not None and len(ticks) >= 10:
                avg_10 = (ticks['current'] * ticks['volume']).sum() / ticks['volume'].sum()
                if avg_10 > open_today:
                    tick_ok = True
                    pass_tick_higher.append(stock)
                    log.info(f"条件3通过 → {stock} {name} 前10笔均价 {avg_10:.3f} > 开盘价 {open_today:.3f}")
        except:
            pass
        
        # 三条件全满足 → 买入
        if vol_ok and open_ok and tick_ok:
            to_buy.append(stock)
            log.info(f"三条件全满足 → 买入 {stock} {name} | 连板缩量+低开护盘+开盘拉升")
    
    # 总结
    log.info("=" * 70)
    log.info(f"【{today}】精选结果（粗选 {len(g.limit_up_pool)} 只）")
    log.info(f"条件1 通过（前天涨停+昨天缩量）: {len(pass_vol_smaller)} 只 → {pass_vol_smaller}")
    log.info(f"条件2 通过（开盘涨幅0~5%）     : {len(pass_open_0_5)} 只 → {pass_open_0_5}")
    log.info(f"条件3 通过（前10笔拉升）       : {len(pass_tick_higher)} 只 → {pass_tick_higher}")
    log.info(f"三条件全满足（最终买入）       : {len(to_buy)} 只 → {to_buy}")
    log.info("=" * 70)
    
    # 满仓一把，留5%防滑点
    if to_buy:
        cash_to_use = context.portfolio.available_cash * 0.95
        cash_per_stock = cash_to_use / len(to_buy)
        for stock in to_buy:
            order_value(stock, cash_per_stock)
            log.info(f"已下单买入 {stock} {get_security_info(stock).display_name} "
                     f"金额 {cash_per_stock:,.0f}元（满仓模式，留5%防滑点）")
    else:
        log.info("今日无股票满足全部三个精选条件")


# ==================== 次日09:30全仓卖出 ====================
def sell_all_next_day(context):
    positions = list(context.portfolio.positions.keys())
    if not positions:
        return
        
    log.info(f"【{context.current_dt.date()}】第二个交易日开盘卖出昨日买入股票，共 {len(positions)} 只")
    for stock in positions:
        if context.portfolio.positions[stock].total_amount > 0:
            order_target(stock, 0)
            log.info(f"已卖出 {stock} {get_security_info(stock).display_name}")