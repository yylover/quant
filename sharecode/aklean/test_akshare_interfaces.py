import time
import logging
from typing import Dict, List, Tuple

import akshare as ak
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AkShareInterfaceTester:
    """测试akshare股票相关接口的可用性"""
    
    def __init__(self):
        self.interfaces = []
        self.results = []
        
    def add_interface(self, name: str, func, params: Dict = None, description: str = ""):
        """添加接口测试项"""
        self.interfaces.append({
            'name': name,
            'func': func,
            'params': params or {},
            'description': description
        })
    
    def test_interface(self, interface: Dict) -> Dict:
        """测试单个接口"""
        name = interface['name']
        func = interface['func']
        params = interface['params']
        
        start_time = time.time()
        success = False
        error = ""
        
        try:
            result = func(**params)
            if isinstance(result, pd.DataFrame):
                success = not result.empty
                data_info = f"DataFrame with {len(result)} rows and {len(result.columns)} columns"
            else:
                success = result is not None
                data_info = f"Type: {type(result).__name__}"
        except Exception as e:
            success = False
            error = str(e)
            data_info = "Error occurred"
        
        elapsed = time.time() - start_time
        
        result = {
            'name': name,
            'success': success,
            'elapsed': round(elapsed, 3),
            'error': error,
            'data_info': data_info,
            'description': interface['description']
        }
        
        return result
    
    def test_all(self) -> List[Dict]:
        """测试所有接口"""
        logger.info(f"开始测试 {len(self.interfaces)} 个akshare接口...")
        
        for interface in self.interfaces:
            logger.info(f"测试接口: {interface['name']}")
            result = self.test_interface(interface)
            self.results.append(result)
            
            status = "成功" if result['success'] else "失败"
            logger.info(f"  结果: {status}, 耗时: {result['elapsed']}s")
            if not result['success']:
                logger.error(f"  错误: {result['error']}")
            
            # 添加延迟，避免频繁请求
            time.sleep(0.5)
        
        return self.results
    
    def print_summary(self):
        """打印测试总结"""
        total = len(self.results)
        success_count = sum(1 for r in self.results if r['success'])
        failure_count = total - success_count
        
        print("\n" + "="*60)
        print("AkShare接口测试报告")
        print("="*60)
        print(f"测试接口总数: {total}")
        print(f"成功: {success_count} ({success_count/total*100:.1f}%)")
        print(f"失败: {failure_count} ({failure_count/total*100:.1f}%)")
        print("-"*60)
        
        # 打印失败的接口
        if failure_count > 0:
            print("\n失败的接口:")
            for r in self.results:
                if not r['success']:
                    print(f"  - {r['name']}: {r['error']}")
        
        # 打印成功的接口
        print("\n成功的接口:")
        for r in self.results:
            if r['success']:
                print(f"  - {r['name']}: {r['data_info']} (耗时: {r['elapsed']}s)")

