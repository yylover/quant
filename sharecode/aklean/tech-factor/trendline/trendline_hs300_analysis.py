import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class TrendlineAnalysis:
    """基于沪深300的趋势线分析"""
    
    def __init__(self):
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/trendline"
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
    
    def calculate_trendline(self, data, method='linear'):
        """计算趋势线"""
        # 创建日期索引的数值表示
        x = np.arange(len(data))
        
        if method == 'linear':
            # 线性趋势线（手动实现线性回归）
            n = len(x)
            mean_x = np.mean(x)
            mean_y = np.mean(data['close'])
            
            numerator = np.sum((x - mean_x) * (data['close'] - mean_y))
            denominator = np.sum((x - mean_x) ** 2)
            
            slope = numerator / denominator
            intercept = mean_y - slope * mean_x
            data['trendline'] = intercept + slope * x
            
        elif method == 'high_low':
            # 基于高低点的趋势线
            # 寻找上升趋势线（连接低点）
            low_points = []
            for i in range(1, len(data)-1):
                if data['low'].iloc[i]< data['low'].iloc[i-1] and data['low'].iloc[i]< data['low'].iloc[i+1]:
                    low_points.append(i)
            
            if len(low_points) >= 2:
                # 取第一个和最后一个低点
                start_idx = low_points[0]
                end_idx = low_points[-1]
                
                # 计算上升趋势线
                rise = data['low'].iloc[end_idx] - data['low'].iloc[start_idx]
                run = end_idx - start_idx
                slope = rise / run
                intercept = data['low'].iloc[start_idx] - slope * start_idx
                data['uptrend_line'] = intercept + slope * x
            
            # 寻找下降趋势线（连接高点）
            high_points = []
            for i in range(1, len(data)-1):
                if data['high'].iloc[i] > data['high'].iloc[i-1] and data['high'].iloc[i] > data['high'].iloc[i+1]:
                    high_points.append(i)
            
            if len(high_points) >= 2:
                # 取第一个和最后一个高点
                start_idx = high_points[0]
                end_idx = high_points[-1]
                
                # 计算下降趋势线
                rise = data['high'].iloc[end_idx] - data['high'].iloc[start_idx]
                run = end_idx - start_idx
                slope = rise / run
                intercept = data['high'].iloc[start_idx] - slope * start_idx
                data['downtrend_line'] = intercept + slope * x
        
        return data
    
    def calculate_channel_lines(self, data):
        """计算通道线"""
        x = np.arange(len(data))
        
        # 如果已经有上升趋势线，计算通道上轨
        if 'uptrend_line' in data.columns:
            # 计算价格与上升趋势线的距离
            distance = data['high'] - data['uptrend_line']
            avg_distance = distance.mean()
            
            # 创建通道上轨
            data['channel_upper'] = data['uptrend_line'] + avg_distance
        
        # 如果已经有下降趋势线，计算通道下轨
        if 'downtrend_line' in data.columns:
            # 计算价格与下降趋势线的距离
            distance = data['downtrend_line'] - data['low']
            avg_distance = distance.mean()
            
            # 创建通道下轨
            data['channel_lower'] = data['downtrend_line'] - avg_distance
        
        return data
    
    def plot_analysis(self, data):
        """绘制分析图表"""
        plt.figure(figsize=(15, 12))
        
        # 子图1：价格和线性趋势线
        plt.subplot(2, 1, 1)
        plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
        plt.plot(data.index, data['trendline'], label='线性趋势线', color='red', linewidth=2)
        
        plt.title('沪深300指数与线性趋势线')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：价格、趋势线和通道线
        plt.subplot(2, 1, 2)
        plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
        
        # 绘制上升趋势线和通道
        if 'uptrend_line' in data.columns:
            plt.plot(data.index, data['uptrend_line'], label='上升趋势线', color='green', linewidth=2)
            if 'channel_upper' in data.columns:
                plt.plot(data.index, data['channel_upper'], label='通道上轨', color='green', linestyle='--', linewidth=2)
        
        # 绘制下降趋势线和通道
        if 'downtrend_line' in data.columns:
            plt.plot(data.index, data['downtrend_line'], label='下降趋势线', color='red', linewidth=2)
            if 'channel_lower' in data.columns:
                plt.plot(data.index, data['channel_lower'], label='通道下轨', color='red', linestyle='--', linewidth=2)
        
        plt.title('沪深300指数与趋势通道')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/trendline_hs300_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("图表已保存：trendline_hs300_analysis.png")
    
    def analyze_trendline_effectiveness(self, data):
        """分析趋势线的有效性"""
        analysis_results = []
        
        # 计算趋势线与价格的相关性
        if 'trendline' in data.columns:
            correlation = data['close'].corr(data['trendline'])
            analysis_results.append({
                '指标': '价格与线性趋势线相关性',
                '数值': correlation
            })
        
        # 分析上升趋势线的支撑效果
        if 'uptrend_line' in data.columns:
            # 统计价格跌破趋势线后的表现
            below_trend = data['close']< data['uptrend_line']
            recovery_days = []
            
            for i in range(len(data)):
                if below_trend.iloc[i]:
                    # 寻找恢复到趋势线上方的天数
                    for j in range(i, min(i+20, len(data))):
                        if data['close'].iloc[j] >= data['uptrend_line'].iloc[j]:
                            recovery_days.append(j - i)
                            break
            
            avg_recovery_days = np.mean(recovery_days) if recovery_days else 0
            analysis_results.append({
                '指标': '跌破上升趋势线后的平均恢复天数',
                '数值': avg_recovery_days
            })
        
        # 分析通道交易的效果
        if 'channel_upper' in data.columns and 'uptrend_line' in data.columns:
            # 计算在通道内交易的收益
            channel_trades = []
            
            for i in range(1, len(data)):
                # 在下轨附近买入，上轨附近卖出
                if data['close'].iloc[i-1]< data['uptrend_line'].iloc[i-1] * 1.005 and data['close'].iloc[i] >= data['uptrend_line'].iloc[i]:
                    # 买入信号
                    buy_price = data['close'].iloc[i]
                    # 寻找卖出点
                    for j in range(i, min(i+30, len(data))):
                        if data['close'].iloc[j] >= data['channel_upper'].iloc[j] * 0.995:
                            sell_price = data['close'].iloc[j]
                            channel_trades.append((sell_price - buy_price) / buy_price * 100)
                            break
            
            avg_channel_return = np.mean(channel_trades) if channel_trades else 0
            analysis_results.append({
                '指标': '通道内交易平均收益率',
                '数值': avg_channel_return
            })
        
        return analysis_results
    
    def run_analysis(self):
        """运行完整分析"""
        print("开始生成沪深300数据...")
        data = self.generate_hs300_data()
        
        print("计算线性趋势线...")
        data = self.calculate_trendline(data, method='linear')
        
        print("计算高低点趋势线...")
        data = self.calculate_trendline(data, method='high_low')
        
        print("计算通道线...")
        data = self.calculate_channel_lines(data)
        
        print("绘制分析图表...")
        self.plot_analysis(data)
        
        print("分析趋势线有效性...")
        effectiveness = self.analyze_trendline_effectiveness(data)
        
        # 保存结果
        data.to_csv(f"{self.output_dir}/trendline_hs300_data.csv")
        
        return effectiveness

if __name__ == "__main__":
    analysis = TrendlineAnalysis()
    effectiveness = analysis.run_analysis()
    
    print("\n=== 趋势线有效性分析 ===")
    for result in effectiveness:
        print(f"{result['指标']}: {result['数值']:.4f}")
