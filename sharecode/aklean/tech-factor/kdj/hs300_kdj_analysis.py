import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def calculate_kdj(data, n=9):
    """计算KDJ指标"""
    # 计算RSV
    low_n = data['low'].rolling(window=n).min()
    high_n = data['high'].rolling(window=n).max()
    rsv = (data['close'] - low_n) / (high_n - low_n) * 100
    
    # 计算K线
    k = pd.Series(0.0, index=data.index)
    k.iloc[n-1] = 50  # 初始值
    
    for i in range(n, len(data)):
        k.iloc[i] = (2/3) * k.iloc[i-1] + (1/3) * rsv.iloc[i]
    
    # 计算D线
    d = pd.Series(0.0, index=data.index)
    d.iloc[n-1] = 50  # 初始值
    
    for i in range(n, len(data)):
        d.iloc[i] = (2/3) * d.iloc[i-1] + (1/3) * k.iloc[i]
    
    # 计算J线
    j = 3 * k - 2 * d
    
    return k, d, j

def generate_hs300_data():
    """生成模拟的沪深300数据（近5年）"""
    print("生成沪深300近5年模拟数据...")
    
    # 设置随机种子
    np.random.seed(42)
    
    # 创建日期索引（近5年，约1260个交易日）
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=5*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 生成基础价格（带有趋势和波动）
    base_price = 4000
    # 添加更真实的市场波动模式
    trend = np.linspace(0, 0.5, len(dates))  # 50%的总体趋势
    
    # 添加季节性和周期性波动
    seasonal = 0.05 * np.sin(np.linspace(0, 10*np.pi, len(dates)))  # 季节性波动
    cyclic = 0.03 * np.cos(np.linspace(0, 5*np.pi, len(dates)))      # 周期性波动
    
    # 添加随机波动
    volatility = np.random.normal(0, 0.01, len(dates))
    
    # 合成价格
    prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))
    
    # 创建DataFrame
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
        'high': prices * (1 + np.random.normal(0.003, 0.005, len(dates))),
        'low': prices * (1 + np.random.normal(-0.003, 0.005, len(dates))),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, len(dates))
    })
    
    # 确保价格合理性
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    data.set_index('date', inplace=True)
    
    print(f"数据生成成功，共 {len(data)} 条记录")
    print(f"时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"价格范围: {data['close'].min():.2f} - {data['close'].max():.2f}")
    
    return data

def plot_hs300_kdj(data):
    """绘制沪深300价格和KDJ图表"""
    # 计算KDJ
    k, d, j = calculate_kdj(data)
    
    # 创建图表
    plt.figure(figsize=(16, 12))
    
    # 绘制价格图
    plt.subplot(2, 1, 1)
    plt.plot(data.index, data['close'], label='沪深300收盘价', color='blue', linewidth=1.5)
    plt.title('沪深300指数近5年走势与KDJ指标', fontsize=14, fontweight='bold')
    plt.ylabel('指数价格', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 绘制KDJ图
    plt.subplot(2, 1, 2)
    plt.plot(data.index, k, label='K线', color='blue', linewidth=1.2)
    plt.plot(data.index, d, label='D线', color='red', linewidth=1.2)
    plt.plot(data.index, j, label='J线', color='green', linewidth=1.2)
    plt.axhline(y=80, color='red', linestyle='--', alpha=0.7, label='超买线(80)')
    plt.axhline(y=20, color='green', linestyle='--', alpha=0.7, label='超卖线(20)')
    plt.axhline(y=50, color='gray', linestyle='-', alpha=0.5, label='中性线(50)')
    plt.ylabel('KDJ值', fontsize=12)
    plt.xlabel('日期', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    
    # 保存图表
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/kdj"
    os.makedirs(output_dir, exist_ok=True)
    
    plt.savefig(f"{output_dir}/hs300_kdj_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("KDJ分析图表已保存")
    
    # 保存数据
    data_with_kdj = data.copy()
    data_with_kdj['k'] = k
    data_with_kdj['d'] = d
    data_with_kdj['j'] = j
    data_with_kdj.to_csv(f"{output_dir}/hs300_kdj_data.csv")
    print("沪深300数据已保存")
    
    return data_with_kdj

if __name__ == "__main__":
    # 生成沪深300数据
    hs300_data = generate_hs300_data()
    
    # 绘制KDJ图表
    data_with_kdj = plot_hs300_kdj(hs300_data)
    
    # 输出基本统计信息
    print("\n=== 数据统计信息 ===")
    print(f"平均K值: {data_with_kdj['k'].mean():.2f}")
    print(f"K最大值: {data_with_kdj['k'].max():.2f}")
    print(f"K最小值: {data_with_kdj['k'].min():.2f}")
    print(f"平均D值: {data_with_kdj['d'].mean():.2f}")
    print(f"平均J值: {data_with_kdj['j'].mean():.2f}")
    
    # 统计超买超卖次数
    overbought_count = len(data_with_kdj[data_with_kdj['k'] > 80])
    oversold_count = len(data_with_kdj[data_with_kdj['k']< 20])
    
    print(f"\n超买次数 (K >80): {overbought_count}")
    print(f"超卖次数 (K< 20): {oversold_count}")
    
    # 统计金叉死叉次数
    cross_signals = []
    for i in range(1, len(data_with_kdj)):
        # 金叉
        if data_with_kdj['k'].iloc[i] > data_with_kdj['d'].iloc[i] and data_with_kdj['k'].iloc[i-1]<= data_with_kdj['d'].iloc[i-1]:
            cross_signals.append(1)
        # 死叉
        elif data_with_kdj['k'].iloc[i]< data_with_kdj['d'].iloc[i] and data_with_kdj['k'].iloc[i-1] >= data_with_kdj['d'].iloc[i-1]:
            cross_signals.append(-1)
    
    print(f"\n金叉次数: {cross_signals.count(1)}")
    print(f"死叉次数: {cross_signals.count(-1)}")
