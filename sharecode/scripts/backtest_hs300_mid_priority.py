"""
沪深300指数中优先级均值回归策略回测
测试: ATR回归、ROC回归、PSAR逆向
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import vectorbt as vbt
from sharecode.strategies.mean_reversion import (
    atr_reversion_signals,
    roc_reversion_signals,
    psar_reversion_signals,
)


def run_backtest(
    name: str,
    strategy_func,
    df: pd.DataFrame,
    **params
) -> dict:
    """运行单个策略回测

    Args:
        name: 策略名称
        strategy_func: 策略函数
        df: 价格数据
        **params: 策略参数

    Returns:
        策略回测结果字典
    """
    print(f"\n正在回测: {name}...")
    close, entries, exits = strategy_func(df, **params)

    # 创建投资组合
    portfolio = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=100000,
        fees=0.0003,  # 0.03% 手续费
        slippage=0.0001,  # 0.01% 滑点
        freq='1D'
    )

    # 计算基准收益(买入持有)
    benchmark_return = (close.iloc[-1] / close.iloc[0] - 1) * 100

    # 提取关键指标
    stats = portfolio.stats()

    # 尝试获取各项指标,使用try-except处理不同版本的兼容性问题
    result = {
        '策略名称': name,
        '基准收益率 (%)': benchmark_return,
    }

    # 总收益率
    try:
        result['总收益率 (%)'] = stats['Total Return [%]']
    except:
        result['总收益率 (%)'] = None

    # 最大回撤
    try:
        result['最大回撤 (%)'] = stats['Max Drawdown [%]']
    except:
        result['最大回撤 (%)'] = None

    # 夏普比率
    try:
        result['夏普比率'] = stats['Sharpe Ratio']
    except:
        result['夏普比率'] = None

    # 卡玛比率
    try:
        result['卡玛比率'] = stats['Calmar Ratio']
    except:
        result['卡玛比率'] = None

    # 胜率
    try:
        result['胜率 (%)'] = stats['Win Rate [%]']
    except:
        result['胜率 (%)'] = None

    # 交易次数
    try:
        result['交易次数'] = int(stats['# Trades'])
    except:
        result['交易次数'] = None

    # 年化收益
    try:
        result['年化收益率 (%)'] = stats['Annual Return [%]']
    except:
        result['年化收益率 (%)'] = None

    # 计算超额收益
    if result['总收益率 (%)'] is not None:
        result['超额收益 (%)'] = result['总收益率 (%)'] - benchmark_return
    else:
        result['超额收益 (%)'] = None

    print(f"  总收益率: {result['总收益率 (%)']:.2f}%")
    print(f"  最大回撤: {result['最大回撤 (%)']:.2f}%")
    print(f"  胜率: {result['胜率 (%)']:.2f}%")
    print(f"  超额收益: {result['超额收益 (%)']:.2f}%")

    return result


def main():
    # 加载数据
    print("加载沪深300数据...")
    df = pd.read_csv('data/hs300_daily.csv')
    print(f"数据范围: {df['日期'].iloc[0]} 至 {df['日期'].iloc[-1]}")
    print(f"数据行数: {len(df)}")

    # 定义策略配置
    strategies = [
        {
            'name': 'ATR 回归',
            'func': atr_reversion_signals,
            'params': {
                'window': 14,
                'atr_multiplier': 2.0,
            }
        },
        {
            'name': 'ROC 回归',
            'func': roc_reversion_signals,
            'params': {
                'window': 12,
                'low': -0.08,
                'high': 0.08,
            }
        },
        {
            'name': 'PSAR 逆向',
            'func': psar_reversion_signals,
            'params': {
                'af': 0.02,
                'max_af': 0.2,
                'lookback': 3,
            }
        },
    ]

    # 运行回测
    results = []
    for strategy in strategies:
        try:
            result = run_backtest(
                strategy['name'],
                strategy['func'],
                df,
                **strategy['params']
            )
            results.append(result)
        except Exception as e:
            print(f"回测失败 {strategy['name']}: {e}")
            import traceback
            traceback.print_exc()

    # 保存结果
    results_df = pd.DataFrame(results)
    output_file = 'data/hs300_mid_priority_backtest_results.csv'
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n回测结果已保存到: {output_file}")

    # 打印汇总表格
    print("\n" + "="*80)
    print("回测结果汇总")
    print("="*80)
    print(results_df.to_string(index=False))
    print("="*80)

    # 排序并找出最佳策略
    results_df_sorted = results_df.sort_values('总收益率 (%)', ascending=False)
    print(f"\n最佳策略: {results_df_sorted.iloc[0]['策略名称']}")
    print(f"总收益率: {results_df_sorted.iloc[0]['总收益率 (%)']:.2f}%")
    print(f"超额收益: {results_df_sorted.iloc[0]['超额收益 (%)']:.2f}%")

    # 统计跑赢基准的策略数量
    beat_benchmark = (results_df['超额收益 (%)'] > 0).sum()
    print(f"\n跑赢基准的策略数量: {beat_benchmark}/{len(results_df)}")


if __name__ == '__main__':
    main()
