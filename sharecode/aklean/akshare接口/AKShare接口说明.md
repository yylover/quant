# AKShare 股票数据接口说明文档

## 目录

1. [交易所数据接口](#交易所数据接口)
2. [个股信息接口](#个股信息接口)
3. [实时行情接口](#实时行情接口)
4. [历史数据接口](#历史数据接口)
5. [实时交易数据接口](#实时交易数据接口)
6. [指数数据接口](#指数数据接口)
7. [ETF数据接口](#etf数据接口)
8. [资金流向接口](#资金流向接口)
9. [财务数据接口](#财务数据接口)
10. [行业板块接口](#行业板块接口)
11. [港股数据接口](#港股数据接口)
12. [美股数据接口](#美股数据接口)
13. [其他常用接口](#其他常用接口)

---

## 交易所数据接口

### stock_sse_summary
**功能**：上海证券交易所-股票数据总貌
**返回数据**：DataFrame，包含上海证券交易所的股票数据概况

### stock_sse_deal_daily
**功能**：上海证券交易所-每日股票成交概况
**参数**：
- date: 日期，格式如 "20260324"
**返回数据**：DataFrame，包含每日股票成交概况

### stock_szse_summary
**功能**：深圳证券交易所-市场总貌-证券类别统计
**参数**：
- date: 日期，格式如 "20260224"
**返回数据**：DataFrame，包含证券类别统计数据

### stock_szse_area_summary
**功能**：深圳证券交易所-市场总貌-地区交易排序
**参数**：
- date: 日期，格式如 "202602"
**返回数据**：DataFrame，包含地区交易排序数据

### stock_szse_sector_summary
**功能**：深圳证券交易所-统计资料-股票行业成交数据
**参数**：
- symbol: 时间范围，如 "当年"
- date: 日期，格式如 "202602"
**返回数据**：DataFrame，包含股票行业成交数据

---

## 个股信息接口

### stock_individual_info_em
**功能**：东方财富-个股-股票信息
**参数**：
- symbol: 股票代码，如 "600000"
**返回数据**：DataFrame，包含个股详细信息

### stock_individual_basic_info_xq
**功能**：雪球财经-个股-公司概况-公司简介
**参数**：
- symbol: 股票代码，如 "SH601127"
**返回数据**：DataFrame，包含公司基本信息

### stock_bid_ask_em
**功能**：东方财富-行情报价
**参数**：
- symbol: 股票代码，如 "000001"
**返回数据**：DataFrame，包含买卖盘报价数据

### stock_individual_spot_xq
**功能**：雪球财经-个股-实时行情
**参数**：
- symbol: 股票代码，如 "SH600000"
**返回数据**：DataFrame，包含实时行情数据

### stock_profile_cninfo
**功能**：中国证监会-个股-公司概况
**参数**：
- symbol: 股票代码，如 "600000"
**返回数据**：DataFrame，包含公司概况信息

---

## 实时行情接口

### stock_zh_a_spot_em
**功能**：东方财富网-全部A股-实时行情数据
**返回数据**：DataFrame，包含全部A股实时行情

### stock_sh_a_spot_em
**功能**：东方财富网-沪A股-实时行情数据
**返回数据**：DataFrame，包含沪A股实时行情

### stock_sz_a_spot_em
**功能**：东方财富网-深A股-实时行情数据
**返回数据**：DataFrame，包含深A股实时行情

### stock_bj_a_spot_em
**功能**：东方财富网-京A股-实时行情数据
**返回数据**：DataFrame，包含京A股实时行情

### stock_new_a_spot_em
**功能**：东方财富网-新股-实时行情数据
**返回数据**：DataFrame，包含新股实时行情

### stock_cy_a_spot_em
**功能**：东方财富网-创业板-实时行情数据
**返回数据**：DataFrame，包含创业板实时行情

### stock_kc_a_spot_em
**功能**：东方财富网-科创板-实时行情数据
**返回数据**：DataFrame，包含科创板实时行情

### stock_zh_ab_comparison_em
**功能**：东方财富网-A股B股比价
**返回数据**：DataFrame，包含A股B股比价数据

### stock_zh_a_spot
**功能**：新浪财经-A股实时行情数据
**返回数据**：DataFrame，包含A股实时行情

---

## 历史数据接口

### stock_zh_a_hist
**功能**：东方财富网-A股历史行情数据
**参数**：
- symbol: 股票代码，如 "000001"
- period: 周期，如 "daily"
- start_date: 开始日期，格式如 "20260301"
- end_date: 结束日期，格式如 "20260324"
- adjust: 复权方式，可选值："qfq"（前复权）、"hfq"（后复权）、""（不复权）
**返回数据**：DataFrame，包含历史行情数据，列包括：日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率

### stock_zh_a_hist_tx
**功能**：腾讯财经-A股历史行情数据
**参数**：
- symbol: 股票代码，如 "000001"
- start_date: 开始日期，格式如 "20260301"
- end_date: 结束日期，格式如 "20260324"
- adjust: 复权方式，可选值："qfq"（前复权）、"hfq"（后复权）、""（不复权）
**返回数据**：DataFrame，包含历史行情数据

### stock_zh_a_daily
**功能**：新浪财经-A股历史行情数据
**参数**：
- symbol: 股票代码，如 "000001"
- start_date: 开始日期，格式如 "20260301"
- end_date: 结束日期，格式如 "20260324"
- adjust: 复权方式，可选值："qfq"（前复权）、"hfq"（后复权）、"qfq-factor"（前复权因子）、"hfq-factor"（后复权因子）
**返回数据**：DataFrame，包含历史行情数据或复权因子

---

## 实时交易数据接口

### stock_intraday_em
**功能**：东方财富-A股实时交易数据
**参数**：
- symbol: 股票代码，如 "000001"
**返回数据**：DataFrame，包含实时交易数据，列包括：时间、成交价、手数、买卖盘性质

### stock_intraday_sina
**功能**：新浪财经-A股实时交易数据
**参数**：
- symbol: 股票代码，如 "sz000001"
- date: 日期，格式如 "20260324"
**返回数据**：DataFrame，包含实时交易数据

### stock_zh_a_minute
**功能**：新浪财经-A股分钟级行情数据
**参数**：
- symbol: 股票代码，如 "sh600751"
- period: 周期，如 "1"（1分钟）
- adjust: 复权方式，如 "qfq"（前复权）
**返回数据**：DataFrame，包含分钟级行情数据

### stock_zh_a_hist_min_em
**功能**：东方财富-A股分钟级历史行情数据
**参数**：
- symbol: 股票代码，如 "000001"
- period: 周期，如 "1"（1分钟）、"5"（5分钟）
- adjust: 复权方式，可选值：""（不复权）、"hfq"（后复权）
**返回数据**：DataFrame，包含分钟级历史行情数据

### stock_zh_a_hist_pre_min_em
**功能**：东方财富-A股盘前盘后分钟级行情数据
**参数**：
- symbol: 股票代码，如 "000001"
- start_time: 开始时间，格式如 "09:00:00"
- end_time: 结束时间，格式如 "15:40:00"
**返回数据**：DataFrame，包含盘前盘后分钟级行情数据，列包括：时间、开盘、收盘、最高、最低、成交量、成交额、最新价

### stock_zh_a_tick_tx_js
**功能**：腾讯财经-A股成交明细数据
**参数**：
- symbol: 股票代码，如 "sz000001"
**返回数据**：DataFrame，包含成交明细数据，列包括：成交时间、成交价格、价格变动、成交量、成交额、性质

---

## 指数数据接口

### stock_zh_index_daily_em
**功能**：东方财富-指数历史行情数据
**参数**：
- symbol: 指数代码，如 "sh000300"
- start_date: 开始日期，格式如 "20260301"
- end_date: 结束日期，格式如 "20260324"
**返回数据**：DataFrame，包含指数历史行情数据

### stock_zh_index_daily
**功能**：新浪财经-指数历史行情数据
**参数**：
- symbol: 指数代码，如 "sh000300"
**返回数据**：DataFrame，包含指数历史行情数据

### index_zh_a_hist
**功能**：东方财富-指数历史行情数据(旧版)
**参数**：
- symbol: 指数代码，如 "000300"
- period: 周期，如 "daily"
- start_date: 开始日期，格式如 "20260301"
- end_date: 结束日期，格式如 "20260324"
**返回数据**：DataFrame，包含指数历史行情数据

### stock_zh_index_spot_em
**功能**：东方财富-指数实时行情数据
**返回数据**：DataFrame，包含指数实时行情数据

---

## ETF数据接口

### fund_etf_hist_em
**功能**：东方财富-ETF历史行情数据
**参数**：
- symbol: ETF代码，如 "510300"
- period: 周期，如 "daily"
- start_date: 开始日期，格式如 "20260301"
- end_date: 结束日期，格式如 "20260324"
- adjust: 复权方式，如 "qfq"（前复权）
**返回数据**：DataFrame，包含ETF历史行情数据

### fund_etf_hist_sina
**功能**：新浪财经-ETF历史行情数据
**参数**：
- symbol: ETF代码，如 "sh510300"
**返回数据**：DataFrame，包含ETF历史行情数据

---

## 资金流向接口

### stock_market_fund_flow
**功能**：东方财富-市场资金流向
**返回数据**：DataFrame，包含市场资金流向数据

### stock_main_fund_flow
**功能**：东方财富-主力资金流向
**返回数据**：DataFrame，包含主力资金流向数据

### stock_fund_flow_industry
**功能**：东方财富-行业资金流向
**返回数据**：DataFrame，包含行业资金流向数据

### stock_fund_flow_concept
**功能**：东方财富-概念资金流向
**返回数据**：DataFrame，包含概念资金流向数据

---

## 财务数据接口

### stock_yjbb_em
**功能**：东方财富-业绩报表
**参数**：
- symbol: 股票代码，如 "600000"
- year: 年份，如 "2025"
- quarter: 季度，如 "4"
**返回数据**：DataFrame，包含业绩报表数据

### stock_zcfz_em
**功能**：东方财富-资产负债表
**参数**：
- symbol: 股票代码，如 "600000"
- year: 年份，如 "2025"
- quarter: 季度，如 "4"
**返回数据**：DataFrame，包含资产负债表数据

### stock_xjll_em
**功能**：东方财富-现金流量表
**参数**：
- symbol: 股票代码，如 "600000"
- year: 年份，如 "2025"
- quarter: 季度，如 "4"
**返回数据**：DataFrame，包含现金流量表数据

---

## 行业板块接口

### stock_sector_spot
**功能**：东方财富-行业板块行情
**返回数据**：DataFrame，包含行业板块行情数据

### stock_industry_category_cninfo
**功能**：中国证监会-行业分类
**返回数据**：DataFrame，包含行业分类数据

---

## 港股数据接口

### stock_hk_spot_em
**功能**：东方财富-港股实时行情
**返回数据**：DataFrame，包含港股实时行情数据

### stock_hk_index_spot_em
**功能**：东方财富-港股指数实时行情
**返回数据**：DataFrame，包含港股指数实时行情数据

---

## 美股数据接口

### stock_us_spot_em
**功能**：东方财富-美股实时行情
**返回数据**：DataFrame，包含美股实时行情数据

### stock_us_famous_spot_em
**功能**：东方财富-美股知名股票实时行情
**返回数据**：DataFrame，包含美股知名股票实时行情数据

---

## 其他常用接口

### stock_register_sh
**功能**：上海证券交易所-上市公司列表
**返回数据**：DataFrame，包含上海证券交易所上市公司列表

### stock_register_sz
**功能**：深圳证券交易所-上市公司列表
**返回数据**：DataFrame，包含深圳证券交易所上市公司列表

### stock_hot_rank_em
**功能**：东方财富-热门排行榜
**返回数据**：DataFrame，包含热门排行榜数据

### stock_news_em
**功能**：东方财富-股票新闻
**返回数据**：DataFrame，包含股票新闻数据

### stock_zh_growth_comparison_em
**功能**：东方财富-A股成长对比数据
**参数**：
- symbol: 股票代码，如 "SZ000895"
**返回数据**：DataFrame，包含成长对比数据，列包括：代码、简称、基本每股收益增长率等
