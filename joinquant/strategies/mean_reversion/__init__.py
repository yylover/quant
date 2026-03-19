# -*- coding: utf-8 -*-
"""
均值回归策略包 (Mean Reversion Strategies)
===========================================

本目录包含基于均值回归原理实现的聚宽交易策略。

均值回归策略的核心思想：
价格在短期内会围绕均值波动，当价格偏离均值超过一定阈值时，
预期价格会回归到均值水平。在震荡市中，这类策略通过低买高卖
获得收益。

包含策略（共14个）：
-------------------

1. mean_reversion.py - 标准均值回归策略
   - 策略名称：zscore_reversion
   - 核心逻辑：价格偏离均值2倍标准差时反向交易
   - 参数：window(60), k(2.0)

2. bollinger_bands.py - 布林带策略
   - 策略名称：boll_reversion
   - 核心逻辑：价格触及下轨买入,回到中轨卖出
   - 参数：window(20), n_std(2.0)

3. rsi_strategy.py - RSI策略
   - 策略名称：rsi_reversion
   - 核心逻辑：RSI超卖(<30)买入,超买(>70)卖出
   - 参数：window(14), low(30), high(70)

4. zscore_reversion.py - Z-Score均值回归策略
   - 核心逻辑：价格偏离均值2倍标准差时反向交易
   - 参数：window(60), k(2.0)

5. deviation_reversion.py - 偏离度均值回归策略
   - 核心逻辑：价格偏离均线5%时反向交易
   - 参数：ma_window(20), entry_dev(0.05)

6. kdj_reversion.py - KDJ均值回归策略
   - 核心逻辑：K值低于20买入,高于80卖出
   - 参数：window(9), m1(3), m2(3), low(20), high(80)

7. williams_r_reversion.py - 威廉指标均值回归策略
   - 核心逻辑：%R低于-80买入,高于-20卖出
   - 参数：window(14), low(-80), high(-20)

8. cci_reversion.py - CCI均值回归策略
   - 核心逻辑：CCI低于-100买入,高于100卖出
   - 参数：window(20), low(-100), high(100)

9. macd_reversion.py - MACD均值回归策略
   - 核心逻辑：MACD柱状图偏离过大时反向交易
   - 参数：fast(12), slow(26), signal(9)

10. bias_reversion.py - 乖离率均值回归策略
    - 核心逻辑：乖离率偏离±5%时反向交易
    - 参数：window(20), low(-0.05), high(0.05)

11. bb_width_reversion.py - 布林带宽度回归策略
    - 核心逻辑：波动率压缩时买入
    - 参数：window(20), n_std(2.0), width_percentile(0.1)

12. atr_reversion.py - ATR均值回归策略
    - 核心逻辑：价格突破ATR通道时反向交易
    - 参数：window(14), atr_multiplier(2.0)

13. roc_reversion.py - ROC均值回归策略
    - 核心逻辑：ROC偏离±8%时反向交易
    - 参数：window(12), low(-0.08), high(0.08)

14. psar_reversion.py - PSAR均值回归策略
    - 核心逻辑：价格偏离PSAR线超过1.5倍标准差时反向交易
    - 参数：af(0.02), max_af(0.2), lookback(3)

适用场景：
---------
- 震荡市：价格在一定区间内反复波动
- 横盘整理：没有明确趋势方向
- 波动率适中：过高波动可能导致频繁止损，过低波动收益有限

风险提示：
---------
- 趋势市亏损：在单边牛市或熊市中持续亏损
- 假信号：超买超卖可能持续存在
- 需要结合：建议配合趋势判断、波动率过滤等指标使用

改进方向：
---------
- 添加趋势过滤：只在震荡行情中启用均值回归
- 动态参数：根据市场波动率调整阈值
- 多周期：结合不同时间周期的均值回归信号
- 风险控制：设置止损和仓位管理

使用示例：
---------
在聚宽平台回测时，直接使用对应的策略文件即可。

如需调整参数，修改 initialize() 函数中的全局变量。
"""

# 导入所有策略的初始化函数
from .mean_reversion import initialize as init_mean_reversion
from .bollinger_bands import initialize as init_bollinger_bands
from .rsi_strategy import initialize as init_rsi_strategy
from .zscore_reversion import initialize as init_zscore_reversion
from .deviation_reversion import initialize as init_deviation_reversion
from .kdj_reversion import initialize as init_kdj_reversion
from .williams_r_reversion import initialize as init_williams_r_reversion
from .cci_reversion import initialize as init_cci_reversion
from .macd_reversion import initialize as init_macd_reversion
from .bias_reversion import initialize as init_bias_reversion
from .bb_width_reversion import initialize as init_bb_width_reversion
from .atr_reversion import initialize as init_atr_reversion
from .roc_reversion import initialize as init_roc_reversion
from .psar_reversion import initialize as init_psar_reversion

# 策略映射表（方便按名称调用）
STRATEGY_MAP = {
    'zscore_reversion': init_mean_reversion,        # 标准均值回归
    'boll_reversion': init_bollinger_bands,         # 布林带回归
    'rsi_reversion': init_rsi_strategy,             # RSI回归
    'zscore_reversion_alt': init_zscore_reversion,   # Z-Score回归（60日）
    'deviation_reversion': init_deviation_reversion,# 偏离度回归
    'kdj_reversion': init_kdj_reversion,            # KDJ回归
    'williams_r_reversion': init_williams_r_reversion, # 威廉指标回归
    'cci_reversion': init_cci_reversion,            # CCI回归
    'macd_reversion': init_macd_reversion,          # MACD回归
    'bias_reversion': init_bias_reversion,          # 乖离率回归
    'bb_width_reversion': init_bb_width_reversion,  # 布林带宽度回归
    'atr_reversion': init_atr_reversion,            # ATR回归
    'roc_reversion': init_roc_reversion,            # ROC回归
    'psar_reversion': init_psar_reversion,          # PSAR回归
}

