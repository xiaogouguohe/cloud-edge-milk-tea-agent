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
        根据订单ID查询订单
        
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
        
        # 从数据库查询
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM orders WHERE order_id = ?"
        else:
            query = "SELECT * FROM orders WHERE order_id = %s"
        return self.db.fetch_one(query, (order_id,))
    
    def get_order_by_user_and_id(self, user_id: int, order_id: str) -> Optional[Dict]:
        """
        根据用户ID和订单ID查询订单
        
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
        return self.db.fetch_one(query, (user_id, order_id))
    
    def get_orders_by_user(self, user_id: int) -> List[Dict]:
        """
        根据用户ID查询所有订单
        
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
        return self.db.fetch_all(query, (user_id,))
    
    def create_order(self, order_data: Dict) -> Dict:
        """
        创建订单
        
        Args:
            order_data: 订单数据
            
        Returns:
            创建的订单信息
        """
        if self.use_memory:
            order_data["id"] = len(self.memory_orders) + 1
            order_data["created_at"] = datetime.now().isoformat()
            order_data["updated_at"] = datetime.now().isoformat()
            self.memory_orders.append(order_data)
            return order_data
        
        # 插入数据库
        if self.db.db_type == "sqlite":
            query = """INSERT INTO orders 
                       (order_id, user_id, product_id, product_name, sweetness, ice_level, 
                        quantity, unit_price, total_price, remark, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        else:  # MySQL
            query = """INSERT INTO orders 
                       (order_id, user_id, product_id, product_name, sweetness, ice_level, 
                        quantity, unit_price, total_price, remark, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        params = (
            order_data["order_id"],
            order_data["user_id"],
            order_data.get("product_id", 0),
            order_data["product_name"],
            order_data["sweetness"],
            order_data["ice_level"],
            order_data["quantity"],
            order_data["unit_price"],
            order_data["total_price"],
            order_data.get("remark", ""),
            datetime.now(),
            datetime.now()
        )
        
        self.db.execute(query, params)
        return self.get_order_by_id(order_data["order_id"])
    
    def delete_order(self, user_id: int, order_id: str) -> bool:
        """
        删除订单
        
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
        
        if self.db.db_type == "sqlite":
            query = "DELETE FROM orders WHERE user_id = ? AND order_id = ?"
        else:
            query = "DELETE FROM orders WHERE user_id = %s AND order_id = %s"
        self.db.execute(query, (user_id, order_id))
        # 检查是否删除成功（通过查询确认）
        deleted_order = self.get_order_by_user_and_id(user_id, order_id)
        return deleted_order is None
    
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
        return self.get_order_by_user_and_id(user_id, order_id)
    
    def query_orders(self, user_id: int, filters: Optional[Dict] = None) -> List[Dict]:
        """
        多条件查询订单
        
        Args:
            user_id: 用户ID
            filters: 筛选条件（product_name, sweetness, ice_level, start_time, end_time）
            
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
        
        # 构建 SQL 查询
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM orders WHERE user_id = ?"
            param_placeholder = "?"
        else:
            query = "SELECT * FROM orders WHERE user_id = %s"
            param_placeholder = "%s"
        
        params = [user_id]
        
        if filters:
            if "product_name" in filters and filters["product_name"]:
                query += f" AND product_name LIKE {param_placeholder}"
                params.append(f"%{filters['product_name']}%")
            if "sweetness" in filters and filters["sweetness"]:
                query += f" AND sweetness = {param_placeholder}"
                params.append(filters["sweetness"])
            if "ice_level" in filters and filters["ice_level"]:
                query += f" AND ice_level = {param_placeholder}"
                params.append(filters["ice_level"])
        
        query += " ORDER BY created_at DESC"
        return self.db.fetch_all(query, tuple(params))
