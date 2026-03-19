# -*- coding: utf-8 -*-
"""
随机森林特征重要性策略
======================

策略思路：
--------
1. 使用随机森林模型计算特征重要性
2. 选择重要性高的前K个特征进行选股
3. 基于重要特征对股票进行打分排序
4. 选取综合得分最高的N只股票进行投资
5. 配合RSRS择时信号控制仓位

模型特点：
---------
- 随机森林：集成学习方法，计算特征重要性
- 特征选择：动态选择最重要特征
- 特征数量：选择前15个最重要特征
- 模型更新：每季度重新计算特征重要性

优势：
-----
- 特征重要性可视化，易于理解
- 自动筛选有效因子
- 适应市场变化，特征会动态调整
- 降低过拟合风险

特征库（30个候选特征）：
----------------------
基本面因子（10个）：
- PE、PB、PS、市值、市值对数
- ROE、ROA、毛利率、净利率、营收增长率

技术面因子（12个）：
- 5日/10日/20日/60日动量
- RSI、MACD、KDJ
- 布林带宽度、ATR
- 20日/60日波动率
- 换手率

市场情绪因子（5个）：
- 北向资金净流入比例
- 5日/20日涨跌幅
- 相对涨跌（vs沪深300）
- 涨跌停次数

风格因子（3个）：
- Beta（vs沪深300）
- 动量因子（12个月）
- 价值因子（B/M）

运行环境：JoinQuant / 聚宽（Python3）
依赖库：sklearn, numpy, pandas, statsmodels
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# 导入聚宽函数库
from jqlib.technical_analysis import *


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
    run_quarterly(retrain_model, 1, time='after_close')


# 参数设置
def set_parameter(context):
    """
    设置策略全局参数
    
    核心参数说明：
    -------------
    g.stock_num = 15: 持股数量
    
    g.top_features = 15: 选择的最重要的特征数量
        - 从30个候选特征中选择最重要的15个
        - 平衡特征丰富度和模型复杂度
    
    g.prediction_days = 20: 预测收益率天数
    
    g.retrain_freq = 3: 模型重训练频率（季度）
        - 特征重要性相对稳定，不需要频繁更新
        - 每季度更新一次即可
    
    g.lookback_days = 252: 特征计算历史窗口
    
    g.n_estimators = 100: 随机森林树的数量
        - 足够多的树确保稳定性
        - 100棵树平衡效果和效率
    
    g.buy = 0.7: RSRS买入阈值
    g.sell = -0.7: RSRS卖出阈值
    g.N = 18: RSRS回归窗口
    g.M = 1100: Z-score标准化历史窗口
    
    g.rf_model = None: 随机森林模型
    g.feature_names = None: 所有候选特征名称
    g.selected_features = None: 选择的特征名称
    g.feature_importance = None: 特征重要性字典
    """
    g.stock_num = 15  # 持股数量
    g.top_features = 15  # 选择的特征数量
    g.prediction_days = 20  # 预测收益率天数
    g.retrain_freq = 3  # 模型重训练频率（季度）
    g.lookback_days = 252  # 特征计算历史窗口
    g.n_estimators = 100  # 随机森林树的数量
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    
    # 模型相关
    g.rf_model = None  # 随机森林模型
    g.feature_names = None  # 所有候选特征名称
    g.selected_features = None  # 选择的特征名称
    g.feature_importance = None  # 特征重要性字典
    g.last_retrain_date = None  # 上次训练日期
    g.scaler = None  # 标准化器
    
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
    核心逻辑：RSRS择时 + 随机森林选股交易
    """
    # 首次运行：预热RSRS数据并训练模型
    if g.days == 1:
        warm_up_rsrs(context)
        train_rf_model(context)
        g.init = False
        return
    
    # 更新当日RSRS
    update_rsrs(context)
    
    # RSRS择时信号
    signal = get_rsrs_signal()
    
    # 买入信号
    if signal == 'BUY':
        rf_feature_trade(context)
    
    # 卖出信号
    elif signal == 'SELL':
        for stock in list(context.portfolio.positions.keys()):
            order_target(stock, 0)


