"""
多因子选股策略模块

提供基于技术指标和价格数据的多因子选股功能，支持：
- 因子计算：价值、动量、技术、波动率等因子
- 因子处理：标准化、中性化、去极值
- 因子合成：等权、IC加权、机器学习方法
- 选股逻辑：综合打分、行业中性化

作者：量化交易系统
日期：2026-03
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Callable, Literal, Optional
from dataclasses import dataclass
from scipy import stats as scipy_stats

# ==================== 核心数据结构 ====================

@dataclass
class FactorConfig:
    """因子配置类"""
    name: str
    func: Callable
    direction: Literal["positive", "negative"]  # "positive"表示因子值越大越好，"negative"表示越小越好
    params: dict = None
    weight: float = 1.0
    desc: str = ""

    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class SelectionConfig:
    """选股配置"""
    top_n: int = 10  # 选择前N只股票
    rebalance_days: int = 20  # 调仓频率（交易日）
    min_price: float = 2.0  # 最低价格过滤
    max_price: float = 1000.0  # 最高价格过滤
    min_volume: float = 0  # 最小成交量过滤
    
    # 因子合成方法
    combine_method: Literal["equal_weight", "ic_weight", "max_ic"] = "equal_weight"
    
    # 因子处理选项
    winsorize: bool = True  # 是否去极值
    winsorize_method: Literal["mad", "std"] = "mad"  # 去极值方法：MAD（中位数绝对偏差）或标准差
    winsorize_n: float = 3.0  # 去极值倍数
    standardize: bool = True  # 是否标准化
    neutralize: bool = False  # 是否行业中性化（需要行业数据）
    
    # 权重方案
    weight_scheme: Literal["equal", "inv_vol", "score"] = "equal"
    max_weight: float = 1.0  # 单一标的最大权重


# ==================== 因子计算函数 ====================

def momentum_factor(
    close_df: pd.DataFrame,
    lookback: int = 20,
    method: Literal["roc", "cumret"] = "roc"
) -> pd.DataFrame:
    """
    动量因子：衡量价格趋势强度
    
    参数:
        close_df: 收盘价数据，格式为 (日期, 标的)
        lookback: 回看窗口（交易日）
        method: 计算方法
            - "roc": 变动率 = (当前价 - N日前的价) / N日前的价
            - "cumret": 累计收益率
    
    返回:
        因子值 DataFrame，值越大表示动量越强
    """
    if method == "roc":
        factor = close_df.pct_change(lookback, fill_method=None)
    else:  # cumret
        factor = close_df.pct_change(1, fill_method=None).rolling(lookback, min_periods=1).apply(
            lambda x: (1 + x).prod() - 1, raw=True
        )
    
    return factor


def reversal_factor(
    close_df: pd.DataFrame,
    lookback: int = 5
) -> pd.DataFrame:
    """
    反转因子：短期反转效应
    
    参数:
        close_df: 收盘价数据
        lookback: 回看窗口（通常较短，如5日）
    
    返回:
        因子值 DataFrame，值越小表示短期超卖越严重（买入机会）
    """
    return -close_df.pct_change(lookback, fill_method=None)


def volatility_factor(
    close_df: pd.DataFrame,
    window: int = 20
) -> pd.DataFrame:
    """
    波动率因子：衡量价格波动程度
    
    参数:
        close_df: 收盘价数据
        window: 计算窗口
    
    返回:
        因子值 DataFrame，值越小表示波动越低（更稳定）
    """
    returns = close_df.pct_change(1, fill_method=None)
    vol = returns.rolling(window, min_periods=1).std()
    return -vol  # 取负值，波动越小因子值越大


def ma_distance_factor(
    close_df: pd.DataFrame,
    ma_window: int = 60,
    method: Literal["ratio", "diff"] = "ratio"
) -> pd.DataFrame:
    """
    均线偏离因子：价格相对于均线的位置
    
    参数:
        close_df: 收盘价数据
        ma_window: 均线窗口
        method: 计算方法
            - "ratio": 比率 = 收盘价 / 均线
            - "diff": 差值 = 收盘价 - 均线
    
    返回:
        因子值 DataFrame
    """
    ma = close_df.rolling(ma_window, min_periods=1).mean()
    
    if method == "ratio":
        factor = (close_df - ma) / ma
    else:
        factor = close_df - ma
    
    return factor


def rsi_factor(
    close_df: pd.DataFrame,
    window: int = 14
) -> pd.DataFrame:
    """
    RSI因子：相对强弱指标
    
    参数:
        close_df: 收盘价数据
        window: RSI计算窗口
    
    返回:
        因子值 DataFrame，RSI值在0-100之间
        - RSI < 30: 超卖（买入机会）
        - RSI > 70: 超买（卖出机会）
    """
    delta = close_df.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=1).mean()
    
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    # 转换为超卖因子：RSI越小，因子值越大
    return 50 - rsi


def macd_factor(
    close_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> pd.DataFrame:
    """
    MACD因子：趋势跟踪指标
    
    参数:
        close_df: 收盘价数据
        fast: 快速EMA周期
        slow: 慢速EMA周期
        signal: 信号线周期
    
    返回:
        因子值 DataFrame，使用MACD柱状图
    """
    ema_fast = close_df.ewm(span=fast, adjust=False).mean()
    ema_slow = close_df.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return histogram


def bollinger_position_factor(
    close_df: pd.DataFrame,
    window: int = 20,
    n_std: float = 2.0
) -> pd.DataFrame:
    """
    布林带位置因子：价格在布林带中的相对位置
    
    参数:
        close_df: 收盘价数据
        window: 布林带窗口
        n_std: 标准差倍数
    
    返回:
        因子值 DataFrame
        - 值 < 0: 接近下轨（超卖）
        - 值 > 1: 接近上轨（超买）
    """
    ma = close_df.rolling(window, min_periods=1).mean()
    std = close_df.rolling(window, min_periods=1).std()
    upper = ma + n_std * std
    lower = ma - n_std * std
    
    # 价格在布林带中的位置：(收盘价 - 下轨) / (上轨 - 下轨)
    position = (close_df - lower) / (upper - lower)
    
    # 转换：值越小表示越接近下轨（超卖机会）
    return 0.5 - position


def volume_factor(
    close_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    window: int = 20
) -> pd.DataFrame:
    """
    成交量因子：成交量相对均量水平
    
    参数:
        close_df: 收盘价数据
        volume_df: 成交量数据，格式同close_df
        window: 计算窗口
    
    返回:
        因子值 DataFrame，值越大表示成交量越活跃
    """
    vol_ma = volume_df.rolling(window, min_periods=1).mean()
    vol_ratio = volume_df / vol_ma
    return vol_ratio


def price_trend_factor(
    close_df: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20
) -> pd.DataFrame:
    """
    价格趋势因子：短期和长期均线的关系
    
    参数:
        close_df: 收盘价数据
        short_window: 短期均线窗口
        long_window: 长期均线窗口
    
    返回:
        因子值 DataFrame
        - 值 > 0: 短期均线上穿长期均线（金叉）
        - 值 < 0: 短期均线下穿长期均线（死叉）
    """
    ma_short = close_df.rolling(short_window, min_periods=1).mean()
    ma_long = close_df.rolling(long_window, min_periods=1).mean()
    
    return (ma_short - ma_long) / ma_long


def high_low_ratio_factor(
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    window: int = 20
) -> pd.DataFrame:
    """
    高低价因子：价格区间相对位置
    
    参数:
        high_df: 最高价数据
        low_df: 最低价数据
        window: 计算窗口
    
    返回:
        因子值 DataFrame，值越大表示价格越接近区间高点
    """
    high_n = high_df.rolling(window, min_periods=1).max()
    low_n = low_df.rolling(window, min_periods=1).min()
    
    return (high_df - low_n) / (high_n - low_n)


def rsrs_factor(
    high_df: pd.DataFrame,
    low_df: pd.DataFrame,
    window: int = 18,
    lookback: int = 1100,
    buy_threshold: float = 0.7,
    sell_threshold: float = -0.7
) -> pd.DataFrame:
    """
    RSRS择时因子：用最高价对最低价回归，衡量支撑阻力强度

    原理：高点相对于低点的斜率（beta）越大，说明市场处于强势
    通过标准化beta值得到择时信号

    参数:
        high_df: 最高价数据
        low_df: 最低价数据
        window: 回归窗口（N日）
        lookback: 标准化回看期（M日）
        buy_threshold: 买入阈值
        sell_threshold: 卖出阈值

    返回:
        因子值 DataFrame
        - 值 > buy_threshold: 强势信号
        - 值 < sell_threshold: 弱势信号
    """
    rsrs_values = pd.DataFrame(index=high_df.index, columns=high_df.columns, dtype=float)

    for symbol in high_df.columns:
        high = high_df[symbol].dropna()
        low = low_df[symbol].dropna()

        if len(high) < window:
            continue

        # 对齐数据
        common_index = high.index.intersection(low.index)
        high = high.loc[common_index]
        low = low.loc[common_index]

        # 计算滚动回归beta值
        beta_series = []

        for i in range(len(high))[window:]:
            high_window = high.iloc[i - window + 1:i + 1]
            low_window = low.iloc[i - window + 1:i + 1]

            # 移除空值
            mask = high_window.notna() & low_window.notna()
            if mask.sum() < 2:
                continue

            high_clean = high_window[mask]
            low_clean = low_window[mask]

            # 线性回归: high = beta * low + alpha
            try:
                slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(low_clean.values, high_clean.values)
                beta_series.append((high.index[i], slope, r_value ** 2))
            except:
                continue

        if not beta_series:
            continue

        # 转换为Series
        beta_df = pd.DataFrame(beta_series, columns=['date', 'beta', 'r2']).set_index('date')

        # 计算标准化RSRS值
        if len(beta_df) >= lookback:
            # 取最后lookback个beta值
            betas = beta_df['beta'].iloc[-lookback:]
            mu = betas.mean()
            sigma = betas.std()

            if sigma > 0:
                zscore = (beta_df['beta'] - mu) / sigma
                # 调整后的RSRS: zscore * beta * r2
                rsrs_adj = zscore * beta_df['beta'] * beta_df['r2']
            else:
                rsrs_adj = 0
        else:
            rsrs_adj = beta_df['beta'] - beta_df['beta'].mean()

        # 转换为择时信号：值越大越适合买入
        rsrs_values[symbol] = rsrs_adj

    return rsrs_values


def value_rank_factor(
    pb_df: pd.DataFrame,
    roe_df: pd.DataFrame,
    weight_pb: float = 0.5,
    weight_roe: float = 0.5
) -> pd.DataFrame:
    """
    价值排名因子：PB和ROE的排名合成

    原理：
    - PB越低越便宜（排名越高越便宜）
    - ROE越高盈利能力越强（排名越高越强）
    - 综合得分 = PB排名权重 + ROE排名权重

    参数:
        pb_df: 市净率数据
        roe_df: 净资产收益率数据
        weight_pb: PB因子权重
        weight_roe: ROE因子权重

    返回:
        因子值 DataFrame，值越大表示价值越高
    """
    value_scores = pd.DataFrame(index=pb_df.index, columns=pb_df.columns, dtype=float)

    for date in pb_df.index:
        if date not in roe_df.index:
            continue

        pb_row = pb_df.loc[date]
        roe_row = roe_df.loc[date]

        # 过滤无效值
        valid_mask = (pb_row > 0) & (pb_row.notna()) & (roe_row > 0.01) & (roe_row.notna())

        if valid_mask.sum() < 2:
            continue

        pb_valid = pb_row[valid_mask]
        roe_valid = roe_row[valid_mask]

        # 排名：PB越小排名越大，ROE越大排名越大
        pb_rank = pb_valid.rank(ascending=True)  # PB越小排名越高
        roe_rank = roe_valid.rank(ascending=False)  # ROE越大排名越高

        # 合成得分
        total_score = weight_pb * pb_rank + weight_roe * roe_rank

        value_scores.loc[date] = total_score

    return value_scores


def low_quality_factor(
    vol_df: pd.DataFrame,
    window: int = 20
) -> pd.DataFrame:
    """
    低质量因子（低波动）：选择波动率较低的标的

    参数:
        vol_df: 价格数据
        window: 计算窗口

    返回:
        因子值 DataFrame，值越大表示波动越低
    """
    # 计算日收益率
    ret = vol_df.pct_change(1, fill_method=None)

    # 计算波动率
    volatility = ret.rolling(window, min_periods=1).std()

    # 取倒数，值越大表示波动越小
    low_quality = 1 / volatility.replace([np.inf, -np.inf], np.nan)

    return low_quality


# ==================== 内置因子库 ====================

BUILTIN_FACTORS = {
    "momentum_20d": FactorConfig(
        name="momentum_20d",
        func=momentum_factor,
        direction="positive",
        params={"lookback": 20},
        desc="20日动量因子",
    ),
    "momentum_60d": FactorConfig(
        name="momentum_60d",
        func=momentum_factor,
        direction="positive",
        params={"lookback": 60},
        desc="60日动量因子",
    ),
    "reversal_5d": FactorConfig(
        name="reversal_5d",
        func=reversal_factor,
        direction="positive",
        params={"lookback": 5},
        desc="5日反转因子（短期超卖）",
    ),
    "volatility_20d": FactorConfig(
        name="volatility_20d",
        func=volatility_factor,
        direction="positive",
        params={"window": 20},
        desc="20日波动率因子（低波动）",
    ),
    "ma_distance_60d": FactorConfig(
        name="ma_distance_60d",
        func=ma_distance_factor,
        direction="positive",
        params={"ma_window": 60, "method": "ratio"},
        desc="60日均线偏离因子",
    ),
    "rsi_14d": FactorConfig(
        name="rsi_14d",
        func=rsi_factor,
        direction="positive",
        params={"window": 14},
        desc="14日RSI因子（超卖）",
    ),
    "macd": FactorConfig(
        name="macd",
        func=macd_factor,
        direction="positive",
        params={"fast": 12, "slow": 26, "signal": 9},
        desc="MACD柱状图因子",
    ),
    "bollinger_position": FactorConfig(
        name="bollinger_position",
        func=bollinger_position_factor,
        direction="positive",
        params={"window": 20, "n_std": 2.0},
        desc="布林带位置因子（超卖）",
    ),
    "price_trend": FactorConfig(
        name="price_trend",
        func=price_trend_factor,
        direction="positive",
        params={"short_window": 5, "long_window": 20},
        desc="价格趋势因子（金叉）",
    ),
    "rsrs": FactorConfig(
        name="rsrs",
        func=rsrs_factor,
        direction="positive",
        params={"window": 18, "lookback": 1100, "buy_threshold": 0.7, "sell_threshold": -0.7},
        desc="RSRS择时因子（支撑阻力强度）",
    ),
    "value_rank": FactorConfig(
        name="value_rank",
        func=value_rank_factor,
        direction="positive",
        params={"weight_pb": 0.5, "weight_roe": 0.5},
        desc="价值排名因子（PB+ROE排名）",
    ),
    "low_quality": FactorConfig(
        name="low_quality",
        func=low_quality_factor,
        direction="positive",
        params={"window": 20},
        desc="低质量因子（低波动）",
    ),
}


# ==================== 因子处理函数 ====================

def winsorize(
    factor_df: pd.DataFrame,
    method: Literal["mad", "std"] = "mad",
    n: float = 3.0
) -> pd.DataFrame:
    """
    去极值处理
    
    参数:
        factor_df: 因子值 DataFrame
        method: 去极值方法
            - "mad": 使用中位数绝对偏差（更稳健）
            - "std": 使用标准差
        n: 倍数
    
    返回:
        去极值后的因子 DataFrame
    """
    result = factor_df.copy()
    
    for col in result.columns:
        series = result[col]
        
        if method == "mad":
            median = series.median()
            mad = np.abs(series - median).median()
            lower = median - n * mad
            upper = median + n * mad
        else:  # std
            mean = series.mean()
            std = series.std()
            lower = mean - n * std
            upper = mean + n * std
        
        result[col] = series.clip(lower=lower, upper=upper)
    
    return result


def standardize(
    factor_df: pd.DataFrame,
    method: Literal["zscore", "rank"] = "zscore"
) -> pd.DataFrame:
    """
    标准化处理
    
    参数:
        factor_df: 因子值 DataFrame
        method: 标准化方法
            - "zscore": Z-Score标准化
            - "rank": 排序标准化
    
    返回:
        标准化后的因子 DataFrame
    """
    result = factor_df.copy()
    
    if method == "zscore":
        # 截面标准化：每个时间点对所有标的标准化
        for idx in result.index:
            row = result.loc[idx]
            if row.notna().sum() > 1:
                mean = row.mean()
                std = row.std()
                if std > 0:
                    result.loc[idx] = (row - mean) / std
    else:  # rank
        # 排序标准化到 [0, 1]
        for idx in result.index:
            row = result.loc[idx]
            if row.notna().sum() > 1:
                rank = row.rank(pct=True, na_option="keep")
                result.loc[idx] = (rank - 0.5) * 2  # 映射到 [-1, 1]
    
    return result


def combine_factors(
    factor_dfs: dict[str, pd.DataFrame],
    weights: dict[str, float] = None,
    method: Literal["equal_weight", "sum"] = "equal_weight"
) -> pd.DataFrame:
    """
    合并多个因子为综合得分
    
    参数:
        factor_dfs: 因子字典 {因子名: 因子DataFrame}
        weights: 因子权重字典 {因子名: 权重}
        method: 合并方法
            - "equal_weight": 等权合并
            - "sum": 按指定权重合并（需要提供weights）
    
    返回:
        综合得分 DataFrame
    """
    if not factor_dfs:
        raise ValueError("至少需要一个因子")
    
    # 确保所有因子有相同的索引和列
    first_factor = list(factor_dfs.values())[0]
    combined = pd.DataFrame(0.0, index=first_factor.index, columns=first_factor.columns)
    
    if method == "equal_weight":
        weight = 1.0 / len(factor_dfs)
        for factor_name, factor_df in factor_dfs.items():
            combined += factor_df * weight
    else:  # sum
        if weights is None:
            raise ValueError("method='sum' 需要提供 weights 参数")
        total_weight = sum(weights.values())
        for factor_name, factor_df in factor_dfs.items():
            combined += factor_df * (weights.get(factor_name, 0) / total_weight)
    
    return combined


# ==================== 选股逻辑 ====================

def select_by_score(
    score_df: pd.DataFrame,
    config: SelectionConfig,
    rebalance_dates: list = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    根据综合得分选择股票
    
    参数:
        score_df: 综合得分 DataFrame (日期 × 标的)
        config: 选股配置
        rebalance_dates: 调仓日期列表（可选，默认按配置自动生成）
    
    返回:
        (weights_df, selections_df)
        - weights_df: 权重矩阵 (日期 × 标的)
        - selections_df: 选股结果 (日期 × 标的), 1表示选中，0表示未选中
    """
    dates = score_df.index
    symbols = score_df.columns
    weights_df = pd.DataFrame(0.0, index=dates, columns=symbols)
    selections_df = pd.DataFrame(False, index=dates, columns=symbols)
    
    # 生成调仓日期
    if rebalance_dates is None:
        rebalance_dates = []
        for i in range(config.top_n, len(dates), config.rebalance_days):
            rebalance_dates.append(dates[i])
    
    for rebalance_date in rebalance_dates:
        if rebalance_date not in dates:
            continue
        
        # 获取当期得分
        scores = score_df.loc[rebalance_date].dropna()
        
        if len(scores) < config.top_n:
            continue
        
        # 选择得分最高的 top_n 只
        selected = scores.nlargest(config.top_n)
        
        # 更新选股结果
        selections_df.loc[rebalance_date, selected.index] = True
        
        # 计算权重
        if config.weight_scheme == "equal":
            w = 1.0 / len(selected)
            weights_df.loc[rebalance_date, selected.index] = w
        
        elif config.weight_scheme == "score":
            # 按得分加权（得分越高权重越大）
            total_score = selected.sum()
            weights_df.loc[rebalance_date, selected.index] = selected / total_score
    
    # 将权重向前填充到下次调仓前
    weights_df = weights_df.ffill().fillna(0)
    selections_df = selections_df.ffill().fillna(False)
    
    # 限制单一标的最大权重
    if config.max_weight < 1.0:
        for idx in weights_df.index:
            row = weights_df.loc[idx]
            row = row.clip(upper=config.max_weight)
            total = row.sum()
            if total > 0:
                weights_df.loc[idx] = row / total
    
    return weights_df, selections_df


