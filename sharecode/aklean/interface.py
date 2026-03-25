import akshare as ak

#  上海证券交易所-股票数据总貌
#       项目         股票         主板        科创板
# 0   流通股本   48055.48   46065.86    1989.62
# 1    总市值     638042  533575.83  104466.17
# 2  平均市盈率      16.05      14.50      67.81
# 3   上市公司       2310       1706        604
# 4   上市股票       2348       1744        604
# 5   流通市值  598415.22  511725.26   86689.96
# 6   报告时间   20260324   20260324   20260324
# 8    总股本   50831.82   48391.83    2439.98
stock_sse_summary_df = ak.stock_sse_summary()
# print(stock_sse_summary_df)

# 深圳证券交易所-市场总貌-证券类别统计
#  证券类别     数量          成交金额           总市值          流通市值
# 0      股票   2921  1.264094e+12  4.683284e+13  4.022196e+13
# 1    主板A股   1491  6.667593e+11  2.778351e+13  2.477194e+13
# 2    主板B股     38  8.666102e+07  4.288808e+10  4.286981e+10
# 3   创业板A股   1392  5.972478e+11  1.900644e+13  1.540715e+13
# 4      基金    921  1.469118e+11  1.853746e+12  1.824084e+12
# 5     ETF    610  1.426307e+11  1.729021e+12  1.729021e+12
# 6     LOF    285  4.128733e+09  5.030258e+10  5.030258e+10
# 7   封闭式基金      0  0.000000e+00  0.000000e+00  0.000000e+00
# 8   不动产基金     26  1.523746e+08  7.442301e+10  4.476120e+10
# 9      债券  17694  3.952046e+11           NaN           NaN
# 10   债券现券  16882  3.698409e+10  9.948543e+13  3.403808e+12
# 11   债券回购     27  3.580557e+11           NaN           NaN
# 12    ABS    785  1.648532e+08  5.071985e+11  5.071985e+11
# 13     期权    616  7.411038e+08           NaN           NaN

stock_szse_summary_df = ak.stock_szse_summary("20260224")
print(type(stock_szse_summary_df))


# 描述: 深圳证券交易所-市场总貌-地区交易排序
# 
#    序号    地区          总交易额     占市场         股票交易额         基金交易额         债券交易额  优先股交易额         期权交易额
# 0    1    上海  8.432298e+12  16.717  5.451040e+12  1.076990e+12  1.897329e+12     0.0  6.937815e+09
# 1    2    深圳  7.458096e+12  14.785  4.510531e+12  1.002755e+12  1.940137e+12     0.0  4.672334e+09
# 2    3    北京  5.539116e+12  10.981  3.858217e+12  6.225039e+11  1.055683e+12     0.0  2.711690e+09
# 3    4    浙江  4.170374e+12   8.268  3.526708e+12  1.362916e+11  5.064581e+11     0.0  9.159540e+08
# 4    5    江苏  3.630697e+12   7.198  2.620067e+12  2.686394e+11  7.403433e+11     0.0  1.646984e+09
# 5    6  境外地区  2.246968e+12   4.455  2.226384e+12  2.058420e+10  0.000000e+00     0.0  0.000000e+00
# 6    7    广州  2.043969e+12   4.052  1.313164e+12  1.400740e+11  5.886167e+11     0.0  2.114854e+09
# 7    8    福建  1.842029e+12   3.652  1.265960e+12  1.562180e+11  4.191139e+11     0.0  7.369614e+08
# 8    9    广东  1.733351e+12   3.436  1.465943e+12  6.727955e+10  1.995906e+11     0.0  5.383459e+08
stock_szse_summary_area_df = ak.stock_szse_area_summary("202602")
# print(stock_szse_summary_area_df)