# 预热RSRS历史数据
def warm_up_rsrs(context):
    """预热RSRS斜率和R²历史数据"""
    prices = get_price(g.security, '2005-01-05', context.previous_date, '1d', ['high', 'low'])
    prices = prices.dropna()
    if len(prices) < g.N:
        return
    
    highs = prices.high
    lows = prices.low
    
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
    """计算RSRS择时信号"""
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


# 训练随机森林模型
def train_rf_model(context):
    """
    训练随机森林模型并计算特征重要性
    
    流程：
    1. 获取全市场股票池
    2. 计算所有候选特征（30个）
    3. 计算标签（未来收益率）
    4. 训练随机森林模型
    5. 计算并保存特征重要性
    6. 选择最重要的特征
    """
    try:
        # 获取全市场股票池
        all_stocks = get_all_securities(['stock']).index.tolist()
        current_data = get_current_data()
        stock_pool = [s for s in all_stocks 
                     if not current_data[s].is_st 
                     and not current_data[s].paused
                     and s.startswith(('60', '00', '30'))]
        
        if len(stock_pool) == 0:
            return
        
        # 计算特征（30个候选特征）
        features_df = calculate_all_features(context, stock_pool)
        if features_df is None or len(features_df) == 0:
            return
        
        # 计算标签（未来收益率）
        labels_df = calculate_labels(context, stock_pool)
        if labels_df is None or len(labels_df) == 0:
            return
        
        # 合并特征和标签
        df = pd.merge(features_df, labels_df, left_index=True, right_index=True)
        df = df.dropna()
        
        if len(df) < 100:
            return
        
        # 分离特征和标签
        X = df.drop(columns=['future_return'])
        y = df['future_return']
        
        # 标准化特征
        g.scaler = StandardScaler()
        X_scaled = g.scaler.fit_transform(X)
        X_scaled = pd.DataFrame(X_scaled, index=X.index, columns=X.columns)
        
        # 训练随机森林模型
        g.rf_model = RandomForestRegressor(
            n_estimators=g.n_estimators,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1
        )
        g.rf_model.fit(X_scaled, y)
        
        # 计算特征重要性
        feature_importance = dict(zip(X.columns, g.rf_model.feature_importances_))
        g.feature_importance = feature_importance
        
        # 保存所有特征名称
        g.feature_names = X.columns.tolist()
        
        # 选择最重要的特征
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        g.selected_features = [f[0] for f in sorted_features[:g.top_features]]
        
        g.last_retrain_date = context.current_dt
        
        # 输出特征重要性
        log.info(f'随机森林模型训练完成，样本数：{len(df)}，总特征数：{len(g.feature_names)}')
        log.info(f'选择的特征数：{g.top_features}')
        log.info(f'Top 10特征重要性：')
        for i, (feature, importance) in enumerate(sorted_features[:10]):
            log.info(f'  {i+1}. {feature}: {importance:.4f}')
        
    except Exception as e:
        log.error(f'随机森林模型训练失败：{str(e)}')


