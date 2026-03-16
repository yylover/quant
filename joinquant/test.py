import akshare as ak

# 获取股票日线数据
stock_df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20250101", end_date="20260316")

# 查看数据
print(stock_df.head())
