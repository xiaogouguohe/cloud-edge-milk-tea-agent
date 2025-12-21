"""
直接测试工具调用 - 绕过 LLM，直接调用工具
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp.client import MCPClient
from service_discovery import ServiceDiscovery

def test_create_order_directly():
    """直接测试创建订单工具"""
    print("=" * 80)
    print("直接测试工具调用 - 创建订单")
    print("=" * 80)
    print()
    
    # 检查服务是否启动
    import requests
    try:
        response = requests.get("http://localhost:10002/mcp/health", timeout=2)
        if response.status_code != 200:
            print("⚠️  OrderMCPServer 未正常启动")
            print("请先启动服务: ./start_process2_mcp_server_background.sh")
            return
    except Exception:
        print("⚠️  OrderMCPServer 未启动")
        print("请先启动服务: ./start_process2_mcp_server_background.sh")
        return
    
    print("✓ OrderMCPServer 已启动")
    print()
    
    # 初始化
    sd = ServiceDiscovery(method="config")
    mcp_client = MCPClient(service_discovery=sd)
    
    # 测试参数
    test_params = {
        "userId": 12345678901,
        "productName": "云边茉莉",
        "sweetness": "标准糖",
        "iceLevel": "正常冰",
        "quantity": 1
    }
    
    print(f"测试参数: {test_params}")
    print()
    
    try:
        # 直接调用工具
        print("调用工具: order-create-order-with-user")
        result = mcp_client.invoke_tool(
            "order-mcp-server",
            "order-create-order-with-user",
            test_params
        )
        
        print(f"工具调用结果:")
        print(result)
        print()
        
        # 验证数据库
        from database.db_manager import DatabaseManager
        db = DatabaseManager(db_type="sqlite")
        count = db.fetch_one("SELECT COUNT(*) as cnt FROM orders")['cnt']
        print(f"数据库订单总数: {count}")
        
        if count > 0:
            latest = db.fetch_all("SELECT * FROM orders ORDER BY created_at DESC LIMIT 1")
            if latest:
                print(f"最新订单: {latest[0]}")
        
        db.close()
        
    except Exception as e:
        import traceback
        print(f"错误: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    test_create_order_directly()
