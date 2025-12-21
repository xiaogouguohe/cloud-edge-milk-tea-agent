"""
启动订单 MCP Server
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from order_mcp_server import OrderMCPServer
from service_discovery import ServiceDiscovery

def main():
    """启动订单 MCP Server"""
    print("=" * 60)
    print("订单 MCP Server")
    print("=" * 60)
    print()
    
    # 创建订单 MCP Server
    server = OrderMCPServer(port=10002)
    
    # 注册到服务发现
    sd = ServiceDiscovery(method="config")
    sd.register(
        "order-mcp-server",
        host="localhost",
        port=10002,
        url="http://localhost:10002",
        description="订单管理 MCP Server"
    )
    
    print("订单 MCP Server 已注册到服务发现")
    print()
    
    # 启动服务
    try:
        server.run(host='0.0.0.0', debug=False)
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
