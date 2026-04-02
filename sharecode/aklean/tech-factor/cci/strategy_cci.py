import pandas as pd
import numpy as np
import os

# 设置中文字体
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from cci_basic.strategy_cci_basic import CCIBasicStrategy
from cci_trend.strategy_cci_trend import CCITrendStrategy
from cci_divergence.strategy_cci_divergence import CCIDivergenceStrategy
from cci_multi_period.strategy_cci_multi_period import CCIMultiPeriodStrategy
from cci_dynamic_threshold.strategy_cci_dynamic_threshold import CCIDynamicThresholdStrategy

class CCIStrategyRunner:
    """CCI策略运行器"""
    
    def __init__(self):
        self.output_dir = "/Users/quickyang/Documents/workspace/develop/mycode/quant/sharecode/aklean/tech-factor/cci"
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
    
    def run_all_strategies(self):
        """运行所有CCI策略"""
        print("=== 开始运行CCI策略 ===")
        
        # 生成数据
        print("生成沪深300数据...")
        data = self.generate_hs300_data()
        
        # 运行各个策略
        results = []
        
        # 1. 基础超买超卖策略
        print("\n运行CCI基础超买超卖策略...")
        basic_strategy = CCIBasicStrategy(data, cci_period=20, overbought_threshold=100, oversold_threshold=-100)
        basic_metrics = basic_strategy.run_strategy()
        results.append(basic_metrics)
        print(f"基础策略完成：年化收益率 {basic_metrics['年化收益率']:.2f}%")
        
        # 2. 趋势跟踪策略
        print("\n运行CCI趋势跟踪策略...")
        trend_strategy = CCITrendStrategy(data, cci_period=20, ma_period=50, trend_threshold=0)
        trend_metrics = trend_strategy.run_strategy()
        results.append(trend_metrics)
        print(f"趋势策略完成：年化收益率 {trend_metrics['年化收益率']:.2f}%")
        
        # 3. 背离策略
        print("\n运行CCI背离策略...")
        divergence_strategy = CCIDivergenceStrategy(data, cci_period=20, divergence_period=20)
        divergence_metrics = divergence_strategy.run_strategy()
        results.append(divergence_metrics)
        print(f"背离策略完成：年化收益率 {divergence_metrics['年化收益率']:.2f}%")
        
        # 4. 多周期策略
        print("\n运行CCI多周期策略...")
        multi_period_strategy = CCIMultiPeriodStrategy(data, fast_period=14, slow_period=50)
        multi_period_metrics = multi_period_strategy.run_strategy()
        results.append(multi_period_metrics)
        print(f"多周期策略完成：年化收益率 {multi_period_metrics['年化收益率']:.2f}%")
        
        # 5. 动态阈值策略
        print("\n运行CCI动态阈值策略...")
        dynamic_threshold_strategy = CCIDynamicThresholdStrategy(data, cci_period=20, volatility_period=20, base_threshold=100)
        dynamic_threshold_metrics = dynamic_threshold_strategy.run_strategy()
        results.append(dynamic_threshold_metrics)
        print(f"动态阈值策略完成：年化收益率 {dynamic_threshold_metrics['年化收益率']:.2f}%")
        
        return results
    
    def generate_summary_report(self, results):
        """生成综合分析报告"""
        # 创建结果DataFrame
        df_results = pd.DataFrame(results)
        
        # 保存详细结果
        df_results.to_csv(f"{self.output_dir}/cci_strategy_results.csv", index=False, encoding='utf-8-sig')
        
        # 生成报告
        report = "# CCI策略综合分析报告\n\n"
        report += "## 策略表现对比\n\n"
        
        # 按年化收益率排序
        df_sorted = df_results.sort_values('年化收益率', ascending=False)
        
        report += "| 排名 | 策略名称 | 年化收益率 | 总收益率 | 最大回撤 | 胜率 | 盈亏比 | 交易次数 |\n"
        report += "|------|----------|------------|----------|----------|------|--------|----------|\n"
        
        for idx, row in df_sorted.iterrows():
            report += f"| {idx+1} | {row['策略名称']} | {row['年化收益率']:.2f}% | {row['总收益率']:.2f}% | {row['最大回撤']:.2f}% | {row['胜率']:.2f}% | {row['盈亏比']:.2f} | {row['总交易次数']} |\n"
        
        report += "\n## 策略详细分析\n\n"
        
        for row in df_sorted.itertuples():
            report += f"### {row.策略名称}\n\n"
            report += f"- **年化收益率**: {row.年化收益率:.2f}%\n"
            report += f"- **总收益率**: {row.总收益率:.2f}%\n"
            report += f"- **最大回撤**: {row.最大回撤:.2f}%\n"
            report += f"- **胜率**: {row.胜率:.2f}%\n"
            report += f"- **盈亏比**: {row.盈亏比:.2f}\n"
            report += f"- **交易次数**: {row.总交易次数}\n"
            report += f"- **参数配置**: {row.参数}\n\n"
        
        # 策略评估和建议
        report += "## 策略评估与建议\n\n"
        
        best_strategy = df_sorted.iloc[0]
        report += f"### 最佳策略\n\n"
        report += f"{best_strategy['策略名称']}表现最佳，年化收益率达到{best_strategy['年化收益率']:.2f}%。\n\n"
        
        # 策略特点分析
        report += "### 策略特点总结\n\n"
        report += "1. **趋势跟踪策略**：在长期趋势市场中表现较好，但震荡市场中可能产生较多假信号。\n"
        report += "2. **动态阈值策略**：自适应市场波动率，在不同市场环境下表现更稳定。\n"
        report += "3. **多周期策略**：结合短期和长期动量，信号更加稳定可靠。\n"
        report += "4. **背离策略**：能够识别趋势反转，但信号频率较低。\n"
        report += "5. **基础超买超卖策略**：简单直观，但在趋势市场中容易过早卖出。\n\n"
        
        # 优化建议
        report += "### 优化建议\n\n"
        report += "1. **参数优化**：针对不同市场环境调整策略参数\n"
        report += "2. **策略组合**：结合多个策略的信号，提高交易决策质量\n"
        report += "3. **风险控制**：添加止损机制，控制单笔交易风险\n"
        report += "4. **市场适应性**：根据市场状态动态选择合适的策略\n"
        report += "5. **多指标结合**：结合均线、成交量等其他指标确认信号\n\n"
        
        # 保存报告
        with open(f"{self.output_dir}/CCI策略综合分析报告.md", 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("\n=== 综合分析报告已生成 ===")
        print(f"报告文件：{self.output_dir}/CCI策略综合分析报告.md")
        print(f"详细数据：{self.output_dir}/cci_strategy_results.csv")
        
        return df_sorted

if __name__ == "__main__":
    runner = CCIStrategyRunner()
    results = runner.run_all_strategies()
    df_results = runner.generate_summary_report(results)
    
    print("\n=== 策略运行完成 ===")
    print("最佳策略：", df_results.iloc[0]['策略名称'])
    print("年化收益率：", f"{df_results.iloc[0]['年化收益率']:.2f}%")