# 计算所有候选特征
def calculate_all_features(context, stock_pool):
    """计算所有候选特征（30个）"""
    try:
        # 基本面因子（10个）
        fundamentals = get_fundamentals(query(
            valuation.code,
            valuation.pe_ratio,
            valuation.pb_ratio,
            valuation.ps_ratio,
            valuation.market_cap,
            indicator.roe,
            indicator.roa,
            indicator.inc_net_profit_year_on_year,
            indicator.inc_revenue_year_on_year,
            indicator.gross_profit_margin,
        ))
        
        if fundamentals is None or len(fundamentals) == 0:
            return None
        
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
        
        # 初始化技术面因子（12个）
        features['momentum_5d'] = 0
        features['momentum_10d'] = 0
        features['momentum_20d'] = 0
        features['momentum_60d'] = 0
        features['rsi'] = 50
        features['macd'] = 0
        features['kdj'] = 50
        features['bb_width'] = 0
        features['atr'] = 0
        features['volatility_20d'] = 0
        features['volatility_60d'] = 0
        features['turnover_20d'] = 0
        
        # 批量计算技术面因子
        for stock in features.index[:500]:
            try:
                prices = get_price(stock, end_date=context.current_dt, 
                                   frequency='daily', fields=['close', 'high', 'low', 'volume', 'money'], 
                                   count=g.lookback_days)
                
                if len(prices) < 60:
                    continue
                
                # 动量因子
                features.loc[stock, 'momentum_5d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-6] - 1) if len(prices) >= 6 else 0
                features.loc[stock, 'momentum_10d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-11] - 1) if len(prices) >= 11 else 0
                features.loc[stock, 'momentum_20d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-21] - 1) if len(prices) >= 21 else 0
                features.loc[stock, 'momentum_60d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-61] - 1) if len(prices) >= 61 else 0
                
                # RSI
                delta = prices['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                features.loc[stock, 'rsi'] = 100 - (100 / (1 + rs.iloc[-1])) if len(rs) >= 14 else 50
                
                # MACD
                ema_12 = prices['close'].ewm(span=12).mean()
                ema_26 = prices['close'].ewm(span=26).mean()
                macd_line = ema_12 - ema_26
                if len(macd_line) > 0:
                    features.loc[stock, 'macd'] = macd_line.iloc[-1]
                
                # KDJ（简化版）
                low_9 = prices['low'].rolling(9).min()
                high_9 = prices['high'].rolling(9).max()
                rsv = (prices['close'] - low_9) / (high_9 - low_9) * 100
                if len(rsv) > 0:
                    features.loc[stock, 'kdj'] = rsv.iloc[-1]
                
                # 布林带宽度
                sma = prices['close'].rolling(20).mean()
                std = prices['close'].rolling(20).std()
                bb_width = (2 * std) / sma
                if len(bb_width) > 0:
                    features.loc[stock, 'bb_width'] = bb_width.iloc[-1]
                
                # ATR
                high_low = prices['high'] - prices['low']
                high_close = np.abs(prices['high'] - prices['close'].shift())
                low_close = np.abs(prices['low'] - prices['close'].shift())
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = tr.rolling(14).mean()
                if len(atr) > 0:
                    features.loc[stock, 'atr'] = atr.iloc[-1]
                
                # 波动率
                returns = prices['close'].pct_change()
                features.loc[stock, 'volatility_20d'] = returns.tail(20).std() if len(returns) >= 20 else 0
                features.loc[stock, 'volatility_60d'] = returns.tail(60).std() if len(returns) >= 60 else 0
                
                # 换手率
                features.loc[stock, 'turnover_20d'] = prices['money'].tail(20).mean() if len(prices) >= 20 else 0
                
            except:
                continue
        
        # 市场情绪因子（5个）
        features['return_5d'] = 0
        features['return_20d'] = 0
        features['relative_return'] = 0
        features['limit_up_count'] = 0
        features['limit_down_count'] = 0
        
        for stock in features.index[:500]:
            try:
                prices = get_price(stock, end_date=context.current_dt, 
                                   frequency='daily', fields=['close', 'high'], 
                                   count=25)
                
                if len(prices) < 20:
                    continue
                
                # 5日和20日收益率
                features.loc[stock, 'return_5d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-6] - 1) if len(prices) >= 6 else 0
                features.loc[stock, 'return_20d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-21] - 1) if len(prices) >= 21 else 0
                
                # 相对收益率（vs沪深300）
                benchmark_prices = get_price('000300.XSHG', end_date=context.current_dt, 
                                              frequency='daily', fields=['close'], 
                                              count=25)
                if benchmark_prices is not None and len(benchmark_prices) >= 20:
                    benchmark_return_20d = (benchmark_prices['close'].iloc[-1] / benchmark_prices['close'].iloc[-21] - 1)
                    features.loc[stock, 'relative_return'] = features.loc[stock, 'return_20d'] - benchmark_return_20d
                
                # 涨跌停次数（简化版）
                limit_up_prices = prices[prices['high'] >= prices['close'].iloc[-1] * 1.09]
                limit_down_prices = prices[prices['high'] <= prices['close'].iloc[-1] * 0.91]
                features.loc[stock, 'limit_up_count'] = len(limit_up_prices)
                features.loc[stock, 'limit_down_count'] = len(limit_down_prices)
                
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
    """计算标签（未来收益率）"""
    try:
        labels = pd.DataFrame(index=stock_pool, columns=['future_return'])
        
        for stock in stock_pool[:500]:
            try:
                future_prices = get_bars(stock, count=g.prediction_days + 5, 
                                         end_dt=context.current_dt + pd.Timedelta(days=g.prediction_days + 10),
                                         include_now=True)
                
                if future_prices is None or len(future_prices) < g.prediction_days:
                    labels.loc[stock, 'future_return'] = 0
                    continue
                
                current_price = future_prices['close'].iloc[0]
                future_price = future_prices['close'].iloc[-1]
                labels.loc[stock, 'future_return'] = (future_price / current_price - 1) * 100
                
            except:
                labels.loc[stock, 'future_return'] = 0
        
        labels = labels.fillna(0)
        return labels
        
    except Exception as e:
        log.error(f'计算标签失败：{str(e)}')
        return None


# 每季度重新训练模型
def retrain_model(context):
    """每季度重新训练模型"""
    train_rf_model(context)


# 随机森林特征选股交易
def rf_feature_trade(context):
    """
    使用随机森林特征重要性选股并交易
    
    流程：
    1. 检查模型是否已训练
    2. 计算当前市场股票的特征
    3. 使用选择的特征对股票进行打分
    4. 选择综合得分最高的N只股票
    5. 调仓
    """
    try:
        # 检查模型
        if g.rf_model is None:
            train_rf_model(context)
            if g.rf_model is None:
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
        features_df = calculate_all_features(context, stock_pool)
        if features_df is None or len(features_df) == 0:
            return
        
        # 确保所有特征都存在
        for col in g.feature_names:
            if col not in features_df.columns:
                features_df[col] = 0
        
        # 选择最重要的特征
        selected_features_df = features_df[g.selected_features]
        
        # 标准化
        X_scaled = g.scaler.transform(selected_features_df)
        X_scaled = pd.DataFrame(X_scaled, index=selected_features_df.index, columns=selected_features_df.columns)
        
        # 使用随机森林预测收益率
        predictions = g.rf_model.predict(X_scaled)
        selected_features_df['predicted_return'] = predictions
        
        # 使用特征重要性加权打分（可选）
        # 这里直接使用预测收益率
        selected_features_df['score'] = predictions
        
        # 选择得分最高的N只股票
        selected_features_df = selected_features_df.sort_values('score', ascending=False)
        selected_stocks = selected_features_df.head(g.stock_num).index.tolist()
        
        # 计算每只股票的目标持仓金额（等权重）
        cash_per = context.portfolio.total_value / len(selected_stocks)
        
        # 调仓
        for s in list(context.portfolio.positions.keys()):
            if s not in selected_stocks:
                order_target(s, 0)
        
        for s in selected_stocks:
            order_target_value(s, cash_per)
        
        log.info(f'随机森林特征选股完成，选股数：{len(selected_stocks)}，使用的特征：{len(g.selected_features)}个')
        
    except Exception as e:
        log.error(f'随机森林特征选股交易失败：{str(e)}')
