import akshare as ak
import time

print("=" * 50)
print("测试akshare可用的替代接口")
print("=" * 50)

# 测试1: 获取大盘指数数据
print("\n1. 获取大盘指数数据的替代接口...")
methods = [
    ('stock_zh_index_spot_em', '东方财富-实时行情'),
    ('stock_zh_index_daily_em', '东方财富-日K线'),
    ('index_zh_a_hist', '东方财富-指数历史'),
]

for method_name, desc in methods:
    try:
        start_time = time.time()
        if method_name == 'stock_zh_index_spot_em':
            data = ak.stock_zh_index_spot_em()
        elif method_name == 'stock_zh_index_daily_em':
            data = ak.stock_zh_index_daily_em(symbol="sh000001")
        elif method_name == 'index_zh_a_hist':
            data = ak.index_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20240110")
        
        elapsed = time.time() - start_time
        print(f"✓ {method_name} ({desc}) 成功! 耗时: {elapsed:.2f}秒, 数据形状: {data.shape}")
    except Exception as e:
        print(f"✗ {method_name} ({desc}) 失败: {str(e)[:100]}")

# 测试2: 获取A股市场数据
print("\n2. 获取A股市场数据的替代接口...")
methods = [
    ('stock_zh_a_spot_em', '东方财富-实时行情'),
    ('stock_zh_a_hist', '新浪-历史数据'),
    ('stock_zh_a_hist_min_em', '东方财富-分钟数据'),
]

for method_name, desc in methods:
    try:
        start_time = time.time()
        if method_name == 'stock_zh_a_spot_em':
            data = ak.stock_zh_a_spot_em()
        elif method_name == 'stock_zh_a_hist':
            data = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20240110", adjust="")
        elif method_name == 'stock_zh_a_hist_min_em':
            data = ak.stock_zh_a_hist_min_em(symbol="000001", period="1", adjust="")
        
        elapsed = time.time() - start_time
        print(f"✓ {method_name} ({desc}) 成功! 耗时: {elapsed:.2f}秒, 数据形状: {data.shape}")
    except Exception as e:
        print(f"✗ {method_name} ({desc}) 失败: {str(e)[:100]}")

# 测试3: 获取板块数据
print("\n3. 获取板块数据的替代接口...")
methods = [
    ('stock_board_industry_name_em', '东方财富-行业板块'),
    ('stock_board_concept_name_em', '东方财富-概念板块'),
    ('stock_board_industry_hist_em', '东方财富-行业历史'),
]

for method_name, desc in methods:
    try:
        start_time = time.time()
        if method_name == 'stock_board_industry_name_em':
            data = ak.stock_board_industry_name_em()
        elif method_name == 'stock_board_concept_name_em':
            data = ak.stock_board_concept_name_em()
        elif method_name == 'stock_board_industry_hist_em':
            data = ak.stock_board_industry_hist_em()
        
        elapsed = time.time() - start_time
        print(f"✓ {method_name} ({desc}) 成功! 耗时: {elapsed:.2f}秒, 数据形状: {data.shape}")
    except Exception as e:
        print(f"✗ {method_name} ({desc}) 失败: {str(e)[:100]}")

# 测试4: 获取资金流向数据
print("\n4. 获取资金流向数据的替代接口...")
methods = [
    ('stock_individual_fund_flow', '东方财富-个股资金流'),
    ('stock_market_fund_flow', '东方财富-市场资金流'),
]

for method_name, desc in methods:
    try:
        start_time = time.time()
        if method_name == 'stock_individual_fund_flow':
            data = ak.stock_individual_fund_flow(stock="000001", market="sh")
        elif method_name == 'stock_market_fund_flow':
            data = ak.stock_market_fund_flow()
        
        elapsed = time.time() - start_time
        print(f"✓ {method_name} ({desc}) 成功! 耗时: {elapsed:.2f}秒, 数据形状: {data.shape}")
    except Exception as e:
        print(f"✗ {method_name} ({desc}) 失败: {str(e)[:100]}")

# 测试5: 获取北向资金数据
print("\n5. 获取北向资金数据的替代接口...")
methods = [
    ('stock_hk_hold_stock_em', '东方财富-港股持股'),
    ('stock_em_hsgt_north_net_flow_in_em', '东方财富-北向资金'),
]

for method_name, desc in methods:
    try:
        start_time = time.time()
        if method_name == 'stock_hk_hold_stock_em':
            data = ak.stock_hk_hold_stock_em()
        elif method_name == 'stock_em_hsgt_north_net_flow_in_em':
            data = ak.stock_em_hsgt_north_net_flow_in_em()
        
        elapsed = time.time() - start_time
        print(f"✓ {method_name} ({desc}) 成功! 耗时: {elapsed:.2f}秒, 数据形状: {data.shape}")
    except Exception as e:
        print(f"✗ {method_name} ({desc}) 失败: {str(e)[:100]}")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