# 描述: 深圳证券交易所-统计资料-股票行业成交数据
# http://docs.static.szse.cn/www/market/periodical/month/W020220511355248518608.html
#    项目名称                   项目名称-英文  交易天数       成交金额-人民币元  成交金额-占总计        成交股数-股数  成交股数-占总计      成交笔数-笔  成交笔数-占总计
# 0     合计                     Total    34  52711588336862    100.00  2962195080303    100.00  3269728259    100.00
# 1   农林牧渔               Agriculture    34    308873574751      0.59    32358074864      1.09    23705195      0.72
# 2    采矿业                    Mining    34   1110877718945      2.11    50195205082      1.69    63536333      1.94
# 3    制造业             Manufacturing    34  37767727698342     71.65  1849176775721     62.43  2252651315     68.89
# 4   水电煤气                 Utilities    34    495093109743      0.94    63904908366      2.16    47989834      1.47
# 5    建筑业              Construction    34    353106116557      0.67    40554398662      1.37    30837455      0.94
# 6   批发零售        Wholesale & Retail    34   1151705330918      2.18    95159397733      3.21    87353981      2.67
# 7   运输仓储            Transportation    34    233051512541      0.44    21404272298      0.72    22375568      0.68
# 8   住宿餐饮         Hotels & Catering    34     25212223836      0.05     3158890401      0.11     2397793      0.07
# 9   信息技术                        IT    34   6226850359735     11.81   333868532249     11.27   384331814     11.75
# 10   金融业                   Finance    34   1036823434423      1.97    70708695473      2.39    53237281      1.63
# 11   房地产               Real Estate    34    370897398530      0.70    81353601003      2.75    35494122      1.09
# 12  商务服务          Business Support    34   1667703732212      3.16   152489837536      5.15   116552985      3.56
# 13  科研服务    Research & Development    34    501013045310      0.95    25173031910      0.85    39462194      1.21
# 14  公共环保  Environmental Protection    34    321530536113      0.61    39767048921      1.34    30319139      0.93
# 15  居民服务         Resident Services    34      4948542774      0.01      272769079      0.01      440455      0.01
# 16    教育                 Education    34     72503283147      0.14    13448416202      0.45     5839216      0.18
# 17    卫生             Public Health    34    341773180646      0.65    29886320888      1.01    24145607      0.74
# 18  文化传播                     Media    34    677791972584      1.29    56890230460      1.92    45439888      1.39
stock_szse_sector_summary_df = ak.stock_szse_sector_summary(symbol="当年", date="202602")
# print(stock_szse_sector_summary_df)

# 描述: 上海证券交易所-数据-股票数据-成交概况-股票成交概况-每日股票情况
#     单日情况           股票          主板A       主板B          科创板  股票回购
# 0    挂牌数    2348.0000    1703.0000   41.0000     604.0000   0.0
# 1   市价总值  638042.0000  532664.9100  910.9200  104466.1700   0.0
# 2   流通市值  598415.2200  511054.3300  670.9300   86689.9600   0.0
# 3   成交金额    9320.5600    7182.5500    0.9800    2137.0400   0.0
# 4    成交量     680.8500     638.2300    0.2800      42.3300   0.0
# 5  平均市盈率      16.0500      14.5200    9.6400      67.8100   NaN
# 6    换手率       1.4608       1.3484    0.1072       2.0457   0.0
# 7  流通换手率       1.5575       1.4054    0.1455       2.4652   0.0
stock_sse_deal_daily_df = ak.stock_sse_deal_daily(date="20260324")
# print(stock_sse_deal_daily_df)


# # 东方财富-个股-股票信息
# 0    最新           10.05
# 1  股票代码          600000
# 2  股票简称            浦发银行
# 3   总股本   33305838300.0
# 4   流通股   33305838300.0
# 5   总市值  334723674915.0
# 6  流通市值  334723674915.0
# 7    行业             银行Ⅱ
# 8  上市时间        19991110
stock_individual_info_em_df = ak.stock_individual_info_em(symbol="600000")
# print(stock_individual_info_em_df)


