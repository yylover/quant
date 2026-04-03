#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试个股/趋势分析功能
"""
import pandas as pd
from datetime import datetime

# 创建模拟数据
stock_data = pd.DataFrame({
    '股票名称': ['科大讯飞', '寒武纪', '中芯国际', '海康威视', '兆易创新', '三六零', '用友网络', '金山办公', '恒生电子', '东方财富',
               '万科A', '保利发展', '金地集团', '招商蛇口', '绿地控股', '华夏幸福', '金科股份', '蓝光发展', '泰禾集团', '荣盛发展'],
    '涨跌幅': [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0,
               -10.0, -10.0, -10.0, -10.0, -10.0, -10.0, -10.0, -10.0, -10.0, -10.0],
    '成交额': [520, 480, 450, 420, 400, 380, 360, 340, 320, 300,
               120, 110, 105, 100, 95, 90, 85, 80, 75, 70]
})

# 模拟MarketAnalysisSystem类的核心功能
class MarketAnalysisSystem:
    def analyze_stocks(self):
        """分析个股表现"""
        print("分析个股表现...")
        
        # 计算个股统计
        up_count = len(stock_data[stock_data['涨跌幅'] > 0])
        down_count = len(stock_data[stock_data['涨跌幅'] < 0])
        flat_count = len(stock_data[stock_data['涨跌幅'] == 0])
        
        # 获取涨停和跌停股票
        limit_up = stock_data[stock_data['涨跌幅'] >= 9.9].head(20)
        limit_down = stock_data[stock_data['涨跌幅'] <= -9.9].head(20)
        top_gainers = stock_data.nlargest(20, '涨跌幅')
        top_losers = stock_data.nsmallest(20, '涨跌幅')
        top_volume = stock_data.nlargest(20, '成交额')
        
        # 分板块分析个股
        stocks_analysis = self.analyze_stocks_by_sector(top_gainers, top_losers, top_volume)
        
        stocks = {
            '涨停股票': limit_up,
            '跌停股票': limit_down,
            '上涨家数': up_count,
            '下跌家数': down_count,
            '平盘家数': flat_count,
            '板块个股分析': stocks_analysis
        }
        
        return stocks
    
    def analyze_stocks_by_sector(self, top_gainers, top_losers, top_volume):
        """分板块分析个股"""
        # 龙头股分析
        sector_leaders = {
            'AI人工智能': ['科大讯飞', '寒武纪', '三六零', '用友网络', '金山办公'],
            '半导体': ['中芯国际', '韦尔股份', '北方华创', '兆易创新', '卓胜微'],
            '新能源': ['宁德时代', '比亚迪', '隆基绿能', '阳光电源', '亿纬锂能'],
            '医药生物': ['恒瑞医药', '药明康德', '迈瑞医疗', '智飞生物', '长春高新'],
            '金融服务': ['招商银行', '中国平安', '中信证券', '国泰君安', '华泰证券'],
            '消费': ['贵州茅台', '五粮液', '伊利股份', '海天味业', '美的集团']
        }
        
        # 市场总龙头（模拟）
        market_leaders = ['科大讯飞', '宁德时代', '比亚迪', '贵州茅台']
        
        # 连板龙头（模拟）
        consecutive_limit_up = ['寒武纪', '中芯国际', '三六零', '兆易创新']
        
        # 强势股分析
        strong_stocks = {
            '涨幅榜': ['科大讯飞', '寒武纪', '中芯国际', '海康威视', '兆易创新'],
            '资金榜': ['贵州茅台', '宁德时代', '比亚迪', '隆基绿能', '中国平安'],
            '龙虎榜': ['科大讯飞', '寒武纪', '中芯国际', '宁德时代', '比亚迪']
        }
        
        # 趋势股分析
        trend_stocks = {
            '均线多头': ['宁德时代', '比亚迪', '隆基绿能', '阳光电源', '亿纬锂能'],
            '成交量放大': ['科大讯飞', '寒武纪', '中芯国际', '海康威视', '兆易创新'],
            '资金持续流入': ['宁德时代', '比亚迪', '隆基绿能', '科大讯飞', '寒武纪']
        }
        
        # 风险股分析
        risk_stocks = {
            '跌幅榜': ['万科A', '保利发展', '金地集团', '招商蛇口', '绿地控股'],
            '资金流出': ['万科A', '保利发展', '金地集团', '华夏幸福', '金科股份'],
            '炸板': ['泰禾集团', '蓝光发展', '荣盛发展', '华远地产', '大悦城'],
            '减持': ['绿地控股', '金科股份', '蓝光发展', '泰禾集团', '荣盛发展']
        }
        
        return {
            '龙头股': {
                '板块龙头': sector_leaders,
                '市场总龙头': market_leaders,
                '连板龙头': consecutive_limit_up
            },
            '强势股': strong_stocks,
            '趋势股': trend_stocks,
            '风险股': risk_stocks
        }
    
    def calculate_bull_bear_indicators(self):
        """计算牛熊指标"""
        return {
            '市场状态': '震荡',
            '均线状态': '多头排列',
            'MACD状态': '金叉',
            'RSI状态': '超买',
            '当前波动率': 0.025
        }
    
    def generate_report(self):
        """生成完整的个股/趋势分析报告"""
        report = f"# 个股/趋势分析报告\n\n"
        report += f"**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 获取分析数据
        stocks = self.analyze_stocks()
        bull_bear = self.calculate_bull_bear_indicators()
        
        # 个股表现
        report += "## 个股表现\n\n"
        if stocks:
            report += f"- 涨停股票数: {len(stocks['涨停股票'])}\n"
            report += f"- 跌停股票数: {len(stocks['跌停股票'])}\n"
            report += f"- 上涨家数: {stocks['上涨家数']}\n"
            report += f"- 下跌家数: {stocks['下跌家数']}\n"
            
            # 分板块个股分析
            if '板块个股分析' in stocks:
                stock_analysis = stocks['板块个股分析']
                
                # 龙头股分析
                if '龙头股' in stock_analysis:
                    report += "\n### 龙头股分析\n"
                    leaders = stock_analysis['龙头股']
                    
                    if '板块龙头' in leaders:
                        report += "#### 板块龙头\n"
                        for sector, stocks_list in leaders['板块龙头'].items():
                            report += f"- **{sector}**: {', '.join(stocks_list)}\n"
                    
                    if '市场总龙头' in leaders:
                        report += "\n#### 市场总龙头\n"
                        report += f"- {', '.join(leaders['市场总龙头'])}\n"
                    
                    if '连板龙头' in leaders:
                        report += "\n#### 连板龙头\n"
                        report += f"- {', '.join(leaders['连板龙头'])}\n"
                
                # 强势股分析
                if '强势股' in stock_analysis:
                    report += "\n### 强势股分析\n"
                    strong = stock_analysis['强势股']
                    
                    if '涨幅榜' in strong:
                        report += "#### 涨幅榜\n"
                        report += f"- {', '.join(strong['涨幅榜'])}\n"
                    
                    if '资金榜' in strong:
                        report += "\n#### 资金榜\n"
                        report += f"- {', '.join(strong['资金榜'])}\n"
                    
                    if '龙虎榜' in strong:
                        report += "\n#### 龙虎榜\n"
                        report += f"- {', '.join(strong['龙虎榜'])}\n"
                
                # 趋势股分析
                if '趋势股' in stock_analysis:
                    report += "\n### 趋势股分析\n"
                    trend = stock_analysis['趋势股']
                    
                    if '均线多头' in trend:
                        report += "#### 均线多头\n"
                        report += f"- {', '.join(trend['均线多头'])}\n"
                    
                    if '成交量放大' in trend:
                        report += "\n#### 成交量放大\n"
                        report += f"- {', '.join(trend['成交量放大'])}\n"
                    
                    if '资金持续流入' in trend:
                        report += "\n#### 资金持续流入\n"
                        report += f"- {', '.join(trend['资金持续流入'])}\n"
                
                # 风险股分析
                if '风险股' in stock_analysis:
                    report += "\n### 风险股分析\n"
                    risk = stock_analysis['风险股']
                    
                    if '跌幅榜' in risk:
                        report += "#### 跌幅榜\n"
                        report += f"- {', '.join(risk['跌幅榜'])}\n"
                    
                    if '资金流出' in risk:
                        report += "\n#### 资金流出\n"
                        report += f"- {', '.join(risk['资金流出'])}\n"
                    
                    if '炸板' in risk:
                        report += "\n#### 炸板\n"
                        report += f"- {', '.join(risk['炸板'])}\n"
                    
                    if '减持' in risk:
                        report += "\n#### 减持\n"
                        report += f"- {', '.join(risk['减持'])}\n"
        
        # 趋势分析预测
        report += "\n## 趋势分析预测\n\n"
        
        # 短期趋势预测（1-3日）
        report += "### 短期趋势预测（1-3日）\n"
        report += "- **情绪**: 当前情绪状态良好，涨停家数较多，赚钱效应明显\n"
        report += "- **资金**: 主力资金持续流入，北向资金大幅净流入\n"
        report += "- **板块轮动**: 主线板块持续性较强，切换速度较慢\n"
        
        # 中期趋势预测（1-4周）
        report += "\n### 中期趋势预测（1-4周）\n"
        if bull_bear:
            if bull_bear['市场状态'] == '牛市':
                report += "- **指数趋势**: 市场处于牛市状态，指数有望继续上行\n"
                report += "- **主线持续性**: 主线板块资金集中，持续性较强\n"
                report += "- **宏观政策**: 政策支持力度较大，有利于市场稳定\n"
            elif bull_bear['市场状态'] == '熊市':
                report += "- **指数趋势**: 市场处于熊市状态，指数可能继续下行\n"
                report += "- **主线持续性**: 主线板块持续性较差，轮动较快\n"
                report += "- **宏观政策**: 政策有待进一步观察\n"
            else:
                report += "- **指数趋势**: 市场处于震荡状态，指数上下波动\n"
                report += "- **主线持续性**: 主线板块持续性一般，需要观察\n"
                report += "- **宏观政策**: 政策偏中性，市场结构性机会\n"
        
        # 投资建议
        report += "\n## 投资建议\n\n"
        report += "### 策略建议\n"
        report += "- **做多主线**: 重点关注资金持续流入的主线板块，参与龙头股\n"
        report += "- **规避风险**: 远离资金流出、跌幅较大的板块和个股\n"
        report += "- **控制仓位**: 根据市场状态调整仓位，牛市可适当提高仓位，熊市控制仓位\n"
        report += "- **交易策略**: 结合技术指标，高抛低吸，灵活操作\n"
        report += "- **止损止盈**: 设置合理的止损位，保护本金安全\n"
        
        return report

# 创建分析系统实例
analysis_system = MarketAnalysisSystem()

# 生成报告
report = analysis_system.generate_report()

# 保存报告到文件
report_filename = f"stock_analysis_report_{datetime.now().strftime('%Y%m%d')}.md"
with open(report_filename, 'w', encoding='utf-8') as f:
    f.write(report)

print(f"报告已生成: {report_filename}")
print("\n=== 报告预览 ===")
print(report[:1500] + "...")  # 显示前1500个字符作为预览
