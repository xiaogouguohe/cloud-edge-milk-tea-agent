"""
订单 MCP Server - 提供订单相关的工具
参考原项目的 OrderMcpTools
"""
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import MCPServer, Tool, ToolDefinition
from .order_service import OrderService
from .database import OrderDAO

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
    """订单 MCP Server - 提供订单相关的工具"""
    
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
        
        # 注册工具
        self._register_tools()
    
    def _register_tools(self):
        """注册所有订单相关的工具"""
        
        # 1. 根据订单ID查询订单
        self.mcp_server.register_tool_func(
            name="order-get-order",
            description="根据订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。",
            parameters={
                "type": "object",
                "properties": {
                    "orderId": {
                        "type": "string",
                        "description": "订单ID，格式为ORDER_开头的唯一标识符，例如：ORDER_1693654321000"
                    }
                },
                "required": ["orderId"]
            },
            handler=self._get_order
        )
        
        # 2. 根据用户ID和订单ID查询订单
        self.mcp_server.register_tool_func(
            name="order-get-order-by-user",
            description="根据用户ID和订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID，必须为正整数"
                    },
                    "orderId": {
                        "type": "string",
                        "description": "订单ID，格式为ORDER_开头的唯一标识符"
                    }
                },
                "required": ["userId", "orderId"]
            },
            handler=self._get_order_by_user
        )
        
        # 3. 创建订单
        self.mcp_server.register_tool_func(
            name="order-create-order-with-user",
            description="为用户创建新的奶茶订单。支持云边奶茶铺的所有产品，包括云边茉莉、桂花云露、云雾观音等经典产品。系统会自动检查库存并计算价格。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID，必须为正整数"
                    },
                    "productName": {
                        "type": "string",
                        "description": "产品名称，必须是云边奶茶铺的现有产品"
                    },
                    "sweetness": {
                        "type": "string",
                        "description": "甜度要求，可选值：标准糖、少糖、半糖、微糖、无糖",
                        "enum": ["无糖", "微糖", "半糖", "少糖", "标准糖"]
                    },
                    "iceLevel": {
                        "type": "string",
                        "description": "冰量要求，可选值：正常冰、少冰、去冰、温、热",
                        "enum": ["热", "温", "去冰", "少冰", "正常冰"]
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "购买数量，必须为正整数，默认为1",
                        "minimum": 1
                    },
                    "remark": {
                        "type": "string",
                        "description": "订单备注，可选"
                    }
                },
                "required": ["userId", "productName", "sweetness", "iceLevel", "quantity"]
            },
            handler=self._create_order
        )
        
        # 4. 根据用户ID获取订单列表
        self.mcp_server.register_tool_func(
            name="order-get-orders-by-user",
            description="根据用户ID获取该用户的所有订单列表，包括订单ID、产品信息、价格和创建时间。用于查看用户的订单历史。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID，必须为正整数"
                    }
                },
                "required": ["userId"]
            },
            handler=self._get_orders_by_user
        )
        
        # 5. 删除订单
        self.mcp_server.register_tool_func(
            name="order-delete-order",
            description="根据用户ID和订单ID删除订单。只能删除属于该用户的订单。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID，必须为正整数"
                    },
                    "orderId": {
                        "type": "string",
                        "description": "订单ID，格式为ORDER_开头的唯一标识符"
                    }
                },
                "required": ["userId", "orderId"]
            },
            handler=self._delete_order
        )
        
        # 6. 更新订单备注
        self.mcp_server.register_tool_func(
            name="order-update-remark",
            description="根据用户ID和订单ID更新订单备注。只能更新属于该用户的订单。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID，必须为正整数"
                    },
                    "orderId": {
                        "type": "string",
                        "description": "订单ID，格式为ORDER_开头的唯一标识符"
                    },
                    "remark": {
                        "type": "string",
                        "description": "新的备注内容"
                    }
                },
                "required": ["userId", "orderId", "remark"]
            },
            handler=self._update_remark
        )
    
    def _convert_sweetness(self, sweetness: str) -> int:
        """甜度字符串转数字"""
        sweetness_map = {
            "无糖": 1,
            "微糖": 2,
            "半糖": 3,
            "少糖": 4,
            "标准糖": 5
        }
        return sweetness_map.get(sweetness, 5)
    
    def _convert_ice_level(self, ice_level: str) -> int:
        """冰量字符串转数字"""
        ice_level_map = {
            "热": 1,
            "温": 2,
            "去冰": 3,
            "少冰": 4,
            "正常冰": 5
        }
        return ice_level_map.get(ice_level, 5)
    
    def _get_order(self, orderId: str) -> str:
        """工具：根据订单ID查询订单"""
        try:
            order = self.order_service.get_order(orderId)
            if not order:
                return f"订单不存在: {orderId}"
            return self.order_service.format_order_response(order)
        except Exception as e:
            return f"查询订单失败: {str(e)}"
    
    def _get_order_by_user(self, userId: int, orderId: str) -> str:
        """工具：根据用户ID和订单ID查询订单"""
        try:
            order = self.order_service.get_order_by_user(userId, orderId)
            if not order:
                return f"订单不存在: {orderId} (用户ID: {userId})"
            return self.order_service.format_order_response(order)
        except Exception as e:
            return f"查询订单失败: {str(e)}"
    
    def _create_order(self, userId: int, productName: str, sweetness: str, 
                     iceLevel: str, quantity: int, remark: Optional[str] = None) -> str:
        """工具：创建订单"""
        try:
            # 确保 userId 是整数类型
            if isinstance(userId, str):
                userId = int(userId)
            if isinstance(quantity, str):
                quantity = int(quantity)
            
            print(f"[OrderMCPServer] 创建订单 - userId: {userId} (type: {type(userId)}), product: {productName}, quantity: {quantity}")
            
            sweetness_num = self._convert_sweetness(sweetness)
            ice_level_num = self._convert_ice_level(iceLevel)
            
            order = self.order_service.create_order(
                user_id=userId,
                product_name=productName,
                sweetness=sweetness_num,
                ice_level=ice_level_num,
                quantity=quantity,
                remark=remark
            )
            
            print(f"[OrderMCPServer] 订单创建成功 - order_id: {order.get('order_id')}, user_id: {order.get('user_id')}")
            
            # 验证订单是否真的写入数据库
            if self.order_service.order_dao.db:
                verify_order = self.order_service.order_dao.get_order_by_id(order['order_id'])
                if verify_order:
                    print(f"[OrderMCPServer] 数据库验证成功 - 订单已写入")
                else:
                    print(f"[OrderMCPServer] ⚠️  数据库验证失败 - 订单未找到")
            
            return f"""订单创建成功！
订单ID: {order['order_id']}
用户ID: {userId}
产品: {productName}
甜度: {sweetness}
冰量: {iceLevel}
数量: {quantity}
总价: ¥{order['total_price']:.2f}"""
        except Exception as e:
            import traceback
            error_msg = f"创建订单失败: {str(e)}"
            print(f"[OrderMCPServer] {error_msg}")
            traceback.print_exc()
            return error_msg
    
    def _get_orders_by_user(self, userId: int) -> str:
        """工具：获取用户的所有订单"""
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
    
    def _delete_order(self, userId: int, orderId: str) -> str:
        """工具：删除订单"""
        try:
            success = self.order_service.delete_order(userId, orderId)
            if success:
                return f"订单删除成功: {orderId}"
            else:
                return f"订单删除失败，订单不存在或无权限: {orderId}"
        except Exception as e:
            return f"删除订单失败: {str(e)}"
    
    def _update_remark(self, userId: int, orderId: str, remark: str) -> str:
        """工具：更新订单备注"""
        try:
            order = self.order_service.update_order_remark(userId, orderId, remark)
            if order:
                return f"订单备注更新成功: {orderId}\n新备注: {remark}"
            else:
                return f"订单备注更新失败，订单不存在或无权限: {orderId}"
        except Exception as e:
            return f"更新订单备注失败: {str(e)}"
    
    def run(self, host: str = '0.0.0.0', debug: bool = False):
        """
        启动 MCP Server
        
        Args:
            host: 监听地址
            debug: 是否开启调试模式
        """
        print(f"订单 MCP Server 启动在 http://{host}:{self.port}")
        print(f"已注册工具: {len(self.mcp_server.tools)} 个")
        for tool_name in self.mcp_server.tools.keys():
            print(f"  - {tool_name}")
        print()
        
        self.mcp_server.run(host=host, debug=debug)
