"""
数据库访问层 - 订单相关操作
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入数据库管理器
try:
    from database.db_manager import DatabaseManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("警告: 数据库模块未找到，将使用内存存储")


class OrderDAO:
    """订单数据访问对象"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化订单 DAO
        
        Args:
            db_manager: 数据库管理器，如果为 None 则使用内存存储
        """
        self.db = db_manager
        self.use_memory = db_manager is None
        
        if self.use_memory:
            # 内存存储（用于测试）
            self.memory_orders: List[Dict] = []
            print("使用内存存储订单数据（仅用于测试）")
    
    def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        """
        根据订单ID查询订单（包含订单项）
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单信息字典，如果不存在则返回 None
        """
        if self.use_memory:
            for order in self.memory_orders:
                if order.get("order_id") == order_id:
                    return order
            return None
        
        # 从数据库查询订单主表
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM orders WHERE order_id = ?"
        else:
            query = "SELECT * FROM orders WHERE order_id = %s"
        order = self.db.fetch_one(query, (order_id,))
        if not order:
            return None
        
        # 查询订单项
        order["items"] = self.get_order_items(order_id)
        return order
    
    def get_order_by_user_and_id(self, user_id: int, order_id: str) -> Optional[Dict]:
        """
        根据用户ID和订单ID查询订单（包含订单项）
        
        Args:
            user_id: 用户ID
            order_id: 订单ID
            
        Returns:
            订单信息字典
        """
        if self.use_memory:
            for order in self.memory_orders:
                if order.get("order_id") == order_id and order.get("user_id") == user_id:
                    return order
            return None
        
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM orders WHERE user_id = ? AND order_id = ?"
        else:
            query = "SELECT * FROM orders WHERE user_id = %s AND order_id = %s"
        order = self.db.fetch_one(query, (user_id, order_id))
        if not order:
            return None
        
        # 查询订单项
        order["items"] = self.get_order_items(order_id)
        return order
    
    def get_orders_by_user(self, user_id: int) -> List[Dict]:
        """
        根据用户ID查询所有订单（包含订单项）
        
        Args:
            user_id: 用户ID
            
        Returns:
            订单列表
        """
        if self.use_memory:
            return [order for order in self.memory_orders if order.get("user_id") == user_id]
        
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC"
        else:
            query = "SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC"
        orders = self.db.fetch_all(query, (user_id,))
        
        # 为每个订单加载订单项
        for order in orders:
            order["items"] = self.get_order_items(order["order_id"])
        return orders
    
    def create_order(self, order_data: Dict) -> Dict:
        """
        创建订单主记录
        
        Args:
            order_data: 订单数据（只包含订单基本信息，不包含产品信息）
            
        Returns:
            创建的订单信息
        """
        if self.use_memory:
            order_data["id"] = len(self.memory_orders) + 1
            order_data["created_at"] = datetime.now().isoformat()
            order_data["updated_at"] = datetime.now().isoformat()
            self.memory_orders.append(order_data)
            return order_data
        
        # 插入数据库（只插入订单主表）
        if self.db.db_type == "sqlite":
            query = """INSERT INTO orders 
                       (order_id, user_id, total_price, status, remark, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)"""
        else:  # MySQL
            query = """INSERT INTO orders 
                       (order_id, user_id, total_price, status, remark, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        
        params = (
            order_data["order_id"],
            order_data["user_id"],
            order_data["total_price"],
            order_data.get("status", "UNPAID"),
            order_data.get("remark", ""),
            datetime.now(),
            datetime.now()
        )
        
        print(f"[OrderDAO] 准备插入订单 - order_id: {order_data['order_id']}, user_id: {order_data['user_id']}")
        cursor = self.db.execute(query, params)
        # execute 方法已经自动提交，但为了确保，再次提交
        if hasattr(self.db, 'connection'):
            self.db.connection.commit()
            print(f"[OrderDAO] 事务已提交")
        
        # 立即查询验证
        result = self.get_order_by_id(order_data["order_id"])
        if result:
            print(f"[OrderDAO] 订单查询成功 - order_id: {result.get('order_id')}")
        else:
            print(f"[OrderDAO] ⚠️  订单查询失败 - 订单未找到")
        return result
    
    def create_order_item(self, item_data: Dict) -> Dict:
        """
        创建订单项
        
        Args:
            item_data: 订单项数据
            
        Returns:
            创建的订单项信息
        """
        if self.use_memory:
            if "items" not in item_data:
                item_data["items"] = []
            item_data["items"].append(item_data)
            return item_data
        
        # 插入订单项表
        if self.db.db_type == "sqlite":
            query = """INSERT INTO order_items
                       (order_id, product_id, product_name, sweetness, ice_level,
                        quantity, unit_price, item_price, remark, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        else:  # MySQL
            query = """INSERT INTO order_items
                       (order_id, product_id, product_name, sweetness, ice_level,
                        quantity, unit_price, item_price, remark, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        params = (
            item_data["order_id"],
            item_data.get("product_id", 0),  # TODO: 从 products 表查询实际 ID
            item_data["product_name"],
            item_data["sweetness"],
            item_data["ice_level"],
            item_data["quantity"],
            item_data["unit_price"],
            item_data["item_price"],
            item_data.get("remark", ""),
            datetime.now()
        )
        
        self.db.execute(query, params)
        if hasattr(self.db, 'connection'):
            self.db.connection.commit()
        return item_data
    
    def get_order_items(self, order_id: str) -> List[Dict]:
        """
        获取订单的所有订单项
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单项列表
        """
        if self.use_memory:
            for order in self.memory_orders:
                if order.get("order_id") == order_id:
                    return order.get("items", [])
            return []
        
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM order_items WHERE order_id = ?"
        else:
            query = "SELECT * FROM order_items WHERE order_id = %s"
        return self.db.fetch_all(query, (order_id,))
    
    def delete_order(self, user_id: int, order_id: str) -> bool:
        """
        删除订单（级联删除订单项）
        
        Args:
            user_id: 用户ID
            order_id: 订单ID
            
        Returns:
            是否删除成功
        """
        if self.use_memory:
            for i, order in enumerate(self.memory_orders):
                if order.get("order_id") == order_id and order.get("user_id") == user_id:
                    del self.memory_orders[i]
                    return True
            return False
        
        # 删除订单（由于外键约束，会自动删除订单项）
        if self.db.db_type == "sqlite":
            query = "DELETE FROM orders WHERE user_id = ? AND order_id = ?"
        else:
            query = "DELETE FROM orders WHERE user_id = %s AND order_id = %s"
        self.db.execute(query, (user_id, order_id))
        if hasattr(self.db, 'connection'):
            self.db.connection.commit()
        # 检查是否删除成功（通过查询确认）
        deleted_order = self.get_order_by_user_and_id(user_id, order_id)
        return deleted_order is None
    
    def update_order_remark(self, user_id: int, order_id: str, remark: str) -> Optional[Dict]:
        """
        更新订单备注（只更新订单主表）
        
        Args:
            user_id: 用户ID
            order_id: 订单ID
            remark: 新备注
            
        Returns:
            更新后的订单信息
        """
        if self.use_memory:
            for order in self.memory_orders:
                if order.get("order_id") == order_id and order.get("user_id") == user_id:
                    order["remark"] = remark
                    order["updated_at"] = datetime.now().isoformat()
                    return order
            return None
        
        if self.db.db_type == "sqlite":
            query = "UPDATE orders SET remark = ?, updated_at = ? WHERE user_id = ? AND order_id = ?"
        else:
            query = "UPDATE orders SET remark = %s, updated_at = %s WHERE user_id = %s AND order_id = %s"
        self.db.execute(query, (remark, datetime.now(), user_id, order_id))
        if hasattr(self.db, 'connection'):
            self.db.connection.commit()
        return self.get_order_by_user_and_id(user_id, order_id)
    
    def query_orders(self, user_id: int, filters: Optional[Dict] = None) -> List[Dict]:
        """
        多条件查询订单（包含订单项）
        
        Args:
            user_id: 用户ID
            filters: 筛选条件（product_name, sweetness, ice_level, start_time, end_time）
                   注意：product_name, sweetness, ice_level 现在在 order_items 表中
            
        Returns:
            订单列表
        """
        if self.use_memory:
            orders = [o for o in self.memory_orders if o.get("user_id") == user_id]
            # 简单的内存过滤
            if filters:
                if "product_name" in filters:
                    orders = [o for o in orders if filters["product_name"] in o.get("product_name", "")]
            return orders
        
        # 构建 SQL 查询（只查询订单主表）
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM orders WHERE user_id = ?"
            param_placeholder = "?"
        else:
            query = "SELECT * FROM orders WHERE user_id = %s"
            param_placeholder = "%s"
        
        params = [user_id]
        
        # 注意：product_name, sweetness, ice_level 现在在 order_items 表中
        # 如果需要按这些条件过滤，需要 JOIN order_items 表
        # 这里简化处理，先查询所有订单，然后加载订单项
        
        query += " ORDER BY created_at DESC"
        orders = self.db.fetch_all(query, tuple(params))
        
        # 为每个订单加载订单项
        for order in orders:
            order["items"] = self.get_order_items(order["order_id"])
        
        # 如果需要在订单项级别过滤，可以在这里进行
        # 目前简化处理，返回所有订单
        
        return orders