# 描述: 雪球财经-个股-公司概况-公司简介
# 
#                             item                                              value
# 0                         org_id                                         T000071215
# 1                    org_name_cn                                        赛力斯集团股份有限公司
# 2              org_short_name_cn                                                赛力斯
# 3                    org_name_en                               Seres Group Co.,Ltd.
# 4              org_short_name_en                                              SERES
# 5        main_operation_business                         新能源汽车及核心三电等产品的研发、制造、销售及服务。
# 6                operating_scope  　　一般项目：制造、销售：汽车零部件、机动车辆零部件、普通机械、电器机械、电器、电子产品（不...
# 7                district_encode                                             500106
# 8            org_cn_introduction  赛力斯始创于1986年，是以新能源汽车为核心业务的技术科技型企业，A股、H股上市公司，中国企...
# 9           legal_representative                                                张正萍
# 10               general_manager                                                张正萍
# 11                     secretary                                                 申薇
# 12              established_date                                      1178812800000
# 13                     reg_asset                                       1741985086.0
# 14                     staff_num                                              18838
# 15                     telephone                                     86-23-65179666
# 16                      postcode                                             401335
# 17                           fax                                     86-23-65179777
# 18                         email                                    601127@seres.cn
# 19                   org_website                                       www.seres.cn
# 20                reg_address_cn                                      重庆市沙坪坝区五云湖路7号
# 21                reg_address_en                                               None
# 22             office_address_cn                                      重庆市沙坪坝区五云湖路7号
# 23             office_address_en                                               None
# 24               currency_encode                                             019001
# 25                      currency                                                CNY
# 26                   listed_date                                      1465920000000
# 27               provincial_name                                                重庆市
# 28             actual_controller                                       张兴海 (13.07%)
# 29                   classi_name                                               民营企业
# 30                   pre_name_cn                                     重庆小康工业集团股份有限公司
# 31                      chairman                                                张正萍
# 32               executives_nums                                                 18
# 33              actual_issue_vol                                        142500000.0
# 34                   issue_price                                               5.81
# 35             actual_rc_net_amt                                        738451000.0
# 36              pe_after_issuing                                              18.19
# 37  online_success_rate_of_issue                                           0.110176
# 38            affiliate_industry         {'ind_code': 'BK0025', 'ind_name': '汽车整车'}
stock_individual_basic_info_xq_df = ak.stock_individual_basic_info_xq(symbol="SH601127")
# print(stock_individual_basic_info_xq_df)


# 描述: 东方财富-行情报价  单次返回指定股票的行情报价数据
# 目标地址: https://quote.eastmoney.com/sz000001.html
# 限量: 单次返回指定股票的行情报价数据
# error
stock_bid_ask_em_df = ak.stock_bid_ask_em(symbol="000001")
# print(stock_bid_ask_em_df)



# 实时行情数据
# 实时行情数据-东财
# 接口: stock_zh_a_spot_em
# 目标地址: https://quote.eastmoney.com/center/gridlist.html#hs_a_board

stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
# print(stock_zh_a_spot_em_df)


# 接口: stock_sh_a_spot_em
# 目标地址: http://quote.eastmoney.com/center/gridlist.html#sh_a_board
# 描述: 东方财富网-沪 A 股-实时行情数据
stock_sh_a_spot_em_df = ak.stock_sh_a_spot_em()
# print(stock_sh_a_spot_em_df)


# 接口: stock_sz_a_spot_em
# 目标地址: http://quote.eastmoney.com/center/gridlist.html#sz_a_board
# 描述: 东方财富网-深 A 股-实时行情数据
stock_sz_a_spot_em_df = ak.stock_sz_a_spot_em()
# print(stock_sz_a_spot_em_df)


# 接口: stock_bj_a_spot_em
# 目标地址: http://quote.eastmoney.com/center/gridlist.html#bj_a_board
# 描述: 东方财富网-京 A 股-实时行情数据
# 限量: 单次返回所有京 A 股上市公司的实时行情数据

stock_bj_a_spot_em_df = ak.stock_bj_a_spot_em()
# print(stock_bj_a_spot_em_df)


stock_new_a_spot_em_df = ak.stock_new_a_spot_em()
print(stock_new_a_spot_em_df)