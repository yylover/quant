import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    """计算MACD指标"""
    # 计算快速EMA
    alpha_fast = 2 / (fast_period + 1)
    ema_fast = data['close'].ewm(alpha=alpha_fast, adjust=False).mean()
    
    # 计算慢速EMA
    alpha_slow = 2 / (slow_period + 1)
    ema_slow = data['close'].ewm(alpha=alpha_slow, adjust=False).mean()
    
    # 计算DIF
    dif = ema_fast - ema_slow
    
    # 计算DEA
    alpha_signal = 2 / (signal_period + 1)
    dea = dif.ewm(alpha=alpha_signal, adjust=False).mean()
    
    # 计算MACD柱
    macd_hist = dif - dea
    
    return dif, dea, macd_hist

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

def plot_hs300_macd(data):
    """绘制沪深300价格和MACD图表"""
    # 计算MACD
    dif, dea, macd_hist = calculate_macd(data)
    
    # 创建图表
    plt.figure(figsize=(16, 12))
    
    # 绘制价格图
    plt.subplot(2, 1, 1)
    plt.plot(data.index, data['close'], label='沪深300收盘价', color='blue', linewidth=1.5)
    plt.title('沪深300指数近5年走势与MACD指标', fontsize=14, fontweight='bold')
    plt.ylabel('指数价格', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 绘制MACD图
    plt.subplot(2, 1, 2)
    plt.plot(data.index, dif, label='DIF', color='blue', linewidth=1.2)
    plt.plot(data.index, dea, label='DEA', color='red', linewidth=1.2)
    plt.bar(data.index, macd_hist, label='MACD柱', color='green', alpha=0.5)
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    plt.ylabel('MACD值', fontsize=12)
    plt.xlabel('日期', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    
    # 保存图表
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/macd"
    os.makedirs(output_dir, exist_ok=True)
    
    plt.savefig(f"{output_dir}/hs300_macd_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("MACD分析图表已保存")
    
    # 保存数据
    data_with_macd = data.copy()
    data_with_macd['dif'] = dif
    data_with_macd['dea'] = dea
    data_with_macd['macd_hist'] = macd_hist
    data_with_macd.to_csv(f"{output_dir}/hs300_macd_data.csv")
    print("沪深300数据已保存")
    
    return data_with_macd

if __name__ == "__main__":
    # 生成沪深300数据
    hs300_data = generate_hs300_data()
    
    # 绘制MACD图表
    data_with_macd = plot_hs300_macd(hs300_data)
    
    # 输出基本统计信息
    print("\n=== 数据统计信息 ===")
    print(f"平均DIF值: {data_with_macd['dif'].mean():.2f}")
    print(f"DIF最大值: {data_with_macd['dif'].max():.2f}")
    print(f"DIF最小值: {data_with_macd['dif'].min():.2f}")
    print(f"平均DEA值: {data_with_macd['dea'].mean():.2f}")
    print(f"平均MACD柱值: {data_with_macd['macd_hist'].mean():.2f}")
    
    # 统计金叉死叉次数
    cross_signals = []
    for i in range(1, len(data_with_macd)):
        # 金叉
        if data_with_macd['dif'].iloc[i] > data_with_macd['dea'].iloc[i] and data_with_macd['dif'].iloc[i-1]<= data_with_macd['dea'].iloc[i-1]:
            cross_signals.append(1)
        # 死叉
        elif data_with_macd['dif'].iloc[i] < data_with_macd['dea'].iloc[i] and data_with_macd['dif'].iloc[i-1] >= data_with_macd['dea'].iloc[i-1]:
            cross_signals.append(-1)
    
    print(f"\n金叉次数: {cross_signals.count(1)}")
    print(f"死叉次数: {cross_signals.count(-1)}")
