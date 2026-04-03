import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ETFPatternPlot:
    """ETF技术形态可视化"""
    
    def __init__(self):
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/tech-pattern/etf_analysis_v2/plots"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 10个ETF列表
        self.etf_list = [
            {'name': '沪深300ETF', 'code': '510300'},
            {'name': '中证500ETF', 'code': '510500'},
            {'name': '创业板ETF', 'code': '159915'},
            {'name': '上证50ETF', 'code': '510050'},
            {'name': '科创板ETF', 'code': '588000'},
            {'name': '中证1000ETF', 'code': '512100'},
            {'name': '创业板50ETF', 'code': '159949'},
            {'name': '红利ETF', 'code': '510880'},
            {'name': '证券ETF', 'code': '512880'}
        ]
    
    def get_etf_data(self, etf_code):
        """生成ETF数据"""
        try:
            # 生成近5年的日期序列
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5*365)
            dates = pd.date_range(start=start_date, end=end_date, freq='B')
            
            # 根据ETF代码设置不同的参数
            etf_params = {
                '510300': {'base_price': 4.0, 'volatility': 0.15, 'trend': 0.08},
                '510500': {'base_price': 6.0, 'volatility': 0.18, 'trend': 0.10},
                '159915': {'base_price': 3.0, 'volatility': 0.22, 'trend': 0.12},
                '510050': {'base_price': 3.5, 'volatility': 0.14, 'trend': 0.07},
                '588000': {'base_price': 2.0, 'volatility': 0.25, 'trend': 0.15},
                '512100': {'base_price': 5.0, 'volatility': 0.20, 'trend': 0.11},
                '159949': {'base_price': 2.5, 'volatility': 0.23, 'trend': 0.13},
                '510880': {'base_price': 3.2, 'volatility': 0.12, 'trend': 0.06},
                '512880': {'base_price': 4.5, 'volatility': 0.28, 'trend': 0.09}
            }
            
            params = etf_params.get(etf_code, {'base_price': 4.0, 'volatility': 0.15, 'trend': 0.08})
            
            # 生成价格数据
            np.random.seed(42)
            
            daily_returns = np.random.normal(
                loc=params['trend']/252,
                scale=params['volatility']/np.sqrt(252),
                size=len(dates)
            )
            
            prices = [params['base_price']]
            for ret in daily_returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = pd.DataFrame({
                'date': dates,
                'close': prices
            })
            
            data['open'] = data['close'] * (1 + np.random.normal(0, 0.005, len(data)))
            data['high'] = data[['open', 'close']].max(axis=1) * (1 + np.random.normal(0, 0.008, len(data)))
            data['low'] = data[['open', 'close']].min(axis=1) * (1 - np.random.normal(0, 0.008, len(data)))
            
            price_change = data['close'].pct_change().abs()
            price_change = price_change.fillna(0)
            base_volume = 10000000
            data['volume'] = (base_volume * (1 + price_change * 10)).astype(int)
            
            data.set_index('date', inplace=True)
            
            # 添加技术形态
            self._add_realistic_patterns(data, etf_code)
            
            return data
            
        except Exception as e:
            print(f"生成{etf_code}数据失败: {e}")
            return None
    
    def _add_realistic_patterns(self, data, etf_code):
        """添加技术形态"""
        # 添加各种技术形态
        if len(data) > 100:
            # 头肩顶
            start_idx = 100
            for i in range(start_idx, start_idx + 20):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.08
            for i in range(start_idx + 30, start_idx + 50):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.12
            for i in range(start_idx + 60, start_idx + 80):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.93
            
            # 双重顶
            start_idx = 200
            for i in range(start_idx, start_idx + 15):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.09
            for i in range(start_idx + 20, start_idx + 35):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.95
            for i in range(start_idx + 40, start_idx + 55):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.08
            
            # 头肩底
            start_idx = 350
            for i in range(start_idx, start_idx + 20):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.92
            for i in range(start_idx + 30, start_idx + 50):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.88
            for i in range(start_idx + 60, start_idx + 80):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.07
            
            # 双重底
            start_idx = 500
            for i in range(start_idx, start_idx + 15):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.91
            for i in range(start_idx + 20, start_idx + 35):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 1.05
            for i in range(start_idx + 40, start_idx + 55):
                if i < len(data):
                    data.loc[data.index[i], 'close'] *= 0.92
            
            # 更新高低价
            data['high'] = data[['open', 'close']].max(axis=1) * 1.01
            data['low'] = data[['open', 'close']].min(axis=1) * 0.99
    
    def find_local_extrema(self, data, window=5):
        """寻找局部极值点"""
        data['local_high'] = data['high'].rolling(window=window, center=True).apply(
            lambda x: x.argmax() == window//2
        )
        data['local_low'] = data['low'].rolling(window=window, center=True).apply(
            lambda x: x.argmin() == window//2
        )
        return data
    
    def identify_patterns(self, data):
        """识别技术形态"""
        patterns = []
        extrema = self.find_local_extrema(data)
        
        # 识别头肩顶
        high_points = extrema[extrema['local_high'] == 1].index
        for i in range(2, len(high_points)):
            if (data.loc[high_points[i-2], 'high']< data.loc[high_points[i-1], 'high'] and
                data.loc[high_points[i], 'high'] < data.loc[high_points[i-1], 'high']):
                if abs(data.loc[high_points[i-2], 'high'] - data.loc[high_points[i], 'high']) / \
                   data.loc[high_points[i-2], 'high'] <0.05:
                    mask = (extrema.index >= high_points[i-2]) & (extrema.index <= high_points[i-1])
                    neckline_points = extrema[mask & (extrema['local_low'] == 1)].index.tolist()
                    if len(neckline_points) >= 2:
                        patterns.append({
                            'type': 'head_shoulder_top',
                            'start': high_points[i-2],
                            'head': high_points[i-1],
                            'end': high_points[i],
                            'neckline_points': neckline_points[:2],
                            'color': 'red',
                            'label': '头肩顶'
                        })
        
        # 识别头肩底
        low_points = extrema[extrema['local_low'] == 1].index
        for i in range(2, len(low_points)):
            if (data.loc[low_points[i-2], 'low'] > data.loc[low_points[i-1], 'low'] and
                data.loc[low_points[i], 'low'] > data.loc[low_points[i-1], 'low']):
                if abs(data.loc[low_points[i-2], 'low'] - data.loc[low_points[i], 'low']) / \
                   data.loc[low_points[i-2], 'low'] < 0.05:
                    mask = (extrema.index >= low_points[i-2]) & (extrema.index <= low_points[i-1])
                    neckline_points = extrema[mask & (extrema['local_high'] == 1)].index.tolist()
                    if len(neckline_points) >= 2:
                        patterns.append({
                            'type': 'head_shoulder_bottom',
                            'start': low_points[i-2],
                            'head': low_points[i-1],
                            'end': low_points[i],
                            'neckline_points': neckline_points[:2],
                            'color': 'green',
                            'label': '头肩底'
                        })
        
        # 识别双重顶
        for i in range(1, len(high_points)):
            if (high_points[i] - high_points[i-1]).days >= 10:
                if abs(data.loc[high_points[i], 'high'] - data.loc[high_points[i-1], 'high']) / \
                   data.loc[high_points[i-1], 'high'] <0.05:
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
                            'color': 'orange',
                            'label': '双重顶'
                        })
        
        # 识别双重底
        for i in range(1, len(low_points)):
            if (low_points[i] - low_points[i-1]).days >= 10:
                if abs(data.loc[low_points[i], 'low'] - data.loc[low_points[i-1], 'low']) / \
                   data.loc[low_points[i-1], 'low'] < 0.05:
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
                            'color': 'blue',
                            'label': '双重底'
                        })
        
        return patterns
    
    def plot_etf_patterns(self, etf_name, etf_code):
        """绘制ETF技术形态图表"""
        print(f"正在绘制 {etf_name} ({etf_code}) 的技术形态图...")
        
        # 获取数据
        data = self.get_etf_data(etf_code)
        if data is None:
            return
        
        # 识别形态
        patterns = self.identify_patterns(data)
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1]})
        
        # 绘制价格走势
        ax1.plot(data.index, data['close'], label='收盘价', color='black', linewidth=2)
        ax1.plot(data.index, data['open'], label='开盘价', color='gray', alpha=0.5)
        ax1.fill_between(data.index, data['low'], data['high'], color='lightgray', alpha=0.3)
        
        # 标注技术形态
        for pattern in patterns:
            # 绘制形态区间
            ax1.axvspan(pattern['start'], pattern['end'], alpha=0.2, color=pattern['color'])
            
            # 标注形态名称
            mid_date = pattern['start'] + (pattern['end'] - pattern['start']) / 2
            # 找到最接近的日期
            closest_date = data.index.get_indexer([mid_date], method='nearest')[0]
            price_level = data.iloc[closest_date]['close'] * 1.05
            ax1.text(data.index[closest_date], price_level, pattern['label'], fontsize=10, 
                    ha='center', va='bottom', color=pattern['color'],
                    bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
            
            # 绘制颈线
            if 'neckline_points' in pattern:
                neckline_prices = [data.loc[point, 'low'] if 'top' in pattern['type'] else 
                                data.loc[point, 'high'] for point in pattern['neckline_points']]
                neckline_dates = pattern['neckline_points']
                ax1.plot(neckline_dates, neckline_prices, color=pattern['color'], linestyle='--', linewidth=2)
            
            elif 'neckline_point' in pattern:
                neckline_price = data.loc[pattern['neckline_point'], 'low'] if 'top' in pattern['type'] else \
                                data.loc[pattern['neckline_point'], 'high']
                ax1.axhline(y=neckline_price, xmin=data.index.get_loc(pattern['start'])/len(data),
                          xmax=data.index.get_loc(pattern['end'])/len(data),
                          color=pattern['color'], linestyle='--', linewidth=2)
        
        # 绘制成交量
        ax2.bar(data.index, data['volume'], color='blue', alpha=0.5)
        ax2.set_ylabel('成交量')
        ax2.set_xlabel('日期')
        
        # 设置图表属性
        ax1.set_title(f'{etf_name} ({etf_code}) 技术形态分析', fontsize=16, fontweight='bold')
        ax1.set_ylabel('价格')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax2.grid(True, alpha=0.3)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        plt.savefig(f"{self.output_dir}/{etf_name}_patterns.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"图表已保存：{etf_name}_patterns.png")
    
    def plot_summary_chart(self):
        """绘制汇总图表"""
        print("正在绘制汇总图表...")
        
        # 读取汇总数据
        summary_file = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/tech-pattern/etf_analysis_v2/etf_pattern_analysis_summary.csv"
        
        if os.path.exists(summary_file):
            summary_data = pd.read_csv(summary_file)
            
            # 创建子图
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. 成功率对比
            ax1.bar(range(len(summary_data)), summary_data['success_rate'] * 100, 
                   color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                         '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE'])
            ax1.set_xticks(range(len(summary_data)))
            ax1.set_xticklabels(summary_data['etf_name'], rotation=45, ha='right')
            ax1.set_ylabel('成功率 (%)')
            ax1.set_title('各ETF技术形态成功率对比')
            ax1.grid(axis='y', alpha=0.3)
            
            # 2. 平均收益率对比
            ax2.bar(range(len(summary_data)), summary_data['avg_return'] * 100,
                   color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                         '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE'])
            ax2.set_xticks(range(len(summary_data)))
            ax2.set_xticklabels(summary_data['etf_name'], rotation=45, ha='right')
            ax2.set_ylabel('平均收益率 (%)')
            ax2.set_title('各ETF技术形态平均收益率对比')
            ax2.grid(axis='y', alpha=0.3)
            
            # 3. 形态数量统计
            ax3.bar(range(len(summary_data)), summary_data['total_patterns'],
                   color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                         '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE'])
            ax3.set_xticks(range(len(summary_data)))
            ax3.set_xticklabels(summary_data['etf_name'], rotation=45, ha='right')
            ax3.set_ylabel('识别形态数量')
            ax3.set_title('各ETF识别的技术形态数量')
            ax3.grid(axis='y', alpha=0.3)
            
            # 4. 有效形态数量
            ax4.bar(range(len(summary_data)), summary_data['effective_patterns'],
                   color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                         '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE'])
            ax4.set_xticks(range(len(summary_data)))
            ax4.set_xticklabels(summary_data['etf_name'], rotation=45, ha='right')
            ax4.set_ylabel('有效形态数量')
            ax4.set_title('各ETF有效技术形态数量')
            ax4.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/summary_chart.png", dpi=300, bbox_inches='tight')
            plt.close()
            
            print("汇总图表已保存：summary_chart.png")
    
    def run(self):
        """运行所有绘图"""
        # 为每个ETF绘制图表
        for etf in self.etf_list:
            self.plot_etf_patterns(etf['name'], etf['code'])
        
        # 绘制汇总图表
        self.plot_summary_chart()
        
        print("\n所有图表绘制完成！")

if __name__ == "__main__":
    plotter = ETFPatternPlot()
    plotter.run()
