# -*- coding: utf-8 -*-
"""
LSTM时序预测策略
================

策略思路：
--------
1. 使用LSTM神经网络预测股票未来收益率
2. LSTM擅长捕捉时间序列中的长期依赖关系
3. 选取预测收益率最高的N只股票进行投资
4. 配合RSRS择时信号控制仓位
5. 等权重分散持仓，降低风险

模型特点：
---------
- LSTM：长短期记忆网络，捕获时序依赖
- 输入：过去60天的价格、成交量特征
- 输出：预测未来20日收益率
- 模型更新：每季度重新训练一次

LSTM网络结构：
--------------
输入层：(60, 5) - 60天历史，5个特征
  ↓
LSTM层1：64个单元，return_sequences=True
  ↓
Dropout层：0.2 dropout率
  ↓
LSTM层2：32个单元
  ↓
Dropout层：0.2 dropout率
  ↓
全连接层：16个神经元
  ↓
输出层：1个神经元（预测收益率）

输入特征（5个）：
---------------
- 收盘价（标准化）
- 最高价（标准化）
- 最低价（标准化）
- 成交量（标准化）
- 涨跌幅（pct_change）

训练参数：
---------
- 损失函数：MSE（均方误差）
- 优化器：Adam
- 批量大小：32
- 训练轮数：50
- 验证比例：0.2

运行环境：JoinQuant / 聚宽（Python3）
依赖库：tensorflow, numpy, pandas, statsmodels
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

# 导入聚宽函数库
from jqlib.technical_analysis import *

# 尝试导入tensorflow（聚宽可能不支持，使用模拟模型）
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print('警告：TensorFlow不可用，将使用简化模型（动量加权）')


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
    
    g.sequence_length = 60: LSTM输入序列长度（天）
        - 使用过去60天的价格数据预测未来
        - 60个交易日约等于3个月
        - 较长的序列可以捕捉更长期的趋势
    
    g.prediction_days = 20: 预测收益率天数
        - 预测未来20日收益率
        - 20个交易日约等于1个月
    
    g.retrain_freq = 3: 模型重训练频率（季度）
        - LSTM训练较慢，不宜频繁更新
        - 每季度更新一次
    
    g.batch_size = 32: 批量大小
    g.epochs = 50: 训练轮数
    g.validation_split = 0.2: 验证集比例
    
    g.buy = 0.7: RSRS买入阈值
    g.sell = -0.7: RSRS卖出阈值
    g.N = 18: RSRS回归窗口
    g.M = 1100: Z-score标准化历史窗口
    
    g.lstm_model = None: LSTM模型
    g.scaler = None: 数据标准化器
    """
    g.stock_num = 15  # 持股数量
    g.sequence_length = 60  # LSTM输入序列长度（天）
    g.prediction_days = 20  # 预测收益率天数
    g.retrain_freq = 3  # 模型重训练频率（季度）
    g.batch_size = 32  # 批量大小
    g.epochs = 50  # 训练轮数
    g.validation_split = 0.2  # 验证集比例
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    
    # 模型相关
    g.lstm_model = None  # LSTM模型
    g.scaler = None  # 数据标准化器
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
    核心逻辑：RSRS择时 + LSTM选股交易
    """
    # 首次运行：预热RSRS数据并训练模型
    if g.days == 1:
        warm_up_rsrs(context)
        train_lstm_model(context)
        g.init = False
        return
    
    # 更新当日RSRS
    update_rsrs(context)
    
    # RSRS择时信号
    signal = get_rsrs_signal()
    
    # 买入信号
    if signal == 'BUY':
        lstm_trade(context)
    
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


# 训练LSTM模型
def train_lstm_model(context):
    """
    训练LSTM模型
    
    流程：
    1. 获取全市场股票池
    2. 为每只股票提取时序数据（60天）
    3. 创建训练数据集
    4. 训练LSTM模型（如果TensorFlow可用）
    5. 保存模型和标准化器
    
    注意：聚宽可能不支持TensorFlow，使用简化模型
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
        
        # 获取时序数据
        sequences, labels, stock_list = prepare_lstm_data(context, stock_pool)
        
        if len(sequences) == 0:
            log.warning('没有足够的训练数据')
            return
        
        # 如果TensorFlow不可用，使用简化模型（动量加权）
        if not TENSORFLOW_AVAILABLE:
            log.warning('TensorFlow不可用，使用动量加权简化模型')
            g.lstm_model = 'momentum_based'
            g.last_retrain_date = context.current_dt
            log.info(f'简化模型准备完成，样本数：{len(sequences)}')
            return
        
        # 构建LSTM模型
        g.lstm_model = Sequential([
            LSTM(64, return_sequences=True, input_shape=(g.sequence_length, 5)),
            Dropout(0.2),
            LSTM(32),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1)
        ])
        
        # 编译模型
        optimizer = Adam(learning_rate=0.001)
        g.lstm_model.compile(
            optimizer=optimizer,
            loss='mse',
            metrics=['mae']
        )
        
        # 早停回调
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        # 训练模型
        history = g.lstm_model.fit(
            sequences, labels,
            batch_size=g.batch_size,
            epochs=g.epochs,
            validation_split=g.validation_split,
            callbacks=[early_stopping],
            verbose=0
        )
        
        g.last_retrain_date = context.current_dt
        
        log.info(f'LSTM模型训练完成，样本数：{len(sequences)}')
        log.info(f'训练损失：{history.history["loss"][-1]:.4f}')
        
    except Exception as e:
        log.error(f'LSTM模型训练失败：{str(e)}')
        # 使用简化模型
        g.lstm_model = 'momentum_based'


