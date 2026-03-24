"""markdown

第这是一个涨停板接力策略，寻找"小实体涨停 + 连板缩量 + 次日低开承接"的短线机会，T+1持仓（买入次日开盘卖出）。

  实盘与回测的主要差异

  1. 涨停板成交问题（最致命）
  - 回测假设：close >= pre_close * 1.098 就能买到
  - 实盘现实：涨停板封单可能几十万手，散户根本排不到队
  - 即使是"小实体涨停"（开盘价接近收盘价），如果尾盘封板，你的委托大概率无法成交
  - 影响：回测显示买入10只，实盘可能只成交1-2只，甚至0只

  2. 分时数据的滞后性
  ticks = get_ticks(security=stock, end_dt=now, count=10, ...)
  - 09:31执行时，"前10笔"可能是集合竞价或开盘瞬间的数据
  - 实盘API延迟、数据推送延迟，可能拿到的是09:30:50的数据
  - 等你下单时（09:31:05），价格可能已经拉升5%+
  - 影响：条件3的"开盘拉升"判断失真，追高风险

  3. 滑点与冲击成本
  order_value(stock, cash_per_stock)  # 满仓95%平分
  - 小盘股流动性差，大单会推高价格
  - 涨停附近的股票，买盘踊跃，滑点可能2-3%
  - 回测通常假设滑点0.2-0.5%
  - 影响：10只股票平均滑点2%，收益直接-2%

  4. 次日开盘卖出的风险
  run_daily(sell_all_next_day, time='09:30', ...)
  - 如果次日低开3-5%（情绪退潮），你09:30卖出就是亏损
  - 涨停板接力最怕"一日游"，次日核按钮
  - 回测可能遇到的是牛市/强势行情，次日普遍高开
  - 影响：熊市或震荡市，胜率会大幅下降

  5. 代码bug（已在注释中指出）
  day_before = get_trade_days(end_date=today, count=3)[2]  # 这是今天，不是前天
  - 应该是 [0] 才是前天
  - 导致"前天涨停"判断可能用错日期
  - 影响：条件1逻辑失效，回测结果不可信

  实盘预期

  ┌──────────┬──────────┬────────────────┐
  │   维度   │   回测   │    实盘预期    │
  ├──────────┼──────────┼────────────────┤
  │ 年化收益 │ 可能50%+ │ 10-20%（乐观） │
  ├──────────┼──────────┼────────────────┤
  │ 成交率   │ 100%     │ 20-40%         │
  ├──────────┼──────────┼────────────────┤
  │ 滑点     │ 0.2%     │ 1.5-3%         │
  ├──────────┼──────────┼────────────────┤
  │ 胜率     │ 60%+     │ 40-50%         │
  ├──────────┼──────────┼────────────────┤
  │ 最大回撤 │ 15%      │ 25-35%         │
  └──────────┴──────────┴────────────────┘

  建议

  如果要实盘：
  1. 先修bug：day_before 索引改为 [0]
  2. 降低仓位：不要满仓95%，控制在30-50%
  3. 加入流动性过滤：只选成交额>5亿的股票
  4. 优化卖出：不要死板09:30卖，可以看次日开盘涨幅决定（高开2%+可以持有到尾盘）
  5. 小资金测试：10-20万以内测试，大资金会严重影响成交

  这类策略在2019-2021年牛市可能表现不错，但2022年后市场风格变化，涨停板接力难度大增。实盘前建议用最近1-2年数据回测，看看是否还有效

""""


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