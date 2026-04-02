import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def generate_hs300_data():
    """生成模拟的沪深300数据（近5年）"""
    np.random.seed(42)
    
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=5*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 基础价格趋势
    base_price = 4000
    trend = np.linspace(0, 0.4, len(dates))
    
    # 添加季节性和周期性波动
    seasonal = 0.04 * np.sin(np.linspace(0, 10*np.pi, len(dates)))
    cyclic = 0.03 * np.cos(np.linspace(0, 5*np.pi, len(dates)))
    
    # 添加随机波动
    volatility = np.random.normal(0, 0.01, len(dates))
    
    # 计算价格
    prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))
    
    # 生成成交量数据
    # 基础成交量 + 价格波动影响 + 趋势影响 + 随机因素
    base_volume = 20000000
    volume_trend = np.linspace(0, 0.5, len(dates))
    price_volatility = np.abs(np.diff(prices, prepend=prices[0])) / prices * 100
    volume_seasonal = 0.3 * np.sin(np.linspace(0, 8*np.pi, len(dates)))
    
    volumes = base_volume * (
        1 + volume_trend + 
        price_volatility * 5 + 
        volume_seasonal + 
        np.random.normal(0, 0.2, len(dates))
    )
    
    # 确保成交量为正
    volumes = np.maximum(volumes, base_volume * 0.3)
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
        'high': prices * (1 + np.random.normal(0.003, 0.005, len(dates))),
        'low': prices * (1 + np.random.normal(-0.003, 0.005, len(dates))),
        'close': prices,
        'volume': volumes.astype(int)
    })
    
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    data.set_index('date', inplace=True)
    
    return data

