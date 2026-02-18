"""
订单 MCP Server 测试
使用独立测试数据库，每个用例内清空并插入所需数据，与业务数据库隔离
"""
import sys
import unittest
from pathlib import Path
# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_manager import DatabaseManager
import order_mcp_server.order_service as order_service_module
import order_mcp_server.order_mcp_server as mcp_module
from order_mcp_server.order_mcp_server import OrderMCPServer


# 测试用产品数据：(name, description, price, stock)
TEST_PRODUCTS_MENU = [
    ("云边茉莉", "优质茉莉花茶", 18.00, 100),
    ("桂花云露", "桂花乌龙茶", 20.00, 80),
]
TEST_PRODUCT_SINGLE = [
    ("云边茉莉", "优质茉莉花茶", 18.00, 100),
]


def _insert_products(db: DatabaseManager, products: list):
    """向 products 表插入数据"""
    cursor = db.connection.cursor()
    for name, desc, price, stock in products:
        if db.db_type == "sqlite":
            cursor.execute(
                "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
                (name, desc, price, stock),
            )
        else:
            cursor.execute(
                "INSERT INTO products (name, description, price, stock) VALUES (%s, %s, %s, %s)",
                (name, desc, price, stock),
            )
    db.connection.commit()


def _clear_products(db: DatabaseManager):
    """清空 products 表"""
    if db.db_type == "sqlite":
        db.execute("DELETE FROM products")
    else:
        db.execute("DELETE FROM products")
    db.connection.commit()


