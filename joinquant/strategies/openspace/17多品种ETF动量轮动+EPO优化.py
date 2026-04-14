# 克隆自聚宽文章：https://www.joinquant.com/post/47208
# 标题：多品种ETF动量轮动+EPO优化
# 作者：openhe

# 克隆自聚宽文章：https://www.joinquant.com/post/47192
# 标题：分享一个低波动ETF轮动策略，近四年最大回撤14.26%
# 作者：hornor


# 策略收益 114.65% 基准收益 18.08% Alpha 0.70 Beta 1.21 Sharpe 2.00 最大回撤  22.73%
## 策略概述
# 这是一个基于动量轮动的ETF投资策略，结合了EPO（增强型风险平价）优化算法，旨在通过选择高动量ETF并优化配置权重，实现稳定的风险调整收益。

# ## 核心逻辑
# ### 1. 初始化设置
# - 基准选择 ：沪深300指数（000300.XSHG）
# - 交易成本 ：万分之二（ETF交易无印花税）
# - 滑点设置 ：0
# - 持仓数量 ：3只ETF
# - 动量参考天数 ：34天
# - EPO参数 ：
#   - g._lambda = 10 ：正则化参数
#   - g.w = 0.2 ：锚定权重
# ### 2. ETF池构建
# 策略包含14只ETF，覆盖多个资产类别：

# - 商品 ：黄金ETF、豆粕ETF
# - 海外 ：纳指ETF
# - 宽基 ：沪深300ETF、创业板ETF
# - 窄基 ：创新药、新能车、消费、光伏、通信、计算机、军工、恒生科技ETF
# ### 3. 动量因子计算（get_rank）
# 核心算法 ：

# 1. 计算对数收益率 ： y = np.log(df.close)
# 2. 线性回归 ：对时间序列和对数收益率进行线性回归
# 3. 年化收益 ：基于回归斜率计算年化收益
# 4. 判定系数 ：计算R²，衡量趋势的稳定性
# 5. 综合评分 ： score = annualized_returns * r_squared
# 6. 筛选 ：只保留评分大于0的ETF
# 创新点 ：

# - 结合了年化收益和趋势稳定性（R²），避免了单纯动量策略的高波动
# - 过滤掉负向动量的ETF，只选择具有正向趋势的品种
# ### 4. EPO优化（epo函数）
# EPO（增强型风险平价）算法 ：

# 1. 协方差矩阵 ：计算ETF收益率的协方差矩阵
# 2. 相关性矩阵 ：计算ETF间的相关性
# 3. 矩阵收缩 ：通过参数 w 调整相关性矩阵，提高稳定性
# 4. 权重优化 ：
#    - 方法1（simple）：基于信号和协方差矩阵直接计算
#    - 方法2（anchored）：结合锚定权重，平衡动量信号和风险平价
# 5. 权重归一化 ：确保权重非负且和为1
# 优势 ：

# - 考虑了资产间的相关性
# - 通过正则化提高了优化结果的稳定性
# - 结合了动量信号和风险平价思想
# ### 5. 交易执行（trade函数）
# 交易频率 ：每月1日9:30执行 交易逻辑 ：

# 1. 选择目标ETF ：取动量排名前3的ETF
# 2. 卖出操作 ：卖出不在目标列表中的ETF
# 3. 买入操作 ：
#    - 对目标ETF执行EPO优化，计算权重
#    - 按优化后的权重分配资金

from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd
import talib
from scipy.optimize import minimize
import statsmodels.api as sm
from scipy.linalg import solve
import math

