import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class OBVAnalysis:
    """基于沪深300的OBV指标分析"""
    
    def __init__(self):
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/obv"
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
        
        # 创建成交量数据（与价格变化相关）
        volume_base = 50000000
        price_change = np.diff(prices, prepend=prices[0])
        volume_change = np.abs(price_change) / prices * 100000000
        volumes = volume_base + np.random.normal(0, volume_base * 0.3, len(dates)) + volume_change
        volumes = np.maximum(volumes, 10000000)  # 确保成交量不为负
        
        # 创建DataFrame
        data = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.normal(0, 0.003, len(dates))),
            'high': prices * (1 + np.random.normal(0.004, 0.006, len(dates))),
            'low': prices * (1 + np.random.normal(-0.004, 0.006, len(dates))),
            'close': prices,
            'volume': volumes.astype(int)
        })
        
        # 确保high >= close, open，low<= close, open
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        data.set_index('date', inplace=True)
        
        return data
    
    def calculate_obv(self, data):
        """计算OBV指标"""
        # 初始化OBV
        data['OBV'] = 0.0
        
        # 计算价格变化
        data['price_change'] = data['close'].diff()
        
        # 计算OBV
        for i in range(1, len(data)):
            if data['price_change'].iloc[i] > 0:
                data.at[data.index[i], 'OBV'] = data['OBV'].iloc[i-1] + data['volume'].iloc[i]
            elif data['price_change'].iloc[i]< 0:
                data.at[data.index[i], 'OBV'] = data['OBV'].iloc[i-1] - data['volume'].iloc[i]
            else:
                data.at[data.index[i], 'OBV'] = data['OBV'].iloc[i-1]
        
        # 计算OBV的移动平均
        data['OBV_ma'] = data['OBV'].rolling(window=20).mean()
        
        # 计算OBV变化率
        data['OBV_change'] = data['OBV'].pct_change() * 100
        
        return data
    
    def plot_analysis(self, data):
        """绘制分析图表"""
        plt.figure(figsize=(15, 12))
        
        # 子图1：价格和OBV
        plt.subplot(3, 1, 1)
        plt.plot(data.index, data['close'], label='沪深300收盘价', linewidth=2)
        
        plt.title('沪深300指数')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2：OBV和OBV均线
        plt.subplot(3, 1, 2)
        plt.plot(data.index, data['OBV'], label='OBV', color='blue', linewidth=2)
        plt.plot(data.index, data['OBV_ma'], label='OBV均线(20日)', color='red', linewidth=2)
        
        plt.title('OBV指标')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图3：OBV变化率和成交量
        plt.subplot(3, 1, 3)
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        
        ax1.plot(data.index, data['OBV_change'], label='OBV变化率(%)', color='blue', linewidth=2)
        ax2.bar(data.index, data['volume'] / 1000000, alpha=0.5, color='gray', label='成交量(百万)')
        
        ax1.set_title('OBV变化率与成交量')
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/obv_hs300_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print("图表已保存：obv_hs300_analysis.png")
    
    def analyze_obv_effectiveness(self, data):
        """分析OBV指标的有效性"""
        analysis_results = []
        
        # 计算OBV与价格的相关性
        correlation = data['close'].corr(data['OBV'])
        
        # 分析OBV均线穿越的效果
        obv_cross_up = (data['OBV'] > data['OBV_ma']) & (data['OBV'].shift(1)<= data['OBV_ma'].shift(1))
        obv_cross_down = (data['OBV'] < data['OBV_ma']) & (data['OBV'].shift(1) >= data['OBV_ma'].shift(1))
        
        # 计算穿越后的平均收益
        if obv_cross_up.any():
            up_returns = []
            for date in obv_cross_up[obv_cross_up].index:
                idx = data.index.get_loc(date)
                if idx + 20 < len(data):
                    return_20d = (data['close'].iloc[idx+20] / data['close'].iloc[idx] - 1) * 100
                    up_returns.append(return_20d)
            avg_up_return = np.mean(up_returns) if up_returns else 0
        else:
            avg_up_return = 0
        
        if obv_cross_down.any():
            down_returns = []
            for date in obv_cross_down[obv_cross_down].index:
                idx = data.index.get_loc(date)
                if idx + 20 < len(data):
                    return_20d = (data['close'].iloc[idx+20] / data['close'].iloc[idx] - 1) * 100
                    down_returns.append(return_20d)
            avg_down_return = np.mean(down_returns) if down_returns else 0
        else:
            avg_down_return = 0
        
        analysis_results.append({
            '指标': 'OBV与价格相关性',
            '数值': correlation
        })
        
        analysis_results.append({
            '指标': 'OBV均线上穿后20日平均收益',
            '数值': avg_up_return
        })
        
        analysis_results.append({
            '指标': 'OBV均线下穿后20日平均收益',
            '数值': avg_down_return
        })
        
        return analysis_results
    
    def run_analysis(self):
        """运行完整分析"""
        print("开始生成沪深300数据...")
        data = self.generate_hs300_data()
        
        print("计算OBV指标...")
        data = self.calculate_obv(data)
        
        print("绘制分析图表...")
        self.plot_analysis(data)
        
        print("分析OBV指标有效性...")
        effectiveness = self.analyze_obv_effectiveness(data)
        
        # 保存结果
        data.to_csv(f"{self.output_dir}/obv_hs300_data.csv")
        
        return effectiveness

if __name__ == "__main__":
    analysis = OBVAnalysis()
    effectiveness = analysis.run_analysis()
    
    print("\n=== OBV指标有效性分析 ===")
    for result in effectiveness:
        print(f"{result['指标']}: {result['数值']:.4f}")
