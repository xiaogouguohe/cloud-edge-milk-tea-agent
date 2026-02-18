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
    
    def create_order(self, user_id: int, items: List[Dict], remark: Optional[str] = None) -> Dict:
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
            if product_info is None:
                print(f"[OrderService] 产品不存在: {product_name}, get_all_products 可能为空", file=sys.stderr, flush=True)
            else:
                print(f"[OrderService] 库存检查: {product_name} 当前库存={stock}, 需要={quantity}", file=sys.stderr, flush=True)
            if stock < quantity:
                raise ValueError(f"产品「{product_name}」库存不足，当前库存: {stock}，需要: {quantity}")

            item_price = unit_price * quantity
            total_price += item_price

            processed_item = {
                "order_id": order_id,
                "product_name": product_name,
                "sweetness": sweetness_num,
                "ice_level": ice_level_num,
                "quantity": quantity,
                "unit_price": float(unit_price),
                "item_price": float(item_price),
                "remark": item_data.get("remark", "")
            }
            processed_items.append(processed_item)

        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "total_price": float(total_price),
            "remark": remark or "",
            "status": "UNPAID"
        }

        if self.order_dao.use_memory:
            # 内存模式：无 products 表，仅写订单
            created_order = self.order_dao.create_order(order_data)
            for item in processed_items:
                self.order_dao.create_order_item(item)
        else:
            # 数据库模式：事务内原子扣库存 + 写订单
            def _tx(db):
                for item in processed_items:
                    rows = self.order_dao.decrement_stock(item["product_name"], item["quantity"])
                    if rows == 0:
                        raise ValueError(
                            f"产品「{item['product_name']}」库存不足或已被占用，请稍后重试"
                        )
                self.order_dao._create_order_tx(order_data)
                for item in processed_items:
                    self.order_dao._create_order_item_tx(item)

            self.order_dao.db.run_transaction(_tx)
            created_order = {**order_data, "items": processed_items}

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
    
    def update_order_remark(self, user_id: int, order_id: str, remark: str) -> Optional[Dict]:
        """
        更新订单备注
        
        Args:
            user_id: 用户ID
            order_id: 订单ID
            remark: 新备注
            
        Returns:
            更新后的订单信息
        """
        return self.order_dao.update_order_remark(user_id, order_id, remark)

    def update_order_status(self, order_id: str, status: str) -> Optional[Dict]:
        """
        更新订单状态
        
        Args:
            order_id: 订单ID
            status: 新状态 (MAKING, READY, COMPLETED, etc.)
            
        Returns:
            更新后的订单信息
        """
        return self.order_dao.update_order_status(order_id, status)
    
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
    
    def get_all_products(self) -> List[Dict]:
        """
        获取所有产品信息，包括价格和库存
        
        Returns:
            产品列表
        """
        if not PRODUCT_DB_AVAILABLE or product_db is None:
            # 降级处理：返回模拟数据
            return [
                {"name": "云边茉莉", "price": 18.00, "stock": 100, "status": 1},
                {"name": "桂花云露", "price": 20.00, "stock": 80, "status": 1},
                {"name": "云雾观音", "price": 22.00, "stock": 60, "status": 1},
                {"name": "珍珠奶茶", "price": 15.00, "stock": 120, "status": 1},
                {"name": "红豆奶茶", "price": 16.00, "stock": 100, "status": 1}
            ]
        
        try:
            query = "SELECT name, price, stock, status FROM products WHERE status = 1"
            return product_db.fetch_all(query)
        except Exception as e:
            print(f"获取所有产品失败: {str(e)}")
            return []
    
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
                query = "SELECT price FROM products WHERE name = ? AND status = 1"
            else:
                query = "SELECT price FROM products WHERE name = %s AND status = 1"
            
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
- 订单备注: {order.get('remark', '无')}
- 创建时间: {created_at}

订单项（共 {len(items)} 项）:"""
        
        for i, item in enumerate(items, 1):
            sweetness_text = sweetness_map.get(item.get("sweetness", 5), "标准糖")
            ice_level_text = ice_level_map.get(item.get("ice_level", 5), "正常冰")
            result += f"""
  {i}. {item.get('product_name', '')}
     甜度: {sweetness_text} | 冰量: {ice_level_text} | 数量: {item.get('quantity', 1)}
     单价: ¥{item.get('unit_price', 0):.2f} | 小计: ¥{item.get('item_price', 0):.2f}"""
            if item.get("remark"):
                result += f"\n     备注: {item.get('remark')}"
        
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
