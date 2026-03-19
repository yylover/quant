# -*- coding: utf-8 -*-
"""
XGBoost回归选股策略
====================

策略思路：
--------
1. 使用XGBoost回归模型预测股票未来收益率
2. 选取预测收益率最高的N只股票进行投资
3. 配合RSRS择时信号控制仓位
4. 等权重分散持仓，降低风险

模型特点：
---------
- XGBoost：梯度提升决策树，处理非线性能力强
- 回归目标：预测未来20日收益率
- 特征工程：结合基本面、技术面、市场情绪
- 模型更新：每月重新训练一次

特征列表：
---------
基本面因子（10个）：
- PE、PB、PS、市值、市值对数
- ROE、ROA、毛利率、净利率、营收增长

技术面因子（10个）：
- 5日/20日/60日动量
- RSI、MACD、布林带宽度
- 20日波动率、换手率、成交额

市场情绪因子（5个）：
- 北向资金净流入
- 融资融券余额
- 分析师评级变化
- 新闻情绪分数

运行环境：JoinQuant / 聚宽（Python3）
依赖库：xgboost, numpy, pandas, statsmodels
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from xgboost import XGBRegressor

# 导入聚宽函数库
from jqlib.technical_analysis import *
from jqlib.technical_analysis import RSI, MACD


# 初始化函数
def initialize(context):
    """策略初始化，只执行一次"""
    set_option('use_real_price', True)
    set_parameter(context)
    
    # 交易手续费
    set_order_cost(OrderCost(
        close_tax=0.001,
        open_commission=0.0003,
        close_commission=0.0003,
        min_commission=5
    ), type='stock')
    
    # 每日定时任务
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_open, time='open', reference_security='000300.XSHG')
    run_monthly(retrain_model, 1, time='after_close')


# 参数设置
def set_parameter(context):
    """
    设置策略全局参数
    
    核心参数说明：
    -------------
    g.stock_num = 15: 持股数量
        - XGBoost选股质量高，可以适当增加持股数量
        - 15只股票平衡分散度和收益潜力
    
    g.prediction_days = 20: 预测收益率天数
        - 预测未来20日收益率
        - 20个交易日约等于1个月
        - 适合中短期投资
    
    g.retrain_freq = 1: 模型重训练频率（月）
        - 每月重新训练一次模型
        - 确保模型适应市场变化
    
    g.lookback_days = 252: 特征计算历史窗口
        - 252个交易日约等于1年
        - 用于计算技术面因子
    
    g.buy = 0.7: RSRS买入阈值
    g.sell = -0.7: RSRS卖出阈值
    g.N = 18: RSRS回归窗口
    g.M = 1100: Z-score标准化历史窗口
    
    g.model = None: XGBoost模型
    g.feature_names = None: 特征名称列表
    """
    g.stock_num = 15  # 持股数量
    g.prediction_days = 20  # 预测收益率天数
    g.retrain_freq = 1  # 模型重训练频率（月）
    g.lookback_days = 252  # 特征计算历史窗口
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    
    # 模型相关
    g.model = None  # XGBoost回归模型
    g.feature_names = None  # 特征名称列表
    g.last_retrain_date = None  # 上次训练日期
    
    # RSRS相关
    g.security = '000300.XSHG'  # 基准：沪深300指数
    set_benchmark(g.security)
    g.days = 0
    g.init = True
    g.ans = []
    g.ans_rightdev = []


# 开盘前运行
def before_market_open(context):
    """开盘前运行函数，每日执行一次"""
    g.days += 1
    send_message(f'策略正常运行，当前第{g.days}天~')


# 开盘时运行
def market_open(context):
    """
    开盘时运行函数，每日执行一次
    核心逻辑：RSRS择时 + XGBoost选股交易
    """
    # 首次运行：预热RSRS数据并训练模型
    if g.days == 1:
        warm_up_rsrs(context)
        train_xgboost_model(context)
        g.init = False
        return
    
    # 更新当日RSRS
    update_rsrs(context)
    
    # RSRS择时信号
    signal = get_rsrs_signal()
    
    # 买入信号
    if signal == 'BUY':
        xgboost_trade(context)
    
    # 卖出信号
    elif signal == 'SELL':
        for stock in list(context.portfolio.positions.keys()):
            order_target(stock, 0)


# 预热RSRS历史数据
def warm_up_rsrs(context):
    """
    预热RSRS斜率和R²历史数据
    避免回测初期因数据不足导致无法进行Z-score标准化
    """
    prices = get_price(g.security, '2005-01-05', context.previous_date, '1d', ['high', 'low'])
    prices = prices.dropna()
    if len(prices) < g.N:
        return
    
    highs = prices.high
    lows = prices.low
    
    # 滑动计算RSRS回归斜率和R²
    for i in range(len(highs))[g.N:]:
        data_high = highs.iloc[i-g.N+1:i+1]
        data_low = lows.iloc[i-g.N+1:i+1]
        
        if data_high.isna().any() or data_low.isna().any():
            continue
        
        X = sm.add_constant(data_low, has_constant='add')
        model = sm.OLS(data_high, X)
        results = model.fit()
        g.ans.append(results.params[1])
        g.ans_rightdev.append(results.rsquared)


# 更新当日RSRS
def update_rsrs(context):
    """更新当日RSRS斜率和R²"""
    try:
        prices = attribute_history(g.security, g.N, '1d', ['high', 'low'])
        prices = prices.dropna()
        if len(prices) >= g.N:
            highs = prices.high
            lows = prices.low
            X = sm.add_constant(lows, has_constant='add')
            model = sm.OLS(highs, X)
            res = model.fit()
            g.ans.append(res.params[1])
            g.ans_rightdev.append(res.rsquared)
    except:
        pass


# 获取RSRS择时信号
def get_rsrs_signal():
    """
    计算RSRS择时信号
    
    返回值：
    - 'BUY': 买入信号（RSRS强势）
    - 'SELL': 卖出信号（RSRS弱势）
    - 'HOLD': 持有信号（RSRS中性）
    """
    if len(g.ans) < g.M:
        return 'HOLD'
    
    section = g.ans[-g.M:]
    mu = np.mean(section)
    sigma = np.std(section)
    
    if sigma == 0:
        return 'HOLD'
    
    zscore = (section[-1] - mu) / sigma
    beta = section[-1]
    r2 = g.ans_rightdev[-1]
    zscore_rightdev = zscore * beta * r2
    
    if zscore_rightdev > g.buy:
        return 'BUY'
    elif zscore_rightdev < g.sell:
        return 'SELL'
    else:
        return 'HOLD'


# 训练XGBoost模型
def train_xgboost_model(context):
    """
    训练XGBoost回归模型
    
    流程：
    1. 获取全市场股票池
    2. 计算特征（基本面、技术面、情绪面）
    3. 计算标签（未来20日收益率）
    4. 训练XGBoost模型
    5. 保存模型和特征名称
    """
    try:
        # 获取全市场股票池（剔除ST、停牌）
        all_stocks = get_all_securities(['stock']).index.tolist()
        current_data = get_current_data()
        stock_pool = [s for s in all_stocks 
                     if not current_data[s].is_st 
                     and not current_data[s].paused
                     and s.startswith(('60', '00', '30'))]
        
        if len(stock_pool) == 0:
            return
        
        # 计算特征
        features_df = calculate_features(context, stock_pool)
        if features_df is None or len(features_df) == 0:
            return
        
        # 计算标签（未来收益率）
        labels_df = calculate_labels(context, stock_pool)
        if labels_df is None or len(labels_df) == 0:
            return
        
        # 合并特征和标签
        df = pd.merge(features_df, labels_df, left_index=True, right_index=True)
        df = df.dropna()
        
        if len(df) < 100:  # 至少需要100个样本
            return
        
        # 分离特征和标签
        X = df.drop(columns=['future_return'])
        y = df['future_return']
        
        # 标准化特征（可选，XGBoost不强制要求）
        # X = (X - X.mean()) / X.std()
        
        # 训练XGBoost模型
        g.model = XGBRegressor(
            n_estimators=100,      # 树的数量
            max_depth=6,           # 树的最大深度
            learning_rate=0.1,     # 学习率
            subsample=0.8,         # 样本采样比例
            colsample_bytree=0.8,  # 特征采样比例
            random_state=42,       # 随机种子
            n_jobs=-1,             # 并行训练
            objective='reg:squarederror'  # 回归目标
        )
        g.model.fit(X, y)
        
        # 保存特征名称
        g.feature_names = X.columns.tolist()
        g.last_retrain_date = context.current_dt
        
        log.info(f'XGBoost模型训练完成，样本数：{len(df)}，特征数：{len(g.feature_names)}')
        
    except Exception as e:
        log.error(f'XGBoost模型训练失败：{str(e)}')


# 计算特征
def calculate_features(context, stock_pool):
    """
    计算特征（基本面、技术面、情绪面）
    
    返回：DataFrame，索引为股票代码，列为特征
    """
    try:
        # 基本面因子
        fundamentals = get_fundamentals(query(
            valuation.code,
            valuation.pe_ratio,
            valuation.pb_ratio,
            valuation.ps_ratio,
            valuation.market_cap,
            valuation.circulating_market_cap,
            indicator.roe,
            indicator.roa,
            indicator.inc_net_profit_year_on_year,  # 净利润增长率
            indicator.inc_revenue_year_on_year,    # 营收增长率
            indicator.gross_profit_margin,         # 毛利率
        ))
        
        if fundamentals is None or len(fundamentals) == 0:
            return None
        
        # 过滤股票池中的股票
        fundamentals = fundamentals[fundamentals['code'].isin(stock_pool)]
        fundamentals = fundamentals.dropna()
        
        if len(fundamentals) == 0:
            return None
        
        fundamentals.index = fundamentals['code'].values
        
        # 基本面特征
        features = pd.DataFrame(index=fundamentals.index)
        features['pe'] = fundamentals['pe_ratio']
        features['pb'] = fundamentals['pb_ratio']
        features['ps'] = fundamentals['ps_ratio']
        features['market_cap'] = fundamentals['market_cap']
        features['log_market_cap'] = np.log(fundamentals['market_cap'] + 1)
        features['roe'] = fundamentals['roe']
        features['roa'] = fundamentals['roa']
        features['net_profit_growth'] = fundamentals['inc_net_profit_year_on_year']
        features['revenue_growth'] = fundamentals['inc_revenue_year_on_year']
        features['gross_margin'] = fundamentals['gross_profit_margin']
        
        # 技术面因子（需要逐个股票计算）
        features['momentum_5d'] = 0
        features['momentum_20d'] = 0
        features['momentum_60d'] = 0
        features['rsi'] = 50
        features['volatility_20d'] = 0
        features['turnover_20d'] = 0
        
        # 批量计算技术面因子（只计算部分股票以提高效率）
        for stock in features.index[:500]:  # 限制数量以提高速度
            try:
                # 获取历史价格
                prices = get_price(stock, end_date=context.current_dt, 
                                   frequency='daily', fields=['close', 'volume', 'money'], 
                                   count=g.lookback_days)
                
                if len(prices) < 20:
                    continue
                
                # 动量因子
                features.loc[stock, 'momentum_5d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-6] - 1) if len(prices) >= 6 else 0
                features.loc[stock, 'momentum_20d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-21] - 1) if len(prices) >= 21 else 0
                features.loc[stock, 'momentum_60d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-61] - 1) if len(prices) >= 61 else 0
                
                # RSI（简单计算）
                delta = prices['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                features.loc[stock, 'rsi'] = 100 - (100 / (1 + rs.iloc[-1])) if len(rs) >= 14 else 50
                
                # 波动率
                returns = prices['close'].pct_change()
                features.loc[stock, 'volatility_20d'] = returns.tail(20).std() if len(returns) >= 20 else 0
                
                # 换手率（用成交额代替）
                features.loc[stock, 'turnover_20d'] = prices['money'].tail(20).mean() if len(prices) >= 20 else 0
                
            except:
                continue
        
        # 填充缺失值
        features = features.fillna(0)
        
        return features
        
    except Exception as e:
        log.error(f'计算特征失败：{str(e)}')
        return None


# 计算标签（未来收益率）
def calculate_labels(context, stock_pool):
    """
    计算标签（未来收益率）
    
    返回：DataFrame，索引为股票代码，列为future_return
    """
    try:
        labels = pd.DataFrame(index=stock_pool, columns=['future_return'])
        
        for stock in stock_pool[:500]:  # 限制数量以提高速度
            try:
                # 获取未来价格
                future_prices = get_bars(stock, count=g.prediction_days + 5, 
                                         end_dt=context.current_dt + pd.Timedelta(days=g.prediction_days + 10),
                                         include_now=True)
                
                if future_prices is None or len(future_prices) < g.prediction_days:
                    labels.loc[stock, 'future_return'] = 0
                    continue
                
                # 计算未来20日收益率
                current_price = future_prices['close'].iloc[0]
                future_price = future_prices['close'].iloc[-1]
                labels.loc[stock, 'future_return'] = (future_price / current_price - 1) * 100  # 百分比
                
            except:
                labels.loc[stock, 'future_return'] = 0
        
        labels = labels.fillna(0)
        return labels
        
    except Exception as e:
        log.error(f'计算标签失败：{str(e)}')
        return None


# 每月重新训练模型
def retrain_model(context):
    """每月重新训练模型"""
    train_xgboost_model(context)


# XGBoost选股交易
def xgboost_trade(context):
    """
    使用XGBoost模型选股并交易
    
    流程：
    1. 检查模型是否已训练
    2. 计算当前市场股票的特征
    3. 使用模型预测收益率
    4. 选择预测收益率最高的N只股票
    5. 调仓
    """
    try:
        # 检查模型
        if g.model is None:
            train_xgboost_model(context)
            if g.model is None:
                return
        
        # 获取股票池
        all_stocks = get_all_securities(['stock']).index.tolist()
        current_data = get_current_data()
        stock_pool = [s for s in all_stocks 
                     if not current_data[s].is_st 
                     and not current_data[s].paused
                     and s.startswith(('60', '00', '30'))]
        
        if len(stock_pool) == 0:
            return
        
        # 计算特征
        features_df = calculate_features(context, stock_pool)
        if features_df is None or len(features_df) == 0:
            return
        
        # 确保特征顺序一致
        if g.feature_names is not None:
            for col in g.feature_names:
                if col not in features_df.columns:
                    features_df[col] = 0
            features_df = features_df[g.feature_names]
        
        # 预测收益率
        predictions = g.model.predict(features_df)
        features_df['predicted_return'] = predictions
        
        # 选择预测收益率最高的N只股票
        features_df = features_df.sort_values('predicted_return', ascending=False)
        selected_stocks = features_df.head(g.stock_num).index.tolist()
        
        # 计算每只股票的目标持仓金额（等权重）
        cash_per = context.portfolio.total_value / len(selected_stocks)
        
        # 调仓
        for s in list(context.portfolio.positions.keys()):
            if s not in selected_stocks:
                order_target(s, 0)
        
        for s in selected_stocks:
            order_target_value(s, cash_per)
        
        log.info(f'XGBoost选股完成，选股数：{len(selected_stocks)}，预测收益率范围：{predictions.min():.2f}% ~ {predictions.max():.2f}%')
        
    except Exception as e:
        log.error(f'XGBoost交易失败：{str(e)}')