# 初始化函数 
def initialize(context):
    """初始化函数，设置策略基本参数"""
    # 设定基准：沪深300指数
    set_benchmark('000300.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option('avoid_future_data', True)
    # 设置滑点为0
    set_slippage(FixedSlippage(0))
    # 设置交易成本：ETF交易无印花税，佣金万分之二
    set_order_cost(OrderCost(open_tax=0, close_tax=0, open_commission=0.0002, 
                             close_commission=0.0002, close_today_commission=0, 
                             min_commission=5), type='fund')
    # 过滤一定级别的日志
    log.set_level('system', 'error')
    
    # 策略参数
    g.stock_num = 5  # 持仓ETF数量
    g._lambda = 10   # EPO优化的正则化参数
    g.w = 0.2        # 相关性矩阵收缩参数

    # ETF池：覆盖多个资产类别
    # g.etf_pool = [
    #     # 商品
    #     '518880.XSHG',#黄金ETF
    #     '159985.XSHE',#豆粕ETF
    #     # 海外
    #     '513100.XSHG',#纳指ETF
    #     # 宽基
    #     '510300.XSHG',#沪深300ETF
    #     '159915.XSHE',#创业板
    #     # 窄基
    #     '159992.XSHE',#创新药ETF
    #     '515700.XSHG',#新能车ETF
    #     '510150.XSHG',#消费ETF
    #     '515790.XSHG',#光伏ETF
    #     '515880.XSHG',#通信ETF
    #     '512720.XSHG',#计算机ETF
    #     '512660.XSHG',#军工ETF
    #     '159740.XSHE',#恒生科技ETF
    #     ]	
    g.etf_pool = [
#大宗商品ETF：
        '518880.XSHG',  # (黄金ETF) [ETF]-成交额：54.60亿元-上市日期：2013-07-29
        '161226.XSHE',  # (国投白银LOF) [LOF]-成交额：21.54亿元-上市日期：2015-08-17
        '159980.XSHE',  # (有色ETF大成) [ETF]-成交额：23.57亿元-上市日期：2019-12-24
        '501018.XSHG',  # (南方原油ETF) [LOF]-成交额：1.34亿元-上市日期：2016-06-28
        '159985.XSHE',  # (豆粕ETF) [ETF]-成交额：0.67亿元
#海外ETF：       
        '513100.XSHG',  # (纳指ETF) [ETF]-成交额：4.24亿元-上市日期：2013-05-15
        '159509.XSHE',  # (纳指科技ETF景顺) [ETF]-成交额：5.65亿元-上市日期：2023-08-08
        '513290.XSHG',  # (纳指生物) [ETF]-成交额：1.28亿元-上市日期：2022-08-29        
        '513500.XSHG',  # (标普500) [ETF]-成交额：2.22亿元-上市日期：2014-01-15
        '159518.XSHE',  # (标普油气ETF嘉实) [ETF]-成交额：5.35亿元-上市日期：2023-11-15
        '159502.XSHE',  # (标普生物科技ETF嘉实) [ETF]-成交额：4.00亿元-上市日期：2024-01-10        
        '159529.XSHE',  # (标普消费ETF) [ETF]-成交额：2.25亿元-上市日期：2024-02-02
        '513400.XSHG',  # (道琼斯) [ETF]-成交额：1.09亿元-上市日期：2024-02-02
        '520830.XSHG',  # (沙特ETF) [ETF]-成交额：1.16亿元-上市日期：2024-07-16
        '513520.XSHG',  # (日经ETF) [ETF]-成交额：1.11亿元-上市日期：2019-06-25
        '513030.XSHG',  # (德国ETF) [ETF]-成交额：0.77亿元
#港股ETF：
        '513090.XSHG',  # (香港证券) [ETF]-成交额：68.32亿元-上市日期：2020-03-26
        '513180.XSHG',  # (恒指科技) [ETF]-成交额：61.72亿元-上市日期：2021-05-25
        '513120.XSHG',  # (HK创新药) [ETF]-成交额：48.95亿元-上市日期：2022-07-12
        '513330.XSHG',  # (恒生互联) [ETF]-成交额：37.01亿元-上市日期：2021-02-08
        '513750.XSHG',  # (港股非银) [ETF]-成交额：23.06亿元-上市日期：2023-11-27
        '159892.XSHE',  # (恒生医药ETF) [ETF]-成交额：12.25亿元-上市日期：2021-10-19
        '159605.XSHE',  # (中概互联ETF) [ETF]-成交额：5.14亿元-上市日期：2021-12-02
        '513190.XSHG',  # (H股金融) [ETF]-成交额：5.07亿元-上市日期：2023-10-11
        '510900.XSHG',  # (恒生中国) [ETF]-成交额：3.73亿元-上市日期：2012-10-22
        '513630.XSHG',  # (香港红利) [ETF]-成交额：3.69亿元-上市日期：2023-12-08
        '513920.XSHG',  # (港股通央企红利) [ETF]-成交额：3.11亿元-上市日期：2024-01-05
        '159323.XSHE',  # (港股通汽车ETF) [ETF]-成交额：2.02亿元-上市日期：2025-01-08
        '513970.XSHG',  # (恒生消费) [ETF]-成交额：1.25亿元-上市日期：2023-04-21
#指数ETF：        
        '510500.XSHG',  # (中证500ETF) [ETF]-成交额：263.30亿元-上市日期：2013-03-15
        '512100.XSHG',  # (中证1000ETF) [ETF]-成交额：32.30亿元-上市日期：2016-11-04
        '563300.XSHG',  # (中证2000) [ETF]-成交额：3.34亿元-上市日期：2023-09-14        
        '510300.XSHG',  # (沪深300ETF) [ETF]-成交额：253.91亿元-上市日期：2012-05-28
        '512050.XSHG',  # (A500E) [ETF]-成交额：151.68亿元-上市日期：2024-11-15        
        '510760.XSHG',  # (上证ETF) [ETF]-成交额：1.10亿元-上市日期：2020-09-09        
        '159915.XSHE',  # (创业板ETF易方达) [ETF]-成交额：129.05亿元-上市日期：2011-12-09
        '159949.XSHE',  # (创业板50ETF) [ETF]-成交额：15.23亿元-上市日期：2016-07-22
        '159967.XSHE',  # (创业板成长ETF) [ETF]-成交额：3.27亿元-上市日期：2019-07-15        
        '588080.XSHG',  # (科创板50) [ETF]-成交额：123.46亿元-上市日期：2020-11-16
        '588220.XSHG',  # (科创100) [ETF]-成交额：4.99亿元-上市日期：2023-09-15
        '511380.XSHG',  # (可转债ETF) [ETF]-成交额：165.76亿元-上市日期：2020-04-07
#行业ETF：
        '513310.XSHG',  # (中韩芯片) [ETF]-成交额：38.68亿元-上市日期：2022-12-22
        '588200.XSHG',  # (科创芯片) [ETF]-成交额：37.94亿元-上市日期：2022-10-26
        '159852.XSHE',  # (软件ETF) [ETF]-成交额：36.26亿元-上市日期：2021-02-09
        '512880.XSHG',  # (证券ETF) [ETF]-成交额：34.01亿元-上市日期：2016-08-08
        '159206.XSHE',  # (卫星ETF) [ETF]-成交额：32.60亿元-上市日期：2025-03-14
        '512400.XSHG',  # (有色金属ETF) [ETF]-成交额：31.27亿元-上市日期：2017-09-01
        '512980.XSHG',  # (传媒ETF) [ETF]-成交额：30.96亿元-上市日期：2018-01-19
        '159516.XSHE',  # (半导体设备ETF) [ETF]-成交额：28.21亿元-上市日期：2023-07-27
        '512480.XSHG',  # (半导体) [ETF]-成交额：16.29亿元-上市日期：2019-06-12
        '515880.XSHG',  # (通信ETF) [ETF]-成交额：13.46亿元-上市日期：2019-09-06
        '562500.XSHG',  # (机器人) [ETF]-成交额：12.92亿元-上市日期：2021-12-29
        '159218.XSHE',  # (卫星产业ETF) [ETF]-成交额：12.74亿元-上市日期：2025-05-22
        '159869.XSHE',  # (游戏ETF) [ETF]-成交额：12.42亿元-上市日期：2021-03-05
        '159870.XSHE',  # (化工ETF) [ETF]-成交额：12.30亿元-上市日期：2021-03-03
        '159326.XSHE',  # (电网设备ETF) [ETF]-成交额：12.02亿元-上市日期：2024-09-09
        '159851.XSHE',  # (金融科技ETF) [ETF]-成交额：11.79亿元-上市日期：2021-03-19
        '560860.XSHG',  # (工业有色) [ETF]-成交额：11.71亿元-上市日期：2023-03-13
        '159363.XSHE',  # (创业板人工智能ETF华宝) [ETF]-成交额：10.63亿元-上市日期：2024-12-16
        '588170.XSHG',  # (科创半导) [ETF]-成交额：10.28亿元-上市日期：2025-04-08
        '159755.XSHE',  # (电池ETF) [ETF]-成交额：10.02亿元-上市日期：2021-06-24
        '512170.XSHG',  # (医疗ETF) [ETF]-成交额：9.54亿元-上市日期：2019-06-17
        '512800.XSHG',  # (银行ETF) [ETF]-成交额：9.48亿元-上市日期：2017-08-03
        '159819.XSHE',  # (人工智能ETF易方达) [ETF]-成交额：9.40亿元-上市日期：2020-09-23
        '512710.XSHG',  # (军工龙头) [ETF]-成交额：9.39亿元-上市日期：2019-08-26
        '159638.XSHE',  # (高端装备ETF嘉实) [ETF]-成交额：8.92亿元-上市日期：2022-08-12
        '517520.XSHG',  # (黄金股) [ETF]-成交额：8.73亿元-上市日期：2023-11-01
        '515980.XSHG',  # (人工智能) [ETF]-成交额：8.73亿元-上市日期：2020-02-10
        '159995.XSHE',  # (芯片ETF) [ETF]-成交额：8.45亿元-上市日期：2020-02-10
        '159227.XSHE',  # (航空航天ETF) [ETF]-成交额：8.42亿元-上市日期：2025-05-16
        '512660.XSHG',  # (军工ETF) [ETF]-成交额：7.78亿元-上市日期：2016-08-08
        '512690.XSHG',  # (酒ETF) [ETF]-成交额：6.74亿元-上市日期：2019-05-06
        '516150.XSHG',  # (稀土基金) [ETF]-成交额：6.41亿元-上市日期：2021-03-17
        '512890.XSHG',  # (红利低波) [ETF]-成交额：6.03亿元-上市日期：2019-01-18
        '588790.XSHG',  # (科创智能) [ETF]-成交额：5.92亿元-上市日期：2025-01-09
        '159992.XSHE',  # (创新药ETF) [ETF]-成交额：5.63亿元-上市日期：2020-04-10
        '512070.XSHG',  # (证券保险) [ETF]-成交额：5.50亿元-上市日期：2014-07-18
        '562800.XSHG',  # (稀有金属) [ETF]-成交额：5.49亿元-上市日期：2021-09-27
        '512010.XSHG',  # (医药ETF) [ETF]-成交额：5.22亿元-上市日期：2013-10-28
        '515790.XSHG',  # (光伏ETF) [ETF]-成交额：4.95亿元-上市日期：2020-12-18
        '510880.XSHG',  # (红利ETF) [ETF]-成交额：4.90亿元-上市日期：2007-01-18
        '159928.XSHE',  # (消费ETF) [ETF]-成交额：4.71亿元-上市日期：2013-09-16
        '159883.XSHE',  # (医疗器械ETF) [ETF]-成交额：4.44亿元-上市日期：2021-04-30
        '159998.XSHE',  # (计算机ETF) [ETF]-成交额：3.93亿元-上市日期：2020-04-13
        '515220.XSHG',  # (煤炭ETF) [ETF]-成交额：3.92亿元-上市日期：2020-03-02
        '561980.XSHG',  # (芯片设备) [ETF]-成交额：3.89亿元-上市日期：2023-09-01
        '515400.XSHG',  # (大数据) [ETF]-成交额：3.54亿元-上市日期：2021-01-20
        '515120.XSHG',  # (创新药) [ETF]-成交额：3.54亿元-上市日期：2021-01-04
        '159566.XSHE',  # (储能电池ETF易方达) [ETF]-成交额：3.05亿元-上市日期：2024-02-08
        '515050.XSHG',  # (5GETF) [ETF]-成交额：3.04亿元-上市日期：2019-10-16
        '516510.XSHG',  # (云计算ETF) [ETF]-成交额：2.95亿元-上市日期：2021-04-07
        '159256.XSHE',  # (创业板软件ETF华夏) [ETF]-成交额：2.89亿元-上市日期：2025-08-04
        '159766.XSHE',  # (旅游ETF) [ETF]-成交额：2.57亿元-上市日期：2021-07-23
        '512200.XSHG',  # (地产ETF) [ETF]-成交额：2.53亿元-上市日期：2017-09-25
        '513350.XSHG',  # (油气ETF) [ETF]-成交额：2.48亿元-上市日期：2023-11-28
        '159583.XSHE',  # (通信设备ETF) [ETF]-成交额：2.47亿元-上市日期：2024-07-08
        '159732.XSHE',  # (消费电子ETF) [ETF]-成交额：2.39亿元-上市日期：2021-08-23
        '516160.XSHG',  # (新能源) [ETF]-成交额：2.26亿元-上市日期：2021-02-04
        '516520.XSHG',  # (智能驾驶) [ETF]-成交额：2.22亿元-上市日期：2021-03-01
        '562590.XSHG',  # (半导材料) [ETF]-成交额：1.94亿元-上市日期：2023-10-18
        '515030.XSHG',  # (新汽车) [ETF]-成交额：1.93亿元-上市日期：2020-03-04
        '512670.XSHG',  # (国防ETF) [ETF]-成交额：1.84亿元-上市日期：2019-08-01
        '561330.XSHG',  # (矿业ETF) [ETF]-成交额：1.81亿元-上市日期：2022-11-01
        '516190.XSHG',  # (文娱ETF) [ETF]-成交额：1.67亿元-上市日期：2021-09-17
        '159840.XSHE',  # (锂电池ETF工银) [ETF]-成交额：1.61亿元-上市日期：2021-08-20
        '159611.XSHE',  # (电力ETF) [ETF]-成交额：1.52亿元-上市日期：2022-01-07
        '159981.XSHE',  # (能源化工ETF) [ETF]-成交额：1.48亿元-上市日期：2020-01-17
        '159865.XSHE',  # (养殖ETF) [ETF]-成交额：1.40亿元-上市日期：2021-03-08
        '561360.XSHG',  # (石油ETF) [ETF]-成交额：1.36亿元-上市日期：2023-10-31
        '159667.XSHE',  # (工业母机ETF) [ETF]-成交额：1.32亿元-上市日期：2022-10-26
        '515170.XSHG',  # (食品饮料ETF) [ETF]-成交额：1.30亿元-上市日期：2021-01-13
        '513360.XSHG',  # (教育ETF) [ETF]-成交额：1.09亿元-上市日期：2021-06-17
        '159825.XSHE',  # (农业ETF) [ETF]-成交额：1.05亿元-上市日期：2020-12-29
        '515210.XSHG',  # (钢铁ETF) [ETF]-成交额：1.03亿元-上市日期：2020-03-02
    ]	
    
    # 运行时间：每周一9:30执行调仓
    run_weekly(trade, 1, '9:30')
    # run_daily(trade, '9:30') #每天运行确保即时捕捉动量变化
    
    g.m_days = 34  # 动量参考天数

#============基于年化收益和判定系数打分的动量因子轮动=============
def get_rank(etf_pool):
    """计算ETF的动量评分并排序"""
    score_list = []
    for etf in etf_pool:
        # 获取ETF的历史收盘价
        df = attribute_history(etf, g.m_days, '1d', ['close'])
        # 计算对数收益率
        y = df['log'] = np.log(df.close)
        # 生成时间序列
        x = df['num'] = np.arange(df.log.size)
        # 线性回归，计算斜率和截距
        slope, intercept = np.polyfit(x, y, 1)
        # 计算年化收益率
        annualized_returns = math.pow(math.exp(slope), 250) - 1
        # 计算判定系数R²，衡量趋势的稳定性
        r_squared = 1 - (sum((y - (slope * x + intercept))**2) / ((len(y) - 1) * np.var(y, ddof=1)))
        # 综合评分：年化收益 * R²
        score = annualized_returns * r_squared
        score_list.append(score)
    
    # 构建评分数据框并排序
    df = pd.DataFrame(index=etf_pool, data={'score': score_list})
    df = df.sort_values(by='score', ascending=False)
    df = df.dropna()  # 删除缺失值
    
    # 生成排名列表
    rank_list = list(df.index)
    print(df)
    
    # 过滤掉负向动量的ETF
    filtered_rank_list = [etf for etf in rank_list if df.loc[etf, 'score'] > 0]
    return filtered_rank_list
    # return rank_list   


def epo(x, signal, lambda_, method='simple', w=None, anchor=None, normalize=True, endogenous=True):
    """增强型风险平价（EPO）优化算法"""
    n = x.shape[1]  # 资产数量
    vcov = x.cov()  # 协方差矩阵
    corr = x.corr()  # 相关性矩阵
    I = np.eye(n)    # 单位矩阵
    
    # 构建对角矩阵，对角线为方差
    V = np.zeros((n, n))
    np.fill_diagonal(V, vcov.values.diagonal())
    std = np.sqrt(V)  # 标准差矩阵
    
    s = signal  # 信号向量
    a = anchor  # 锚定权重

    # 相关性矩阵收缩，提高稳定性
    shrunk_cor = ((1 - w) * I @ corr.values) + (w * I)  # equation 7
    # 计算收缩后的协方差矩阵
    cov_tilde = std @ shrunk_cor @ std  # topic 2.II: page 11
    # 计算协方差矩阵的逆
    inv_shrunk_cov = solve(cov_tilde, np.eye(n))

    # 不同方法计算EPO权重
    if method == 'simple':
        # 简单方法：基于信号和协方差矩阵
        epo = (1 / lambda_) * inv_shrunk_cov @ signal  # equation 16
    elif method == 'anchored':
        # 锚定方法：结合锚定权重
        if endogenous:
            # 内生锚定：自动调整信号强度
            gamma = np.sqrt(a.T @ cov_tilde @ a) / np.sqrt(s.T @ inv_shrunk_cov @ cov_tilde @ inv_shrunk_cov @ s)
            epo = inv_shrunk_cov @ (((1 - w) * gamma * s) + ((w * I @ V @ a)))
        else:
            # 外生锚定：固定信号强度
            epo = inv_shrunk_cov @ (((1 - w) * (1 / lambda_) * s) + ((w * I @ V @ a)))

    # 权重归一化
    if normalize:
        # 过滤负权重
        epo = [0 if a < 0 else a for a in epo]
        # 归一化权重和为1
        epo = epo / np.sum(epo)

    return epo

# 定义获取数据并调用优化函数的函数
def run_optimization(stocks, end_date):
    """获取历史数据并执行EPO优化"""
    # 获取ETF的历史收盘价
    prices = get_price(stocks, count=1200, end_date=end_date, 
                      frequency='daily', fields=['close'])['close']
    # 计算收益率
    returns = prices.pct_change().dropna()
    # 计算协方差矩阵的对角线（方差）
    d = np.diag(returns.cov())
    # 基于方差的倒数计算初始锚定权重
    a = (1/d) / (1/d).sum()
    # a= np.array([0.25,0.25,0.25,0.25])  # 等权锚定
    
    # 执行EPO优化
    weights = epo(x=returns, signal=returns.mean(), lambda_=g._lambda, 
                 method='anchored', w=g.w, anchor=a)
    return weights
    
# 交易
def trade(context):
    """执行交易：卖出不在目标列表的ETF，买入并优化目标ETF的权重"""
    end_date = context.previous_date 
    # 获取动量排名前g.stock_num的ETF
    target_list = get_rank(g.etf_pool)[:g.stock_num]
    
    # 卖出：不在目标列表中的ETF
    hold_list = list(context.portfolio.positions)
    for etf in hold_list:
        if etf not in target_list:
            order_target_value(etf, 0)  # 卖出全部持仓
            print('卖出' + str(etf))
        else:
            print('继续持有' + str(etf))
            
    # 买入：对目标ETF执行EPO优化并分配权重
    weights = run_optimization(target_list, end_date)

    if weights is None:
        return
    
    total_value = context.portfolio.total_value  # 总资金
    index = 0
    for w in weights:
        value = total_value * w  # 计算每只ETF的目标市值
        order_target_value(target_list[index], value)  # 下单
        index += 1   
