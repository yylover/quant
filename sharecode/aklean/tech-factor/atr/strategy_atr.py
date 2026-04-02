import pandas as pd
import numpy as np

def generate_hs300_data():
    """生成模拟的沪深300数据（近5年）"""
    np.random.seed(42)
    
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=5*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 基础价格趋势 - 更平缓的趋势
    base_price = 4000
    trend = np.linspace(0, 0.1, len(dates))
    
    # 添加季节性和周期性波动
    seasonal = 0.04 * np.sin(np.linspace(0, 10*np.pi, len(dates)))
    cyclic = 0.03 * np.cos(np.linspace(0, 5*np.pi, len(dates)))
    
    # 添加随机波动
    volatility = np.random.normal(0, 0.015, len(dates))
    
    # 计算价格
    prices = base_price * (1 + trend + seasonal + cyclic + np.cumsum(volatility))
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
        'high': prices * (1 + np.random.normal(0.003, 0.005, len(dates))),
        'low': prices * (1 + np.random.normal(-0.003, 0.005, len(dates))),
        'close': prices,
        'volume': np.random.randint(10000000, 50000000, len(dates))
    })
    
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    data.set_index('date', inplace=True)
    
    return data

def run_all_strategies():
    """运行所有ATR策略"""
    print("=== ATR策略集合运行入口 ===\n")
    
    # 生成数据
    data = generate_hs300_data()
    
    # 测试数据
    print(f"数据基本信息：")
    print(f"数据长度: {len(data)}")
    print(f"价格范围: {data['close'].min():.2f} - {data['close'].max():.2f}")
    print(f"平均价格: {data['close'].mean():.2f}")
    
    # 运行ATR突破策略
    from atr_breakout.strategy_atr_breakout import AtrBreakoutStrategy
    print("运行ATR突破策略...")
    breakout_strategy = AtrBreakoutStrategy(data)
    
    # 调试信息
    breakout_strategy.calculate_atr()
    breakout_strategy.calculate_breakout_levels()
    breakout_strategy.generate_signals()
    print(f"突破策略信号统计:")
    print(f"买入信号数: {len(breakout_strategy.data[breakout_strategy.data['signal'] == 1])}")
    print(f"卖出信号数: {len(breakout_strategy.data[breakout_strategy.data['signal'] == -1])}")
    print(f"ATR范围: {breakout_strategy.data['atr'].min():.4f} - {breakout_strategy.data['atr'].max():.4f}")
    
    breakout_metrics = breakout_strategy.run_strategy()
    print(f"ATR突破策略总收益率: {breakout_metrics['总收益率']:.2f}%")
    print(f"ATR突破策略年化收益率: {breakout_metrics['年化收益率']:.2f}%\n")
    
    # 运行ATR通道策略
    from atr_channel.strategy_atr_channel import AtrChannelStrategy
    print("运行ATR通道策略...")
    channel_strategy = AtrChannelStrategy(data)
    channel_metrics = channel_strategy.run_strategy()
    print(f"ATR通道策略总收益率: {channel_metrics['总收益率']:.2f}%")
    print(f"ATR通道策略年化收益率: {channel_metrics['年化收益率']:.2f}%\n")
    
    # 运行ATR趋势跟踪策略
    from atr_trend_following.strategy_atr_trend_following import AtrTrendFollowingStrategy
    print("运行ATR趋势跟踪策略...")
    trend_strategy = AtrTrendFollowingStrategy(data)
    trend_metrics = trend_strategy.run_strategy()
    print(f"ATR趋势跟踪策略总收益率: {trend_metrics['总收益率']:.2f}%")
    print(f"ATR趋势跟踪策略年化收益率: {trend_metrics['年化收益率']:.2f}%\n")
    
    # 运行ATR均值回归策略
    from atr_mean_reversion.strategy_atr_mean_reversion import AtrMeanReversionStrategy
    print("运行ATR均值回归策略...")
    reversion_strategy = AtrMeanReversionStrategy(data)
    reversion_metrics = reversion_strategy.run_strategy()
    print(f"ATR均值回归策略总收益率: {reversion_metrics['总收益率']:.2f}%")
    print(f"ATR均值回归策略年化收益率: {reversion_metrics['年化收益率']:.2f}%\n")
    
    # 运行ATR动态止损策略
    from atr_dynamic_stop.strategy_atr_dynamic_stop import AtrDynamicStopStrategy
    print("运行ATR动态止损策略...")
    dynamic_stop_strategy = AtrDynamicStopStrategy(data)
    dynamic_stop_metrics = dynamic_stop_strategy.run_strategy()
    print(f"ATR动态止损策略总收益率: {dynamic_stop_metrics['总收益率']:.2f}%")
    print(f"ATR动态止损策略年化收益率: {dynamic_stop_metrics['年化收益率']:.2f}%\n")
    
    print("=== 所有ATR策略运行完成 ===")
    
    # 返回所有策略的指标
    return {
        'breakout': breakout_metrics,
        'channel': channel_metrics,
        'trend_following': trend_metrics,
        'mean_reversion': reversion_metrics,
        'dynamic_stop': dynamic_stop_metrics
    }

if __name__ == "__main__":
    run_all_strategies()
