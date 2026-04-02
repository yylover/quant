import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def generate_hs300_data():
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
    
    # 创建DataFrame
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.003, len(dates))),
        'high': prices * (1 + np.random.normal(0.004, 0.006, len(dates))),
        'low': prices * (1 + np.random.normal(-0.004, 0.006, len(dates))),
        'close': prices,
        'volume': np.random.randint(10000000, 80000000, len(dates))
    })
    
    # 确保high >= close, open，low<= close, open
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    data.set_index('date', inplace=True)
    
    return data

def run_all_strategies():
    """运行所有布林线策略"""
    output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/boll"
    
    # 生成数据
    data = generate_hs300_data()
    
    # 导入策略类
    from boll_breakout.strategy_boll_breakout import BollBreakoutStrategy
    from boll_mean_reversion.strategy_boll_mean_reversion import BollMeanReversionStrategy
    from boll_band_width.strategy_boll_band_width import BollBandWidthStrategy
    from boll_rsi.strategy_boll_rsi import BollRSIStrategy
    from boll_macd.strategy_boll_macd import BollMACDStrategy
    
    # 运行各个策略
    strategies = []
    
    # 1. 布林线突破策略
    breakout_strategy = BollBreakoutStrategy(data)
    breakout_metrics = breakout_strategy.run_strategy()
    strategies.append(breakout_metrics)
    
    # 2. 布林线均值回归策略
    mean_reversion_strategy = BollMeanReversionStrategy(data)
    mean_reversion_metrics = mean_reversion_strategy.run_strategy()
    strategies.append(mean_reversion_metrics)
    
    # 3. 布林带宽度策略
    band_width_strategy = BollBandWidthStrategy(data)
    band_width_metrics = band_width_strategy.run_strategy()
    strategies.append(band_width_metrics)
    
    # 4. 布林线RSI结合策略
    rsi_strategy = BollRSIStrategy(data)
    rsi_metrics = rsi_strategy.run_strategy()
    strategies.append(rsi_metrics)
    
    # 5. 布林线MACD结合策略
    macd_strategy = BollMACDStrategy(data)
    macd_metrics = macd_strategy.run_strategy()
    strategies.append(macd_metrics)
    
    # 创建策略结果DataFrame
    results_df = pd.DataFrame(strategies)
    
    # 保存策略结果
    results_df.to_csv(f"{output_dir}/boll_strategy_results.csv", index=False)
    
    # 生成综合分析报告
    generate_analysis_report(results_df, output_dir)
    
    return strategies

def generate_analysis_report(results_df, output_dir):
    """生成综合分析报告"""
    # 按年化收益率排序
    results_df_sorted = results_df.sort_values('年化收益率', ascending=False)
    
    # 创建Markdown报告
    report_content = f"""# 布林线策略综合分析报告

## 策略表现对比

| 排名 | 策略名称 | 年化收益率 | 总收益率 | 最大回撤 | 胜率 | 盈亏比 | 交易次数 |
|------|----------|------------|----------|----------|------|--------|----------|
"""
    
    for i, row in enumerate(results_df_sorted.itertuples(), 1):
        report_content += f"| {i} | {row.策略名称} | {row.年化收益率:.2f}% | {row.总收益率:.2f}% | {row.最大回撤:.2f}% | {row.胜率:.2f}% | {row.盈亏比:.2f} | {row.总交易次数} |\n"
    
    report_content += "\n## 策略详细分析\n\n"
    
    for _, row in results_df_sorted.iterrows():
        report_content += f"""### {row['策略名称']}

- **年化收益率**: {row['年化收益率']:.2f}%
- **总收益率**: {row['总收益率']:.2f}%
- **最大回撤**: {row['最大回撤']:.2f}%
- **胜率**: {row['胜率']:.2f}%
- **盈亏比**: {row['盈亏比']:.2f}
- **交易次数**: {row['总交易次数']}
- **参数配置**: {row['参数']}

"""
    
    report_content += """## 策略评估与建议

### 最佳策略

根据回测结果，表现最佳的策略是：**""" + results_df_sorted.iloc[0]['策略名称'] + """**，年化收益率达到**""" + f"{results_df_sorted.iloc[0]['年化收益率']:.2f}%" + """**。

### 策略特点总结

1. **突破策略**：捕捉价格突破后的趋势，适合趋势市场。
2. **均值回归策略**：利用价格回归中轨的特性，适合震荡市场。
3. **宽度策略**：基于波动率变化预测行情，信号质量高但频率低。
4. **RSI结合策略**：结合动量指标确认超买超卖状态，信号质量高。
5. **MACD结合策略**：结合趋势指标确认趋势方向，在趋势市场中表现较好。

### 优化建议

1. **参数优化**：针对不同市场环境调整策略参数
2. **策略组合**：结合多个策略的信号，提高交易决策质量
3. **风险控制**：添加止损机制，控制单笔交易风险
4. **市场适应性**：根据市场状态动态选择合适的策略
5. **多指标结合**：结合均线、成交量等其他指标确认信号

"""
    
    # 保存报告
    with open(f"{output_dir}/布林线策略综合分析报告.md", 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print("综合分析报告已生成：布林线策略综合分析报告.md")

if __name__ == "__main__":
    print("开始运行布林线策略...")
    strategies = run_all_strategies()
    
    print("\n=== 策略运行完成 ===")
    print("所有策略已运行并生成分析报告")
    
    # 显示策略表现
    results_df = pd.DataFrame(strategies)
    results_df_sorted = results_df.sort_values('年化收益率', ascending=False)
    
    print("\n策略表现排名：")
    for i, row in enumerate(results_df_sorted.itertuples(), 1):
        print(f"{i}. {row.策略名称}: {row.年化收益率:.2f}% (最大回撤: {row.最大回撤:.2f}%)")
