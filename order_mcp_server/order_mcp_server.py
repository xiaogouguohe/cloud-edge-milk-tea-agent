"""
订单 MCP Server - 提供订单相关的工具
根据当前的 OrderAgent Skills 定义进行对齐
"""
import sys
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import MCPServer
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
        """注册所有订单相关的工具，与 OrderAgent Skills 对齐"""
        
        # 1. 获取菜单 (BASE_SKILLS)
        self.mcp_server.register_tool_func(
            name="order-get-menu",
            description="获取奶茶店当前的菜单列表和价格。",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._get_menu
        )
        
        # 2. 创建订单 (CUSTOMER_SKILLS)
        self.mcp_server.register_tool_func(
            name="order-create-order",
            description="为用户创建奶茶订单，支持单个或多个产品。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID"
                    },
                    "items": {
                        "type": "array",
                        "description": "订单项列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "productName": {
                                    "type": "string",
                                    "description": "产品名称"
                                },
                                "sweetness": {
                                    "type": "string",
                                    "description": "甜度",
                                    "enum": ["无糖", "微糖", "半糖", "少糖", "标准糖"]
                                },
                                "iceLevel": {
                                    "type": "string",
                                    "description": "冰量",
                                    "enum": ["去冰", "少冰", "正常冰", "温", "热"]
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "数量",
                                    "default": 1
                                }
                            },
                            "required": ["productName", "sweetness", "iceLevel"]
                        }
                    }
                },
                "required": ["userId", "items"]
            },
            handler=self._create_order
        )
        
        # 3. 根据用户ID获取订单列表 (CUSTOMER_SKILLS)
        self.mcp_server.register_tool_func(
            name="order-get-orders-by-user",
            description="根据用户ID获取该用户的所有订单列表。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID"
                    }
                },
                "required": ["userId"]
            },
            handler=self._get_orders_by_user
        )

        # 4. 根据用户ID和订单ID查询订单 (ADMIN_SKILLS)
        self.mcp_server.register_tool_func(
            name="order-get-order-by-user",
            description="根据用户ID和订单ID查询订单的详细信息。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID"
                    },
                    "orderId": {
                        "type": "string",
                        "description": "订单ID"
                    }
                },
                "required": ["userId", "orderId"]
            },
            handler=self._get_order_by_user
        )
        
        # 5. 更新订单状态 (STAFF_SKILLS)
        self.mcp_server.register_tool_func(
            name="order-update-order-status",
            description="更新订单状态（如：制作中、待取餐、已完成）。仅限店员操作。",
            parameters={
                "type": "object",
                "properties": {
                    "orderId": {
                        "type": "string",
                        "description": "订单ID"
                    },
                    "status": {
                        "type": "string",
                        "description": "新状态",
                        "enum": ["making", "ready", "completed"]
                    }
                },
                "required": ["orderId", "status"]
            },
            handler=self._update_order_status
        )
        
        # 6. 删除订单 (ADMIN_SKILLS)
        self.mcp_server.register_tool_func(
            name="order-delete-order",
            description="根据用户ID和订单ID删除订单。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID"
                    },
                    "orderId": {
                        "type": "string",
                        "description": "订单ID"
                    }
                },
                "required": ["userId", "orderId"]
            },
            handler=self._delete_order
        )

        # 7. 处理退款 (ADMIN_SKILLS)
        self.mcp_server.register_tool_func(
            name="order-process-refund",
            description="处理订单退款。仅限管理员执行。",
            parameters={
                "type": "object",
                "properties": {
                    "orderId": {
                        "type": "string",
                        "description": "订单ID"
                    },
                    "reason": {
                        "type": "string",
                        "description": "退款原因"
                    }
                },
                "required": ["orderId", "reason"]
            },
            handler=self._process_refund
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

    def _create_order(self, userId: int, items: List[Dict]) -> str:
        """工具：创建订单"""
        try:
            order = self.order_service.create_order(user_id=userId, items=items)
            return self.order_service.format_order_response(order)
        except Exception as e:
            return f"创建订单失败: {str(e)}"

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

    def _get_order_by_user(self, userId: int, orderId: str) -> str:
        """工具：根据用户ID和订单ID查询订单"""
        try:
            order = self.order_service.get_order_by_user(userId, orderId)
            if not order:
                return f"订单不存在: {orderId} (用户ID: {userId})"
            return self.order_service.format_order_response(order)
        except Exception as e:
            return f"查询订单失败: {str(e)}"

    def _update_order_status(self, orderId: str, status: str) -> str:
        """工具：更新订单状态"""
        try:
            status_map = {"making": "MAKING", "ready": "READY", "completed": "COMPLETED"}
            db_status = status_map.get(status, "MAKING")
            order = self.order_service.update_order_status(orderId, db_status)
            if order:
                return f"订单 {orderId} 状态已更新为: {status}"
            return f"订单 {orderId} 状态更新失败，订单可能不存在。"
        except Exception as e:
            return f"更新订单状态失败: {str(e)}"

    def _delete_order(self, userId: int, orderId: str) -> str:
        """工具：删除订单"""
        try:
            success = self.order_service.delete_order(userId, orderId)
            if success:
                return f"订单删除成功: {orderId}"
            return f"订单删除失败，订单不存在或无权限: {orderId}"
        except Exception as e:
            return f"删除订单失败: {str(e)}"

    def _process_refund(self, orderId: str, reason: str) -> str:
        """工具：处理退款"""
        try:
            # 模拟退款逻辑，实际应修改订单状态并处理资金
            return f"订单 {orderId} 退款申请已处理。原因: {reason}。退款金额将原路返回。"
        except Exception as e:
            return f"处理退款失败: {str(e)}"

    def run(self, host: str = '0.0.0.0', debug: bool = False):
        """启动 MCP Server"""
        print(f"订单 MCP Server 启动在 http://{host}:{self.port}")
        print(f"已注册工具: {len(self.mcp_server.tools)} 个")
        for tool_name in self.mcp_server.tools.keys():
            print(f"  - {tool_name}")
        print()
        self.mcp_server.run(host=host, debug=debug)