class VolumeAnalysis:
    def __init__(self, data):
        self.data = data.copy()
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/vol"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def calculate_volume_indicators(self):
        """计算成交量相关指标"""
        # 成交量均线
        self.data['volume_ma5'] = self.data['volume'].rolling(5).mean()
        self.data['volume_ma10'] = self.data['volume'].rolling(10).mean()
        self.data['volume_ma20'] = self.data['volume'].rolling(20).mean()
        
        # 成交量比率
        self.data['volume_ratio_5'] = self.data['volume'] / self.data['volume_ma5']
        self.data['volume_ratio_20'] = self.data['volume'] / self.data['volume_ma20']
        
        # 成交量变化率
        self.data['volume_change'] = self.data['volume'].pct_change()
        
        # 计算OBV
        self.data['obv'] = 0
        for i in range(1, len(self.data)):
            if self.data['close'].iloc[i] > self.data['close'].iloc[i-1]:
                self.data['obv'].iloc[i] = self.data['obv'].iloc[i-1] + self.data['volume'].iloc[i]
            else:
                self.data['obv'].iloc[i] = self.data['obv'].iloc[i-1] - self.data['volume'].iloc[i]
        
        # 计算换手率（假设流通股本为500亿股）
        shares_outstanding = 50000000000  # 500亿股
        self.data['turnover'] = self.data['volume'] / shares_outstanding * 100
        
        return self.data
    
    def plot_volume_trend(self):
        """绘制成交量趋势图"""
        plt.figure(figsize=(16, 12))
        
        # 价格和成交量图
        plt.subplot(3, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='沪深300指数', color='blue', linewidth=1.5)
        plt.title('沪深300指数价格', fontsize=14)
        plt.ylabel('指数价格', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 2)
        plt.bar(self.data.index, self.data['volume'], label='成交量', color='green', alpha=0.6)
        plt.plot(self.data.index, self.data['volume_ma5'], label='5日均线', color='red', linewidth=1.5)
        plt.plot(self.data.index, self.data['volume_ma20'], label='20日均线', color='orange', linewidth=1.5)
        plt.title('成交量趋势', fontsize=14)
        plt.ylabel('成交量', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(3, 1, 3)
        plt.plot(self.data.index, self.data['turnover'], label='换手率', color='purple', linewidth=1.5)
        plt.title('换手率趋势', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('换手率(%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/hs300_volume_trend.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_volume_price_relation(self):
        """绘制量价关系图"""
        plt.figure(figsize=(16, 10))
        
        # 价格与成交量比率关系
        plt.subplot(2, 1, 1)
        plt.plot(self.data.index, self.data['close'], label='价格', color='blue', linewidth=1.5)
        plt.plot(self.data.index, self.data['volume_ratio_20'] * 1000, label='成交量比率', color='red', linewidth=1.2)
        plt.title('价格与成交量比率关系', fontsize=14)
        plt.ylabel('价格/成交量比率', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # OBV指标
        plt.subplot(2, 1, 2)
        plt.plot(self.data.index, self.data['obv'], label='OBV', color='green', linewidth=1.5)
        plt.title('能量潮指标(OBV)', fontsize=14)
        plt.xlabel('日期', fontsize=12)
        plt.ylabel('OBV值', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/hs300_volume_price_relation.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_volume_distribution(self):
        """绘制成交量分布图"""
        plt.figure(figsize=(16, 8))
        
        # 成交量分布直方图
        plt.subplot(2, 2, 1)
        plt.hist(self.data['volume'], bins=50, color='green', alpha=0.7)
        plt.title('成交量分布', fontsize=12)
        plt.xlabel('成交量', fontsize=10)
        plt.ylabel('频数', fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # 换手率分布直方图
        plt.subplot(2, 2, 2)
        plt.hist(self.data['turnover'], bins=50, color='purple', alpha=0.7)
        plt.title('换手率分布', fontsize=12)
        plt.xlabel('换手率(%)', fontsize=10)
        plt.ylabel('频数', fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # 成交量比率分布
        plt.subplot(2, 2, 3)
        plt.hist(self.data['volume_ratio_20'].dropna(), bins=50, color='red', alpha=0.7)
        plt.title('成交量比率分布', fontsize=12)
        plt.xlabel('成交量比率', fontsize=10)
        plt.ylabel('频数', fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # 成交量变化率分布
        plt.subplot(2, 2, 4)
        plt.hist(self.data['volume_change'].dropna(), bins=50, color='orange', alpha=0.7)
        plt.title('成交量变化率分布', fontsize=12)
        plt.xlabel('成交量变化率', fontsize=10)
        plt.ylabel('频数', fontsize=10)
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/hs300_volume_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def analyze_volume_patterns(self):
        """分析成交量模式"""
        patterns = {}
        
        # 识别放量上涨
        price_rise = self.data['close'] > self.data['close'].shift(1)
        volume_rise = self.data['volume'] > self.data['volume'].shift(1)
        patterns['volume_price_rise'] = self.data[price_rise & volume_rise]
        
        # 识别缩量上涨
        patterns['volume_price_rise_low_volume'] = self.data[price_rise & ~volume_rise]
        
        # 识别放量下跌
        price_fall = self.data['close'] < self.data['close'].shift(1)
        patterns['volume_price_fall'] = self.data[price_fall & volume_rise]
        
        # 识别缩量下跌
        patterns['volume_price_fall_low_volume'] = self.data[price_fall & ~volume_rise]
        
        # 识别异常放量
        abnormal_volume = self.data['volume_ratio_20'] > 2
        patterns['abnormal_volume'] = self.data[abnormal_volume]
        
        # 识别极度缩量
        extremely_low_volume = self.data['volume_ratio_20']< 0.5
        patterns['extremely_low_volume'] = self.data[extremely_low_volume]
        
        return patterns
    
    def save_analysis_report(self):
        """保存分析报告"""
        report = []
        report.append("# 沪深300成交量分析报告\n")
        report.append("## 基本统计\n")
        
        # 基本统计信息
        report.append(f"- 数据时间范围: {self.data.index.min().strftime('%Y-%m-%d')} 至 {self.data.index.max().strftime('%Y-%m-%d')}\n")
        report.append(f"- 总交易日数: {len(self.data)}\n")
        report.append(f"- 平均成交量: {self.data['volume'].mean():,.0f}\n")
        report.append(f"- 最大成交量: {self.data['volume'].max():,.0f}\n")
        report.append(f"- 最小成交量: {self.data['volume'].min():,.0f}\n")
        report.append(f"- 平均换手率: {self.data['turnover'].mean():.4f}%\n")
        report.append(f"- 最大换手率: {self.data['turnover'].max():.4f}%\n")
        report.append(f"- 最小换手率: {self.data['turnover'].min():.4f}%\n")
        
        # 成交量模式分析
        patterns = self.analyze_volume_patterns()
        report.append("\n## 成交量模式分析\n")
        report.append(f"- 放量上涨天数: {len(patterns['volume_price_rise'])}\n")
        report.append(f"- 缩量上涨天数: {len(patterns['volume_price_rise_low_volume'])}\n")
        report.append(f"- 放量下跌天数: {len(patterns['volume_price_fall'])}\n")
        report.append(f"- 缩量下跌天数: {len(patterns['volume_price_fall_low_volume'])}\n")
        report.append(f"- 异常放量天数: {len(patterns['abnormal_volume'])}\n")
        report.append(f"- 极度缩量天数: {len(patterns['extremely_low_volume'])}\n")
        
        # 相关性分析
        correlation = self.data['close'].corr(self.data['volume'])
        report.append(f"\n## 相关性分析\n")
        report.append(f"- 价格与成交量相关系数: {correlation:.4f}\n")
        
        with open(f"{self.output_dir}/hs300_volume_analysis_report.md", 'w', encoding='utf-8') as f:
            f.write(''.join(report))
    
    def run_analysis(self):
        """运行完整的成交量分析"""
        # 计算指标
        self.data = self.calculate_volume_indicators()
        
        # 保存数据
        self.data.to_csv(f"{self.output_dir}/hs300_volume_data.csv")
        
        # 绘制图表
        self.plot_volume_trend()
        self.plot_volume_price_relation()
        self.plot_volume_distribution()
        
        # 保存分析报告
        self.save_analysis_report()
        
        print("沪深300成交量分析完成！")
        print(f"数据文件已保存至: {self.output_dir}/hs300_volume_data.csv")
        print(f"分析报告已保存至: {self.output_dir}/hs300_volume_analysis_report.md")
        print(f"图表已保存至: {self.output_dir}/")

if __name__ == "__main__":
    # 生成数据
    data = generate_hs300_data()
    
    # 创建分析实例
    analysis = VolumeAnalysis(data)
    
    # 运行分析
    analysis.run_analysis()
