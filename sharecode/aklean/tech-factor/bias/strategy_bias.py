import pandas as pd
import numpy as np

def generate_hs300_data():
    """生成模拟的沪深300数据（近5年）"""
    np.random.seed(42)
    
    end_date = pd.Timestamp('2026-04-01')
    start_date = end_date - pd.Timedelta(days=5*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 基础价格趋势 - 降低趋势强度
    base_price = 4000
    trend = np.linspace(0, 0.2, len(dates))  # 从0.4降低到0.2
    
    # 添加季节性和周期性波动
    seasonal = 0.04 * np.sin(np.linspace(0, 10*np.pi, len(dates)))
    cyclic = 0.03 * np.cos(np.linspace(0, 5*np.pi, len(dates)))
    
    # 添加随机波动 - 增加波动性
    volatility = np.random.normal(0, 0.015, len(dates))  # 从0.01增加到0.015
    
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
    """运行所有BIAS策略"""
    print("=== BIAS策略集合运行入口 ===\n")
    
    # 生成数据
    data = generate_hs300_data()
    print(f"数据生成完成，共{len(data)}条记录")
    print(f"数据时间范围: {data.index.min()} 到 {data.index.max()}")
    
    # 运行基础策略
    print("\n" + "="*40)
    print("运行基础超买超卖策略")
    print("="*40)
    from bias_basic.strategy_bias_basic import BiasBasicStrategy
    basic_strategy = BiasBasicStrategy(data)
    basic_strategy.calculate_bias()
    basic_strategy.generate_signals()
    basic_strategy.backtest()
    metrics = basic_strategy.calculate_metrics()
    basic_strategy.plot_results()
    print(f"基础策略总收益率: {metrics['total_return']:.2f}%")
    print(f"基础策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行多周期策略
    print("\n" + "="*40)
    print("运行多周期配合策略")
    print("="*40)
    from bias_multi_period.strategy_bias_multi_period import BiasMultiPeriodStrategy
    multi_strategy = BiasMultiPeriodStrategy(data)
    multi_strategy.calculate_bias()
    multi_strategy.generate_signals()
    multi_strategy.backtest()
    metrics = multi_strategy.calculate_metrics()
    multi_strategy.plot_results()
    print(f"多周期策略总收益率: {metrics['total_return']:.2f}%")
    print(f"多周期策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行背离策略
    print("\n" + "="*40)
    print("运行BIAS背离策略")
    print("="*40)
    from bias_divergence.strategy_bias_divergence import BiasDivergenceStrategy
    divergence_strategy = BiasDivergenceStrategy(data)
    divergence_strategy.calculate_bias()
    divergence_strategy.detect_divergence()
    divergence_strategy.generate_signals()
    divergence_strategy.backtest()
    metrics = divergence_strategy.calculate_metrics()
    divergence_strategy.plot_results()
    print(f"背离策略总收益率: {metrics['total_return']:.2f}%")
    print(f"背离策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行自适应策略
    print("\n" + "="*40)
    print("运行自适应参数策略")
    print("="*40)
    from bias_adaptive.strategy_bias_adaptive import BiasAdaptiveStrategy
    adaptive_strategy = BiasAdaptiveStrategy(data)
    adaptive_strategy.calculate_volatility()
    adaptive_strategy.calculate_adaptive_thresholds()
    adaptive_strategy.calculate_bias()
    adaptive_strategy.generate_signals()
    adaptive_strategy.backtest()
    metrics = adaptive_strategy.calculate_metrics()
    adaptive_strategy.plot_results()
    print(f"自适应策略总收益率: {metrics['total_return']:.2f}%")
    print(f"自适应策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行BIAS+成交量配合策略
    print("\n" + "="*40)
    print("运行BIAS+成交量配合策略")
    print("="*40)
    from bias_volume.strategy_bias_volume import BiasVolumeStrategy
    volume_strategy = BiasVolumeStrategy(data)
    volume_strategy.calculate_bias()
    volume_strategy.calculate_volume_indicators()
    volume_strategy.generate_signals()
    volume_strategy.backtest()
    metrics = volume_strategy.calculate_metrics()
    volume_strategy.plot_results()
    print(f"BIAS+成交量策略总收益率: {metrics['total_return']:.2f}%")
    print(f"BIAS+成交量策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行BIAS布林带策略
    print("\n" + "="*40)
    print("运行BIAS布林带策略")
    print("="*40)
    from bias_bollinger.strategy_bias_bollinger import BiasBollingerStrategy
    bollinger_strategy = BiasBollingerStrategy(data)
    bollinger_strategy.calculate_bias()
    bollinger_strategy.calculate_bollinger_bands()
    bollinger_strategy.generate_signals()
    bollinger_strategy.backtest()
    metrics = bollinger_strategy.calculate_metrics()
    bollinger_strategy.plot_results()
    print(f"BIAS布林带策略总收益率: {metrics['total_return']:.2f}%")
    print(f"BIAS布林带策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行BIAS+MACD背离策略
    print("\n" + "="*40)
    print("运行BIAS+MACD背离策略")
    print("="*40)
    from bias_macd.strategy_bias_macd import BiasMacdStrategy
    macd_strategy = BiasMacdStrategy(data)
    macd_strategy.calculate_bias()
    macd_strategy.calculate_macd()
    macd_strategy.detect_bias_divergence()
    macd_strategy.detect_macd_divergence()
    macd_strategy.generate_signals()
    macd_strategy.backtest()
    metrics = macd_strategy.calculate_metrics()
    macd_strategy.plot_results()
    print(f"BIAS+MACD策略总收益率: {metrics['total_return']:.2f}%")
    print(f"BIAS+MACD策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行BIAS+RSI策略
    print("\n" + "="*40)
    print("运行BIAS+RSI策略")
    print("="*40)
    from bias_rsi.strategy_bias_rsi import BiasRsiStrategy
    rsi_strategy = BiasRsiStrategy(data)
    rsi_strategy.calculate_bias()
    rsi_strategy.calculate_rsi()
    rsi_strategy.generate_signals()
    rsi_strategy.backtest()
    metrics = rsi_strategy.calculate_metrics()
    rsi_strategy.plot_results()
    print(f"BIAS+RSI策略总收益率: {metrics['total_return']:.2f}%")
    print(f"BIAS+RSI策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行BIAS通道突破策略
    print("\n" + "="*40)
    print("运行BIAS通道突破策略")
    print("="*40)
    from bias_channel.strategy_bias_channel import BiasChannelStrategy
    channel_strategy = BiasChannelStrategy(data)
    channel_strategy.calculate_bias()
    channel_strategy.calculate_channel()
    channel_strategy.generate_signals()
    channel_strategy.backtest()
    metrics = channel_strategy.calculate_metrics()
    channel_strategy.plot_results()
    print(f"BIAS通道突破策略总收益率: {metrics['total_return']:.2f}%")
    print(f"BIAS通道突破策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行BIAS均线系统策略
    print("\n" + "="*40)
    print("运行BIAS均线系统策略")
    print("="*40)
    from bias_ma_system.strategy_bias_ma_system import BiasMaSystemStrategy
    ma_system_strategy = BiasMaSystemStrategy(data)
    ma_system_strategy.calculate_bias()
    ma_system_strategy.calculate_moving_averages()
    ma_system_strategy.generate_signals()
    ma_system_strategy.backtest()
    metrics = ma_system_strategy.calculate_metrics()
    ma_system_strategy.plot_results()
    print(f"BIAS均线系统策略总收益率: {metrics['total_return']:.2f}%")
    print(f"BIAS均线系统策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行BIAS波动率策略
    print("\n" + "="*40)
    print("运行BIAS波动率策略")
    print("="*40)
    from bias_volatility.strategy_bias_volatility import BiasVolatilityStrategy
    volatility_strategy = BiasVolatilityStrategy(data)
    volatility_strategy.calculate_bias()
    volatility_strategy.calculate_atr()
    volatility_strategy.calculate_volatility()
    volatility_strategy.calculate_adaptive_thresholds()
    volatility_strategy.generate_signals()
    volatility_strategy.backtest()
    metrics = volatility_strategy.calculate_metrics()
    volatility_strategy.plot_results()
    print(f"BIAS波动率策略总收益率: {metrics['total_return']:.2f}%")
    print(f"BIAS波动率策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    # 运行BIAS多因子模型策略
    print("\n" + "="*40)
    print("运行BIAS多因子模型策略")
    print("="*40)
    from bias_multifactor.strategy_bias_multifactor import BiasMultifactorStrategy
    multifactor_strategy = BiasMultifactorStrategy(data)
    multifactor_strategy.calculate_bias()
    multifactor_strategy.calculate_rsi()
    multifactor_strategy.calculate_atr()
    multifactor_strategy.calculate_moving_averages()
    multifactor_strategy.calculate_volume_factors()
    multifactor_strategy.calculate_macd()
    multifactor_strategy.calculate_factor_scores()
    multifactor_strategy.calculate_composite_score()
    multifactor_strategy.generate_signals()
    multifactor_strategy.backtest()
    metrics = multifactor_strategy.calculate_metrics()
    multifactor_strategy.plot_results()
    print(f"BIAS多因子模型策略总收益率: {metrics['total_return']:.2f}%")
    print(f"BIAS多因子模型策略年化收益率: {metrics['annualized_return']:.2f}%")
    
    print("\n=== 所有BIAS策略运行完成 ===")

if __name__ == "__main__":
    run_all_strategies()