# 准备LSTM训练数据
def prepare_lstm_data(context, stock_pool):
    """
    准备LSTM训练数据
    
    返回：
    - sequences: 训练序列，形状为 (样本数, 60, 5)
    - labels: 标签，形状为 (样本数,)
    - stock_list: 股票代码列表
    """
    sequences = []
    labels = []
    stock_list = []
    
    for stock in stock_pool[:100]:  # 限制数量以提高速度
        try:
            # 获取历史价格数据
            # 需要足够长的历史数据：sequence_length + prediction_days + buffer
            total_days = g.sequence_length + g.prediction_days + 20
            
            prices = get_price(stock, end_date=context.current_dt, 
                               frequency='daily', 
                               fields=['close', 'high', 'low', 'volume', 'open'], 
                               count=total_days)
            
            if prices is None or len(prices) < total_days:
                continue
            
            # 特征：收盘价、最高价、最低价、成交量、涨跌幅
            features = pd.DataFrame()
            features['close'] = prices['close']
            features['high'] = prices['high']
            features['low'] = prices['low']
            features['volume'] = prices['volume']
            features['pct_change'] = prices['close'].pct_change()
            
            features = features.fillna(0)
            
            # 标准化特征
            for col in features.columns:
                features[col] = (features[col] - features[col].mean()) / (features[col].std() + 1e-8)
            
            # 创建训练样本
            # 滑动窗口：每5天创建一个样本
            for i in range(len(features) - g.sequence_length - g.prediction_days):
                seq = features.iloc[i:i+g.sequence_length].values
                
                # 计算标签：未来20日收益率
                future_prices = prices['close'].iloc[i+g.sequence_length:i+g.sequence_length+g.prediction_days]
                current_price = prices['close'].iloc[i+g.sequence_length-1]
                future_price = future_prices.iloc[-1]
                label = (future_price / current_price - 1) * 100  # 百分比
                
                sequences.append(seq)
                labels.append(label)
                stock_list.append(stock)
        
        except Exception as e:
            continue
    
    # 转换为numpy数组
    sequences = np.array(sequences, dtype=np.float32)
    labels = np.array(labels, dtype=np.float32)
    
    return sequences, labels, stock_list


# 每季度重新训练模型
def retrain_model(context):
    """每季度重新训练模型"""
    train_lstm_model(context)


# LSTM选股交易
def lstm_trade(context):
    """
    使用LSTM模型选股并交易
    
    流程：
    1. 检查模型是否已训练
    2. 获取股票池
    3. 为每只股票提取时序数据
    4. 使用LSTM预测收益率
    5. 选择预测收益率最高的N只股票
    6. 调仓
    """
    try:
        # 检查模型
        if g.lstm_model is None:
            train_lstm_model(context)
            if g.lstm_model is None:
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
        
        # 计算预测收益率
        predictions = {}
        
        if g.lstm_model == 'momentum_based':
            # 使用动量加权简化模型
            for stock in stock_pool[:500]:
                try:
                    prices = get_price(stock, end_date=context.current_dt, 
                                       frequency='daily', fields=['close'], 
                                       count=60)
                    
                    if prices is None or len(prices) < 20:
                        continue
                    
                    # 多周期动量加权
                    mom_5 = (prices['close'].iloc[-1] / prices['close'].iloc[-6] - 1) if len(prices) >= 6 else 0
                    mom_20 = (prices['close'].iloc[-1] / prices['close'].iloc[-21] - 1) if len(prices) >= 21 else 0
                    mom_60 = (prices['close'].iloc[-1] / prices['close'].iloc[-61] - 1) if len(prices) >= 61 else 0
                    
                    # 加权预测：近期动量权重更高
                    predictions[stock] = mom_5 * 0.5 + mom_20 * 0.3 + mom_60 * 0.2
                    
                except Exception as e:
                    continue
        
        else:
            # 使用LSTM模型预测
            for stock in stock_pool[:200]:  # 限制数量以提高速度
                try:
                    # 获取历史价格数据
                    prices = get_price(stock, end_date=context.current_dt, 
                                       frequency='daily', 
                                       fields=['close', 'high', 'low', 'volume', 'open'], 
                                       count=g.sequence_length)
                    
                    if prices is None or len(prices) < g.sequence_length:
                        continue
                    
                    # 特征
                    features = pd.DataFrame()
                    features['close'] = prices['close']
                    features['high'] = prices['high']
                    features['low'] = prices['low']
                    features['volume'] = prices['volume']
                    features['pct_change'] = prices['close'].pct_change()
                    
                    features = features.fillna(0)
                    
                    # 标准化特征
                    for col in features.columns:
                        features[col] = (features[col] - features[col].mean()) / (features[col].std() + 1e-8)
                    
                    # 准备输入
                    seq = features.values.reshape(1, g.sequence_length, 5)
                    
                    # 预测
                    prediction = g.lstm_model.predict(seq, verbose=0)[0][0]
                    predictions[stock] = prediction
                    
                except Exception as e:
                    continue
        
        if len(predictions) == 0:
            return
        
        # 选择预测收益率最高的N只股票
        sorted_stocks = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        selected_stocks = [s[0] for s in sorted_stocks[:g.stock_num]]
        
        # 计算每只股票的目标持仓金额（等权重）
        cash_per = context.portfolio.total_value / len(selected_stocks)
        
        # 调仓
        for s in list(context.portfolio.positions.keys()):
            if s not in selected_stocks:
                order_target(s, 0)
        
        for s in selected_stocks:
            order_target_value(s, cash_per)
        
        if len(predictions) > 0:
            pred_values = [v for v in predictions.values()]
            log.info(f'LSTM选股完成，选股数：{len(selected_stocks)}，预测收益率范围：{min(pred_values):.2f}% ~ {max(pred_values):.2f}%')
        
    except Exception as e:
        log.error(f'LSTM交易失败：{str(e)}')
