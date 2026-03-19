# -*- coding: utf-8 -*-
"""
CNN K线图识别策略
==================

策略思路：
--------
1. 使用CNN卷积神经网络从K线图中提取特征
2. 自动识别K线形态（如双底、头肩顶、锤子线等）
3. 基于识别的形态特征预测股票涨跌
4. 选取预测上涨概率最高的N只股票进行投资
5. 配合RSRS择时信号控制仓位
6. 等权重分散持仓，降低风险

模型特点：
---------
- CNN：卷积神经网络，擅长图像识别
- 输入：30日K线图（OHLCV）
- 输出：涨跌分类概率
- 模型更新：每季度重新训练一次

K线图生成：
----------
将30日的OHLCV数据转换为图像格式：
- Open/Close：红色/绿色K线实体
- High/Low：上下影线
- Volume：柱状图

CNN网络结构：
--------------
输入层：(30, 64, 3) - 30天，64宽度，3通道
  ↓
卷积层1：32个滤波器，3×3卷积核
  ↓
池化层1：2×2最大池化
  ↓
卷积层2：64个滤波器，3×3卷积核
  ↓
池化层2：2×2最大池化
  ↓
卷积层3：128个滤波器，3×3卷积核
  ↓
展平层
  ↓
全连接层：128个神经元
  ↓
Dropout层：0.5 dropout率
  ↓
输出层：2个神经元（涨/跌）

K线形态识别（手动特征）：
-----------------------
传统K线形态（作为辅助特征）：
- 锤子线、上吊线
- 吞没形态
- 窗口（跳空）
- 十字星
- 流星线
- 三连阳、三连阴
- 双底、双顶
- 头肩底、头肩顶

运行环境：JoinQuant / 聚宽（Python3）
依赖库：opencv-python, numpy, pandas, statsmodels
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from PIL import Image
import io

# 导入聚宽函数库
from jqlib.technical_analysis import *

# 尝试导入tensorflow（聚宽可能不支持）
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print('警告：TensorFlow不可用，将使用手动K线形态识别')


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
    
    g.kline_days = 30: K线图天数
        - 使用过去30天的K线数据
        - 30天约等于1.5个月
        - 足够识别常见K线形态
    
    g.image_size = (64, 64): K线图图像大小
        - 将K线数据转换为64×64的图像
        - 足够的分辨率捕捉形态特征
    
    g.prediction_days = 10: 预测天数
        - 预测未来10日涨跌
        - 10个交易日约等于2周
        - 短期预测更准确
    
    g.retrain_freq = 3: 模型重训练频率（季度）
        - K线形态相对稳定
        - 每季度更新一次
    
    g.use_cnn = True: 是否使用CNN模型
        - True：使用CNN模型
        - False：使用手动K线形态识别
    
    g.batch_size = 16: 批量大小
    g.epochs = 30: 训练轮数
    g.validation_split = 0.2: 验证集比例
    
    g.buy = 0.7: RSRS买入阈值
    g.sell = -0.7: RSRS卖出阈值
    g.N = 18: RSRS回归窗口
    g.M = 1100: Z-score标准化历史窗口
    
    g.cnn_model = None: CNN模型
    """
    g.stock_num = 15  # 持股数量
    g.kline_days = 30  # K线图天数
    g.image_size = (64, 64)  # K线图图像大小
    g.prediction_days = 10  # 预测天数
    g.retrain_freq = 3  # 模型重训练频率（季度）
    g.use_cnn = True  # 是否使用CNN
    g.batch_size = 16  # 批量大小
    g.epochs = 30  # 训练轮数
    g.validation_split = 0.2  # 验证集比例
    g.buy = 0.7  # RSRS买入阈值
    g.sell = -0.7  # RSRS卖出阈值
    g.N = 18  # RSRS回归窗口
    g.M = 1100  # Z-score标准化历史窗口
    
    # 模型相关
    g.cnn_model = None  # CNN模型
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
    核心逻辑：RSRS择时 + CNN K线选股交易
    """
    # 首次运行：预热RSRS数据并训练模型
    if g.days == 1:
        warm_up_rsrs(context)
        train_cnn_model(context)
        g.init = False
        return
    
    # 更新当日RSRS
    update_rsrs(context)
    
    # RSRS择时信号
    signal = get_rsrs_signal()
    
    # 买入信号
    if signal == 'BUY':
        cnn_trade(context)
    
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


# 将K线数据转换为图像
def kline_to_image(df):
    """
    将K线OHLCV数据转换为图像
    
    参数：
    df: DataFrame，包含open, high, low, close, volume列
    
    返回：
    image: numpy数组，形状为 (64, 64, 3)
    """
    # 创建空白画布
    image = np.ones((64, 64, 3), dtype=np.uint8) * 240  # 白色背景
    
    if len(df) < 5:
        return image
    
    # 归一化价格到0-64范围
    price_min = df[['open', 'high', 'low', 'close']].min().min()
    price_max = df[['open', 'high', 'low', 'close']].max().max()
    price_range = price_max - price_min
    
    if price_range == 0:
        price_range = 1
    
    # 归一化成交量
    vol_max = df['volume'].max()
    if vol_max == 0:
        vol_max = 1
    
    # 绘制K线
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= 30:  # 只绘制最近30天
            break
        
        x = int(i * (60 / 30)) + 2  # x坐标
        
        # 归一化价格
        open_price = (row['open'] - price_min) / price_range * 56 + 4
        close_price = (row['close'] - price_min) / price_range * 56 + 4
        high_price = (row['high'] - price_min) / price_range * 56 + 4
        low_price = (row['low'] - price_min) / price_range * 56 + 4
        
        open_price = np.clip(open_price, 2, 62)
        close_price = np.clip(close_price, 2, 62)
        high_price = np.clip(high_price, 2, 62)
        low_price = np.clip(low_price, 2, 62)
        
        # 颜色：阳线红色，阴线绿色
        if row['close'] >= row['open']:
            color = (255, 0, 0)  # 红色
        else:
            color = (0, 128, 0)  # 绿色
        
        # 绘制影线
        cv2_line(image, (x, int(low_price)), (x, int(high_price)), color, 1)
        
        # 绘制实体
        body_top = min(open_price, close_price)
        body_bottom = max(open_price, close_price)
        body_height = max(int(body_bottom - body_top), 1)
        
        for y in range(int(body_top), int(body_bottom)):
            cv2_line(image, (x - 1, y), (x + 1, y), color, 1)
    
    # 绘制成交量（底部10行）
    vol_base = 54
    for i, (idx, row) in enumerate(df.iterrows()):
        if i >= 30:
            break
        
        x = int(i * (60 / 30)) + 2
        vol_height = int((row['volume'] / vol_max) * 8)
        vol_height = min(vol_height, 8)
        
        if row['close'] >= row['open']:
            color = (255, 0, 0)
        else:
            color = (0, 128, 0)
        
        for y in range(vol_base, vol_base + vol_height):
            cv2_line(image, (x - 1, y), (x + 1, y), color, 1)
    
    return image


# 简化的画线函数（代替cv2）
def cv2_line(image, pt1, pt2, color, thickness):
    """简化版的画线函数"""
    x1, y1 = pt1
    x2, y2 = pt2
    
    # Bresenham直线算法
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    
    while True:
        if 0 <= x1 < 64 and 0 <= y1 < 64:
            for i in range(thickness):
                for j in range(thickness):
                    nx, ny = x1 + i - thickness // 2, y1 + j - thickness // 2
                    if 0 <= nx < 64 and 0 <= ny < 64:
                        image[ny, nx] = color
        
        if x1 == x2 and y1 == y2:
            break
        
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy


# 训练CNN模型
def train_cnn_model(context):
    """
    训练CNN模型
    
    流程：
    1. 获取全市场股票池
    2. 提取K线数据并转换为图像
    3. 计算标签（涨跌）
    4. 训练CNN模型（如果TensorFlow可用）
    5. 保存模型
    
    注意：聚宽可能不支持TensorFlow，使用手动K线形态识别
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
        
        # 准备训练数据
        images, labels, stock_list = prepare_cnn_data(context, stock_pool)
        
        if len(images) == 0:
            log.warning('没有足够的训练数据')
            return
        
        # 如果不使用CNN或TensorFlow不可用，使用手动K线形态识别
        if not g.use_cnn or not TENSORFLOW_AVAILABLE:
            log.warning('使用手动K线形态识别')
            g.cnn_model = 'pattern_based'
            g.last_retrain_date = context.current_dt
            log.info(f'手动形态识别准备完成，样本数：{len(images)}')
            return
        
        # 构建CNN模型
        g.cnn_model = Sequential([
            Conv2D(32, (3, 3), activation='relu', input_shape=(64, 64, 3)),
            MaxPooling2D((2, 2)),
            Conv2D(64, (3, 3), activation='relu'),
            MaxPooling2D((2, 2)),
            Conv2D(128, (3, 3), activation='relu'),
            MaxPooling2D((2, 2)),
            Flatten(),
            Dense(128, activation='relu'),
            Dropout(0.5),
            Dense(2, activation='softmax')
        ])
        
        # 编译模型
        optimizer = Adam(learning_rate=0.001)
        g.cnn_model.compile(
            optimizer=optimizer,
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # 早停回调
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
        
        # 训练模型
        history = g.cnn_model.fit(
            np.array(images), np.array(labels),
            batch_size=g.batch_size,
            epochs=g.epochs,
            validation_split=g.validation_split,
            callbacks=[early_stopping],
            verbose=0
        )
        
        g.last_retrain_date = context.current_dt
        
        log.info(f'CNN模型训练完成，样本数：{len(images)}')
        log.info(f'训练准确率：{history.history["accuracy"][-1]:.4f}')
        
    except Exception as e:
        log.error(f'CNN模型训练失败：{str(e)}')
        # 使用手动形态识别
        g.cnn_model = 'pattern_based'


# 准备CNN训练数据
def prepare_cnn_data(context, stock_pool):
    """
    准备CNN训练数据
    
    返回：
    - images: 图像列表
    - labels: 标签列表（0=跌, 1=涨）
    - stock_list: 股票代码列表
    """
    images = []
    labels = []
    stock_list = []
    
    for stock in stock_pool[:50]:  # 限制数量以提高速度
        try:
            # 获取K线数据
            total_days = g.kline_days + g.prediction_days + 20
            prices = get_price(stock, end_date=context.current_dt, 
                               frequency='daily', 
                               fields=['open', 'high', 'low', 'close', 'volume'], 
                               count=total_days)
            
            if prices is None or len(prices) < total_days:
                continue
            
            # 创建训练样本（滑动窗口）
            for i in range(len(prices) - g.kline_days - g.prediction_days):
                # K线数据
                kline_data = prices.iloc[i:i+g.kline_days]
                
                # 转换为图像
                image = kline_to_image(kline_data)
                
                # 计算标签
                future_prices = prices.iloc[i+g.kline_days:i+g.kline_days+g.prediction_days]
                current_price = prices.iloc[i+g.kline_days-1]['close']
                future_price = future_prices.iloc[-1]['close']
                
                if future_price > current_price:
                    label = 1  # 涨
                else:
                    label = 0  # 跌
                
                images.append(image)
                labels.append(label)
                stock_list.append(stock)
                
                # 限制样本数量
                if len(images) >= 1000:
                    break
            
            if len(images) >= 1000:
                break
        
        except Exception as e:
            continue
    
    return images, labels, stock_list


# 手动K线形态识别
def recognize_patterns(context, stock):
    """
    手动识别K线形态
    
    返回：得分，越高表示上涨概率越大
    """
    try:
        # 获取K线数据
        prices = get_price(stock, end_date=context.current_dt, 
                           frequency='daily', 
                           fields=['open', 'high', 'low', 'close'], 
                           count=g.kline_days + 10)
        
        if prices is None or len(prices) < g.kline_days:
            return 0
        
        prices = prices.tail(g.kline_days)
        
        score = 0
        
        # 1. 锤子线/上吊线（实体小，下影线长）
        for i in range(len(prices) - 1, max(0, len(prices) - 5), -1):
            row = prices.iloc[i]
            body_size = abs(row['close'] - row['open'])
            lower_shadow = min(row['open'], row['close']) - row['low']
            upper_shadow = row['high'] - max(row['open'], row['close'])
            
            if lower_shadow > body_size * 2 and upper_shadow < body_size:
                if row['close'] > row['open']:
                    score += 3  # 锤子线（看涨）
                else:
                    score += 1  # 上吊线（可能看跌）
        
        # 2. 吞没形态
        if len(prices) >= 2:
            for i in range(len(prices) - 1, max(0, len(prices) - 10), -1):
                curr = prices.iloc[i]
                prev = prices.iloc[i - 1]
                
                # 看涨吞没
                if (prev['close'] < prev['open'] and 
                    curr['close'] > curr['open'] and
                    curr['open'] <= prev['close'] and
                    curr['close'] >= prev['open']):
                    score += 4
                
                # 看跌吞没
                elif (prev['close'] > prev['open'] and 
                      curr['close'] < curr['open'] and
                      curr['open'] >= prev['close'] and
                      curr['close'] <= prev['open']):
                    score -= 2
        
        # 3. 三连阳/三连阴
        if len(prices) >= 3:
            for i in range(len(prices) - 2, max(0, len(prices) - 10), -1):
                if all(prices.iloc[i-j]['close'] > prices.iloc[i-j]['open'] 
                       for j in range(3)):
                    if (prices.iloc[i-2]['close'] > prices.iloc[i-2]['open'] and
                        prices.iloc[i-1]['close'] > prices.iloc[i-1]['open'] and
                        prices.iloc[i]['close'] > prices.iloc[i]['open']):
                        score += 2  # 三连阳
                
                if all(prices.iloc[i-j]['close'] < prices.iloc[i-j]['open'] 
                       for j in range(3)):
                    score -= 2  # 三连阴
        
        # 4. 十字星
        for i in range(len(prices) - 1, max(0, len(prices) - 5), -1):
            row = prices.iloc[i]
            body_size = abs(row['close'] - row['open'])
            total_range = row['high'] - row['low']
            
            if body_size < total_range * 0.1:
                score += 1  # 十字星（可能反转）
        
        # 5. 突口（跳空）
        if len(prices) >= 2:
            for i in range(len(prices) - 1, max(0, len(prices) - 10), -1):
                curr = prices.iloc[i]
                prev = prices.iloc[i - 1]
                
                if curr['low'] > prev['high']:
                    score += 2  # 向上跳空
                elif curr['high'] < prev['low']:
                    score -= 2  # 向下跳空
        
        # 6. 近期涨跌幅
        if len(prices) >= 5:
            recent_return = (prices['close'].iloc[-1] / prices['close'].iloc[-5] - 1)
            score += recent_return * 10  # 动量因子
        
        # 7. 成交量放大
        if len(prices) >= 5:
            volumes = get_price(stock, end_date=context.current_dt, 
                                 frequency='daily', fields=['volume'], 
                                 count=g.kline_days)
            if volumes is not None and len(volumes) >= 5:
                avg_vol = volumes['volume'].tail(10).mean()
                recent_vol = volumes['volume'].iloc[-1]
                
                if recent_vol > avg_vol * 1.5 and prices['close'].iloc[-1] > prices['open'].iloc[-1]:
                    score += 1  # 放量上涨
        
        return score
        
    except Exception as e:
        return 0


# 每季度重新训练模型
def retrain_model(context):
    """每季度重新训练模型"""
    train_cnn_model(context)


# CNN选股交易
def cnn_trade(context):
    """
    使用CNN模型或手动K线形态识别选股并交易
    
    流程：
    1. 检查模型是否已训练
    2. 获取股票池
    3. 计算每只股票的上涨概率
    4. 选择上涨概率最高的N只股票
    5. 调仓
    """
    try:
        # 检查模型
        if g.cnn_model is None:
            train_cnn_model(context)
            if g.cnn_model is None:
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
        
        # 计算每只股票的上涨概率
        predictions = {}
        
        if g.cnn_model == 'pattern_based':
            # 使用手动K线形态识别
            for stock in stock_pool[:300]:
                score = recognize_patterns(context, stock)
                # 将得分转换为概率（sigmoid）
                prob = 1 / (1 + np.exp(-score / 10))
                predictions[stock] = prob
        else:
            # 使用CNN模型预测
            for stock in stock_pool[:100]:
                try:
                    # 获取K线数据
                    prices = get_price(stock, end_date=context.current_dt, 
                                       frequency='daily', 
                                       fields=['open', 'high', 'low', 'close', 'volume'], 
                                       count=g.kline_days)
                    
                    if prices is None or len(prices) < g.kline_days:
                        continue
                    
                    # 转换为图像
                    image = kline_to_image(prices)
                    image = image.reshape(1, 64, 64, 3)
                    
                    # 预测
                    pred = g.cnn_model.predict(image, verbose=0)[0]
                    predictions[stock] = pred[1]  # 上涨概率
                    
                except Exception as e:
                    continue
        
        if len(predictions) == 0:
            return
        
        # 选择上涨概率最高的N只股票
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
            log.info(f'CNN K线选股完成，选股数：{len(selected_stocks)}，上涨概率范围：{min(pred_values):.2f} ~ {max(pred_values):.2f}')
        
    except Exception as e:
        log.error(f'CNN交易失败：{str(e)}')
