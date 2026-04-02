import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ChannelLineAnalysis:
    """基于沪深300的通道线分析"""
    
    def __init__(self):
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/ChannelLine"
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
    
    def calculate_linear_regression(self, data):
        """计算线性回归趋势线"""
        x = np.arange(len(data))
        n = len(x)
        mean_x = np.mean(x)
        mean_y = np.mean(data['close'])
        
        numerator = np.sum((x - mean_x) * (data['close'] - mean_y))
        denominator = np.sum((x - mean_x) ** 2)
        
        slope = numerator / denominator
        intercept = mean_y - slope * mean_x
        
        return intercept + slope * x
    
    def calculate_parallel_channel(self, data):
        """计算平行通道"""
        x = np.arange(len(data))
        
        # 计算主趋势线（线性回归）
        trendline = self.calculate_linear_regression(data)
        data['trendline'] = trendline
        
        # 计算价格与趋势线的偏离
        deviations = data['close'] - trendline
        
        # 计算通道宽度（使用标准差）
        channel_width = np.std(deviations) * 2
        
        # 创建通道上轨和下轨
        data['channel_upper'] = trendline + channel_width
        data['channel_lower'] = trendline - channel_width
        
        return data
    
    def calculate_trend_channel(self, data):
        """基于趋势线计算通道"""
        x = np.arange(len(data))
        
        # 寻找高点和低点
        high_points = []
        low_points = []
        
        for i in range(1, len(data)-1):
            # 高点检测
            if data['high'].iloc[i] > data['high'].iloc[i-1] and data['high'].iloc[i] > data['high'].iloc[i+1]:
                high_points.append(i)
            
            # 低点检测
            if data['low'].iloc[i]< data['low'].iloc[i-1] and data['low'].iloc[i]< data['low'].iloc[i+1]:
                low_points.append(i)
        
        # 计算上升趋势线（连接低点）
        if len(low_points) >= 2:
            start_idx = low_points[0]
            end_idx = low_points[-1]
            
            rise = data['low'].iloc[end_idx] - data['low'].iloc[start_idx]
            run = end_idx - start_idx
            slope = rise / run
            intercept = data['low'].iloc[start_idx] - slope * start_idx
            data['uptrend_line'] = intercept + slope * x
        
        # 计算下降趋势线（连接高点）
        if len(high_points) >= 2:
            start_idx = high_points[0]
            end_idx = high_points[-1]
            
            rise = data['high'].iloc[end_idx] - data['high'].iloc[start_idx]
            run = end_idx - start_idx
            slope = rise / run
            intercept = data['high'].iloc[start_idx] - slope * start_idx
            data['downtrend_line'] = intercept + slope * x
        
        # 计算通道线
        if 'uptrend_line' in data.columns:
            # 计算价格与上升趋势线的距离
            upper_deviations = data['high'] - data['uptrend_line']
            avg_upper_deviation = np.mean(upper_deviations)
            data['channel_upper'] = data['uptrend_line'] + avg_upper_deviation
        
        if 'downtrend_line' in data.columns:
            # 计算价格与下降趋势线的距离
            lower_deviations = data['downtrend_line'] - data['low']
            avg_lower_deviation = np.mean(lower_deviations)
            data['channel_lower'] = data['downtrend_line'] - avg_lower_deviation
        
        return data
    
    def calculate_bollinger_bands(self, data, window=20, std_dev=2):
        """计算布林带（作为一种通道线）"""
        data['bb_middle'] = data['close'].rolling(window=window).mean()
        data['bb_std'] = data['close'].rolling(window=window).std()
        data['bb_upper'] = data['bb_middle'] + (data['bb_std'] * std_dev)
        data['bb_lower'] = data['bb_middle'] - (data['bb_std'] * std_dev)
        
        return data
    
    def plot_analysis(self, data):
        """绘制分析图表"""
        plt.figure(figsize=(15, 15))
        
        # 子图1：平行通道
        plt.subplot(3, 1, 1)
        plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
        plt.plot(data.index, data['trendline'], label='趋势线', color='red', linewidth=2)
        plt.plot(data.index, data['channel_upper'], label='通道上轨', color='blue', linestyle='--', linewidth=2)
        plt.plot(data.index, data['channel_lower'], label='通道下轨', color='blue', linestyle='--', linewidth=2)
        plt.fill_between(data.index, data['channel_lower'], data['channel_upper'], color='blue', alpha=0.1)
        
        plt.title('沪深300指数与平行通道')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：趋势通道
        plt.subplot(3, 1, 2)
        plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
        
        if 'uptrend_line' in data.columns:
            plt.plot(data.index, data['uptrend_line'], label='上升趋势线', color='green', linewidth=2)
        if 'downtrend_line' in data.columns:
            plt.plot(data.index, data['downtrend_line'], label='下降趋势线', color='red', linewidth=2)
        if 'channel_upper' in data.columns:
            plt.plot(data.index, data['channel_upper'], label='通道上轨', color='blue', linestyle='--', linewidth=2)
        if 'channel_lower' in data.columns:
            plt.plot(data.index, data['channel_lower'], label='通道下轨', color='blue', linestyle='--', linewidth=2)
        
        plt.title('沪深300指数与趋势通道')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图3：布林带
        plt.subplot(3, 1, 3)
        plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
        plt.plot(data.index, data['bb_middle'], label='布林带中轨', color='orange', linewidth=2)
        plt.plot(data.index, data['bb_upper'], label='布林带上轨', color='green', linestyle='--', linewidth=2)
        plt.plot(data.index, data['bb_lower'], label='布林带下轨', color='red', linestyle='--', linewidth=2)
        plt.fill_between(data.index, data['bb_lower'], data['bb_upper'], color='gray', alpha=0.1)
        
        plt.title('沪深300指数与布林带')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/channel_line_hs300_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("图表已保存：channel_line_hs300_analysis.png")
    
    def analyze_channel_effectiveness(self, data):
        """分析通道线的有效性"""
        analysis_results = []
        
        # 分析平行通道的有效性
        if 'channel_upper' in data.columns and 'channel_lower' in data.columns:
            # 计算价格触及通道边界的次数
            upper_touches = np.sum(data['high'] >= data['channel_upper'] * 0.995)
            lower_touches = np.sum(data['low']<= data['channel_lower'] * 1.005)
            
            analysis_results.append({
                '指标': '触及通道上轨次数',
                '数值': upper_touches
            })
            
            analysis_results.append({
                '指标': '触及通道下轨次数',
                '数值': lower_touches
            })
            
            # 计算通道内交易的收益
            channel_trades = []
            in_channel = False
            
            for i in range(1, len(data)):
                # 在下轨附近买入
                if data['close'].iloc[i]<= data['channel_lower'].iloc[i] * 1.005 and not in_channel:
                    buy_price = data['close'].iloc[i]
                    in_channel = True
                
                # 在上轨附近卖出
                elif data['close'].iloc[i] >= data['channel_upper'].iloc[i] * 0.995 and in_channel:
                    sell_price = data['close'].iloc[i]
                    channel_trades.append((sell_price - buy_price) / buy_price * 100)
                    in_channel = False
            
            if channel_trades:
                avg_channel_return = np.mean(channel_trades)
                analysis_results.append({
                    '指标': '通道内交易平均收益率',
                    '数值': avg_channel_return
                })
        
        # 分析布林带的有效性
        if 'bb_upper' in data.columns and 'bb_lower' in data.columns:
            # 计算布林带宽度变化率
            bb_width = data['bb_upper'] - data['bb_lower']
            bb_width_change = bb_width.pct_change() * 100
            
            # 分析波动率变化
            avg_width_change = bb_width_change.mean()
            analysis_results.append({
                '指标': '布林带宽度平均变化率',
                '数值': avg_width_change
            })
        
        return analysis_results
    
    def run_analysis(self):
        """运行完整分析"""
        print("开始生成沪深300数据...")
        data = self.generate_hs300_data()
        
        print("计算平行通道...")
        data = self.calculate_parallel_channel(data)
        
        print("计算趋势通道...")
        data = self.calculate_trend_channel(data)
        
        print("计算布林带...")
        data = self.calculate_bollinger_bands(data)
        
        print("绘制分析图表...")
        self.plot_analysis(data)
        
        print("分析通道线有效性...")
        effectiveness = self.analyze_channel_effectiveness(data)
        
        # 保存结果
        data.to_csv(f"{self.output_dir}/channel_line_hs300_data.csv")
        
        return effectiveness

if __name__ == "__main__":
    analysis = ChannelLineAnalysis()
    effectiveness = analysis.run_analysis()
    
    print("\n=== 通道线有效性分析 ===")
    for result in effectiveness:
        print(f"{result['指标']}: {result['数值']:.4f}")