class TestOrderMCPServer(unittest.TestCase):
    """订单 MCP Server 测试用例"""

    @classmethod
    def setUpClass(cls):
        """创建测试数据库、patch 并初始化 MCP Server"""
        # 1. 创建独立测试数据库（内存 SQLite，与业务库隔离）
        cls.test_db = DatabaseManager(db_type="sqlite", db_path=":memory:")
        cls.test_db._init_tables()

        # 2. 让 order_service 和 OrderDAO 都使用同一测试库（库存扣减需与订单同库）
        order_service_module.product_db = cls.test_db
        order_service_module.PRODUCT_DB_AVAILABLE = True
        mcp_module.db_manager = cls.test_db

        # 3. 创建 MCP Server 和测试客户端
        cls.server = OrderMCPServer(port=19999)
        cls.client = cls.server.mcp_server.app.test_client()

    def _prepare_products(self, products: list):
        """清空并插入指定产品数据"""
        _clear_products(self.test_db)
        _insert_products(self.test_db, products)

    def test_health(self):
        """测试：健康检查接口"""
        response = self.client.get("/mcp/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["server"], "order-mcp-server")
        self.assertGreaterEqual(data["tools_count"], 2)

    def test_list_tools(self):
        """测试：列出所有工具"""
        response = self.client.get("/mcp/tools")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        tools = data.get("tools", [])
        tool_names = [t["name"] for t in tools]
        self.assertIn("order-get-menu", tool_names)
        self.assertIn("order-get-product-info", tool_names)
        self.assertIn("order-get-orders-by-user", tool_names)
        self.assertIn("order-propose-product-update", tool_names)
        self.assertIn("order-update-product", tool_names)

    def test_propose_product_update(self):
        """测试：提议修改产品（不落库），返回当前值与拟修改值"""
        self._prepare_products([("云边茉莉", "优质茉莉花茶", 18.00, 100)])

        response = self.client.post(
            "/mcp/tools/order-propose-product-update/invoke",
            json={"parameters": {"productName": "云边茉莉", "price": 20}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        import json
        parsed = json.loads(result)
        self.assertTrue(parsed.get("_propose_product_update"))
        self.assertEqual(parsed["productName"], "云边茉莉")
        self.assertEqual(parsed["current"]["price"], 18.0)
        self.assertEqual(parsed["current"]["stock"], 100)
        self.assertEqual(parsed["proposed"]["price"], 20)

    def test_update_product(self):
        """测试：执行产品修改"""
        self._prepare_products([("云边茉莉", "优质茉莉花茶", 18.00, 100)])

        response = self.client.post(
            "/mcp/tools/order-update-product/invoke",
            json={"parameters": {"productName": "云边茉莉", "price": 22, "stock": 80}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        self.assertIn("云边茉莉", result)
        self.assertIn("22", result)
        self.assertIn("80", result)

        # 验证数据库已更新
        r2 = self.client.post(
            "/mcp/tools/order-get-product-info/invoke",
            json={"parameters": {"productName": "云边茉莉"}},
            content_type="application/json",
        )
        info = r2.get_json().get("result", "")
        self.assertIn("22", info)
        self.assertIn("有货", info)

    def test_get_menu(self):
        """测试：获取菜单"""
        self._prepare_products(TEST_PRODUCTS_MENU)

        response = self.client.post(
            "/mcp/tools/order-get-menu/invoke",
            json={"parameters": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        self.assertIn("云边奶茶铺", result)
        self.assertIn("茉莉", result)
        self.assertIn("¥", result)
        self.assertIn("有货", result)

    def test_get_product_info_success(self):
        """测试：获取存在产品的详情"""
        self._prepare_products(TEST_PRODUCT_SINGLE)

        response = self.client.post(
            "/mcp/tools/order-get-product-info/invoke",
            json={"parameters": {"productName": "云边茉莉"}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        self.assertIn("云边茉莉", result)
        self.assertIn("价格", result)
        self.assertIn("有货", result)

    def test_get_product_info_not_found(self):
        """测试：获取不存在产品时的友好提示"""
        self._prepare_products(TEST_PRODUCTS_MENU)  # 有云边茉莉等，但没有「不存在的奶茶」

        response = self.client.post(
            "/mcp/tools/order-get-product-info/invoke",
            json={"parameters": {"productName": "不存在的奶茶"}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        self.assertIn("未找到", result)
        self.assertIn("不存在的奶茶", result)

    def test_get_menu_empty(self):
        """测试：数据库无产品时，菜单返回空提示"""
        self._prepare_products([])  # 清空，不插入任何产品

        response = self.client.post(
            "/mcp/tools/order-get-menu/invoke",
            json={"parameters": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        self.assertIn("没有可用的奶茶菜单", result)

    def test_invoke_nonexistent_tool(self):
        """测试：调用不存在的工具返回 404"""
        response = self.client.post(
            "/mcp/tools/order-fake-tool/invoke",
            json={"parameters": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("not found", data.get("error", "").lower())

    def test_create_order_decrements_stock(self):
        """测试：下单成功后库存正确扣减"""
        self._prepare_products([("云边茉莉", "优质茉莉花茶", 18.00, 10)])
        # 下单 3 杯
        r1 = self.client.post(
            "/mcp/tools/order-create-order/invoke",
            json={
                "parameters": {
                    "userId": 10001,
                    "items": [
                        {"productName": "云边茉莉", "sweetness": "少糖", "iceLevel": "去冰", "quantity": 3}
                    ],
                }
            },
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 200)
        self.assertIn("ORDER_", r1.get_json().get("result", ""))
        # 验证库存从 10 变为 7
        r2 = self.client.post(
            "/mcp/tools/order-get-product-info/invoke",
            json={"parameters": {"productName": "云边茉莉"}},
            content_type="application/json",
        )
        result = r2.get_json().get("result", "")
        self.assertIn("有货", result)
        # 从 products 表直接查库存
        cursor = self.test_db.connection.cursor()
        cursor.execute("SELECT stock FROM products WHERE name = ?", ("云边茉莉",))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(dict(row)["stock"], 7)

    def test_create_order_success(self):
        """测试：下单成功"""
        self._prepare_products([("云边茉莉", "优质茉莉花茶", 18.00, 100)])
        response = self.client.post(
            "/mcp/tools/order-create-order/invoke",
            json={
                "parameters": {
                    "userId": 10001,
                    "items": [
                        {"productName": "云边茉莉", "sweetness": "少糖", "iceLevel": "去冰", "quantity": 1}
                    ],
                }
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        self.assertIn("ORDER_", result)
        self.assertIn("云边茉莉", result)
        self.assertIn("¥", result)

    def test_create_order_insufficient_stock(self):
        """测试：库存不足时下单失败"""
        self._prepare_products([("云边茉莉", "优质茉莉花茶", 18.00, 2)])  # 库存仅 2
        response = self.client.post(
            "/mcp/tools/order-create-order/invoke",
            json={
                "parameters": {
                    "userId": 10002,
                    "items": [
                        {"productName": "云边茉莉", "sweetness": "少糖", "iceLevel": "去冰", "quantity": 5}
                    ],
                }
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")  # MCP 返回 success，错误在 result 中
        result = data.get("result", "")
        self.assertIn("库存不足", result)
        self.assertIn("2", result)
        self.assertIn("5", result)

    def test_get_orders_by_user(self):
        """测试：查询用户历史订单"""
        self._prepare_products(TEST_PRODUCTS_MENU)  # 云边茉莉、桂花云露
        user_id = 20001

        # 先创建两笔订单
        r1 = self.client.post(
            "/mcp/tools/order-create-order/invoke",
            json={
                "parameters": {
                    "userId": user_id,
                    "items": [
                        {"productName": "云边茉莉", "sweetness": "半糖", "iceLevel": "去冰", "quantity": 2}
                    ],
                }
            },
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 200)
        self.assertIn("ORDER_", r1.get_json().get("result", ""))

        r2 = self.client.post(
            "/mcp/tools/order-create-order/invoke",
            json={
                "parameters": {
                    "userId": user_id,
                    "items": [
                        {"productName": "桂花云露", "sweetness": "少糖", "iceLevel": "少冰", "quantity": 1}
                    ],
                }
            },
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)

        # 查询该用户订单列表
        r3 = self.client.post(
            "/mcp/tools/order-get-orders-by-user/invoke",
            json={"parameters": {"userId": user_id}},
            content_type="application/json",
        )
        self.assertEqual(r3.status_code, 200)
        data = r3.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        self.assertIn("云边茉莉", result)
        self.assertIn("桂花云露", result)
        self.assertIn("ORDER_", result)
        self.assertIn("20001", result)

    def test_get_orders_by_user_empty(self):
        """测试：用户无订单时返回空提示"""
        self._prepare_products(TEST_PRODUCTS_MENU)
        r = self.client.post(
            "/mcp/tools/order-get-orders-by-user/invoke",
            json={"parameters": {"userId": 99999}},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "success")
        result = data.get("result", "")
        self.assertIn("没有", result)
        self.assertIn("99999", result)


if __name__ == "__main__":
    unittest.main()
