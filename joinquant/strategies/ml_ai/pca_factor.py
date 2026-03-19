# -*- coding: utf-8 -*-
"""
PCA因子提取策略
===============

策略思路：
--------
1. 使用PCA主成分分析从多个因子中提取主要成分
2. 将高维因子空间降维到低维主成分空间
3. 基于主成分得分对股票进行排序选股
4. 选取主成分得分最高的N只股票进行投资
5. 配合RSRS择时信号控制仓位
6. 等权重分散持仓，降低风险

模型特点：
---------
- PCA：主成分分析，无监督降维
- 输入：20+个原始因子
- 输出：5-10个主成分
- 模型更新：每季度重新计算PCA

PCA原理：
---------
PCA通过正交变换将原始变量转换为一组线性不相关的变量（主成分）。

数学公式：
-----------
设X为标准化的特征矩阵（n×p）：
X = [x1, x2, ..., xp]

协方差矩阵：
Σ = X^T X / (n-1)

特征分解：
Σ = U Λ U^T

主成分得分：
Z = X U

主成分得分：
-----------
- 第一主成分（PC1）：解释方差最大的方向
- 第二主成分（PC2）：解释方差第二大的方向
- 依此类推

选股逻辑：
---------
1. 计算所有股票的因子
2. 标准化因子
3. PCA降维提取主成分
4. 计算每只股票的主成分得分
5. 加权综合得分（按方差贡献率加权）
6. 选择得分最高的N只股票

原始因子库（20个）：
------------------
基本面因子（10个）：
- PE、PB、PS、市值、市值对数
- ROE、ROA、毛利率、净利率、营收增长率

技术面因子（6个）：
- 5日/20日/60日动量
- RSI、20日波动率、换手率

风格因子（4个）：
- Beta、动量因子
- 价值因子（B/M）、质量因子（ROE）

运行环境：JoinQuant / 聚宽（Python3）
依赖库：sklearn, numpy, pandas, statsmodels
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.decomposition import PCA
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
    run_quarterly(retrain_pca, 1, time='after_close')


# 参数设置
def set_parameter(context):
    """
    设置策略全局参数
    
    核心参数说明：
    -------------
    g.stock_num = 15: 持股数量
    
    g.n_components = 5: 主成分数量
        - 从20个原始因子中提取5个主成分
        - 5个主成分通常能解释60-80%的方差
        - 平衡信息保留和降维效果
    
    g.explained_variance_threshold = 0.8: 解释方差阈值
        - 如果前N个主成分解释方差超过80%，则使用N个
        - 确保保留足够的信息
    
    g.retrain_freq = 3: PCA重计算频率（季度）
        - 因子关系相对稳定
        - 每季度更新一次即可
    
    g.lookback_days = 252: 特征计算历史窗口
    
    g.buy = 0.7: RSRS买入阈值
    g.sell = -0.7: RSRS卖出阈值
    g.N = 18: RSRS回归窗口
    g.M = 1100: Z-score标准化历史窗口
    
    g.pca = None: PCA模型
    g.scaler = None: 标准化器
    g.component_weights = None: 主成分权重
    """
    g.stock_num = 15  # 持股数量
    g.n_components = 5  # 主成分数量
    g.explained_variance_threshold = 0.8  # 解释方差阈值
    g.retrain_freq = 3  # PCA重计算频率（季度）
    g.lookback_days = 252  # 特征计算历史窗口
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    
    # PCA相关
    g.pca = None  # PCA模型
    g.scaler = None  # 标准化器
    g.component_weights = None  # 主成分权重
    g.last_retrain_date = None  # 上次计算日期
    
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
    核心逻辑：RSRS择时 + PCA选股交易
    """
    # 首次运行：预热RSRS数据并计算PCA
    if g.days == 1:
        warm_up_rsrs(context)
        calculate_pca(context)
        g.init = False
        return
    
    # 更新当日RSRS
    update_rsrs(context)
    
    # RSRS择时信号
    signal = get_rsrs_signal()
    
    # 买入信号
    if signal == 'BUY':
        pca_trade(context)
    
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


