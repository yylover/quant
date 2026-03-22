#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI优化ETF轮动策略 V1.1 - 防御兜底版
======================================
基于AI多因子框架改造的ETF轮动策略

特点：
- 55只ETF池（商品/美股/国际/港股/A股/债券/货币）
- 5日动量主导+金叉加分买入进攻品种
- 无进攻信号时自动买入防御品种（债券/货币）
- ETF分类轮动（8大类）
- 多因子评分：动量+趋势+成交量
- 15%盈利后回撤10%止盈（让利润奔跑）
- 4次盘中止损检查
"""

from kuanke.wizard import *
from jqdata import *
import talib
import numpy as np
import pandas as pd
import datetime

# ============================================================================
# 初始化
# ============================================================================
def initialize(context):
    log.info("="*60)
    log.info("【策略启动】AI优化ETF轮动策略 V1.1 - 防御兜底版")
    log.info("="*60)
    
    # ==================== ETF池配置 ====================
    g.etf_pool = [
        # 1. 大宗商品 (8只)
        "518880.XSHG", "159985.XSHE", "501018.XSHG", "161226.XSHE", 
        "159980.XSHE", "159981.XSHE", "561360.XSHG", "518800.XSHG",
        # 2. 美股 (7只)
        "513100.XSHG", "159941.XSHE", "513500.XSHG", "159509.XSHE", 
        "513290.XSHG", "159529.XSHE", "513400.XSHG",
        # 3. 国际市场 (5只)
        "513520.XSHG", "513030.XSHG", "513080.XSHG", "513310.XSHG", "513730.XSHG",
        # 4. 港股 (5只)
        "159792.XSHE", "513130.XSHG", "513050.XSHG", "159920.XSHE", "513690.XSHG",
        # 5. A股大盘 (8只)
        "510300.XSHG", "510500.XSHG", "510050.XSHG", "159915.XSHE", 
        "588080.XSHG", "512100.XSHG", "563360.XSHG", "563300.XSHG",
        # 6. A股行业 (15只)
        "512890.XSHG", "159967.XSHE", "512040.XSHG", "159201.XSHE", 
        "515050.XSHG", "512480.XSHG", "515030.XSHG", "515790.XSHG", 
        "512010.XSHG", "512170.XSHG", "512800.XSHG", "512000.XSHG", 
        "512200.XSHG", "510880.XSHG", "516970.XSHG",
        # 7. 债券 (4只)
        "511380.XSHG", "511010.XSHG", "511220.XSHG", "511260.XSHG",
        # 8. 货币/防御 (3只)
        "511880.XSHG", "511990.XSHG", "511830.XSHG",
    ]
    
    # ETF分类
    g.etf_categories = {
        'commodity': ["518880.XSHG", "159985.XSHE", "501018.XSHG", "161226.XSHE", 
                      "159980.XSHE", "159981.XSHE", "561360.XSHG", "518800.XSHG"],
        'us_equity': ["513100.XSHG", "159941.XSHE", "513500.XSHG", "159509.XSHE", 
                      "513290.XSHG", "159529.XSHE", "513400.XSHG"],
        'intl_equity': ["513520.XSHG", "513030.XSHG", "513080.XSHG", "513310.XSHG", "513730.XSHG"],
        'hk_equity': ["159792.XSHE", "513130.XSHG", "513050.XSHG", "159920.XSHE", "513690.XSHG"],
        'cn_large': ["510300.XSHG", "510500.XSHG", "510050.XSHG", "159915.XSHE", 
                     "588080.XSHG", "512100.XSHG", "563360.XSHG", "563300.XSHG"],
        'cn_sector': ["512890.XSHG", "159967.XSHE", "512040.XSHG", "159201.XSHE", 
                      "515050.XSHG", "512480.XSHG", "515030.XSHG", "515790.XSHG", 
                      "512010.XSHG", "512170.XSHG", "512800.XSHG", "512000.XSHG", 
                      "512200.XSHG", "510880.XSHG", "516970.XSHG"],
        'bond': ["511380.XSHG", "511010.XSHG", "511220.XSHG", "511260.XSHG"],
        'cash': ["511880.XSHG", "511990.XSHG", "511830.XSHG"],
    }
    
    # ==================== 核心配置 ====================
    g.config = {
        'benchmark': '510500.XSHG',       # 中证500ETF作为基准
        
        # MACD参数（ETF波动较慢，适当放宽）
        'fastperiod': 12,
        'slowperiod': 26,
        'signalperiod': 9,
        
        # RSI参数
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        
        # 持仓管理
        'hold_max': 3,                    # ETF集中持仓3只
        'max_single_position': 0.35,      # 单ETF最大35%
        
        # 止损止盈（ETF波动较小，可适当放宽）
        'stop_loss': -0.06,               # -6%止损
        'trail_profit_trigger': 0.15,     # 15%启动跟踪止盈
        'trail_stop_drawdown': 0.10,      # 回撤10%止盈
        
        # 买入信号
        'macd_threshold': 0.005,          # ETF阈值适当降低
        'buy_signal_mode': 'golden_cross', # 严格金叉
        'ma20_filter': True,
        'volume_confirm': 1.0,            # ETF成交量确认放宽到1.0倍
        
        # 分类轮动
        'category_num': 3,                # Top3强势分类
        'category_lookback': 20,          # 20日动量
        
        # 风险控制
        'max_per_category': 1,            # 每类最多1只（分散）
        'enable_category_limit': True,    # 启用分类限制
        
        # 防御品种配置
        'defensive_min_return': -0.5,     # 防御品种最小收益要求（允许轻微下跌）
        'defensive_max_hold': 2,          # 防御品种最多持仓2只
        
        # 市场波动
        'vix_threshold': 18,
    }
    
    # 全局数据存储
    g.macd_data = {}
    g.prev_macd_data = {}
    g.category_strength = {}            # ETF分类强度
    g.top_categories = []               # Top3强势分类
    g.max_prices = {}
    g.volume_data = {}
    g.ma20_data = {}
    g.category_map = {}                 # ETF->分类映射
    g.no_offensive_count = 0            # 连续无进攻候选天数计数器
    
    # 构建ETF分类映射
    build_category_map()
    
    # 基础设置
    set_benchmark(g.config['benchmark'])
    set_option('use_real_price', True)
    set_order_cost(
        OrderCost(
            open_tax=0, close_tax=0.001,
            open_commission=0.0003, close_commission=0.0003,
            min_commission=5
        ), type='stock'
    )
    
    # 定时任务
    run_daily(market_open, time='09:30')
    run_daily(prepare, time='09:30')
    run_daily(check_stop_loss, time='10:30')
    run_daily(check_stop_loss, time='11:30')
    run_daily(check_stop_loss, time='14:00')
    run_daily(check_stop_loss, time='14:50')
    
    log.info(f"【配置】ETF池共{len(g.etf_pool)}只，分{len(g.etf_categories)}类")
    log.info(f"【配置】持仓:{g.config['hold_max']}只 | 防御兜底:连续3天无信号才触发")
    log.info(f"【配置】止损:{g.config['stop_loss']:.1%} | 止盈:15%回撤10% | 买入:5日动量+金叉加分")


def build_category_map():
    """构建ETF到分类的映射"""
    for category, etfs in g.etf_categories.items():
        for etf in etfs:
            g.category_map[etf] = category


def prepare(context):
    pass


# ============================================================================
# 主交易逻辑
# ============================================================================
def market_open(context):
    log.info("")
    log.info("="*60)
    log.info(f"【交易日】{context.current_dt.date()}")
    log.info(f"【账户】总资产:{context.portfolio.total_value:.2f}元 | 现金:{context.portfolio.cash:.2f}元")
    
    update_vix_and_position(context)
    update_category_strength(context)   # ETF分类强度计算
    calculate_indicators_etf(context)   # ETF指标计算
    
    log.info("")
    log.info("-"*40)
    log.info("【执行卖出检查】")
    execute_sell_etf(context)
    
    log.info("")
    log.info("-"*40)
    log.info("【执行买入检查】")
    execute_buy_etf(context)
    
    log.info("")
    log.info("="*60)
    log.info("【本时段交易结束】")
    log.info("="*60)


# ============================================================================
# VIX计算（使用50ETF）
# ============================================================================
def update_vix_and_position(context):
    try:
        etf_code = '510050.XSHG'
        index_data = get_price(etf_code, end_date=context.current_dt, count=20, fields=['close'])
        
        if index_data.empty:
            g.config['max_single_position'] = 0.35
            return
        
        returns = np.log(index_data['close'] / index_data['close'].shift(1)).dropna()
        volatility = returns.std() * np.sqrt(252)
        vix_proxy = volatility * 100
        
        if vix_proxy > g.config['vix_threshold']:
            new_position = 0.25
            log.info(f"【VIX】高波动({vix_proxy:.1f})，仓位降至25%")
        elif vix_proxy > g.config['vix_threshold'] * 0.7:
            new_position = 0.30
            log.info(f"【VIX】中波动({vix_proxy:.1f})，仓位30%")
        else:
            new_position = 0.35
            log.info(f"【VIX】低波动({vix_proxy:.1f})，仓位35%")
        
        g.config['max_single_position'] = new_position
        
    except Exception as e:
        g.config['max_single_position'] = 0.35


# ============================================================================
# ETF分类强度计算
# ============================================================================
def update_category_strength(context):
    """计算ETF分类强度（类似股票的行业强度）"""
    g.category_strength = {}
    g.top_categories = []
    
    log.info("")
    log.info("【ETF分类强度计算】")
    
    try:
        end_date = context.current_dt
        start_date = end_date - datetime.timedelta(days=g.config['category_lookback'])
        
        price_df = get_price(
            g.etf_pool, start_date=start_date, end_date=end_date,
            frequency='daily', fields=['close'], panel=False
        )
        
        if price_df.empty:
            return
        
        # 按分类计算强度
        category_returns = {}
        
        for etf in g.etf_pool:
            try:
                etf_data = price_df[price_df['code'] == etf]
                if etf_data.empty:
                    continue
                
                close_prices = etf_data['close'].values
                if len(close_prices) < 10:
                    continue
                
                returns = np.diff(close_prices) / close_prices[:-1]
                avg_return = np.mean(returns)
                total_return = (close_prices[-1] / close_prices[0]) - 1
                score = (avg_return * 0.4 + total_return * 0.6) * 100
                
                category = g.category_map.get(etf, 'other')
                
                if category not in category_returns:
                    category_returns[category] = {'total_score': 0, 'count': 0}
                
                category_returns[category]['total_score'] += score
                category_returns[category]['count'] += 1
                
            except:
                continue
        
        # 计算平均分
        for category, data in category_returns.items():
            if data['count'] > 0:
                g.category_strength[category] = data['total_score'] / data['count']
        
        # 排序取Top
        g.top_categories = sorted(
            g.category_strength.items(),
            key=lambda x: x[1], reverse=True
        )[:g.config['category_num']]
        
        if g.top_categories:
            log.info(f"【分类】Top3强势分类:")
            for i, (cat, score) in enumerate(g.top_categories, 1):
                cat_name = {'commodity': '商品', 'us_equity': '美股', 'intl_equity': '国际',
                           'hk_equity': '港股', 'cn_large': 'A股大盘', 'cn_sector': 'A股行业',
                           'bond': '债券', 'cash': '货币'}.get(cat, cat)
                log.info(f"  #{i} {cat_name} 分数:{score:.2f}")
        
    except Exception as e:
        log.error(f"【分类】出错: {str(e)}")


# ============================================================================
# ETF指标计算
# ============================================================================
def calculate_indicators_etf(context):
    """计算ETF技术指标"""
    g.prev_macd_data = g.macd_data.copy() if g.macd_data else {}
    g.macd_data = {}
    g.ma20_data = {}
    g.volume_data = {}
    
    log.info("")
    log.info("【ETF指标计算】")
    
    try:
        end_date = context.current_dt
        start_date = end_date - datetime.timedelta(days=90)
        
        price_df = get_price(
            g.etf_pool, start_date=start_date, end_date=end_date,
            frequency='daily', fields=['close', 'volume'], panel=False
        )
        
        if price_df.empty:
            return
        
        success_count = 0
        for etf in g.etf_pool:
            try:
                etf_data = price_df[price_df['code'] == etf]
                if etf_data.empty:
                    continue
                
                close_prices = etf_data['close'].values
                volumes = etf_data['volume'].values
                
                if len(close_prices) < g.config['slowperiod'] + g.config['signalperiod']:
                    continue
                
                macd, signal, hist = talib.MACD(
                    close_prices,
                    fastperiod=g.config['fastperiod'],
                    slowperiod=g.config['slowperiod'],
                    signalperiod=g.config['signalperiod']
                )
                
                rsi = talib.RSI(close_prices, timeperiod=g.config['rsi_period'])
                ma20 = talib.SMA(close_prices, timeperiod=20)
                
                avg_volume_5 = np.mean(volumes[-5:]) if len(volumes) >= 5 else 0
                current_volume = volumes[-1] if len(volumes) > 0 else 0
                
                g.macd_data[etf] = {
                    'dif': macd[-1], 'dea': signal[-1], 'macd': hist[-1],
                    'prev_macd': hist[-2] if len(hist) > 1 else 0,
                    'prev_dif': macd[-2] if len(macd) > 1 else 0,
                    'prev_dea': signal[-2] if len(signal) > 1 else 0,
                    'rsi': rsi[-1] if len(rsi) > 0 and not np.isnan(rsi[-1]) else 50
                }
                
                g.ma20_data[etf] = {
                    'ma20': ma20[-1] if not np.isnan(ma20[-1]) else close_prices[-1],
                    'ma20_trend': ma20[-1] > ma20[-5] if len(ma20) >= 5 else True,
                    'close': close_prices[-1]
                }
                
                g.volume_data[etf] = {
                    'current': current_volume,
                    'avg_5': avg_volume_5,
                    'ratio': current_volume / avg_volume_5 if avg_volume_5 > 0 else 0
                }
                
                success_count += 1
                
            except:
                continue
        
        log.info(f"【指标】成功{success_count}/{len(g.etf_pool)}只")
        
    except Exception as e:
        log.error(f"【指标】出错: {str(e)}")


# ============================================================================
# ETF卖出逻辑
# ============================================================================
def execute_sell_etf(context):
    """执行ETF卖出"""
    hold_etfs = list(context.portfolio.positions.keys())
    
    if not hold_etfs:
        log.info("【卖出】无持仓")
        return
    
    log.info(f"【卖出】当前持仓{len(hold_etfs)}只")
    
    sell_count = 0
    for etf in hold_etfs:
        try:
            should_sell_flag, reason = should_sell_etf(context, etf)
            
            if should_sell_flag:
                position = context.portfolio.positions[etf]
                profit_pct = position.price / position.avg_cost - 1
                
                order_target_value(etf, 0)
                log.info(f"  [卖出] {etf} | {reason} | {profit_pct:+.2%}")
                
                if etf in g.max_prices:
                    del g.max_prices[etf]
                
                sell_count += 1
            
        except Exception as e:
            log.error(f"  [卖出]{etf}出错: {e}")
    
    log.info(f"【卖出】卖出{sell_count}只")


def should_sell_etf(context, etf):
    """判断ETF是否应该卖出"""
    macd_info = g.macd_data.get(etf, {})
    if not macd_info:
        return False, "无数据"
    
    position = context.portfolio.positions[etf]
    if position.total_amount <= 0:
        return False, "无持仓"
    
    current_price = position.price
    cost_price = position.avg_cost
    profit_pct = current_price / cost_price - 1
    
    # 固定止损 -6%
    if profit_pct <= g.config['stop_loss']:
        return True, f"止损({profit_pct:+.2%})"
    
    # 更新最高价
    if etf not in g.max_prices or current_price > g.max_prices[etf]:
        g.max_prices[etf] = current_price
    
    max_price = g.max_prices[etf]
    max_profit = max_price / cost_price - 1
    
    # 跟踪止盈：盈利>10%后回撤15%
    if max_profit > g.config['trail_profit_trigger']:
        drawdown = (max_price - current_price) / max_price
        if drawdown > g.config['trail_stop_drawdown']:
            return True, f"止盈(最大{max_profit:+.2%}/回撤{drawdown:.1%})"
    
    # MACD死叉（进攻品种才看死叉，防御品种宽松处理）
    category = g.category_map.get(etf, 'other')
    if category not in ['bond', 'cash']:  # 进攻品种
        current_macd = macd_info['macd']
        prev_macd = macd_info.get('prev_macd', 0)
        
        macd_sell = (
            (current_macd < 0 and prev_macd >= 0) or
            (macd_info['dif'] < macd_info['dea'] and
             macd_info['prev_dif'] >= macd_info['prev_dea'])
        )
        
        if macd_sell:
            return True, "MACD死叉"
    
    return False, "持有"


# ============================================================================
# ETF买入逻辑 - 含防御兜底
# ============================================================================
def execute_buy_etf(context):
    """执行ETF买入（含防御品种兜底）"""
    hold_etfs = context.portfolio.positions
    
    log.info(f"【买入】当前持仓{len(hold_etfs)}/{g.config['hold_max']}只")
    
    # 1. 尝试买入进攻品种（金叉ETF）
    offensive_list = get_offensive_buy_list(context)
    
    if offensive_list and len(offensive_list) > 0:
        # 有候选，买入进攻品种
        g.no_offensive_count = 0  # 重置计数器
        bought_count = buy_offensive_etfs(context, offensive_list)
        return bought_count
    
    # 2. 无进攻信号，增加计数器
    g.no_offensive_count += 1
    log.info(f"【买入】无进攻品种符合条件，连续{g.no_offensive_count}天")
    
    # 连续3天无进攻候选才转入防御模式
    if g.no_offensive_count < 3:
        log.info(f"【防御】连续无进攻候选天数不足3天({g.no_offensive_count}/3)，暂不买入防御品种")
        return 0
    
    # 检查当前持仓是否已有进攻品种
    offensive_holdings = [etf for etf in hold_etfs 
                          if g.category_map.get(etf) not in ['bond', 'cash']]
    
    if len(offensive_holdings) > 0:
        log.info(f"【防御】已持有{len(offensive_holdings)}只进攻品种，无需防御兜底")
        return 0
    
    # 检查是否已持有防御品种
    defensive_holdings = [etf for etf in hold_etfs 
                          if g.category_map.get(etf) in ['bond', 'cash']]
    
    if len(defensive_holdings) >= g.config['defensive_max_hold']:
        log.info(f"【防御】已持有{len(defensive_holdings)}只防御品种，无需追加")
        return 0
    
    # 买入防御品种
    bought_count = buy_defensive_etfs(context)
    return bought_count


def buy_offensive_etfs(context, buy_list):
    """买入进攻品种（金叉ETF）"""
    hold_etfs = context.portfolio.positions
    available_cash = context.portfolio.cash
    
    slots_available = g.config['hold_max'] - len(hold_etfs)
    num_to_buy = min(slots_available, len(buy_list))
    
    if num_to_buy <= 0:
        return 0
    
    base_cash = available_cash / num_to_buy
    
    log.info(f"【进攻买入】金叉候选{len(buy_list)}只 | 计划买{num_to_buy}只")
    
    buy_count = 0
    for etf, score, ret_5d, is_golden_cross in buy_list[:num_to_buy]:
        if etf in hold_etfs:
            continue
        
        try:
            category = g.category_map.get(etf, 'other')
            category_factor = get_category_factor(etf)
            
            allocate_cash = base_cash * category_factor
            max_allocate = context.portfolio.total_value * g.config['max_single_position']
            final_cash = min(allocate_cash, max_allocate, available_cash * 0.95)
            
            if final_cash < 1000:
                continue
            
            if order_target_value(etf, final_cash):
                cat_name = {'commodity': '商品', 'us_equity': '美股', 'intl_equity': '国际',
                           'hk_equity': '港股', 'cn_large': 'A股大盘', 'cn_sector': 'A股行业'}.get(category, category)
                
                cross_mark = "✓金叉" if is_golden_cross else "○动量"
                log.info(f"  [买入进攻] {etf} | {cat_name} | {cross_mark} | 评分:{score:.1f} | 5日收益:{ret_5d:.2f}% | {final_cash:.0f}元")
                available_cash -= final_cash
                buy_count += 1
            
        except Exception as e:
            log.error(f"  [买入进攻]{etf}出错: {e}")
    
    log.info(f"【进攻买入】成功{buy_count}只")
    return buy_count


def buy_defensive_etfs(context):
    """买入防御品种（债券/货币ETF）"""
    hold_etfs = context.portfolio.positions
    available_cash = context.portfolio.cash
    
    # 防御品种列表
    defensive_etfs = g.etf_categories.get('bond', []) + g.etf_categories.get('cash', [])
    
    if not defensive_etfs:
        log.warning("【防御买入】无防御品种配置")
        return 0
    
    # 获取防御品种排名
    defensive_candidates = rank_defensive_etfs(context, defensive_etfs)
    
    if not defensive_candidates:
        log.warning("【防御买入】无可用防御品种（可能都在下跌）")
        return 0
    
    # 计算可买入数量
    current_defensive = len([e for e in hold_etfs if g.category_map.get(e) in ['bond', 'cash']])
    slots_for_defensive = g.config['defensive_max_hold'] - current_defensive
    
    num_to_buy = min(slots_for_defensive, len(defensive_candidates), 2)
    
    if num_to_buy <= 0:
        return 0
    
    base_cash = available_cash / num_to_buy
    
    log.info(f"【防御买入】候选{len(defensive_candidates)}只 | 计划买{num_to_buy}只")
    
    buy_count = 0
    for etf, ret_20d in defensive_candidates[:num_to_buy]:
        if etf in hold_etfs:
            continue
        
        try:
            max_allocate = context.portfolio.total_value * g.config['max_single_position']
            final_cash = min(base_cash, max_allocate, available_cash * 0.95)
            
            if final_cash < 1000:
                continue
            
            if order_target_value(etf, final_cash):
                category = g.category_map.get(etf, 'other')
                cat_name = {'bond': '债券', 'cash': '货币'}.get(category, category)
                
                log.info(f"  [买入防御] {etf} | {cat_name} | 20日收益:{ret_20d:.2f}% | {final_cash:.0f}元")
                available_cash -= final_cash
                buy_count += 1
            
        except Exception as e:
            log.error(f"  [买入防御]{etf}出错: {e}")
    
    log.info(f"【防御买入】成功{buy_count}只（避险配置）")
    return buy_count


def rank_defensive_etfs(context, defensive_etfs):
    """防御品种排名（按20日收益率，选最强的）"""
    candidates = []
    
    try:
        end_date = context.current_dt
        start_date = end_date - datetime.timedelta(days=25)
        
        price_df = get_price(
            defensive_etfs, start_date=start_date, end_date=end_date,
            frequency='daily', fields=['close'], panel=False
        )
        
        if price_df.empty:
            return []
        
        for etf in defensive_etfs:
            try:
                etf_data = price_df[price_df['code'] == etf]
                if etf_data.empty:
                    continue
                
                close_prices = etf_data['close'].values
                if len(close_prices) < 15:
                    continue
                
                # 计算20日收益率
                total_return = (close_prices[-1] / close_prices[0] - 1) * 100
                
                # 检查是否在允许范围内（允许轻微下跌）
                if total_return >= g.config['defensive_min_return'] * 100:
                    candidates.append((etf, total_return))
                
            except:
                continue
        
        # 按收益率排序（选最强的债券/货币）
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            log.info(f"【防御排名】Top候选:")
            for i, (etf, ret) in enumerate(candidates[:3], 1):
                log.info(f"  #{i} {etf} 20日收益:{ret:.2f}%")
        
        return candidates
        
    except Exception as e:
        log.error(f"【防御排名】出错: {str(e)}")
        return []


# ============================================================================
# 进攻品种买入候选筛选 - 动量主导+金叉加分
# ============================================================================
def get_offensive_buy_list(context):
    """
    ETF买入候选（5日动量主导+金叉加分）
    
    核心逻辑：
    1. 动量优先：5日收益率排名Top15的ETF进入候选
    2. 金叉加分：有金叉额外加20分
    3. 趋势过滤：RSI<70，收盘价>MA20
    4. 非防御品种
    5. 分类集中度控制
    
    评分体系（满分100）：
    - 动量排名分 (60%)：5日收益率越高越好
    - 金叉加分 (20%)：有MACD金叉额外加分
    - MACD柱分 (10%)：柱状图强度
    - 分类因子分 (10%)：Top3强势分类加分
    """
    buy_candidates = []
    
    # 获取当前持仓的分类计数
    hold_etfs = list(context.portfolio.positions.keys())
    category_count = {}
    for etf in hold_etfs:
        cat = g.category_map.get(etf, 'other')
        category_count[cat] = category_count.get(cat, 0) + 1
    
    # 第一步：计算所有进攻品种的20日收益率并排序
    momentum_list = []
    
    for etf in g.etf_pool:
        try:
            category = g.category_map.get(etf, 'other')
            # 跳过防御品种
            if category in ['bond', 'cash']:
                continue
            
            # 分类集中度检查
            if g.config['enable_category_limit']:
                if category_count.get(category, 0) >= g.config['max_per_category']:
                    continue
            
            # 获取基础数据
            macd_info = g.macd_data.get(etf, {})
            ma20_info = g.ma20_data.get(etf, {})
            
            if not macd_info or not ma20_info:
                continue
            
            # 基础过滤：RSI<70，收盘价>MA20
            if macd_info.get('rsi', 50) > g.config['rsi_overbought']:
                continue
            
            close = ma20_info['close']
            ma20 = ma20_info['ma20']
            if close <= ma20 or not ma20_info['ma20_trend']:
                continue
            
            # 计算5日收益率
            ret_5d = 0
            try:
                price_data = get_price(etf, end_date=context.current_dt, 
                                      count=5, fields=['close'])
                if not price_data.empty:
                    ret_5d = (price_data['close'][-1] / price_data['close'][0] - 1) * 100
            except:
                continue
            
            momentum_list.append((etf, ret_5d, macd_info, ma20_info, category))
            
        except:
            continue
    
    # 按动量排序，取Top15进入评分
    momentum_list.sort(key=lambda x: x[1], reverse=True)
    top_momentum = momentum_list[:15]
    
    # 第二步：对Top15进行详细评分
    for etf, ret_5d, macd_info, ma20_info, category in top_momentum:
        try:
            score = 0
            is_golden_cross = False
            
            # 1. 动量排名分 (60%) - 5日收益率，最高60分
            # 收益率>4%得满分60分，0-4%线性递减
            momentum_score = min(max(ret_5d, 0) / 4 * 60, 60)
            score += momentum_score
            
            # 2. 金叉加分 (20%) - 有金叉额外加20分
            curr_dif = macd_info['dif']
            curr_dea = macd_info['dea']
            prev_dif = macd_info.get('prev_dif', 0)
            prev_dea = macd_info.get('prev_dea', 0)
            
            is_golden_cross = (curr_dif > curr_dea) and (prev_dif <= prev_dea)
            if is_golden_cross and macd_info['macd'] > 0:
                score += 20
            elif curr_dif > curr_dea:  # DIF在DEA上方但未金叉
                score += 10
            
            # 3. MACD柱分 (10%) - 柱状图强度
            macd_score = min(max(macd_info['macd'], 0) / 0.03, 1.0) * 10
            score += macd_score
            
            # 4. 分类因子分 (10%) - Top3分类加分
            category_factor = get_category_factor(etf)
            score += (category_factor - 1.0) / 0.3 * 10
            
            # 买入条件：评分>50且(有金叉或5日动量>3%)
            if score > 50 and (is_golden_cross or ret_5d > 3):
                buy_candidates.append((etf, score, ret_5d, is_golden_cross))
            
        except:
            continue
    
    buy_candidates.sort(key=lambda x: x[1], reverse=True)
    
    if buy_candidates:
        log.info(f"【买入候选】共{len(buy_candidates)}只ETF符合条件，Top5:")
        for i, (etf, score, ret_5d, is_golden_cross) in enumerate(buy_candidates[:5], 1):
            category = g.category_map.get(etf, 'other')
            cross_mark = "✓金叉" if is_golden_cross else "○动量"
            log.info(f"  #{i} {etf} ({category}) 评分:{score:.1f} | 5日收益:{ret_5d:.2f}% | {cross_mark}")
    else:
        log.info("【买入候选】无进攻品种符合条件（动量不足）")
    
    return buy_candidates


def get_category_factor(etf):
    """获取ETF分类因子"""
    try:
        category = g.category_map.get(etf, 'other')
        
        for cat, _ in g.top_categories:
            if cat == category:
                return 1.3
        
        return 1.0
        
    except:
        return 1.0


# ============================================================================
# 盘中止损检查
# ============================================================================
def check_stop_loss(context):
    log.info("")
    log.info("【盘中检查】")
    
    stop_count = 0
    
    for etf in list(context.portfolio.positions.keys()):
        try:
            position = context.portfolio.positions[etf]
            if position.total_amount <= 0:
                continue
            
            current_price = position.price
            cost_price = position.avg_cost
            profit_pct = current_price / cost_price - 1
            
            if etf not in g.max_prices or current_price > g.max_prices[etf]:
                g.max_prices[etf] = current_price
            
            if profit_pct <= g.config['stop_loss']:
                order_target_value(etf, 0)
                log.info(f"  [止损] {etf} {profit_pct:+.2%}")
                if etf in g.max_prices:
                    del g.max_prices[etf]
                stop_count += 1
                continue
            
            max_price = g.max_prices[etf]
            max_profit = max_price / cost_price - 1
            
            if max_profit > g.config['trail_profit_trigger']:
                drawdown = (max_price - current_price) / max_price
                if drawdown > g.config['trail_stop_drawdown']:
                    order_target_value(etf, 0)
                    log.info(f"  [止盈] {etf} 最大{max_profit:+.2%}/当前{profit_pct:+.2%}")
                    del g.max_prices[etf]
                    stop_count += 1
            
        except Exception as e:
            log.error(f"  [检查]{etf}出错: {e}")
    
    if stop_count == 0:
        log.info("  [检查] 无触发")
    else:
        log.info(f"  [检查] 触发{stop_count}只")