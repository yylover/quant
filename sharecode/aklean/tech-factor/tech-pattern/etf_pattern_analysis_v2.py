import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ETFPatternAnalysisV2:
    """10个ETF技术形态全面分析"""
    
    def __init__(self):
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/tech-pattern/etf_analysis_v2"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 选择10个常见的ETF
        self.etf_list = [
            {'name': '沪深300ETF', 'code': '510300'},
            {'name': '中证500ETF', 'code': '510500'},
            {'name': '创业板ETF', 'code': '159915'},
            {'name': '上证50ETF', 'code': '510050'},
            {'name': '科创板ETF', 'code': '588000'},
            {'name': '中证1000ETF', 'code': '512100'},
            {'name': '沪深500ETF', 'code': '510500'},  # 重复作为示例
            {'name': '创业板50ETF', 'code': '159949'},
            {'name': '红利ETF', 'code': '510880'},
            {'name': '证券ETF', 'code': '512880'}
        ]
    
    def get_etf_data(self, etf_code):
        """生成基于真实ETF特征的模拟数据"""
        try:
            # 生成近5年的日期序列
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5*365)
            dates = pd.date_range(start=start_date, end=end_date, freq='B')
            
            # 根据ETF代码设置不同的参数
            etf_params = {
                '510300': {'base_price': 4.0, 'volatility': 0.15, 'trend': 0.08},  # 沪深300ETF
                '510500': {'base_price': 6.0, 'volatility': 0.18, 'trend': 0.10},  # 中证500ETF
                '159915': {'base_price': 3.0, 'volatility': 0.22, 'trend': 0.12},  # 创业板ETF
                '510050': {'base_price': 3.5, 'volatility': 0.14, 'trend': 0.07},  # 上证50ETF
                '588000': {'base_price': 2.0, 'volatility': 0.25, 'trend': 0.15},  # 科创板ETF
                '512100': {'base_price': 5.0, 'volatility': 0.20, 'trend': 0.11},  # 中证1000ETF
                '159949': {'base_price': 2.5, 'volatility': 0.23, 'trend': 0.13},  # 创业板50ETF
                '510880': {'base_price': 3.2, 'volatility': 0.12, 'trend': 0.06},  # 红利ETF
                '512880': {'base_price': 4.5, 'volatility': 0.28, 'trend': 0.09}   # 证券ETF
            }
            
            params = etf_params.get(etf_code, {'base_price': 4.0, 'volatility': 0.15, 'trend': 0.08})
            
            # 生成价格数据
            np.random.seed(42)  # 设置随机种子以保证结果可复现
            
            # 生成趋势和随机波动
            daily_returns = np.random.normal(
                loc=params['trend']/252,  # 年化收益率转换为日收益率
                scale=params['volatility']/np.sqrt(252),  # 年化波动率转换为日波动率
                size=len(dates)
            )
            
            # 计算价格序列
            prices = [params['base_price']]
            for ret in daily_returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # 创建DataFrame
            data = pd.DataFrame({
                'date': dates,
                'close': prices
            })
            
            # 计算开盘价、最高价、最低价（基于收盘价加上一些随机波动）
            data['open'] = data['close'] * (1 + np.random.normal(0, 0.005, len(data)))
            data['high'] = data[['open', 'close']].max(axis=1) * (1 + np.random.normal(0, 0.008, len(data)))
            data['low'] = data[['open', 'close']].min(axis=1) * (1 - np.random.normal(0, 0.008, len(data)))
            
            # 生成成交量（与价格波动相关）
            price_change = data['close'].pct_change().abs()
            price_change = price_change.fillna(0)  # 填充第一个NaN值
            base_volume = 10000000  # 基础成交量
            data['volume'] = (base_volume * (1 + price_change * 10)).astype(int)
            
            # 设置索引
            data.set_index('date', inplace=True)
            
            # 添加一些真实的市场事件和形态
            self._add_realistic_patterns(data, etf_code)
            
            print(f"生成了 {len(data)} 条{etf_code}的模拟数据")
            return data
            
        except Exception as e:
            print(f"生成{etf_code}数据失败: {e}")
            return None
    
    def _add_realistic_patterns(self, data, etf_code):
        """添加真实的技术形态到数据中"""
        # 在特定位置添加各种技术形态
        
        # 添加头肩顶形态
        if len(data) > 100:
            start_idx = 100
            end_idx = min(180, len(data))
            
            # 创建左肩
            for i in range(start_idx, start_idx + 20):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.08
            
            # 创建头部
            for i in range(start_idx + 30, start_idx + 50):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.12
            
            # 创建右肩
            for i in range(start_idx + 60, start_idx + 80):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.07
            
            # 更新高低价
            data['high'] = data[['open', 'close']].max(axis=1) * 1.01
            data['low'] = data[['open', 'close']].min(axis=1) * 0.99
        
        # 添加双重顶形态
        if len(data) > 200:
            start_idx = 200
            end_idx = min(280, len(data))
            
            # 创建第一个顶
            for i in range(start_idx, start_idx + 15):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.09
            
            # 创建回调
            for i in range(start_idx + 20, start_idx + 35):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.95
            
            # 创建第二个顶
            for i in range(start_idx + 40, start_idx + 55):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.08
            
            # 更新高低价
            data['high'] = data[['open', 'close']].max(axis=1) * 1.01
            data['low'] = data[['open', 'close']].min(axis=1) * 0.99
        
        # 添加三角形形态
        if len(data) > 300:
            start_idx = 300
            end_idx = min(400, len(data))
            
            # 创建收敛的价格区间
            for i in range(start_idx, end_idx):
                if i < len(data):
                    volatility = 0.02 * (1 - (i - start_idx) / (end_idx - start_idx))
                    data.loc[data.index[i], 'close'] *= (1 + np.random.normal(0, volatility))
            
            # 更新高低价
            data['high'] = data[['open', 'close']].max(axis=1) * 1.01
            data['low'] = data[['open', 'close']].min(axis=1) * 0.99
        
        # 添加矩形形态
        if len(data) > 400:
            start_idx = 400
            end_idx = min(500, len(data))
            
            # 创建水平区间
            base_price = data.loc[data.index[start_idx], 'close']
            for i in range(start_idx, end_idx):
                if i < len(data):
                    data.loc[data.index[i], 'close'] = base_price * (1 + np.random.normal(0, 0.02))
            
            # 更新高低价
            data['high'] = data[['open', 'close']].max(axis=1) * 1.01
            data['low'] = data[['open', 'close']].min(axis=1) * 0.99
        
        # 添加头肩底形态
        if len(data) > 500:
            start_idx = 500
            end_idx = min(580, len(data))
            
            # 创建左肩
            for i in range(start_idx, start_idx + 20):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.92
            
            # 创建头部
            for i in range(start_idx + 30, start_idx + 50):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.88
            
            # 创建右肩
            for i in range(start_idx + 60, start_idx + 80):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.93
            
            # 更新高低价
            data['high'] = data[['open', 'close']].max(axis=1) * 1.01
            data['low'] = data[['open', 'close']].min(axis=1) * 0.99
        
        # 添加双重底形态
        if len(data) > 600:
            start_idx = 600
            end_idx = min(680, len(data))
            
            # 创建第一个底
            for i in range(start_idx, start_idx + 15):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.91
            
            # 创建反弹
            for i in range(start_idx + 20, start_idx + 35):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.05
            
            # 创建第二个底
            for i in range(start_idx + 40, start_idx + 55):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.92
            
            # 更新高低价
            data['high'] = data[['open', 'close']].max(axis=1) * 1.01
            data['low'] = data[['open', 'close']].min(axis=1) * 0.99
    
    def find_local_extrema(self, data, window=5):
        """寻找局部极值点"""
        # 寻找局部高点
        data['local_high'] = data['high'].rolling(window=window, center=True).apply(
            lambda x: x.argmax() == window//2
        )
        
        # 寻找局部低点
        data['local_low'] = data['low'].rolling(window=window, center=True).apply(
            lambda x: x.argmin() == window//2
        )
        
        return data
    
    def identify_head_shoulder_top(self, data):
        """识别头肩顶形态"""
        patterns = []
        extrema = self.find_local_extrema(data)
        
        # 寻找符合条件的高点序列
        high_points = extrema[extrema['local_high'] == 1].index
        
        for i in range(2, len(high_points)):
            # 检查是否形成头肩顶结构
            if (data.loc[high_points[i-2], 'high']< data.loc[high_points[i-1], 'high'] and
                data.loc[high_points[i], 'high'] < data.loc[high_points[i-1], 'high']):
                
                # 检查左肩和右肩高度是否接近
                if abs(data.loc[high_points[i-2], 'high'] - data.loc[high_points[i], 'high']) / \
                   data.loc[high_points[i-2], 'high'] <0.05:
                    
                    # 寻找颈线（两个回调低点）
                    mask = (extrema.index >= high_points[i-2]) & (extrema.index <= high_points[i-1])
                    neckline_points = extrema[mask & (extrema['local_low'] == 1)].index.tolist()
                    
                    if len(neckline_points) >= 2:
                        patterns.append({
                            'type': 'head_shoulder_top',
                            'start': high_points[i-2],
                            'head': high_points[i-1],
                            'end': high_points[i],
                            'neckline_points': neckline_points[:2],
                            'confidence': 0.85
                        })
        
        return patterns
    
    def identify_head_shoulder_bottom(self, data):
        """识别头肩底形态"""
        patterns = []
        extrema = self.find_local_extrema(data)
        
        # 寻找符合条件的低点序列
        low_points = extrema[extrema['local_low'] == 1].index
        
        for i in range(2, len(low_points)):
            # 检查是否形成头肩底结构
            if (data.loc[low_points[i-2], 'low'] > data.loc[low_points[i-1], 'low'] and
                data.loc[low_points[i], 'low'] > data.loc[low_points[i-1], 'low']):
                
                # 检查左肩和右肩深度是否接近
                if abs(data.loc[low_points[i-2], 'low'] - data.loc[low_points[i], 'low']) / \
                   data.loc[low_points[i-2], 'low'] < 0.05:
                    
                    # 寻找颈线（两个反弹高点）
                    mask = (extrema.index >= low_points[i-2]) & (extrema.index <= low_points[i-1])
                    neckline_points = extrema[mask & (extrema['local_high'] == 1)].index.tolist()
                    
                    if len(neckline_points) >= 2:
                        patterns.append({
                            'type': 'head_shoulder_bottom',
                            'start': low_points[i-2],
                            'head': low_points[i-1],
                            'end': low_points[i],
                            'neckline_points': neckline_points[:2],
                            'confidence': 0.85
                        })
        
        return patterns
    
    def identify_double_top(self, data):
        """识别双重顶形态"""
        patterns = []
        extrema = self.find_local_extrema(data)
        
        # 寻找符合条件的高点序列
        high_points = extrema[extrema['local_high'] == 1].index
        
        for i in range(1, len(high_points)):
            # 检查两个高点之间的距离
            if (high_points[i] - high_points[i-1]).days >= 10:
                # 检查两个高点高度是否接近
                if abs(data.loc[high_points[i], 'high'] - data.loc[high_points[i-1], 'high']) / \
                   data.loc[high_points[i-1], 'high'] <0.05:
                    
                    # 寻找颈线（回调低点）
                    mask = (extrema.index >= high_points[i-1]) & (extrema.index<= high_points[i])
                    neckline_points = extrema[mask & (extrema['local_low'] == 1)].index.tolist()
                    
                    if len(neckline_points) >= 1:
                        patterns.append({
                            'type': 'double_top',
                            'first_top': high_points[i-1],
                            'second_top': high_points[i],
                            'start': high_points[i-1],
                            'end': high_points[i],
                            'neckline_point': neckline_points[0],
                            'confidence': 0.75
                        })
        
        return patterns
    
    def identify_double_bottom(self, data):
        """识别双重底形态"""
        patterns = []
        extrema = self.find_local_extrema(data)
        
        # 寻找符合条件的低点序列
        low_points = extrema[extrema['local_low'] == 1].index
        
        for i in range(1, len(low_points)):
            # 检查两个低点之间的距离
            if (low_points[i] - low_points[i-1]).days >= 10:
                # 检查两个低点深度是否接近
                if abs(data.loc[low_points[i], 'low'] - data.loc[low_points[i-1], 'low']) / \
                   data.loc[low_points[i-1], 'low'] < 0.05:
                    
                    # 寻找颈线（反弹高点）
                    mask = (extrema.index >= low_points[i-1]) & (extrema.index <= low_points[i])
                    neckline_points = extrema[mask & (extrema['local_high'] == 1)].index.tolist()
                    
                    if len(neckline_points) >= 1:
                        patterns.append({
                            'type': 'double_bottom',
                            'first_bottom': low_points[i-1],
                            'second_bottom': low_points[i],
                            'start': low_points[i-1],
                            'end': low_points[i],
                            'neckline_point': neckline_points[0],
                            'confidence': 0.75
                        })
        
        return patterns
    
    def identify_triangle(self, data):
        """识别三角形形态"""
        patterns = []
        
        for i in range(30, len(data)):
            window_data = data.iloc[i-30:i]
            
            # 寻找高点和低点
            highs = window_data['high']
            lows = window_data['low']
            
            # 检查是否形成对称三角形
            if self._is_symmetric_triangle(highs, lows):
                patterns.append({
                    'type': 'symmetric_triangle',
                    'start': window_data.index[0],
                    'end': window_data.index[-1],
                    'confidence': 0.70
                })
            
            # 检查是否形成上升三角形
            elif self._is_ascending_triangle(highs, lows):
                patterns.append({
                    'type': 'ascending_triangle',
                    'start': window_data.index[0],
                    'end': window_data.index[-1],
                    'confidence': 0.70
                })
            
            # 检查是否形成下降三角形
            elif self._is_descending_triangle(highs, lows):
                patterns.append({
                    'type': 'descending_triangle',
                    'start': window_data.index[0],
                    'end': window_data.index[-1],
                    'confidence': 0.70
                })
        
        return patterns
    
    def _is_symmetric_triangle(self, highs, lows, tolerance=0.01):
        """判断是否形成对称三角形"""
        # 检查高点是否递减
        high_decreasing = all(highs.iloc[i] >= highs.iloc[i+1] for i in range(len(highs)-1))
        
        # 检查低点是否递增
        low_increasing = all(lows.iloc[i]<= lows.iloc[i+1] for i in range(len(lows)-1))
        
        # 检查收敛性
        price_range = highs.max() - lows.min()
        if price_range / lows.min() < tolerance:
            return False
        
        return high_decreasing and low_increasing
    
    def _is_ascending_triangle(self, highs, lows, tolerance=0.02):
        """判断是否形成上升三角形"""
        # 检查高点是否水平（波动在2%以内）
        high_range = highs.max() - highs.min()
        high_flat = high_range / highs.min()< tolerance
        
        # 检查低点是否递增
        low_increasing = all(lows.iloc[i] <= lows.iloc[i+1] for i in range(len(lows)-1))
        
        return high_flat and low_increasing
    
    def _is_descending_triangle(self, highs, lows, tolerance=0.02):
        """判断是否形成下降三角形"""
        # 检查低点是否水平（波动在2%以内）
        low_range = lows.max() - lows.min()
        low_flat = low_range / lows.min()< tolerance
        
        # 检查高点是否递减
        high_decreasing = all(highs.iloc[i] >= highs.iloc[i+1] for i in range(len(highs)-1))
        
        return low_flat and high_decreasing
    
    def identify_rectangle(self, data):
        """识别矩形形态"""
        patterns = []
        
        for i in range(30, len(data)):
            window_data = data.iloc[i-30:i]
            
            # 计算价格范围
            price_range = window_data['high'].max() - window_data['low'].min()
            price_level = window_data['low'].min()
            
            # 检查是否形成矩形（价格范围在3%以内）
            if price_range / price_level< 0.03:
                # 检查是否多次测试支撑和阻力
                resistance_tests = len(window_data[window_data['high'] >price_level * 1.015])
                support_tests = len(window_data[window_data['low']< price_level * 0.985])
                
                if resistance_tests >= 3 and support_tests >= 3:
                    patterns.append({
                        'type': 'rectangle',
                        'start': window_data.index[0],
                        'end': window_data.index[-1],
                        'resistance': window_data['high'].max(),
                        'support': window_data['low'].min(),
                        'confidence': 0.65
                    })
        
        return patterns
    
    def evaluate_pattern_effectiveness(self, data, pattern):
        """评估形态的有效性"""
        # 获取形态结束后的价格数据（最多60个交易日）
        end_idx = data.index.get_loc(pattern['end'])
        future_data = data.iloc[end_idx:end_idx+60]
        
        if len(future_data)< 10:
            return {'effective': False, 'reason': '数据不足', 'return': 0}
        
        # 根据形态类型评估有效性
        if pattern['type'] in ['head_shoulder_top', 'double_top']:
            # 看跌形态，预期价格下跌
            if 'neckline_points' in pattern:
                neckline_price = data.loc[pattern['neckline_points'][0], 'low']
            elif 'neckline_point' in pattern:
                neckline_price = data.loc[pattern['neckline_point'], 'low']
            else:
                neckline_price = data.loc[pattern['end'], 'close']
            
            # 计算最大跌幅
            max_drawdown = (neckline_price - future_data['low'].min()) / neckline_price
            
            # 检查是否跌破颈线且下跌幅度足够
            if future_data['low'].min()< neckline_price * 0.95 and max_drawdown >0.05:
                return {'effective': True, 'drawdown': max_drawdown, 'return': -max_drawdown}
            else:
                return {'effective': False, 'reason': '下跌幅度不足', 'return': -max_drawdown}
        
        elif pattern['type'] in ['head_shoulder_bottom', 'double_bottom']:
            # 看涨形态，预期价格上涨
            if 'neckline_points' in pattern:
                neckline_price = data.loc[pattern['neckline_points'][0], 'high']
            elif 'neckline_point' in pattern:
                neckline_price = data.loc[pattern['neckline_point'], 'high']
            else:
                neckline_price = data.loc[pattern['end'], 'close']
            
            # 计算最大涨幅
            max_rally = (future_data['high'].max() - neckline_price) / neckline_price
            
            # 检查是否突破颈线且上涨幅度足够
            if future_data['high'].max() > neckline_price * 1.05 and max_rally > 0.05:
                return {'effective': True, 'rally': max_rally, 'return': max_rally}
            else:
                return {'effective': False, 'reason': '上涨幅度不足', 'return': max_rally}
        
        elif pattern['type'] in ['symmetric_triangle', 'ascending_triangle', 'descending_triangle']:
            # 三角形形态，需要看突破方向
            pattern_high = data.loc[pattern['start']:pattern['end'], 'high'].max()
            pattern_low = data.loc[pattern['start']:pattern['end'], 'low'].min()
            pattern_width = pattern_high - pattern_low
            
            # 检查向上突破
            if future_data['high'].max() > pattern_high * 1.03:
                max_rally = (future_data['high'].max() - pattern_high) / pattern_high
                if max_rally > pattern_width / pattern_high * 0.5:
                    return {'effective': True, 'rally': max_rally, 'return': max_rally}
                else:
                    return {'effective': False, 'reason': '上涨幅度不足', 'return': max_rally}
            
            # 检查向下突破
            elif future_data['low'].min()< pattern_low * 0.97:
                max_drawdown = (pattern_low - future_data['low'].min()) / pattern_low
                if max_drawdown > pattern_width / pattern_low * 0.5:
                    return {'effective': True, 'drawdown': max_drawdown, 'return': -max_drawdown}
                else:
                    return {'effective': False, 'reason': '下跌幅度不足', 'return': -max_drawdown}
            else:
                return {'effective': False, 'reason': '未突破', 'return': 0}
        
        elif pattern['type'] == 'rectangle':
            # 矩形形态，需要看突破方向
            resistance = pattern['resistance']
            support = pattern['support']
            range_width = resistance - support
            
            # 检查向上突破
            if future_data['high'].max() > resistance * 1.03:
                max_rally = (future_data['high'].max() - resistance) / resistance
                if max_rally > range_width / resistance * 0.5:
                    return {'effective': True, 'rally': max_rally, 'return': max_rally}
                else:
                    return {'effective': False, 'reason': '上涨幅度不足', 'return': max_rally}
            
            # 检查向下突破
            elif future_data['low'].min()< support * 0.97:
                max_drawdown = (support - future_data['low'].min()) / support
                if max_drawdown > range_width / support * 0.5:
                    return {'effective': True, 'drawdown': max_drawdown, 'return': -max_drawdown}
                else:
                    return {'effective': False, 'reason': '下跌幅度不足', 'return': -max_drawdown}
            else:
                return {'effective': False, 'reason': '未突破', 'return': 0}
        
        return {'effective': False, 'reason': '未知形态类型', 'return': 0}
    
    def run_analysis(self):
        """运行完整分析"""
        all_results = []
        pattern_details = []
        
        for etf in self.etf_list:
            print(f"\n=== 开始分析 {etf['name']} ({etf['code']}) ===")
            
            # 获取数据
            data = self.get_etf_data(etf['code'])
            if data is None:
                continue
            
            print(f"获取到 {len(data)} 条数据")
            
            # 识别各种形态
            patterns = []
            patterns.extend(self.identify_head_shoulder_top(data))
            patterns.extend(self.identify_head_shoulder_bottom(data))
            patterns.extend(self.identify_double_top(data))
            patterns.extend(self.identify_double_bottom(data))
            patterns.extend(self.identify_triangle(data))
            patterns.extend(self.identify_rectangle(data))
            
            print(f"识别到 {len(patterns)} 个技术形态")
            
            # 评估形态有效性
            effective_count = 0
            total_return = 0
            
            for pattern in patterns:
                result = self.evaluate_pattern_effectiveness(data, pattern)
                
                # 记录详细信息
                pattern_details.append({
                    'etf_name': etf['name'],
                    'etf_code': etf['code'],
                    'pattern_type': pattern['type'],
                    'start_date': pattern['start'],
                    'end_date': pattern['end'],
                    'confidence': pattern['confidence'],
                    'effective': result['effective'],
                    'return': result['return']
                })
                
                if result['effective']:
                    effective_count += 1
                total_return += result['return']
            
            # 计算平均收益率
            avg_return = total_return / len(patterns) if patterns else 0
            
            # 保存结果
            etf_result = {
                'etf_name': etf['name'],
                'etf_code': etf['code'],
                'total_patterns': len(patterns),
                'effective_patterns': effective_count,
                'failed_patterns': len(patterns) - effective_count,
                'success_rate': effective_count / len(patterns) if patterns else 0,
                'avg_return': avg_return
            }
            
            all_results.append(etf_result)
        
        # 保存汇总结果
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(f"{self.output_dir}/etf_pattern_analysis_summary.csv", index=False)
        
        # 保存详细结果
        details_df = pd.DataFrame(pattern_details)
        details_df.to_csv(f"{self.output_dir}/etf_pattern_details.csv", index=False)
        
        return results_df, details_df

if __name__ == "__main__":
    analysis = ETFPatternAnalysisV2()
    summary_results, detailed_results = analysis.run_analysis()
    
    print("\n=== ETF技术形态分析汇总 ===")
    print(summary_results)
    
    print("\n=== 各形态类型统计 ===")
    pattern_stats = detailed_results.groupby('pattern_type').agg({
        'effective': ['count', 'sum', 'mean'],
        'return': ['mean', 'std']
    })
    print(pattern_stats)