# ==================== 多因子选股框架 ====================

class MultiFactorSelector:
    """多因子选股器"""
    
    def __init__(
        self,
        factor_configs: list[FactorConfig] = None,
        config: SelectionConfig = None
    ):
        """
        初始化多因子选股器
        
        参数:
            factor_configs: 因子配置列表
            config: 选股配置
        """
        self.factor_configs = factor_configs or []
        self.config = config or SelectionConfig()
        self.factor_dfs: dict[str, pd.DataFrame] = {}
        self.score_df: pd.DataFrame = None
        self.weights_df: pd.DataFrame = None
        self.selections_df: pd.DataFrame = None
    
    def add_factor(self, factor_config: FactorConfig):
        """添加因子"""
        self.factor_configs.append(factor_config)
    
    def add_builtin_factors(self, factor_names: list[str]):
        """从内置因子库添加因子"""
        for name in factor_names:
            if name in BUILTIN_FACTORS:
                self.add_factor(BUILTIN_FACTORS[name])
            else:
                raise ValueError(f"未知因子: {name}, 可选因子: {list(BUILTIN_FACTORS.keys())}")
    
    def compute_factors(
        self,
        close_df: pd.DataFrame,
        high_df: pd.DataFrame = None,
        low_df: pd.DataFrame = None,
        volume_df: pd.DataFrame = None,
        pb_df: pd.DataFrame = None,
        roe_df: pd.DataFrame = None
    ) -> dict[str, pd.DataFrame]:
        """
        计算所有因子

        参数:
            close_df: 收盘价数据 (日期 × 标的)
            high_df: 最高价数据（可选）
            low_df: 最低价数据（可选）
            volume_df: 成交量数据（可选）
            pb_df: 市净率数据（可选）
            roe_df: 净资产收益率数据（可选）

        返回:
            因子字典 {因子名: 因子DataFrame}
        """
        self.factor_dfs = {}
        
        for factor_config in self.factor_configs:
            params = factor_config.params.copy()
            
            # 根据因子类型调用对应函数
            if factor_config.name.startswith("momentum") or factor_config.name.startswith("reversal"):
                factor_df = factor_config.func(close_df, **params)
            elif factor_config.name.startswith("volatility"):
                factor_df = factor_config.func(close_df, **params)
            elif factor_config.name.startswith("ma_distance"):
                factor_df = factor_config.func(close_df, **params)
            elif factor_config.name.startswith("rsi"):
                factor_df = factor_config.func(close_df, **params)
            elif factor_config.name.startswith("macd"):
                factor_df = factor_config.func(close_df, **params)
            elif factor_config.name.startswith("bollinger"):
                factor_df = factor_config.func(close_df, **params)
            elif factor_config.name.startswith("price_trend"):
                factor_df = factor_config.func(close_df, **params)
            elif factor_config.name.startswith("high_low"):
                if high_df is None or low_df is None:
                    raise ValueError(f"{factor_config.name} 需要提供 high_df 和 low_df")
                factor_df = factor_config.func(high_df, low_df, **params)
            elif factor_config.name.startswith("volume"):
                if volume_df is None:
                    raise ValueError(f"{factor_config.name} 需要提供 volume_df")
                factor_df = factor_config.func(close_df, volume_df, **params)
            elif factor_config.name == "rsrs":
                if high_df is None or low_df is None:
                    raise ValueError(f"{factor_config.name} 需要提供 high_df 和 low_df")
                factor_df = factor_config.func(high_df, low_df, **params)
            elif factor_config.name == "value_rank":
                # 从params获取roe_df
                roe_df = params.pop("roe_df", None)
                if roe_df is None:
                    raise ValueError(f"{factor_config.name} 需要提供 roe_df 参数")
                # 使用high_df作为pb_df
                if high_df is None:
                    raise ValueError(f"{factor_config.name} 需要提供 pb_df (high_df参数)")
                factor_df = factor_config.func(high_df, roe_df, **params)
            elif factor_config.name == "low_quality":
                factor_df = factor_config.func(close_df, **params)
            else:
                # 默认只用收盘价
                factor_df = factor_config.func(close_df, **params)
            
            # 因子方向处理
            if factor_config.direction == "negative":
                factor_df = -factor_df
            
            # 因子处理
            if self.config.winsorize:
                factor_df = winsorize(factor_df, method=self.config.winsorize_method, n=self.config.winsorize_n)
            
            if self.config.standardize:
                factor_df = standardize(factor_df)
            
            self.factor_dfs[factor_config.name] = factor_df
        
        return self.factor_dfs
    
    def compute_score(self) -> pd.DataFrame:
        """
        计算综合得分
        
        返回:
            综合得分 DataFrame
        """
        if not self.factor_dfs:
            raise ValueError("请先调用 compute_factors() 计算因子")
        
        # 构建权重字典
        weights = {fc.name: fc.weight for fc in self.factor_configs}
        
        # 合并因子
        self.score_df = combine_factors(
            self.factor_dfs,
            weights=weights,
            method=self.config.combine_method
        )
        
        return self.score_df
    
    def select(self, rebalance_dates: list = None) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        执行选股
        
        参数:
            rebalance_dates: 调仓日期列表
        
        返回:
            (weights_df, selections_df)
        """
        if self.score_df is None:
            self.compute_score()
        
        self.weights_df, self.selections_df = select_by_score(
            self.score_df,
            self.config,
            rebalance_dates
        )
        
        return self.weights_df, self.selections_df
    
    def run(
        self,
        close_df: pd.DataFrame,
        high_df: pd.DataFrame = None,
        low_df: pd.DataFrame = None,
        volume_df: pd.DataFrame = None,
        pb_df: pd.DataFrame = None,
        roe_df: pd.DataFrame = None,
        rebalance_dates: list = None
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
        """
        完整运行：计算因子 → 合并得分 → 选股

        参数:
            close_df: 收盘价数据
            high_df: 最高价数据
            low_df: 最低价数据
            volume_df: 成交量数据
            pb_df: 市净率数据（用于价值因子）
            roe_df: 净资产收益率数据（用于价值因子）
            rebalance_dates: 调仓日期列表

        返回:
            (weights_df, selections_df, factor_dfs)
        """
        self.compute_factors(close_df, high_df, low_df, volume_df, pb_df, roe_df)
        self.compute_score()
        self.select(rebalance_dates)

        return self.weights_df, self.selections_df, self.factor_dfs


# ==================== 便捷函数 ====================

def create_momentum_reversion_selector(
    top_n: int = 10,
    rebalance_days: int = 20,
) -> MultiFactorSelector:
    """
    创建动量+反转组合选股器
    
    适合：趋势轮动策略
    """
    selector = MultiFactorSelector()
    selector.add_builtin_factors([
        "momentum_60d",  # 中期动量
        "momentum_20d",  # 短期动量
        "reversal_5d",   # 短期反转
    ])
    selector.config = SelectionConfig(
        top_n=top_n,
        rebalance_days=rebalance_days,
        weight_scheme="equal",
        winsorize=True,
        standardize=True,
    )
    return selector


def create_quality_value_selector(
    top_n: int = 10,
    rebalance_days: int = 20,
) -> MultiFactorSelector:
    """
    创建质量+价值组合选股器
    
    适合：价值投资策略
    注意：当前仅支持技术因子，需接入财务数据才能实现真正的价值因子
    """
    selector = MultiFactorSelector()
    selector.add_builtin_factors([
        "volatility_20d",     # 低波动
        "ma_distance_60d",    # 低位布局
        "bollinger_position", # 超卖
    ])
    selector.config = SelectionConfig(
        top_n=top_n,
        rebalance_days=rebalance_days,
        weight_scheme="equal",
        winsorize=True,
        standardize=True,
    )
    return selector


def create_trend_strength_selector(
    top_n: int = 10,
    rebalance_days: int = 20,
) -> MultiFactorSelector:
    """
    创建趋势强度选股器

    适合：趋势跟踪策略
    """
    selector = MultiFactorSelector()
    selector.add_builtin_factors([
        "momentum_60d",      # 中期动量
        "price_trend",       # 均线趋势
        "macd",              # MACD趋势
        "ma_distance_60d",   # 均线偏离
    ])
    selector.config = SelectionConfig(
        top_n=top_n,
        rebalance_days=rebalance_days,
        weight_scheme="score",  # 按得分加权
        winsorize=True,
        standardize=True,
    )
    return selector


def create_rsrs_value_selector(
    top_n: int = 10,
    rebalance_days: int = 20,
    buy_threshold: float = 0.7,
    sell_threshold: float = -0.7
) -> MultiFactorSelector:
    """
    创建RSRS+价值因子选股器

    结合：
    - RSRS择时：判断市场强弱
    - 价值因子：PB+ROE排名选股

    适合：价值投资+择时策略
    """
    selector = MultiFactorSelector()

    # 添加价值因子
    value_config = BUILTIN_FACTORS["value_rank"].copy()
    value_config.weight = 1.0
    selector.add_factor(value_config)

    # 添加低质量因子（低波动）
    quality_config = BUILTIN_FACTORS["low_quality"].copy()
    quality_config.weight = 0.5
    selector.add_factor(quality_config)

    # 存储RSRS参数用于择时
    selector.rsrs_config = {
        "window": 18,
        "lookback": 1100,
        "buy_threshold": buy_threshold,
        "sell_threshold": sell_threshold
    }

    selector.config = SelectionConfig(
        top_n=top_n,
        rebalance_days=rebalance_days,
        weight_scheme="equal",
        winsorize=True,
        standardize=True,
    )
    return selector


# ==================== 导出 ====================

__all__ = [
    # 因子配置
    "FactorConfig",
    "SelectionConfig",
    # 内置因子库
    "BUILTIN_FACTORS",
    # 因子计算函数
    "momentum_factor",
    "reversal_factor",
    "volatility_factor",
    "ma_distance_factor",
    "rsi_factor",
    "macd_factor",
    "bollinger_position_factor",
    "volume_factor",
    "price_trend_factor",
    "high_low_ratio_factor",
    "rsrs_factor",
    "value_rank_factor",
    "low_quality_factor",
    # 因子处理函数
    "winsorize",
    "standardize",
    "combine_factors",
    # 选股逻辑
    "select_by_score",
    # 选股器
    "MultiFactorSelector",
    # 便捷函数
    "create_momentum_reversion_selector",
    "create_quality_value_selector",
    "create_trend_strength_selector",
    "create_rsrs_value_selector",
]
