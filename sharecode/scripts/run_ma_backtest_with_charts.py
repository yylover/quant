#!/usr/bin/env python3
"""
均线回测策略可视化运行脚本
支持从 CSV 文件加载数据并生成回测图表
"""

import sys
import os
import argparse
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sharecode.strategies.ma_backtest_chart import (
    MABacktestChart, 
    run_backtest_with_chart,
    batch_backtest
)


def main():
    parser = argparse.ArgumentParser(
        description='均线回测策略可视化工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单只股票回测
  python run_ma_backtest_with_charts.py -f ../data/hs300_daily.csv -s 20 -l 60
  
  # 指定日期范围
  python run_ma_backtest_with_charts.py -f ../data/hs300_daily.csv --start 2020-01-01 --end 2023-12-31
  
  # 批量回测
  python run_ma_backtest_with_charts.py --batch -d ../data/ -o ../out/
  
  # 显示图表（不保存）
  python run_ma_backtest_with_charts.py -f ../data/hs300_daily.csv --show
        """
    )
    
    # 数据参数
    parser.add_argument('-f', '--file', type=str,
                       help='数据文件路径 (CSV格式)')
    parser.add_argument('-d', '--data-dir', type=str,
                       help='数据目录路径（用于批量回测）')
    
    # 策略参数
    parser.add_argument('-s', '--short-window', type=int, default=20,
                       help='短期均线窗口 (默认: 20)')
    parser.add_argument('-l', '--long-window', type=int, default=60,
                       help='长期均线窗口 (默认: 60)')
    
    # 日期参数
    parser.add_argument('--start', '--start-date', type=str, dest='start_date',
                       help='开始日期 (格式: YYYY-MM-DD)')
    parser.add_argument('--end', '--end-date', type=str, dest='end_date',
                       help='结束日期 (格式: YYYY-MM-DD)')
    
    # 输出参数
    parser.add_argument('-o', '--output', type=str, default='./',
                       help='输出目录 (默认: 当前目录)')
    parser.add_argument('--show', action='store_true',
                       help='显示图表窗口')
    parser.add_argument('--no-save', action='store_true',
                       help='不保存图表文件')
    
    # 批量回测参数
    parser.add_argument('--batch', action='store_true',
                       help='批量回测模式')
    parser.add_argument('--short-windows', type=int, nargs='+', default=[10, 20],
                       help='短期均线窗口列表 (批量模式)')
    parser.add_argument('--long-windows', type=int, nargs='+', default=[30, 60],
                       help='长期均线窗口列表 (批量模式)')
    
    # 图表参数
    parser.add_argument('--figsize', type=int, nargs=2, default=[16, 12],
                       help='图表尺寸 (宽 高)')
    parser.add_argument('--dpi', type=int, default=100,
                       help='图表分辨率 (默认: 100)')
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.batch and not args.file:
        parser.error("非批量模式下必须指定数据文件 (-f)")
    
    if args.batch and not args.data_dir:
        parser.error("批量模式下必须指定数据目录 (-d)")
    
    if args.short_window >= args.long_window:
        parser.error("短期均线窗口必须小于长期均线窗口")
    
    # 创建输出目录
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # 从配置创建图表配置
    from sharecode.strategies.ma_visualization import ChartConfig
    config = ChartConfig(
        figsize=tuple(args.figsize),
        dpi=args.dpi
    )
    
    try:
        if args.batch:
            # 批量回测模式
            print("="*60)
            print("批量回测模式")
            print("="*60)
            print(f"数据目录: {args.data_dir}")
            print(f"短期窗口: {args.short_windows}")
            print(f"长期窗口: {args.long_windows}")
            print(f"输出目录: {args.output}")
            print("="*60)
            
            results = batch_backtest(
                data_dir=args.data_dir,
                short_windows=args.short_windows,
                long_windows=args.long_windows,
                output_dir=args.output,
                start_date=args.start_date,
                end_date=args.end_date
            )
            
            if not results.empty:
                print("\n" + "="*60)
                print("批量回测完成")
                print("="*60)
                print(f"共完成 {len(results)} 组回测")
                print("\n最佳参数组合（按总收益率排序）：")
                best = results.nlargest(5, 'total_return')[
                    ['stock_code', 'short_window', 'long_window', 
                     'total_return', 'max_drawdown', 'sharpe_ratio']
                ]
                print(best.to_string(index=False))
            
        else:
            # 单只股票回测模式
            print("="*60)
            print("均线回测策略")
            print("="*60)
            print(f"数据文件: {args.file}")
            print(f"均线参数: MA{args.short_window} / MA{args.long_window}")
            if args.start_date:
                print(f"开始日期: {args.start_date}")
            if args.end_date:
                print(f"结束日期: {args.end_date}")
            print("="*60)
            
            # 创建回测器
            backtest = MABacktestChart(
                short_window=args.short_window,
                long_window=args.long_window,
                config=config
            )
            
            # 加载数据
            print(f"\n正在加载数据...")
            backtest.load_data(args.file, args.start_date, args.end_date)
            
            # 运行回测
            print(f"正在运行回测...")
            backtest.run_backtest()
            
            # 打印摘要
            backtest.print_summary()
            
            # 生成图表
            if not args.no_save or args.show:
                print("正在生成图表...")
                
                # 构建保存路径
                stock_code = os.path.basename(args.file).split('_')[0]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                chart_filename = f"{stock_code}_MA{args.short_window}_{args.long_window}_{timestamp}.png"
                chart_path = os.path.join(args.output, chart_filename)
                
                title = f"{stock_code} 均线回测 (MA{args.short_window}/MA{args.long_window})"
                
                if args.no_save:
                    chart_path = None
                
                fig = backtest.generate_chart(
                    title=title,
                    save_path=chart_path
                )
                
                if args.show:
                    import matplotlib.pyplot as plt
                    plt.show()
                
                if chart_path:
                    print(f"\n图表已保存: {chart_path}")
        
        print("\n完成!")
        
    except FileNotFoundError as e:
        print(f"错误: 找不到文件 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
