"""
订单服务层 - 业务逻辑处理
参考原项目的 OrderService
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from order_mcp_server.database import OrderDAO
from order_mcp_server.mcp_logger import log_backend

# 尝试导入数据库管理器
try:
    from database.db_manager import DatabaseManager
    from database.config import DB_TYPE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
    
    if DB_TYPE == "mysql":
        product_db = DatabaseManager(
            db_type="mysql",
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
    else:
        product_db = DatabaseManager(db_type="sqlite")
    PRODUCT_DB_AVAILABLE = True
except Exception as e:
    PRODUCT_DB_AVAILABLE = False
    product_db = None
    print(f"警告: 无法初始化产品数据库: {str(e)}")


class OrderService:
    """订单服务 - 处理订单相关的业务逻辑"""
    
    def __init__(self, order_dao: OrderDAO):
        """
        初始化订单服务
        
        Args:
            order_dao: 订单数据访问对象
        """
        self.order_dao = order_dao
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        根据订单ID查询订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单信息
        """
        return self.order_dao.get_order_by_id(order_id)
    
    def get_order_by_user(self, user_id: int, order_id: str) -> Optional[Dict]:
        """
        根据用户ID和订单ID查询订单
        
        Args:
            user_id: 用户ID
            order_id: 订单ID
            
        Returns:
            订单信息
        """
        return self.order_dao.get_order_by_user_and_id(user_id, order_id)
    
    def get_orders_by_user(self, user_id: int) -> List[Dict]:
        """
        获取用户的所有订单
        
        Args:
            user_id: 用户ID
            
        Returns:
            订单列表
        """
        return self.order_dao.get_orders_by_user(user_id)
    
    def create_order(self, user_id: int, items: List[Dict]) -> Dict:
        """
        创建订单（支持多产品）
        工业级流程：事务内原子扣减库存 + 写订单，防止超卖
        """
        order_id = f"ORDER_{int(datetime.now().timestamp() * 1000)}"
        total_price = 0.0
        processed_items = []

        for item_data in items:
            product_name = item_data["productName"]
            quantity = item_data.get("quantity", 1)
            sweetness_num = self._convert_sweetness_str_to_int(item_data.get("sweetness", "标准糖"))
            ice_level_num = self._convert_ice_level_str_to_int(item_data.get("iceLevel", "正常冰"))

            unit_price = self._get_product_price(product_name)
            if unit_price is None:
                raise ValueError(f"产品不存在: {product_name}")

            # 预检查库存（快速失败，数据库模式下事务内会再次原子校验）
            product_info = self.get_product_info(product_name)
            stock = product_info.get("stock", 0) if product_info else 0
            log_backend("get_product_info", product_name=product_name, stock=stock, quantity=quantity, product_found=product_info is not None)
            if product_info is None:
                log_backend("stock_check_fail", product_name=product_name, reason="product_not_found")
            if stock < quantity:
                log_backend("stock_check_fail", product_name=product_name, stock=stock, quantity=quantity, reason="insufficient_stock")
                raise ValueError(f"产品「{product_name}」库存不足，当前库存: {stock}，需要: {quantity}")

            item_price = unit_price * quantity
            total_price += item_price

            # 同一产品不同甜度/冰量分条存储，每个 (product, sweetness, ice_level) 一条
            product_id = self._get_product_id(product_name)
            processed_item = {
                "order_id": order_id,
                "product_id": product_id if product_id is not None else 0,
                "product_name": product_name,  # 用于展示和 decrement_stock
                "sweetness": sweetness_num,
                "ice_level": ice_level_num,
                "quantity": quantity,
                "unit_price": float(unit_price),
            }
            processed_items.append(processed_item)

        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "total_price": float(total_price),
        }

        if self.order_dao.use_memory:
            # 内存模式：无 products 表，仅写订单
            log_backend("create_order", mode="memory", order_id=order_data["order_id"], user_id=user_id)
            created_order = self.order_dao.create_order(order_data)
            for item in processed_items:
                self.order_dao.create_order_item(item)
        else:
            # 数据库模式：事务内原子扣库存 + 写订单
            self.order_dao.ensure_user_exists(user_id)
            log_backend("create_order_begin", mode="db", order_id=order_data["order_id"], user_id=user_id, items_count=len(processed_items))
            def _tx(db):
                for item in processed_items:
                    rows = self.order_dao.decrement_stock(item["product_name"], item["quantity"])
                    if rows == 0:
                        log_backend("decrement_stock_fail", product_name=item["product_name"], quantity=item["quantity"], rows_affected=0)
                        raise ValueError(
                            f"产品「{item['product_name']}」库存不足或已被占用，请稍后重试"
                        )
                    log_backend("decrement_stock_ok", product_name=item["product_name"], quantity=item["quantity"], rows_affected=rows)
                self.order_dao._create_order_tx(order_data)
                for item in processed_items:
                    self.order_dao._create_order_item_tx(item)

            self.order_dao.db.run_transaction(_tx)
            created_order = {**order_data, "items": processed_items, "created_at": datetime.now()}
            log_backend("create_order_ok", order_id=order_data["order_id"])

        created_order.setdefault("items", processed_items)
        return created_order
    
    def delete_order(self, user_id: int, order_id: str) -> bool:
        """
        删除订单
        
        Args:
            user_id: 用户ID
            order_id: 订单ID
            
        Returns:
            是否删除成功
        """
        return self.order_dao.delete_order(user_id, order_id)
    
    def query_orders(self, user_id: int, filters: Optional[Dict] = None) -> List[Dict]:
        """
        多条件查询订单
        
        Args:
            user_id: 用户ID
            filters: 筛选条件
            
        Returns:
            订单列表
        """
        return self.order_dao.query_orders(user_id, filters)
    
    def get_product_info(self, product_name: str) -> Optional[Dict]:
        """
        获取单个产品的详细信息，包括价格和是否有货
        
        Args:
            product_name: 奶茶产品名称
            
        Returns:
            产品信息字典，如果不存在则返回 None
        """
        products = self.get_all_products()
        for p in products:
            if p.get("name") == product_name:
                return p
        return None

    def propose_product_update(self, product_name: str, price: Optional[float] = None, stock: Optional[int] = None) -> Dict:
        """
        提议修改产品（不落库），返回当前值与拟修改值，供前端确认。
        
        Args:
            product_name: 产品名称
            price: 拟修改的单价（None 表示不修改）
            stock: 拟修改的库存（None 表示不修改）
            
        Returns:
            {"ok": True, "productName": str, "current": {price, stock}, "proposed": {price?, stock?}}
            或 {"ok": False, "error": str}
        """
        if price is None and stock is None:
            return {"ok": False, "error": "请至少指定要修改的单价或库存"}
        product = self.get_product_info(product_name)
        if not product:
            return {"ok": False, "error": f"未找到产品「{product_name}」"}
        current = {"price": float(product.get("price", 0)), "stock": int(product.get("stock", 0))}
        proposed = {}
        if price is not None:
            if price < 0:
                return {"ok": False, "error": "单价不能为负数"}
            proposed["price"] = float(price)
        if stock is not None:
            if stock < 0:
                return {"ok": False, "error": "库存不能为负数"}
            proposed["stock"] = int(stock)
        return {
            "ok": True,
            "productName": product_name,
            "current": current,
            "proposed": proposed,
        }

    def update_product(self, product_name: str, price: Optional[float] = None, stock: Optional[int] = None) -> Dict:
        """
        执行产品修改（落库）。调用前应由 propose_product_update 确认。
        
        Args:
            product_name: 产品名称
            price: 新单价（None 表示不修改）
            stock: 新库存（None 表示不修改）
            
        Returns:
            {"ok": True, "productName": str, "updated": {price?, stock?}}
            或 {"ok": False, "error": str}
        """
        if price is None and stock is None:
            return {"ok": False, "error": "请至少指定要修改的单价或库存"}
        product = self.get_product_info(product_name)
        if not product:
            return {"ok": False, "error": f"未找到产品「{product_name}」"}
        if not PRODUCT_DB_AVAILABLE or product_db is None:
            return {"ok": False, "error": "当前为模拟数据模式，无法修改产品"}
        try:
            updates = []
            params = []
            if price is not None:
                if price < 0:
                    return {"ok": False, "error": "单价不能为负数"}
                updates.append("price = ?" if product_db.db_type == "sqlite" else "price = %s")
                params.append(price)
            if stock is not None:
                if stock < 0:
                    return {"ok": False, "error": "库存不能为负数"}
                updates.append("stock = ?" if product_db.db_type == "sqlite" else "stock = %s")
                params.append(stock)
            params.append(product_name)
            ph = "?" if product_db.db_type == "sqlite" else "%s"
            query = f"UPDATE products SET {', '.join(updates)} WHERE name = {ph}"
            product_db.execute(query, tuple(params))
            log_backend("update_product", product_name=product_name, price=price, stock=stock)
            updated = {}
            if price is not None:
                updated["price"] = float(price)
            if stock is not None:
                updated["stock"] = int(stock)
            return {"ok": True, "productName": product_name, "updated": updated}
        except Exception as e:
            log_backend("update_product", error=str(e))
            return {"ok": False, "error": str(e)}
    
    def get_all_products(self) -> List[Dict]:
        """
        获取所有产品信息，包括价格和库存
        
        Returns:
            产品列表
        """
        if not PRODUCT_DB_AVAILABLE or product_db is None:
            # 降级处理：返回模拟数据
            fallback = [
                {"name": "云边茉莉", "price": 18.00, "stock": 100},
                {"name": "桂花云露", "price": 20.00, "stock": 80},
                {"name": "云雾观音", "price": 22.00, "stock": 60},
                {"name": "珍珠奶茶", "price": 15.00, "stock": 120},
                {"name": "红豆奶茶", "price": 16.00, "stock": 100}
            ]
            log_backend("get_all_products", source="fallback_mock", products=[{"name": p["name"], "stock": p["stock"]} for p in fallback])
            return fallback

        try:
            query = "SELECT name, price, stock FROM products"
            rows = product_db.fetch_all(query)
            log_backend("get_all_products", source="db", products=[{"name": r.get("name"), "stock": r.get("stock")} for r in rows])
            return rows
        except Exception as e:
            log_backend("get_all_products", source="db", error=str(e))
            print(f"获取所有产品失败: {str(e)}")
            return []
    
    def _get_product_id(self, product_name: str) -> Optional[int]:
        """根据产品名称获取 product_id（用于 order_items 外键）"""
        if not PRODUCT_DB_AVAILABLE or product_db is None:
            return None
        try:
            if product_db.db_type == "sqlite":
                row = product_db.fetch_one("SELECT id FROM products WHERE name = ?", (product_name,))
            else:
                row = product_db.fetch_one("SELECT id FROM products WHERE name = %s", (product_name,))
            return int(row["id"]) if row and row.get("id") is not None else None
        except Exception as e:
            print(f"查询产品ID失败: {str(e)}")
            return None

    def _get_product_price(self, product_name: str) -> Optional[float]:
        """
        查询产品价格
        
        Args:
            product_name: 产品名称
            
        Returns:
            产品价格，如果不存在则返回 None
        """
        if not PRODUCT_DB_AVAILABLE or product_db is None:
            # 如果没有数据库，使用默认价格
            default_prices = {
                "云边茉莉": 18.00,
                "桂花云露": 20.00,
                "云雾观音": 22.00,
                "珍珠奶茶": 15.00,
                "红豆奶茶": 16.00,
            }
            return default_prices.get(product_name, 18.00)
        
        try:
            if product_db.db_type == "sqlite":
                query = "SELECT price FROM products WHERE name = ?"
            else:
                query = "SELECT price FROM products WHERE name = %s"
            
            product = product_db.fetch_one(query, (product_name,))
            if product:
                return float(product.get("price", 18.00))
            return None
        except Exception as e:
            print(f"查询产品价格失败: {str(e)}")
            return None
    
    def format_order_response(self, order: Dict) -> str:
        """
        格式化订单信息为字符串（支持多产品订单）
        
        Args:
            order: 订单信息（包含 items 列表）
            
        Returns:
            格式化的订单信息字符串
        """
        sweetness_map = {1: "无糖", 2: "微糖", 3: "半糖", 4: "少糖", 5: "标准糖"}
        ice_level_map = {1: "热", 2: "温", 3: "去冰", 4: "少冰", 5: "正常冰"}
        
        created_at = order.get("created_at", "")
        if isinstance(created_at, datetime):
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(created_at, str):
            pass
        else:
            created_at = str(created_at)
        
        items = order.get("items", [])
        
        result = f"""订单信息:
- 订单ID: {order.get('order_id', '')}
- 用户ID: {order.get('user_id', '')}
- 订单总价: ¥{order.get('total_price', 0):.2f}
- 创建时间: {created_at}

订单项（共 {len(items)} 项）:"""
        
        for i, item in enumerate(items, 1):
            sweetness_text = sweetness_map.get(item.get("sweetness", 5), "标准糖")
            ice_level_text = ice_level_map.get(item.get("ice_level", 5), "正常冰")
            unit_price = item.get("unit_price", 0)
            quantity = item.get("quantity", 1)
            item_price = item.get("item_price", unit_price * quantity)
            result += f"""
  {i}. {item.get('product_name', '')}
     甜度: {sweetness_text} | 冰量: {ice_level_text} | 数量: {quantity}
     单价: ¥{unit_price:.2f} | 小计: ¥{item_price:.2f}"""
        
        return result
    
    def _convert_sweetness_str_to_int(self, sweetness: str) -> int:
        """甜度字符串转数字"""
        sweetness_map = {
            "无糖": 1,
            "微糖": 2,
            "半糖": 3,
            "少糖": 4,
            "标准糖": 5
        }
        return sweetness_map.get(sweetness, 5)
    
    def _convert_ice_level_str_to_int(self, ice_level: str) -> int:
        """冰量字符串转数字"""
        ice_level_map = {
            "热": 1,
            "温": 2,
            "去冰": 3,
            "少冰": 4,
            "正常冰": 5
        }
        return ice_level_map.get(ice_level, 5)
    
    def _convert_sweetness_int_to_str(self, sweetness: int) -> str:
        """甜度数字转字符串"""
        sweetness_map = {
            1: "无糖",
            2: "微糖",
            3: "半糖",
            4: "少糖",
            5: "标准糖"
        }
        return sweetness_map.get(sweetness, "标准糖")
    
    def _convert_ice_level_int_to_str(self, ice_level: int) -> str:
        """冰量数字转字符串"""
        ice_level_map = {
            1: "热",
            2: "温",
            3: "去冰",
            4: "少冰",
            5: "正常冰"
        }
        return ice_level_map.get(ice_level, "正常冰")