# 计算PCA模型
def calculate_pca(context):
    """
    计算PCA主成分分析模型
    
    流程：
    1. 获取全市场股票池
    2. 计算所有股票的20个因子
    3. 标准化因子
    4. PCA降维提取主成分
    5. 计算主成分权重（按方差贡献率）
    6. 保存PCA模型和标准化器
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
        
        # 计算所有因子
        features_df = calculate_all_factors(context, stock_pool)
        if features_df is None or len(features_df) == 0:
            return
        
        # 删除缺失值
        features_df = features_df.dropna()
        
        if len(features_df) < 100:
            return
        
        # 标准化因子
        g.scaler = StandardScaler()
        features_scaled = g.scaler.fit_transform(features_df)
        features_scaled = pd.DataFrame(features_scaled, 
                                        index=features_df.index, 
                                        columns=features_df.columns)
        
        # PCA降维
        g.pca = PCA(n_components=g.n_components)
        principal_components = g.pca.fit_transform(features_scaled)
        
        # 计算主成分权重（按方差贡献率）
        explained_variance = g.pca.explained_variance_ratio_
        g.component_weights = explained_variance / explained_variance.sum()
        
        g.last_retrain_date = context.current_dt
        
        # 输出结果
        total_variance = sum(explained_variance)
        log.info(f'PCA模型计算完成，样本数：{len(features_df)}，因子数：{len(features_df.columns)}')
        log.info(f'主成分数量：{g.n_components}，解释方差：{total_variance:.2%}')
        log.info(f'各主成分方差贡献率：')
        for i, ev in enumerate(explained_variance):
            log.info(f'  PC{i+1}: {ev:.2%} (权重: {g.component_weights[i]:.2%})')
        
        # 输出主成分与原始因子的关系
        loadings = pd.DataFrame(
            g.pca.components_.T,
            index=features_df.columns,
            columns=[f'PC{i+1}' for i in range(g.n_components)]
        )
        log.info(f'主成分与原始因子的关系（前3个主成分）：')
        for col in loadings.columns[:3]:
            top_factors = loadings[col].abs().sort_values(ascending=False).head(5)
            log.info(f'  {col}: {dict(zip(top_factors.index, top_factors.values.round(3)))}')
        
    except Exception as e:
        log.error(f'PCA模型计算失败：{str(e)}')


# 计算所有因子
def calculate_all_factors(context, stock_pool):
    """
    计算所有因子（20个）
    
    返回：DataFrame，索引为股票代码，列为因子
    """
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
        
        # 技术面因子（6个）
        features['momentum_5d'] = 0
        features['momentum_20d'] = 0
        features['momentum_60d'] = 0
        features['rsi'] = 50
        features['volatility_20d'] = 0
        features['turnover_20d'] = 0
        
        # 批量计算技术面因子
        for stock in features.index[:500]:
            try:
                prices = get_price(stock, end_date=context.current_dt, 
                                   frequency='daily', fields=['close', 'volume', 'money'], 
                                   count=g.lookback_days)
                
                if len(prices) < 60:
                    continue
                
                # 动量因子
                features.loc[stock, 'momentum_5d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-6] - 1) if len(prices) >= 6 else 0
                features.loc[stock, 'momentum_20d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-21] - 1) if len(prices) >= 21 else 0
                features.loc[stock, 'momentum_60d'] = (prices['close'].iloc[-1] / prices['close'].iloc[-61] - 1) if len(prices) >= 61 else 0
                
                # RSI
                delta = prices['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                features.loc[stock, 'rsi'] = 100 - (100 / (1 + rs.iloc[-1])) if len(rs) >= 14 else 50
                
                # 波动率
                returns = prices['close'].pct_change()
                features.loc[stock, 'volatility_20d'] = returns.tail(20).std() if len(returns) >= 20 else 0
                
                # 换手率
                features.loc[stock, 'turnover_20d'] = prices['money'].tail(20).mean() if len(prices) >= 20 else 0
                
            except:
                continue
        
        # 风格因子（4个）
        features['beta'] = 1.0  # 默认值
        features['momentum_12m'] = 0
        features['bm_ratio'] = 0  # 账面市值比
        features['quality'] = 0  # 质量因子
        
        for stock in features.index[:300]:
            try:
                # Beta（vs沪深300）
                stock_prices = get_price(stock, end_date=context.current_dt, 
                                          frequency='daily', fields=['close'], 
                                          count=60)
                benchmark_prices = get_price('000300.XSHG', end_date=context.current_dt, 
                                               frequency='daily', fields=['close'], 
                                               count=60)
                
                if (stock_prices is not None and len(stock_prices) >= 30 and
                    benchmark_prices is not None and len(benchmark_prices) >= 30):
                    stock_returns = stock_prices['close'].pct_change().dropna()
                    benchmark_returns = benchmark_prices['close'].pct_change().dropna()
                    
                    if len(stock_returns) >= 20 and len(benchmark_returns) >= 20:
                        min_len = min(len(stock_returns), len(benchmark_returns))
                        cov = np.cov(stock_returns.tail(min_len), benchmark_returns.tail(min_len))[0, 1]
                        var = np.var(benchmark_returns.tail(min_len))
                        if var > 0:
                            features.loc[stock, 'beta'] = cov / var
                
                # 12个月动量
                if stock_prices is not None and len(stock_prices) >= 252:
                    features.loc[stock, 'momentum_12m'] = (stock_prices['close'].iloc[-1] / stock_prices['close'].iloc[-252] - 1)
                
                # 账面市值比（简化版，使用1/PB）
                if 'pb' in features.columns:
                    features.loc[stock, 'bm_ratio'] = 1 / features.loc[stock, 'pb']
                
                # 质量因子（ROE）
                if 'roe' in features.columns:
                    features.loc[stock, 'quality'] = features.loc[stock, 'roe']
                
            except:
                continue
        
        # 填充缺失值
        features = features.fillna(0)
        
        return features
        
    except Exception as e:
        log.error(f'计算因子失败：{str(e)}')
        return None


# 每季度重新计算PCA
def retrain_pca(context):
    """每季度重新计算PCA"""
    calculate_pca(context)


# PCA选股交易
def pca_trade(context):
    """
    使用PCA选股并交易
    
    流程：
    1. 检查PCA模型是否已计算
    2. 获取股票池
    3. 计算当前股票的因子
    4. 标准化因子
    5. 计算主成分得分
    6. 加权综合得分
    7. 选择得分最高的N只股票
    8. 调仓
    """
    try:
        # 检查PCA模型
        if g.pca is None:
            calculate_pca(context)
            if g.pca is None:
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
        
        # 计算因子
        features_df = calculate_all_factors(context, stock_pool)
        if features_df is None or len(features_df) == 0:
            return
        
        # 填充缺失因子（使用0）
        for col in g.scaler.feature_names_in_:
            if col not in features_df.columns:
                features_df[col] = 0
        
        # 确保列顺序一致
        features_df = features_df[g.scaler.feature_names_in_]
        
        # 标准化因子
        features_scaled = g.scaler.transform(features_df)
        features_scaled = pd.DataFrame(features_scaled, 
                                        index=features_df.index, 
                                        columns=features_df.columns)
        
        # 计算主成分得分
        principal_scores = g.pca.transform(features_scaled)
        principal_scores = pd.DataFrame(
            principal_scores,
            index=features_df.index,
            columns=[f'PC{i+1}' for i in range(g.n_components)]
        )
        
        # 加权综合得分（按主成分权重）
        principal_scores['total_score'] = 0
        for i in range(g.n_components):
            principal_scores['total_score'] += principal_scores[f'PC{i+1}'] * g.component_weights[i]
        
        # 选择得分最高的N只股票
        principal_scores = principal_scores.sort_values('total_score', ascending=False)
        selected_stocks = principal_scores.head(g.stock_num).index.tolist()
        
        # 计算每只股票的目标持仓金额（等权重）
        cash_per = context.portfolio.total_value / len(selected_stocks)
        
        # 调仓
        for s in list(context.portfolio.positions.keys()):
            if s not in selected_stocks:
                order_target(s, 0)
        
        for s in selected_stocks:
            order_target_value(s, cash_per)
        
        if len(principal_scores) > 0:
            scores = principal_scores['total_score']
            log.info(f'PCA选股完成，选股数：{len(selected_stocks)}，综合得分范围：{scores.min():.4f} ~ {scores.max():.4f}')
        
    except Exception as e:
        log.error(f'PCA交易失败：{str(e)}')
