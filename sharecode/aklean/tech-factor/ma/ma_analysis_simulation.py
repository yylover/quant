import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def generate_simulation_data():
    """生成模拟的沪深300数据"""
    print("生成模拟的沪深300数据...")
    
    # 生成近3年的日期序列
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 生成模拟的价格数据
    # 基础趋势 + 随机波动
    base_price = 4000
    trend = np.linspace(0, 1000, len(dates))  # 3年上涨1000点
    random_walk = np.cumsum(np.random.normal(0, 20, len(dates)))
    
    close_prices = base_price + trend + random_walk
    
    # 创建DataFrame
    data = pd.DataFrame({
        '日期': dates,
        '开盘': close_prices * (1 + np.random.normal(0, 0.002, len(dates))),
        '收盘': close_prices,
        '最高': close_prices * (1 + np.random.normal(0, 0.005, len(dates))),
        '最低': close_prices * (1 - np.random.normal(0, 0.005, len(dates))),
        '成交量': np.random.randint(1000000, 5000000, len(dates)),
        '成交额': close_prices * np.random.randint(1000000, 5000000, len(dates)) / 10000
    })
    
    # 设置日期为索引
    data.set_index('日期', inplace=True)
    
    return data

def calculate_ma(data):
    """计算SMA、WMA、EMA"""
    # 计算SMA (简单移动平均)
    data['SMA_20'] = data['收盘'].rolling(window=20).mean()
    data['SMA_60'] = data['收盘'].rolling(window=60).mean()
    
    # 计算EMA (指数移动平均)
    data['EMA_20'] = data['收盘'].ewm(span=20, adjust=False).mean()
    data['EMA_60'] = data['收盘'].ewm(span=60, adjust=False).mean()
    
    # 计算WMA (加权移动平均)
    def wma(series, window):
        weights = np.arange(1, window + 1)
        return series.rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    
    data['WMA_20'] = wma(data['收盘'], 20)
    data['WMA_60'] = wma(data['收盘'], 60)
    
    return data

def plot_ma(data):
    """绘制均线图表"""
    plt.figure(figsize=(16, 10))
    
    # 绘制收盘价
    plt.plot(data.index, data['收盘'], label='收盘价', color='#1f77b4', linewidth=2)
    
    # 绘制SMA
    plt.plot(data.index, data['SMA_20'], label='SMA_20', color='#ff7f0e', linewidth=1.5)
    plt.plot(data.index, data['SMA_60'], label='SMA_60', color='#2ca02c', linewidth=1.5)
    
    # 绘制EMA
    plt.plot(data.index, data['EMA_20'], label='EMA_20', color='#d62728', linewidth=1.5, linestyle='--')
    plt.plot(data.index, data['EMA_60'], label='EMA_60', color='#9467bd', linewidth=1.5, linestyle='--')
    
    # 绘制WMA
    plt.plot(data.index, data['WMA_20'], label='WMA_20', color='#8c564b', linewidth=1.5, linestyle=':')
    plt.plot(data.index, data['WMA_60'], label='WMA_60', color='#e377c2', linewidth=1.5, linestyle=':')
    
    # 设置图表属性
    plt.title('沪深300指数 - 均线分析 (近3年)', fontsize=16, fontweight='bold')
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('价格', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10, loc='best')
    
    # 设置日期格式
    plt.gcf().autofmt_xdate()
    
    # 保存图表
    plt.savefig('hs300_ma_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("图表已保存为: hs300_ma_analysis.png")

def analyze_ma(data):
    """分析均线状态"""
    latest = data.iloc[-1]
    
    print("\n=== 均线分析结果 ===")
    print(f"最新收盘价: {latest['收盘']:.2f}")
    print(f"SMA_20: {latest['SMA_20']:.2f}, SMA_60: {latest['SMA_60']:.2f}")
    print(f"EMA_20: {latest['EMA_20']:.2f}, EMA_60: {latest['EMA_60']:.2f}")
    print(f"WMA_20: {latest['WMA_20']:.2f}, WMA_60: {latest['WMA_60']:.2f}")
    
    # 判断均线排列
    if latest['SMA_20'] > latest['SMA_60']:
        print("均线状态: 多头排列 (SMA_20 > SMA_60)")
    else:
        print("均线状态: 空头排列 (SMA_20 < SMA_60)")
    
    # 计算均线斜率
    def calculate_slope(series, days=10):
        if len(series) >= days:
            x = np.arange(days)
            y = series.iloc[-days:]
            slope, _ = np.polyfit(x, y, 1)
            return slope
        return 0
    
    sma20_slope = calculate_slope(data['SMA_20'])
    sma60_slope = calculate_slope(data['SMA_60'])
    
    print(f"SMA_20斜率: {sma20_slope:.4f}, SMA_60斜率: {sma60_slope:.4f}")
    
    if sma20_slope > 0 and sma60_slope > 0:
        print("趋势判断: 上升趋势")
    elif sma20_slope < 0 and sma60_slope < 0:
        print("趋势判断: 下降趋势")
    else:
        print("趋势判断: 盘整趋势")

def main():
    """主函数"""
    print("=== 沪深300均线分析程序（模拟数据） ===")
    
    try:
        # 生成模拟数据
        data = generate_simulation_data()
        print(f"数据生成成功，共 {len(data)} 条记录")
        
        # 计算均线
        data = calculate_ma(data)
        
        # 绘制图表
        plot_ma(data)
        
        # 分析均线
        analyze_ma(data)
        
        # 保存数据
        data.to_csv('hs300_ma_data.csv')
        print("\n数据已保存为: hs300_ma_data.csv")
        
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()
