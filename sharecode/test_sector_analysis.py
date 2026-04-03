#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新增的板块分析功能
"""
import sys
import os
import pandas as pd

# 模拟MarketAnalysisSystem类的核心功能
class MarketAnalysisSystem:
    def analyze_sector_volume(self, industry_top10, concept_top10):
        """分析板块成交量（放量/缩量）"""
        volume_analysis = {}
        
        # 行业板块成交量分析
        industry_volume = []
        for idx, row in industry_top10.iterrows():
            volume_status = '放量' if row['成交量'] > 1000000000 else '正常'
            industry_volume.append({
                '板块名称': row['板块名称'],
                '成交量': row['成交量'],
                '成交额': row['成交额'],
                '量能状态': volume_status
            })
        
        # 概念板块成交量分析
        concept_volume = []
        for idx, row in concept_top10.iterrows():
            volume_status = '放量' if row['成交量'] > 1000000000 else '正常'
            concept_volume.append({
                '板块名称': row['板块名称'],
                '成交量': row['成交量'],
                '成交额': row['成交额'],
                '量能状态': volume_status
            })
        
        volume_analysis['行业板块'] = industry_volume
        volume_analysis['概念板块'] = concept_volume
        
        return volume_analysis
    
    def analyze_sector_trend(self, industry_top10, concept_top10):
        """分析板块趋势（均线、多头/空头/震荡）"""
        trend_analysis = {}
        
        # 行业板块趋势分析
        industry_trend = []
        for idx, row in industry_top10.iterrows():
            # 模拟均线状态
            ma_status = '多头排列' if row['涨跌幅'] > 1.0 else '震荡'
            trend_analysis_item = {
                '板块名称': row['板块名称'],
                '涨跌幅': row['涨跌幅'],
                '均线状态': ma_status,
                '趋势判断': '上升' if row['涨跌幅'] > 1.0 else '震荡' if row['涨跌幅'] > 0 else '下降'
            }
            industry_trend.append(trend_analysis_item)
        
        # 概念板块趋势分析
        concept_trend = []
        for idx, row in concept_top10.iterrows():
            ma_status = '多头排列' if row['涨跌幅'] > 1.5 else '震荡'
            trend_analysis_item = {
                '板块名称': row['板块名称'],
                '涨跌幅': row['涨跌幅'],
                '均线状态': ma_status,
                '趋势判断': '上升' if row['涨跌幅'] > 1.5 else '震荡' if row['涨跌幅'] > 0 else '下降'
            }
            concept_trend.append(trend_analysis_item)
        
        trend_analysis['行业板块'] = industry_trend
        trend_analysis['概念板块'] = concept_trend
        
        return trend_analysis
    
    def analyze_sector_rotation(self, industry_top10, industry_bottom10):
        """分析板块轮动情况"""
        leading_sectors = industry_top10.head(3)['板块名称'].tolist()
        falling_sectors = industry_bottom10.head(3)['板块名称'].tolist()
        
        # 判断持续性（基于涨幅大小）
        top_gain = industry_top10.iloc[0]['涨跌幅']
        if top_gain > 3.0:
            continuity = '强'
        elif top_gain > 1.5:
            continuity = '中等'
        else:
            continuity = '弱'
        
        # 计算切换速度
        if top_gain >= 2.0:
            rotation_speed = '慢'  # 主线持续
        else:
            rotation_speed = '快'  # 轮动较快
        
        # 构建梯队（涨幅排序）
        sector_tiers = []
        for idx, row in industry_top10.head(5).iterrows():
            sector_tiers.append(f"{row['板块名称']}({row['涨跌幅']:.1f}%)")
        
        return {
            '领涨板块': leading_sectors,
            '领跌板块': falling_sectors,
            '持续性': continuity,
            '切换速度': rotation_speed,
            '梯队': sector_tiers
        }
    
    def analyze_sector_tiers(self, industry_top10, concept_top10):
        """分析板块梯队（主线、分支、跟风、轮动）"""
        # 主线板块：涨幅最高、资金最多
        main_sector = industry_top10.iloc[0]['板块名称']
        
        # 分支板块：主线的细分概念
        branch_sectors = []
        if main_sector == '新能源':
            branch_sectors = ['光伏', '新能源车']
        elif main_sector == '半导体':
            branch_sectors = ['AI人工智能', '算力']
        elif main_sector == '医药生物':
            branch_sectors = ['创新药']
        
        # 跟风板块：跟随主线但持续性差
        follow_sectors = industry_top10[industry_top10['涨跌幅'] < 1.0]['板块名称'].tolist()[:2]
        
        # 轮动板块：一日游、无持续性
        rotation_sectors = industry_top10[industry_top10['涨跌幅'] < 0.5]['板块名称'].tolist()[:2]
        
        return {
            '主线板块': main_sector,
            '分支板块': branch_sectors,
            '跟风板块': follow_sectors,
            '轮动板块': rotation_sectors
        }
    
    def analyze_sector_leaders(self, industry_top10, concept_top10):
        """分析板块龙头（每个板块的龙头股、涨幅、资金、连板）"""
        sector_leaders = {}
        
        # 行业板块龙头
        industry_leaders = {
            '新能源': {'龙头股': '宁德时代', '涨幅': 5.2, '资金净流入': 15.2, '连板数': 0},
            '半导体': {'龙头股': '中芯国际', '涨幅': 4.8, '资金净流入': 8.6, '连板数': 0},
            '医药生物': {'龙头股': '恒瑞医药', '涨幅': 3.5, '资金净流入': 6.2, '连板数': 0},
            '消费': {'龙头股': '贵州茅台', '涨幅': 2.8, '资金净流入': 5.2, '连板数': 0},
            '通信': {'龙头股': '中兴通讯', '涨幅': 2.5, '资金净流入': 4.8, '连板数': 0},
            '计算机': {'龙头股': '科大讯飞', '涨幅': 3.8, '资金净流入': 7.8, '连板数': 1},
            '电气设备': {'龙头股': '阳光电源', '涨幅': 2.2, '资金净流入': 4.5, '连板数': 0},
            '机械设备': {'龙头股': '三一重工', '涨幅': 1.8, '资金净流入': 3.2, '连板数': 0},
            '化工': {'龙头股': '万华化学', '涨幅': 1.5, '资金净流入': 2.8, '连板数': 0},
            '有色金属': {'龙头股': '赣锋锂业', '涨幅': 1.2, '资金净流入': 2.5, '连板数': 0}
        }
        
        # 概念板块龙头
        concept_leaders = {
            'AI人工智能': {'龙头股': '寒武纪', '涨幅': 6.5, '资金净流入': 12.8, '连板数': 2},
            '算力': {'龙头股': '浪潮信息', '涨幅': 5.8, '资金净流入': 10.5, '连板数': 1},
            '创新药': {'龙头股': '药明康德', '涨幅': 4.2, '资金净流入': 7.5, '连板数': 0},
            '光伏': {'龙头股': '隆基绿能', '涨幅': 3.8, '资金净流入': 8.2, '连板数': 0},
            '机器人': {'龙头股': '机器人', '涨幅': 5.2, '资金净流入': 9.8, '连板数': 1},
            '数字经济': {'龙头股': '用友网络', '涨幅': 4.5, '资金净流入': 7.2, '连板数': 0},
            '云计算': {'龙头股': '金山办公', '涨幅': 4.2, '资金净流入': 6.8, '连板数': 0},
            '大数据': {'龙头股': '东方财富', '涨幅': 3.8, '资金净流入': 6.5, '连板数': 0},
            '区块链': {'龙头股': '恒生电子', '涨幅': 3.5, '资金净流入': 6.2, '连板数': 0},
            '新能源车': {'龙头股': '比亚迪', '涨幅': 4.8, '资金净流入': 9.5, '连板数': 0}
        }
        
        sector_leaders['行业板块'] = industry_leaders
        sector_leaders['概念板块'] = concept_leaders
        
        return sector_leaders
    
    def identify_main_sectors(self, industry_top10, concept_top10):
        """识别主线板块"""
        # 找出涨幅最大的板块作为最强板块
        strongest_sector = industry_top10.iloc[0]['板块名称']
        max_gain = industry_top10.iloc[0]['涨跌幅']
        
        # 判断资金集中度（基于成交额）
        total_volume = industry_top10['成交额'].sum()
        top_sector_volume = industry_top10.iloc[0]['成交额']
        concentration = '高' if top_sector_volume / total_volume > 0.25 else '中等'
        
        # 模拟龙头股
        if strongest_sector == '新能源':
            leader_stocks = '宁德时代、比亚迪、隆基绿能'
        elif strongest_sector == '半导体':
            leader_stocks = '中芯国际、韦尔股份、北方华创'
        elif strongest_sector == '医药生物':
            leader_stocks = '恒瑞医药、药明康德、迈瑞医疗'
        else:
            leader_stocks = '板块龙头股'
        
        # 模拟持续时间
        if max_gain > 3.0:
            duration = '5天以上'
        elif max_gain > 1.5:
            duration = '3-5天'
        else:
            duration = '1-3天'
        
        return {
            '最强板块': strongest_sector,
            '持续时间': duration,
            '资金集中度': concentration,
            '龙头股': leader_stocks
        }

# 创建分析系统实例
analysis_system = MarketAnalysisSystem()

# 创建模拟数据
industry_top10 = pd.DataFrame({
    '板块名称': ['新能源', '半导体', '医药生物', '消费', '通信', '计算机', '电气设备', '机械设备', '化工', '有色金属'],
    '涨跌幅': [2.5, 1.8, 0.9, 1.2, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2],
    '成交量': [1200000000, 950000000, 800000000, 750000000, 680000000, 620000000, 580000000, 550000000, 520000000, 500000000],
    '成交额': [45000000000, 38000000000, 32000000000, 30000000000, 28000000000, 26000000000, 24000000000, 22000000000, 20000000000, 18000000000]
})

concept_top10 = pd.DataFrame({
    '板块名称': ['AI人工智能', '算力', '创新药', '光伏', '机器人', '数字经济', '云计算', '大数据', '区块链', '新能源车'],
    '涨跌幅': [3.2, 2.8, 1.5, 0.8, 2.1, 1.9, 1.7, 1.6, 1.4, 1.3],
    '成交量': [1500000000, 1300000000, 900000000, 850000000, 1100000000, 1050000000, 980000000, 950000000, 920000000, 900000000],
    '成交额': [60000000000, 52000000000, 36000000000, 34000000000, 44000000000, 42000000000, 39000000000, 38000000000, 37000000000, 36000000000]
})

industry_bottom10 = pd.DataFrame({
    '板块名称': ['房地产', '建筑材料', '纺织服装', '煤炭', '钢铁', '石油石化', '银行', '非银金融', '公用事业', '交通运输'],
    '涨跌幅': [-1.2, -0.8, -0.7, -0.6, -0.5, -0.4, -0.3, -0.2, -0.1, 0.0],
    '成交量': [800000000, 750000000, 700000000, 680000000, 650000000, 620000000, 600000000, 580000000, 550000000, 520000000],
    '成交额': [15000000000, 14000000000, 13000000000, 12500000000, 12000000000, 11500000000, 11000000000, 10500000000, 10000000000, 9500000000]
})

# 测试各个新功能
print("=== 测试板块成交量分析 ===")
volume_analysis = analysis_system.analyze_sector_volume(industry_top10, concept_top10)
print("行业板块成交量:", volume_analysis['行业板块'][:3])
print("概念板块成交量:", volume_analysis['概念板块'][:3])

print("\n=== 测试板块趋势分析 ===")
trend_analysis = analysis_system.analyze_sector_trend(industry_top10, concept_top10)
print("行业板块趋势:", trend_analysis['行业板块'][:3])
print("概念板块趋势:", trend_analysis['概念板块'][:3])

print("\n=== 测试板块轮动分析 ===")
rotation_analysis = analysis_system.analyze_sector_rotation(industry_top10, industry_bottom10)
print("轮动分析:", rotation_analysis)

print("\n=== 测试板块梯队分析 ===")
tiers_analysis = analysis_system.analyze_sector_tiers(industry_top10, concept_top10)
print("梯队分析:", tiers_analysis)

print("\n=== 测试板块龙头分析 ===")
leaders_analysis = analysis_system.analyze_sector_leaders(industry_top10, concept_top10)
print("行业板块龙头:", list(leaders_analysis['行业板块'].keys())[:3])
print("概念板块龙头:", list(leaders_analysis['概念板块'].keys())[:3])

print("\n=== 测试主线板块判断 ===")
main_sectors = analysis_system.identify_main_sectors(industry_top10, concept_top10)
print("主线板块:", main_sectors)

print("\n所有测试完成！")
