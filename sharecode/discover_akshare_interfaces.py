import akshare as ak
import inspect

def discover_stock_interfaces():
    """发现akshare中所有股票相关的接口"""
    stock_interfaces = []
    
    # 获取akshare模块中的所有属性
    for name in dir(ak):
        if name.startswith('stock_') or name.startswith('index_') or name.startswith('fund_'):
            obj = getattr(ak, name)
            if inspect.isfunction(obj):
                stock_interfaces.append(name)
    
    return sorted(stock_interfaces)

if __name__ == "__main__":
    interfaces = discover_stock_interfaces()
    print(f"发现了 {len(interfaces)} 个股票相关接口:")
    for i, interface in enumerate(interfaces, 1):
        print(f"{i:2d}. {interface}")
