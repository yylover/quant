import requests
import akshare as ak
import time

print("=" * 50)
print("测试网络连接和API访问")
print("=" * 50)

# 测试1: 基础网络连接
print("\n1. 测试基础网络连接...")
try:
    response = requests.get('https://www.baidu.com', timeout=5)
    print(f"✓ 百度连接成功: {response.status_code}")
except Exception as e:
    print(f"✗ 百度连接失败: {e}")

try:
    response = requests.get('https://www.eastmoney.com', timeout=5)
    print(f"✓ 东方财富连接成功: {response.status_code}")
except Exception as e:
    print(f"✗ 东方财富连接失败: {e}")

# 测试2: 测试不同的akshare接口
print("\n2. 测试akshare不同接口...")

# 测试股票指数接口
print("\n测试股票指数接口...")
try:
    start_time = time.time()
    sh_index = ak.stock_zh_index_spot_em()
    elapsed = time.time() - start_time
    print(f"✓ stock_zh_index_spot_em 成功! 耗时: {elapsed:.2f}秒")
    print(f"  数据形状: {sh_index.shape}")
    print(f"  列名: {list(sh_index.columns)[:5]}...")
except Exception as e:
    print(f"✗ stock_zh_index_spot_em 失败: {e}")

# 测试A股实时行情接口
print("\n测试A股实时行情接口...")
try:
    start_time = time.time()
    stock_data = ak.stock_zh_a_spot_em()
    elapsed = time.time() - start_time
    print(f"✓ stock_zh_a_spot_em 成功! 耗时: {elapsed:.2f}秒")
    print(f"  数据形状: {stock_data.shape}")
    print(f"  列名: {list(stock_data.columns)[:5]}...")
except Exception as e:
    print(f"✗ stock_zh_a_spot_em 失败: {e}")

# 测试3: 测试其他数据源接口
print("\n3. 测试其他数据源接口...")

# 测试新浪财经接口
print("\n测试新浪财经接口...")
try:
    start_time = time.time()
    sina_data = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20240110", adjust="")
    elapsed = time.time() - start_time
    print(f"✓ stock_zh_a_hist (新浪) 成功! 耗时: {elapsed:.2f}秒")
    print(f"  数据形状: {sina_data.shape}")
except Exception as e:
    print(f"✗ stock_zh_a_hist 失败: {e}")

# 测试腾讯财经接口
print("\n测试腾讯财经实时行情...")
try:
    start_time = time.time()
    qq_data = ak.stock_zh_a_hist_min_em(symbol="000001", period="1", adjust="")
    elapsed = time.time() - start_time
    print(f"✓ stock_zh_a_hist_min_em (腾讯) 成功! 耗时: {elapsed:.2f}秒")
    print(f"  数据形状: {qq_data.shape}")
except Exception as e:
    print(f"✗ stock_zh_a_hist_min_em 失败: {e}")

# 测试4: 测试代理设置
print("\n4. 检查代理设置...")
import os
http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
print(f"HTTP_PROXY: {http_proxy}")
print(f"HTTPS_PROXY: {https_proxy}")

# 测试5: 测试直接HTTP请求（不使用代理）
print("\n5. 测试直接HTTP请求...")
try:
    session = requests.Session()
    session.trust_env = False  # 不使用环境变量中的代理
    response = session.get('https://push2.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&fqt=0&beg=20240101&end=20240110', timeout=10)
    print(f"✓ 直接请求东方财富API成功: {response.status_code}")
    data = response.json()
    if data and 'data' in data:
        print(f"  返回数据: {data['data'] is not None}")
except Exception as e:
    print(f"✗ 直接请求失败: {e}")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
