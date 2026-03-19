"""
量化交易策略模块包

包含以下策略类型：
- common: 通用策略（兼容旧版本）
- trend_following: 趋势跟踪策略
- mean_reversion: 均值回归策略
- multi_factor: 多因子选股策略
"""

from . import common
from . import trend_following
from . import mean_reversion
from . import multi_factor

__all__ = ["common", "trend_following", "mean_reversion", "multi_factor"]

