"""
数据库访问层 - 反馈相关操作
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


class FeedbackDAO:
    """反馈数据访问对象"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化反馈 DAO
        
        Args:
            db_manager: 数据库管理器，如果为 None 则使用内存存储
        """
        self.db = db_manager
        self.use_memory = db_manager is None
        
        if self.use_memory:
            # 内存存储（用于测试）
            self.memory_feedbacks: List[Dict] = []
            print("使用内存存储反馈数据（仅用于测试）")
    
    def create_feedback(self, user_id: int, feedback_type: int, content: str,
                       order_id: Optional[str] = None, rating: Optional[int] = None) -> Dict:
        """
        创建反馈记录
        
        Args:
            user_id: 用户ID
            feedback_type: 反馈类型 (1-产品反馈, 2-服务反馈, 3-投诉, 4-建议)
            content: 反馈内容
            order_id: 关联订单ID（可选）
            rating: 评分 1-5（可选）
            
        Returns:
            创建的反馈信息字典
        """
        now = datetime.now()
        
        if self.use_memory:
            feedback_id = len(self.memory_feedbacks) + 1
            feedback = {
                "id": feedback_id,
                "user_id": user_id,
                "order_id": order_id,
                "feedback_type": feedback_type,
                "rating": rating,
                "content": content,
                "solution": None,
                "created_at": now,
                "updated_at": now
            }
            self.memory_feedbacks.append(feedback)
            return feedback
        
        # 插入数据库
        if self.db.db_type == "sqlite":
            query = """
                INSERT INTO feedback (user_id, order_id, feedback_type, rating, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (user_id, order_id, feedback_type, rating, content, now, now)
        else:
            query = """
                INSERT INTO feedback (user_id, order_id, feedback_type, rating, content, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (user_id, order_id, feedback_type, rating, content, now, now)
        
        cursor = self.db.connection.cursor()
        cursor.execute(query, params)
        self.db.connection.commit()
        
        # 获取插入的ID
        if self.db.db_type == "sqlite":
            feedback_id = cursor.lastrowid
        else:
            feedback_id = cursor.lastrowid
        
        cursor.close()
        
        # 查询创建的反馈
        return self.get_feedback_by_id(feedback_id)
    
    def get_feedback_by_id(self, feedback_id: int) -> Optional[Dict]:
        """
        根据反馈ID查询反馈
        
        Args:
            feedback_id: 反馈ID
            
        Returns:
            反馈信息字典
        """
        if self.use_memory:
            for feedback in self.memory_feedbacks:
                if feedback.get("id") == feedback_id:
                    return feedback
            return None
        
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM feedback WHERE id = ?"
        else:
            query = "SELECT * FROM feedback WHERE id = %s"
        
        return self.db.fetch_one(query, (feedback_id,))
    
    def get_feedbacks_by_user_id(self, user_id: int) -> List[Dict]:
        """
        根据用户ID查询反馈列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            反馈列表
        """
        if self.use_memory:
            return [f for f in self.memory_feedbacks if f.get("user_id") == user_id]
        
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM feedback WHERE user_id = ? ORDER BY created_at DESC"
        else:
            query = "SELECT * FROM feedback WHERE user_id = %s ORDER BY created_at DESC"
        
        return self.db.fetch_all(query, (user_id,))
    
    def get_feedbacks_by_order_id(self, order_id: str) -> List[Dict]:
        """
        根据订单ID查询反馈列表
        
        Args:
            order_id: 订单ID
            
        Returns:
            反馈列表
        """
        if self.use_memory:
            return [f for f in self.memory_feedbacks if f.get("order_id") == order_id]
        
        if self.db.db_type == "sqlite":
            query = "SELECT * FROM feedback WHERE order_id = ? ORDER BY created_at DESC"
        else:
            query = "SELECT * FROM feedback WHERE order_id = %s ORDER BY created_at DESC"
        
        return self.db.fetch_all(query, (order_id,))
    
    def update_feedback_solution(self, feedback_id: int, solution: str) -> bool:
        """
        更新反馈解决方案
        
        Args:
            feedback_id: 反馈ID
            solution: 解决方案
            
        Returns:
            是否更新成功
        """
        now = datetime.now()
        
        if self.use_memory:
            for feedback in self.memory_feedbacks:
                if feedback.get("id") == feedback_id:
                    feedback["solution"] = solution
                    feedback["updated_at"] = now
                    return True
            return False
        
        if self.db.db_type == "sqlite":
            query = "UPDATE feedback SET solution = ?, updated_at = ? WHERE id = ?"
        else:
            query = "UPDATE feedback SET solution = %s, updated_at = %s WHERE id = %s"
        
        cursor = self.db.connection.cursor()
        cursor.execute(query, (solution, now, feedback_id))
        self.db.connection.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        
        return affected_rows > 0

