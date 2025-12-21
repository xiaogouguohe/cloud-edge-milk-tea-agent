"""
订单服务层 - 业务逻辑处理
参考原项目的 OrderService
"""
from typing import List, Dict, Optional
from datetime import datetime
from .database import OrderDAO


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
    
    def create_order(self, user_id: int, product_name: str, 
                    sweetness: int, ice_level: int, quantity: int,
                    remark: Optional[str] = None) -> Dict:
        """
        创建订单
        
        Args:
            user_id: 用户ID
            product_name: 产品名称
            sweetness: 甜度 (1-5)
            ice_level: 冰量 (1-5)
            quantity: 数量
            remark: 备注
            
        Returns:
            创建的订单信息
        """
        # 生成订单ID
        order_id = f"ORDER_{int(datetime.now().timestamp() * 1000)}"
        
        # TODO: 查询产品信息获取价格（这里简化处理）
        unit_price = 18.00  # 默认价格，实际应该从 products 表查询
        total_price = unit_price * quantity
        
        order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "product_id": 1,  # TODO: 从 products 表查询
            "product_name": product_name,
            "sweetness": sweetness,
            "ice_level": ice_level,
            "quantity": quantity,
            "unit_price": float(unit_price),
            "total_price": float(total_price),
            "remark": remark or ""
        }
        
        return self.order_dao.create_order(order_data)
    
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
    
    def format_order_response(self, order: Dict) -> str:
        """
        格式化订单信息为字符串
        
        Args:
            order: 订单信息
            
        Returns:
            格式化的订单信息字符串
        """
        sweetness_map = {1: "无糖", 2: "微糖", 3: "半糖", 4: "少糖", 5: "标准糖"}
        ice_level_map = {1: "热", 2: "温", 3: "去冰", 4: "少冰", 5: "正常冰"}
        
        sweetness_text = sweetness_map.get(order.get("sweetness", 5), "标准糖")
        ice_level_text = ice_level_map.get(order.get("ice_level", 5), "正常冰")
        
        created_at = order.get("created_at", "")
        if isinstance(created_at, datetime):
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(created_at, str):
            # 如果已经是字符串，直接使用
            pass
        else:
            created_at = str(created_at)
        
        return f"""订单信息:
- 订单ID: {order.get('order_id', '')}
- 用户ID: {order.get('user_id', '')}
- 产品: {order.get('product_name', '')}
- 甜度: {sweetness_text}
- 冰量: {ice_level_text}
- 数量: {order.get('quantity', 1)}
- 总价: ¥{order.get('total_price', 0):.2f}
- 备注: {order.get('remark', '无')}
- 创建时间: {created_at}"""
