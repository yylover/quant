import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 画线分析均线
# 
# 
# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def get_hs300_data():
    """获取沪深300近3年K线数据"""
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=3*365)).strftime('%Y%m%d')
    
    print(f"正在获取沪深300数据 ({start_date} 到 {end_date})...")
    
    # 尝试使用不同的接口获取数据
    for _ in range(3):  # 重试3次
        try:
            # 尝试使用新浪财经接口
            data = ak.stock_zh_index_daily(symbol="sh000300")
            if not data.empty:
                break
        except Exception as e:
            print(f"新浪财经接口失败: {e}")
            time.sleep(1)
    
    print("数据列名:", data.columns.tolist())
    
    # 转换日期格式
    date_column = data.columns[0]
    data[date_column] = pd.to_datetime(data[date_column])
    data.set_index(date_column, inplace=True)
    
    # 筛选近3年数据
    three_years_ago = datetime.now() - timedelta(days=3*365)
    data = data[data.index >= three_years_ago]
    
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
    print("=== 沪深300均线分析程序 ===")
    
    try:
        # 获取数据
        data = get_hs300_data()
        print(f"数据获取成功，共 {len(data)} 条记录")
        
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