def main():
    tester = AkShareInterfaceTester()
    
    # ========== 交易所数据接口 ==========
    # 上海证券交易所
    tester.add_interface("stock_sse_summary", ak.stock_sse_summary, description="上海证券交易所-股票数据总貌")
    tester.add_interface("stock_sse_deal_daily", ak.stock_sse_deal_daily, params={"date": "20260324"}, description="上海证券交易所-每日股票成交概况")
    
    # 深圳证券交易所
    tester.add_interface("stock_szse_summary", ak.stock_szse_summary, params={"date": "20260224"}, description="深圳证券交易所-市场总貌-证券类别统计")
    tester.add_interface("stock_szse_area_summary", ak.stock_szse_area_summary, params={"date": "202602"}, description="深圳证券交易所-市场总貌-地区交易排序")
    tester.add_interface("stock_szse_sector_summary", ak.stock_szse_sector_summary, params={"symbol": "当年", "date": "202602"}, description="深圳证券交易所-统计资料-股票行业成交数据")
    
    # ========== 个股信息接口 ==========
    tester.add_interface("stock_individual_info_em", ak.stock_individual_info_em, params={"symbol": "600000"}, description="东方财富-个股-股票信息")
    tester.add_interface("stock_individual_basic_info_xq", ak.stock_individual_basic_info_xq, params={"symbol": "SH601127"}, description="雪球财经-个股-公司概况-公司简介")
    tester.add_interface("stock_bid_ask_em", ak.stock_bid_ask_em, params={"symbol": "000001"}, description="东方财富-行情报价")
    tester.add_interface("stock_individual_spot_xq", ak.stock_individual_spot_xq, params={"symbol": "SH600000"}, description="雪球财经-个股-实时行情")
    tester.add_interface("stock_profile_cninfo", ak.stock_profile_cninfo, params={"symbol": "600000"}, description="中国证监会-个股-公司概况")
    
    # ========== 实时行情接口 ==========
    tester.add_interface("stock_zh_a_spot_em", ak.stock_zh_a_spot_em, description="东方财富网-全部A股-实时行情数据")
    tester.add_interface("stock_sh_a_spot_em", ak.stock_sh_a_spot_em, description="东方财富网-沪A股-实时行情数据")
    tester.add_interface("stock_sz_a_spot_em", ak.stock_sz_a_spot_em, description="东方财富网-深A股-实时行情数据")
    tester.add_interface("stock_bj_a_spot_em", ak.stock_bj_a_spot_em, description="东方财富网-京A股-实时行情数据")
    tester.add_interface("stock_new_a_spot_em", ak.stock_new_a_spot_em, description="东方财富网-新股-实时行情数据")
    tester.add_interface("stock_cy_a_spot_em", ak.stock_cy_a_spot_em, description="东方财富网-创业板-实时行情数据")
    tester.add_interface("stock_kc_a_spot_em", ak.stock_kc_a_spot_em, description="东方财富网-科创板-实时行情数据")
    tester.add_interface("stock_zh_ab_comparison_em", ak.stock_zh_ab_comparison_em, description="东方财富网-A股B股比价")
    tester.add_interface("stock_zh_a_spot", ak.stock_zh_a_spot, description="新浪财经-A股实时行情数据")
    
    # ========== 历史数据接口 ==========
    tester.add_interface("stock_zh_a_hist", ak.stock_zh_a_hist, params={"symbol": "000001", "period": "daily", "start_date": "20260301", "end_date": "20260324", "adjust": "qfq"}, description="东方财富网-A股历史行情数据-前复权")
    tester.add_interface("stock_zh_a_hist", ak.stock_zh_a_hist, params={"symbol": "000001", "period": "daily", "start_date": "20260301", "end_date": "20260324", "adjust": "hfq"}, description="东方财富网-A股历史行情数据-后复权")
    tester.add_interface("stock_zh_a_hist", ak.stock_zh_a_hist, params={"symbol": "000001", "period": "daily", "start_date": "20260301", "end_date": "20260324", "adjust": ""}, description="东方财富网-A股历史行情数据-不复权")
    tester.add_interface("stock_zh_a_hist_tx", ak.stock_zh_a_hist_tx, params={"symbol": "000001", "start_date": "20260301", "end_date": "20260324", "adjust": "qfq"}, description="腾讯财经-A股历史行情数据-前复权")
    tester.add_interface("stock_zh_a_hist_tx", ak.stock_zh_a_hist_tx, params={"symbol": "000001", "start_date": "20260301", "end_date": "20260324", "adjust": "hfq"}, description="腾讯财经-A股历史行情数据-后复权")
    tester.add_interface("stock_zh_a_hist_tx", ak.stock_zh_a_hist_tx, params={"symbol": "000001", "start_date": "20260301", "end_date": "20260324", "adjust": ""}, description="腾讯财经-A股历史行情数据-不复权")
    tester.add_interface("stock_zh_a_daily", ak.stock_zh_a_daily, params={"symbol": "000001", "start_date": "20260301", "end_date": "20260324", "adjust": "qfq"}, description="新浪财经-A股历史行情数据-前复权")
    tester.add_interface("stock_zh_a_daily", ak.stock_zh_a_daily, params={"symbol": "000001", "start_date": "20260301", "end_date": "20260324", "adjust": "hfq"}, description="新浪财经-A股历史行情数据-后复权")
    tester.add_interface("stock_zh_a_daily", ak.stock_zh_a_daily, params={"symbol": "000002", "adjust": "qfq-factor"}, description="新浪财经-A股前复权因子")
    tester.add_interface("stock_zh_a_daily", ak.stock_zh_a_daily, params={"symbol": "000002", "adjust": "hfq-factor"}, description="新浪财经-A股后复权因子")
    
    # ========== 实时交易数据接口（网页示例） ==========
    tester.add_interface("stock_intraday_em", ak.stock_intraday_em, params={"symbol": "000001"}, description="东方财富-A股实时交易数据")
    tester.add_interface("stock_intraday_sina", ak.stock_intraday_sina, params={"symbol": "sz000001", "date": "20260324"}, description="新浪财经-A股实时交易数据")
    tester.add_interface("stock_zh_a_minute", ak.stock_zh_a_minute, params={"symbol": "sh600751", "period": "1", "adjust": "qfq"}, description="新浪财经-A股分钟级行情数据")
    tester.add_interface("stock_zh_a_hist_min_em", ak.stock_zh_a_hist_min_em, params={"symbol": "000001", "period": "1", "adjust": ""}, description="东方财富-A股分钟级历史行情数据-不复权")
    tester.add_interface("stock_zh_a_hist_min_em", ak.stock_zh_a_hist_min_em, params={"symbol": "000001", "period": "5", "adjust": "hfq"}, description="东方财富-A股分钟级历史行情数据-后复权")
    tester.add_interface("stock_zh_a_hist_pre_min_em", ak.stock_zh_a_hist_pre_min_em, params={"symbol": "000001", "start_time": "09:00:00", "end_time": "15:40:00"}, description="东方财富-A股盘前盘后分钟级行情数据")
    tester.add_interface("stock_zh_a_tick_tx_js", ak.stock_zh_a_tick_tx_js, params={"symbol": "sz000001"}, description="腾讯财经-A股成交明细数据")
    
    # ========== 指数数据接口 ==========
    tester.add_interface("stock_zh_index_daily_em", ak.stock_zh_index_daily_em, params={"symbol": "sh000300", "start_date": "20260301", "end_date": "20260324"}, description="东方财富-指数历史行情数据")
    tester.add_interface("stock_zh_index_daily", ak.stock_zh_index_daily, params={"symbol": "sh000300"}, description="新浪财经-指数历史行情数据")
    tester.add_interface("index_zh_a_hist", ak.index_zh_a_hist, params={"symbol": "000300", "period": "daily", "start_date": "20260301", "end_date": "20260324"}, description="东方财富-指数历史行情数据(旧版)")
    tester.add_interface("stock_zh_index_spot_em", ak.stock_zh_index_spot_em, description="东方财富-指数实时行情数据")
    
    # ========== ETF数据接口 ==========
    tester.add_interface("fund_etf_hist_em", ak.fund_etf_hist_em, params={"symbol": "510300", "period": "daily", "start_date": "20260301", "end_date": "20260324", "adjust": "qfq"}, description="东方财富-ETF历史行情数据")
    tester.add_interface("fund_etf_hist_sina", ak.fund_etf_hist_sina, params={"symbol": "sh510300"}, description="新浪财经-ETF历史行情数据")
    
    # ========== 资金流向接口 ==========
    tester.add_interface("stock_market_fund_flow", ak.stock_market_fund_flow, description="东方财富-市场资金流向")
    tester.add_interface("stock_main_fund_flow", ak.stock_main_fund_flow, description="东方财富-主力资金流向")
    tester.add_interface("stock_fund_flow_industry", ak.stock_fund_flow_industry, description="东方财富-行业资金流向")
    tester.add_interface("stock_fund_flow_concept", ak.stock_fund_flow_concept, description="东方财富-概念资金流向")
    
    # ========== 财务数据接口 ==========
    tester.add_interface("stock_yjbb_em", ak.stock_yjbb_em, params={"symbol": "600000", "year": "2025", "quarter": "4"}, description="东方财富-业绩报表")
    tester.add_interface("stock_zcfz_em", ak.stock_zcfz_em, params={"symbol": "600000", "year": "2025", "quarter": "4"}, description="东方财富-资产负债表")
    tester.add_interface("stock_xjll_em", ak.stock_xjll_em, params={"symbol": "600000", "year": "2025", "quarter": "4"}, description="东方财富-现金流量表")
    
    # ========== 行业板块接口 ==========
    tester.add_interface("stock_sector_spot", ak.stock_sector_spot, description="东方财富-行业板块行情")
    tester.add_interface("stock_industry_category_cninfo", ak.stock_industry_category_cninfo, description="中国证监会-行业分类")
    
    # ========== 港股数据接口 ==========
    tester.add_interface("stock_hk_spot_em", ak.stock_hk_spot_em, description="东方财富-港股实时行情")
    tester.add_interface("stock_hk_index_spot_em", ak.stock_hk_index_spot_em, description="东方财富-港股指数实时行情")
    
    # ========== 美股数据接口 ==========
    tester.add_interface("stock_us_spot_em", ak.stock_us_spot_em, description="东方财富-美股实时行情")
    tester.add_interface("stock_us_famous_spot_em", ak.stock_us_famous_spot_em, description="东方财富-美股知名股票实时行情")
    
    # ========== 其他常用接口 ==========
    tester.add_interface("stock_register_sh", ak.stock_register_sh, description="上海证券交易所-上市公司列表")
    tester.add_interface("stock_register_sz", ak.stock_register_sz, description="深圳证券交易所-上市公司列表")
    tester.add_interface("stock_hot_rank_em", ak.stock_hot_rank_em, description="东方财富-热门排行榜")
    tester.add_interface("stock_news_em", ak.stock_news_em, description="东方财富-股票新闻")
    tester.add_interface("stock_zh_growth_comparison_em", ak.stock_zh_growth_comparison_em, params={"symbol": "SZ000895"}, description="东方财富-A股成长对比数据")
    
    # 测试所有接口
    results = tester.test_all()
    
    # 打印总结
    tester.print_summary()

if __name__ == "__main__":
    main()
