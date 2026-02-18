"""
订单 MCP Server - 提供订单相关的工具
仅保留 BASE_SKILLS：获取菜单、获取产品详情
"""
import sys
from pathlib import Path

# 强制将项目根目录添加到 sys.path，解决直接运行脚本时的导入问题
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server import MCPServer
from order_mcp_server.order_service import OrderService
from order_mcp_server.database import OrderDAO

# 尝试导入数据库管理器
try:
    from database.db_manager import DatabaseManager
    from database.config import DB_TYPE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
    
    if DB_TYPE == "mysql":
        db_manager = DatabaseManager(
            db_type="mysql",
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
    else:
        db_manager = DatabaseManager(db_type="sqlite")
except Exception as e:
    print(f"警告: 无法初始化数据库，将使用内存存储: {str(e)}")
    db_manager = None


class OrderMCPServer:
    """订单 MCP Server - 仅提供 BASE_SKILLS 工具"""
    
    def __init__(self, port: int = 10002):
        """
        初始化订单 MCP Server
        
        Args:
            port: 服务端口
        """
        self.port = port
        
        # 初始化数据访问层和服务层
        order_dao = OrderDAO(db_manager=db_manager)
        self.order_service = OrderService(order_dao)
        
        # 创建 MCP Server
        self.mcp_server = MCPServer(server_name="order-mcp-server", port=port)
        
        # 注册工具（仅 BASE_SKILLS）
        self._register_tools()
    
    def _register_tools(self):
        """注册 BASE_SKILLS 工具：获取菜单、获取产品详情"""
        
        # 1. 获取菜单
        self.mcp_server.register_tool_func(
            name="order-get-menu",
            description="获取奶茶店当前的完整菜单列表、价格及库存状态。",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._get_menu
        )
        
        # 2. 获取产品详情
        self.mcp_server.register_tool_func(
            name="order-get-product-info",
            description="获取某个特定奶茶产品的详细信息，包括价格和是否有货。",
            parameters={
                "type": "object",
                "properties": {
                    "productName": {"type": "string", "description": "奶茶名称"}
                },
                "required": ["productName"]
            },
            handler=self._get_product_info
        )

    def _get_menu(self) -> str:
        """工具：获取菜单"""
        try:
            products = self.order_service.get_all_products()
            if not products:
                return "抱歉，目前没有可用的奶茶菜单。"
            
            result = "云边奶茶铺菜单 (支持冰度: 去冰/少冰/正常冰/温/热, 糖度: 无糖/微糖/半糖/少糖/标准糖):\n"
            for p in products:
                stock_status = "有货" if p.get('stock', 0) > 0 else "售罄"
                result += f"- {p['name']}: ¥{p['price']:.2f} ({stock_status})\n"
            return result
        except Exception as e:
            return f"获取菜单失败: {str(e)}"

    def _get_product_info(self, productName: str) -> str:
        """工具：获取产品详情"""
        try:
            product = self.order_service.get_product_info(productName)
            if not product:
                return f"抱歉，未找到产品「{productName}」，请确认产品名称是否正确。"
            
            stock_status = "有货" if product.get('stock', 0) > 0 else "售罄"
            return f"产品：{product['name']}\n价格：¥{product['price']:.2f}\n库存状态：{stock_status}"
        except Exception as e:
            return f"获取产品信息失败: {str(e)}"

    def run(self, host: str = '0.0.0.0', debug: bool = False):
        """启动 MCP Server"""
        print(f"订单 MCP Server 启动在 http://{host}:{self.port}")
        print(f"已注册工具: {len(self.mcp_server.tools)} 个")
        for tool_name in self.mcp_server.tools.keys():
            print(f"  - {tool_name}")
        print()
        self.mcp_server.run(host=host, debug=debug)
