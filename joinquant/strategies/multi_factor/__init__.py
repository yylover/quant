# -*- coding: utf-8 -*-
"""
多因子选股策略包 (Multi-Factor Selection Strategies)
====================================================

本目录包含基于多因子选股原理实现的聚宽交易策略。

多因子选股策略的核心思想：
通过综合多个因子（如PB、ROE、市值、动量、成长、低波等）对股票进行打分排序，
选取综合质量最高的股票构建组合，配合择时信号控制仓位，
实现"好公司+好价格+好时机"的投资逻辑。

包含策略（共5个）：
-----------------

1. multi.py - PB+ROE双因子选股 + RSRS择时策略
   - 价值因子：PB（市净率）
   - 质量因子：ROE（净资产收益率）
   - 择时因子：RSRS（相对强弱回归斜率）
   - 持股数量：10只
   - 策略特点：经典价值投资+动量择时组合

2. three_factor.py - 三因子扩展策略（市值+价值+动量）
   - 市值因子（SMB）：小盘股因子
   - 价值因子（HML）：低估值因子
   - 动量因子（MOM）：过去12个月动量
   - 持股数量：15只
   - 策略特点：基于Fama-French三因子模型

3. growth_value.py - 成长价值复合策略（成长+价值+质量）
   - 成长因子：营收增长、利润增长、ROE增长
   - 价值因子：PE、PB、PEG
   - 质量因子：ROE、ROIC、毛利率
   - 持股数量：12只
   - 策略特点：成长性+估值安全边际+盈利质量

4. low_vol_quality.py - 低波质量策略（低波+质量+防御）
   - 低波因子：历史波动率、Beta、最大回撤
   - 质量因子：ROE、ROA、毛利率、债务/权益比
   - 防御因子：股息率、现金流/净利润
   - 持股数量：15只
   - 策略特点：防御性强，回撤小，适合保守投资者

5. sector_rotation.py - 行业轮动多因子策略
   - 行业动量因子：行业指数收益率、RSI突破
   - 行业估值因子：行业PE分位数、PB分位数
   - 行业景气度因子：行业营收增长、订单增速
   - 持仓结构：3个行业×4只股票=12只
   - 策略特点：捕捉行业轮动机会

适用场景：
---------
- 震荡偏牛市：价值因子有效，择时捕捉机会
- 中长期投资：基本面因子需要时间验证
- 价值投资风格：关注估值和盈利质量
- 能承受一定回撤：根据策略类型不同，回撤水平不同

风险提示：
---------
- 熊市表现：大部分多因子策略在熊市可能失效
- 价值陷阱：低估值可能是基本面恶化
- 行业集中：可能选入同一行业多只股票（行业轮动策略除外）
- 择时滞后：RSRS在急跌时可能滞后
- 因子拥挤：多因子策略使用增多导致效果下降

改进方向：
---------
1. 选股层面：
   - 增加更多因子（PE、市值、动量等）
   - 因子权重优化（基于IC、ICIR）
   - 因子正交化（行业、市值中性化）

2. 择时层面：
   - 多信号融合（MA60、ATR等）
   - 动态阈值调整
   - 增加止损机制

3. 交易层面：
   - 降低换手率
   - 分批建仓
   - 仓位动态管理

使用示例：
---------
在聚宽平台回测时，直接使用对应的策略文件即可。

如需调整参数，修改各策略文件中 set_parameter() 函数中的全局变量。
"""

# 导入所有策略
from .multi import initialize as init_multi_factor
from .three_factor import initialize as init_three_factor
from .growth_value import initialize as init_growth_value
from .low_vol_quality import initialize as init_low_vol_quality
from .sector_rotation import initialize as init_sector_rotation

# 策略映射表（方便按名称调用）
STRATEGY_MAP = {
    'multi_factor_pb_roe': init_multi_factor,  # PB+ROE多因子选股
    'three_factor_ff': init_three_factor,  # 三因子扩展策略（市值+价值+动量）
    'growth_value_quality': init_growth_value,  # 成长价值复合策略
    'low_vol_quality_defensive': init_low_vol_quality,  # 低波质量策略
    'sector_rotation': init_sector_rotation,  # 行业轮动策略
}
