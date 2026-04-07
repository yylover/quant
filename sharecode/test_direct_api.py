import requests
import pandas as pd
import json
import time

print("=" * 50)
print("使用requests直接访问东方财富API")
print("=" * 50)

# 创建不使用代理的session
session = requests.Session()
session.trust_env = False

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.eastmoney.com/'
}

# 测试1: 获取大盘指数实时数据
print("\n1. 获取大盘指数实时数据...")
try:
    url = 'https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001,0.399006,1.000300&fields=f2,f3,f4,f5,f6,f7,f12,f14'
    response = session.get(url, headers=headers, timeout=10)
    data = response.json()
    
    if data and 'data' in data and data['data']:
        items = data['data']['diff']
        print(f"✓ 成功获取 {len(items)} 个指数数据")
        for item in items:
            print(f"  {item['f14']}: 最新价={item['f2']}, 涨跌幅={item['f3']}%, 涨跌额={item['f4']}")
    else:
        print("✗ 返回数据为空")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试2: 获取A股市场实时数据（分批获取）
print("\n2. 获取A股市场实时数据（前100只）...")
try:
    url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f4,f5,f6,f7,f12,f14'
    response = session.get(url, headers=headers, timeout=10)
    data = response.json()
    
    if data and 'data' in data and data['data']:
        items = data['data']['diff']
        print(f"✓ 成功获取 {len(items)} 只股票数据")
        
        # 统计涨跌家数
        up_count = sum(1 for item in items if item['f3'] > 0)
        down_count = sum(1 for item in items if item['f3'] < 0)
        flat_count = sum(1 for item in items if item['f3'] == 0)
        
        print(f"  上涨: {up_count}, 下跌: {down_count}, 平盘: {flat_count}")
        print(f"  涨跌比: {up_count/down_count if down_count > 0 else 0:.2f}")
        
        # 显示前5只股票
        print("  前5只股票:")
        for item in items[:5]:
            print(f"    {item['f14']}({item['f12']}): 涨跌幅={item['f3']}%")
    else:
        print("✗ 返回数据为空")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试3: 获取行业板块数据
print("\n3. 获取行业板块数据...")
try:
    url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f2,f3,f4,f5,f6,f12,f14'
    response = session.get(url, headers=headers, timeout=10)
    data = response.json()
    
    if data and 'data' in data and data['data']:
        items = data['data']['diff']
        print(f"✓ 成功获取 {len(items)} 个行业板块数据")
        
        # 按涨跌幅排序
        sorted_items = sorted(items, key=lambda x: x['f3'], reverse=True)
        
        print("  涨幅前5:")
        for item in sorted_items[:5]:
            print(f"    {item['f14']}: 涨跌幅={item['f3']}%")
        
        print("  跌幅前5:")
        for item in sorted_items[-5:]:
            print(f"    {item['f14']}: 涨跌幅={item['f3']}%")
    else:
        print("✗ 返回数据为空")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试4: 获取概念板块数据
print("\n4. 获取概念板块数据...")
try:
    url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:3&fields=f2,f3,f4,f5,f6,f12,f14'
    response = session.get(url, headers=headers, timeout=10)
    data = response.json()
    
    if data and 'data' in data and data['data']:
        items = data['data']['diff']
        print(f"✓ 成功获取 {len(items)} 个概念板块数据")
        
        # 按涨跌幅排序
        sorted_items = sorted(items, key=lambda x: x['f3'], reverse=True)
        
        print("  涨幅前5:")
        for item in sorted_items[:5]:
            print(f"    {item['f14']}: 涨跌幅={item['f3']}%")
    else:
        print("✗ 返回数据为空")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试5: 获取沪深300历史数据
print("\n5. 获取沪深300历史数据...")
try:
    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000300&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&fqt=0&beg=20240101&end=20240110'
    response = session.get(url, headers=headers, timeout=10)
    data = response.json()
    
    if data and 'data' in data and data['data']:
        klines = data['data']['klines']
        print(f"✓ 成功获取 {len(klines)} 条K线数据")
        
        # 显示前5条
        print("  前5条数据:")
        for kline in klines[:5]:
            parts = kline.split(',')
            print(f"    日期:{parts[0]}, 开盘:{parts[1]}, 收盘:{parts[2]}, 最高:{parts[3]}, 最低:{parts[4]}, 成交量:{parts[5]}")
    else:
        print("✗ 返回数据为空")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试6: 获取北向资金数据
print("\n6. 获取北向资金数据...")
try:
    url = 'https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?secid=1.000300&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&lmt=10'
    response = session.get(url, headers=headers, timeout=10)
    data = response.json()
    
    if data and 'data' in data and data['data']:
        klines = data['data']['klines']
        print(f"✓ 成功获取 {len(klines)} 条资金流向数据")
        
        # 显示数据
        print("  资金流向数据:")
        for kline in klines[:5]:
            parts = kline.split(',')
            print(f"    日期:{parts[0]}, 主力净流入:{parts[1]}, 超大单净流入:{parts[2]}, 大单净流入:{parts[3]}")
    else:
        print("✗ 返回数据为空")
except Exception as e:
    print(f"✗ 失败: {e}")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
