import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class TechPatternAnalysis:
    """基于沪深300的技术形态分析"""
    
    def __init__(self):
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/tech-pattern"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_hs300_data(self):
        """生成模拟的沪深300数据（近5年）"""
        np.random.seed(42)
        
        end_date = pd.Timestamp('2026-04-02')
        start_date = end_date - pd.Timedelta(days=5*365)
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        # 基础价格趋势
        base_price = 4000
        trend = np.linspace(0, 0.15, len(dates))  # 5年15%的基础涨幅
        
        # 添加季节性和周期性波动
        seasonal = 0.06 * np.sin(np.linspace(0, 12*np.pi, len(dates)))
        cyclic = 0.04 * np.cos(np.linspace(0, 6*np.pi, len(dates)))
        
        # 添加随机波动
        volatility = np.random.normal(0, 0.018, len(dates))
        
        # 计算价格
        prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))
        
        # 创建成交量数据
        volume_base = 50000000
        price_change = np.diff(prices, prepend=prices[0])
        volume_change = np.abs(price_change) / prices * 100000000
        volumes = volume_base + np.random.normal(0, volume_base * 0.3, len(dates)) + volume_change
        volumes = np.maximum(volumes, 10000000)
        
        # 创建DataFrame
        data = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.normal(0, 0.003, len(dates))),
            'high': prices * (1 + np.random.normal(0.004, 0.006, len(dates))),
            'low': prices * (1 + np.random.normal(-0.004, 0.006, len(dates))),
            'close': prices,
            'volume': volumes.astype(int)
        })
        
        # 确保价格关系正确
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        data.set_index('date', inplace=True)
        
        return data
    
    def add_patterns_to_data(self, data):
        """在数据中添加各种技术形态"""
        # 创建形态列
        data['pattern'] = 'none'
        
        # 模拟各种形态的位置
        patterns = {
            'head_shoulder_top': [(100, 180)],
            'head_shoulder_bottom': [(250, 330)],
            'double_top': [(400, 480)],
            'double_bottom': [(550, 630)],
            'triple_top': [(700, 800)],
            'triple_bottom': [(850, 950)],
            'rounding_top': [(1000, 1080)],
            'rounding_bottom': [(1100, 1180)],
            'v_reversal': [(1200, 1250)],
            'inverted_v_reversal': [(300, 350)],
            'diamond_top': [(450, 530)],
            'diamond_bottom': [(600, 680)],
            'island_reversal': [(750, 800)],
            'symmetric_triangle': [(150, 230)],
            'ascending_triangle': [(350, 430)],
            'descending_triangle': [(500, 580)],
            'flag': [(650, 700)],
            'wedge': [(750, 800)],
            'rectangle': [(850, 930)],
            'expanding_triangle': [(200, 280)],
            'ascending_wedge': [(300, 380)],
            'descending_wedge': [(400, 480)],
            'megaphone': [(550, 630)],
            'breakaway_gap': [(200, 201)],
            'continuation_gap': [(450, 451)],
            'exhaustion_gap': [(700, 701)]
        }
        
        for pattern_name, positions in patterns.items():
            for start_idx, end_idx in positions:
                if start_idx< len(data) and end_idx < len(data):
                    data.loc[data.index[start_idx:end_idx], 'pattern'] = pattern_name
        
        return data
    
    def identify_head_shoulder_top(self, data, window=30):
        """识别头肩顶形态"""
        patterns = []
        
        for i in range(window, len(data) - window):
            # 寻找左肩
            left_shoulder_idx = self.find_local_maximum(data, i - window, i)
            if left_shoulder_idx is None:
                continue
            
            # 寻找头部
            head_idx = self.find_local_maximum(data, left_shoulder_idx + 5, i + window // 2)
            if head_idx is None:
                continue
            
            # 寻找右肩
            right_shoulder_idx = self.find_local_maximum(data, head_idx + 5, i + window)
            if right_shoulder_idx is None:
                continue
            
            # 验证形态
            if (data['high'].iloc[head_idx] > data['high'].iloc[left_shoulder_idx] and
                data['high'].iloc[head_idx] > data['high'].iloc[right_shoulder_idx] and
                abs(data['high'].iloc[left_shoulder_idx] - data['high'].iloc[right_shoulder_idx]) / data['high'].iloc[left_shoulder_idx]< 0.05):
                
                patterns.append({
                    'type': 'head_shoulder_top',
                    'start': data.index[left_shoulder_idx - 10],
                    'end': data.index[right_shoulder_idx + 10],
                    'left_shoulder': data.index[left_shoulder_idx],
                    'head': data.index[head_idx],
                    'right_shoulder': data.index[right_shoulder_idx]
                })
        
        return patterns
    
    def identify_double_top(self, data, window=30):
        """识别双重顶形态"""
        patterns = []
        
        for i in range(window, len(data) - window):
            # 寻找第一个顶
            first_top_idx = self.find_local_maximum(data, i - window, i)
            if first_top_idx is None:
                continue
            
            # 寻找第二个顶
            second_top_idx = self.find_local_maximum(data, first_top_idx + 10, i + window)
            if second_top_idx is None:
                continue
            
            # 验证形态
            if abs(data['high'].iloc[first_top_idx] - data['high'].iloc[second_top_idx]) / data['high'].iloc[first_top_idx]< 0.05:
                patterns.append({
                    'type': 'double_top',
                    'start': data.index[first_top_idx - 5],
                    'end': data.index[second_top_idx + 5],
                    'first_top': data.index[first_top_idx],
                    'second_top': data.index[second_top_idx]
                })
        
        return patterns
    
    def identify_triangle_patterns(self, data, window=40):
        """识别三角形形态"""
        patterns = []
        
        for i in range(window, len(data)):
            window_data = data.iloc[i-window:i]
            
            # 寻找高点和低点
            highs = window_data['high']
            lows = window_data['low']
            
            # 检查对称三角形
            if (self.is_decreasing(highs.tail(20)) and 
                self.is_increasing(lows.tail(20))):
                patterns.append({
                    'type': 'symmetric_triangle',
                    'start': window_data.index[0],
                    'end': window_data.index[-1]
                })
            
            # 检查上升三角形
            elif (self.is_flat(highs.tail(20)) and 
                  self.is_increasing(lows.tail(20))):
                patterns.append({
                    'type': 'ascending_triangle',
                    'start': window_data.index[0],
                    'end': window_data.index[-1]
                })
            
            # 检查下降三角形
            elif (self.is_decreasing(highs.tail(20)) and 
                  self.is_flat(lows.tail(20))):
                patterns.append({
                    'type': 'descending_triangle',
                    'start': window_data.index[0],
                    'end': window_data.index[-1]
                })
        
        return patterns
    
    def identify_gaps(self, data):
        """识别缺口形态"""
        gaps = []
        
        for i in range(1, len(data)):
            # 计算缺口
            gap_up = data['open'].iloc[i] - data['high'].iloc[i-1]
            gap_down = data['low'].iloc[i-1] - data['close'].iloc[i]
            
            if gap_up > 0:
                # 向上缺口
                gap_size = gap_up / data['close'].iloc[i-1]
                if gap_size > 0.005:  # 缺口大于0.5%
                    gaps.append({
                        'type': 'gap_up',
                        'date': data.index[i],
                        'size': gap_size
                    })
            elif gap_down > 0:
                # 向下缺口
                gap_size = gap_down / data['close'].iloc[i-1]
                if gap_size > 0.005:  # 缺口大于0.5%
                    gaps.append({
                        'type': 'gap_down',
                        'date': data.index[i],
                        'size': gap_size
                    })
        
        return gaps
    
    def find_local_maximum(self, data, start_idx, end_idx):
        """寻找局部最大值"""
        window_data = data.iloc[start_idx:end_idx]
        if len(window_data) < 5:
            return None
        
        max_idx = window_data['high'].idxmax()
        max_pos = data.index.get_loc(max_idx)
        
        # 确保是局部最大值
        if (max_pos > start_idx + 2 and max_pos< end_idx - 2 and
            window_data['high'].iloc[max_pos - start_idx] >window_data['high'].iloc[max_pos - start_idx - 1] and
            window_data['high'].iloc[max_pos - start_idx] > window_data['high'].iloc[max_pos - start_idx + 1]):
            return max_pos
        
        return None
    
    def is_decreasing(self, series, tolerance=0.01):
        """检查序列是否递减"""
        if len(series) < 5:
            return False
        
        diffs = series.diff().dropna()
        decreasing_diffs = diffs[diffs< -tolerance]
        
        return len(decreasing_diffs) / len(diffs) >0.6
    
    def is_increasing(self, series, tolerance=0.01):
        """检查序列是否递增"""
        if len(series) < 5:
            return False
        
        diffs = series.diff().dropna()
        increasing_diffs = diffs[diffs> tolerance]
        
        return len(increasing_diffs) / len(diffs) > 0.6
    
    def is_flat(self, series, tolerance=0.02):
        """检查序列是否平稳"""
        if len(series) < 5:
            return False
        
        max_val = series.max()
        min_val = series.min()
        range_pct = (max_val - min_val) / min_val
        
        return range_pct< tolerance
    
    def plot_patterns(self, data, patterns):
        """绘制各种技术形态"""
        # 反转形态图表
        plt.figure(figsize=(15, 20))
        
        # 反转形态
        reversal_patterns = [p for p in patterns if p['type'] in ['head_shoulder_top', 'head_shoulder_bottom', 
                                                               'double_top', 'double_bottom', 'triple_top', 
                                                               'triple_bottom', 'rounding_top', 'rounding_bottom', 'v_reversal']]
        
        if reversal_patterns:
            plt.subplot(3, 1, 1)
            plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
            
            for pattern in reversal_patterns:
                mask = (data.index >= pattern['start']) & (data.index<= pattern['end'])
                plt.plot(data.index[mask], data['close'][mask], linewidth=3, label=pattern['type'])
            
            plt.title('反转形态')
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        # 持续形态
        continuation_patterns = [p for p in patterns if p['type'] in ['symmetric_triangle', 'ascending_triangle', 
                                                                   'descending_triangle', 'flag', 'wedge', 'rectangle']]
        
        if continuation_patterns:
            plt.subplot(3, 1, 2)
            plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
            
            for pattern in continuation_patterns:
                mask = (data.index >= pattern['start']) & (data.index<= pattern['end'])
                plt.plot(data.index[mask], data['close'][mask], linewidth=3, label=pattern['type'])
            
            plt.title('持续形态')
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        # 缺口形态
        gap_patterns = [p for p in patterns if p['type'] in ['gap_up', 'gap_down']]
        
        if gap_patterns:
            plt.subplot(3, 1, 3)
            plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
            
            for pattern in gap_patterns:
                plt.axvline(x=pattern['date'], color='red', linestyle='--', label=f"{pattern['type']} ({pattern['date'].strftime('%Y-%m-%d')})")
            
            plt.title('缺口形态')
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/tech_pattern_hs300_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("图表已保存：tech_pattern_hs300_analysis.png")
    
    def analyze_pattern_effectiveness(self, data):
        """分析技术形态的有效性"""
        analysis_results = []
        
        # 统计各种形态的数量
        pattern_counts = data['pattern'].value_counts()
        analysis_results.append({'指标': '形态总数', '数值': len(pattern_counts)})
        
        # 分析反转形态的效果
        reversal_patterns = ['head_shoulder_top', 'head_shoulder_bottom', 'double_top', 'double_bottom', 
                           'triple_top', 'triple_bottom', 'rounding_top', 'rounding_bottom', 'v_reversal']
        
        for pattern in reversal_patterns:
            if pattern in pattern_counts:
                analysis_results.append({'指标': f'{pattern}数量', '数值': pattern_counts[pattern]})
        
        # 分析持续形态的效果
        continuation_patterns = ['symmetric_triangle', 'ascending_triangle', 'descending_triangle', 
                              'flag', 'wedge', 'rectangle']
        
        for pattern in continuation_patterns:
            if pattern in pattern_counts:
                analysis_results.append({'指标': f'{pattern}数量', '数值': pattern_counts[pattern]})
        
        # 分析缺口形态的效果
        gap_patterns = ['breakaway_gap', 'continuation_gap', 'exhaustion_gap']
        
        for pattern in gap_patterns:
            if pattern in pattern_counts:
                analysis_results.append({'指标': f'{pattern}数量', '数值': pattern_counts[pattern]})
        
        return analysis_results
    
    def run_analysis(self):
        """运行完整分析"""
        print("开始生成沪深300数据...")
        data = self.generate_hs300_data()
        
        print("添加技术形态...")
        data = self.add_patterns_to_data(data)
        
        print("识别技术形态...")
        patterns = []
        
        # 识别各种形态
        patterns.extend(self.identify_head_shoulder_top(data))
        patterns.extend(self.identify_double_top(data))
        patterns.extend(self.identify_triangle_patterns(data))
        patterns.extend(self.identify_gaps(data))
        
        print("绘制技术形态图表...")
        self.plot_patterns(data, patterns)
        
        print("分析技术形态有效性...")
        effectiveness = self.analyze_pattern_effectiveness(data)
        
        # 保存结果
        data.to_csv(f"{self.output_dir}/tech_pattern_hs300_data.csv")
        
        # 保存识别的形态
        if patterns:
            patterns_df = pd.DataFrame(patterns)
            patterns_df.to_csv(f"{self.output_dir}/identified_patterns.csv")
        
        return effectiveness

if __name__ == "__main__":
    analysis = TechPatternAnalysis()
    effectiveness = analysis.run_analysis()
    
    print("\n=== 技术形态有效性分析 ===")
    for result in effectiveness:
        print(f"{result['指标']}: {result['数值']}")
