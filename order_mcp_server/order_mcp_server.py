"""
订单 MCP Server - 提供订单相关的工具
仅保留 BASE_SKILLS：获取菜单、获取产品详情
"""
import json
import sys
from pathlib import Path

# 强制将项目根目录添加到 sys.path，解决直接运行脚本时的导入问题
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server import MCPServer
from order_mcp_server.order_service import OrderService


def _format_propose_message(result: dict) -> str:
    """格式化提议修改的提示文案"""
    name = result.get("productName", "")
    cur = result.get("current", {})
    pro = result.get("proposed", {})
    parts = []
    if "price" in pro:
        parts.append(f"单价 {cur.get('price')} → {pro['price']} 元")
    if "stock" in pro:
        parts.append(f"库存 {cur.get('stock')} → {pro['stock']}")
    return f"产品「{name}」拟修改：{'；'.join(parts)}。请在前端确认后执行。"
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

        # 3. 创建订单（顾客）
        self.mcp_server.register_tool_func(
            name="order-create-order",
            description="创建奶茶订单。当用户想要下单、点单或购买时使用此工具。同一产品若糖度或冰量不同，需拆成多条 items（每条对应一种规格）。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {"type": "integer", "description": "用户ID"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "productName": {"type": "string"},
                                "sweetness": {"type": "string", "enum": ["无糖", "微糖", "半糖", "少糖", "标准糖"]},
                                "iceLevel": {"type": "string", "enum": ["去冰", "少冰", "正常冰", "温", "热"]},
                                "quantity": {"type": "integer", "default": 1}
                            },
                            "required": ["productName", "sweetness", "iceLevel"]
                        }
                    }
                },
                "required": ["userId", "items"]
            },
            handler=self._create_order
        )

        # 4. 查询用户订单列表（顾客）
        self.mcp_server.register_tool_func(
            name="order-get-orders-by-user",
            description="根据用户ID获取该用户的所有订单列表。",
            parameters={
                "type": "object",
                "properties": {"userId": {"type": "integer", "description": "用户ID"}},
                "required": ["userId"]
            },
            handler=self._get_orders_by_user
        )

        # 5. 提议修改产品（店员，不落库，供前端确认）
        self.mcp_server.register_tool_func(
            name="order-propose-product-update",
            description="提议修改产品的单价或库存。不执行修改，仅返回当前值与拟修改值，供前端弹出确认框。店员修改产品时必须先调用此工具。",
            parameters={
                "type": "object",
                "properties": {
                    "productName": {"type": "string", "description": "产品名称"},
                    "price": {"type": "number", "description": "拟修改的单价（不修改则不传）"},
                    "stock": {"type": "integer", "description": "拟修改的库存（不修改则不传）"},
                },
                "required": ["productName"]
            },
            handler=self._propose_product_update
        )

        # 6. 根据订单 ID 查询订单（店员，可查任意订单）
        self.mcp_server.register_tool_func(
            name="order-get-order",
            description="根据订单ID查询订单详情。店员可查任意订单，顾客只能查自己的。",
            parameters={
                "type": "object",
                "properties": {"orderId": {"type": "string", "description": "订单ID，如 ORDER_xxx"}},
                "required": ["orderId"]
            },
            handler=self._get_order
        )

        # 7. 执行产品修改（店员，落库）
        self.mcp_server.register_tool_func(
            name="order-update-product",
            description="执行产品修改，更新数据库中的单价或库存。应在用户确认后调用。",
            parameters={
                "type": "object",
                "properties": {
                    "productName": {"type": "string", "description": "产品名称"},
                    "price": {"type": "number", "description": "新单价（不修改则不传）"},
                    "stock": {"type": "integer", "description": "新库存（不修改则不传）"},
                },
                "required": ["productName"]
            },
            handler=self._update_product
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

    def _create_order(self, userId: int, items: list) -> str:
        """工具：创建订单"""
        try:
            order = self.order_service.create_order(user_id=userId, items=items)
            return self.order_service.format_order_response(order)
        except Exception as e:
            return f"创建订单失败: {str(e)}"

    def _get_order(self, orderId: str) -> str:
        """工具：根据订单 ID 查询订单详情"""
        try:
            order = self.order_service.get_order(orderId)
            if not order:
                return f"未找到订单「{orderId}」，请确认订单号是否正确。"
            return self.order_service.format_order_response(order)
        except Exception as e:
            return f"查询订单失败: {str(e)}"

    def _get_orders_by_user(self, userId: int) -> str:
        """工具：获取用户订单列表"""
        try:
            orders = self.order_service.get_orders_by_user(userId)
            if not orders:
                return f"用户 {userId} 当前没有任何订单记录。"
            result = f"用户 {userId} 的订单列表（共 {len(orders)} 条）:\n\n"
            for order in orders:
                result += self.order_service.format_order_response(order) + "\n\n"
            return result
        except Exception as e:
            return f"获取订单列表失败: {str(e)}"

    def _propose_product_update(self, productName: str, price: float = None, stock: int = None) -> str:
        """工具：提议修改产品（不落库），返回 JSON 供前端解析确认"""
        try:
            result = self.order_service.propose_product_update(productName, price, stock)
            if not result.get("ok"):
                return result.get("error", "提议失败")
            # 返回 JSON，供 Order Agent 解析并触发 pending_action
            return json.dumps({
                "_propose_product_update": True,
                "productName": result["productName"],
                "current": result["current"],
                "proposed": result["proposed"],
                "message": _format_propose_message(result),
            }, ensure_ascii=False)
        except Exception as e:
            return f"提议修改失败: {str(e)}"

    def _update_product(self, productName: str, price: float = None, stock: int = None) -> str:
        """工具：执行产品修改"""
        try:
            result = self.order_service.update_product(productName, price, stock)
            if not result.get("ok"):
                return result.get("error", "修改失败")
            updated = result.get("updated", {})
            parts = [f"产品「{productName}」已更新："]
            if "price" in updated:
                parts.append(f"单价 → ¥{updated['price']:.2f}")
            if "stock" in updated:
                parts.append(f"库存 → {updated['stock']}")
            return "；".join(parts)
        except Exception as e:
            return f"修改产品失败: {str(e)}"

    def run(self, host: str = '0.0.0.0', debug: bool = False):
        """启动 MCP Server"""
        print(f"订单 MCP Server 启动在 http://{host}:{self.port}")
        print(f"已注册工具: {len(self.mcp_server.tools)} 个")
        for tool_name in self.mcp_server.tools.keys():
            print(f"  - {tool_name}")
        print()
        self.mcp_server.run(host=host, debug=debug)
