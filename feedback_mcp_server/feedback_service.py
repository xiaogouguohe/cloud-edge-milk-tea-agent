"""
反馈服务层 - 业务逻辑处理
参考原项目的 FeedbackService
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .database import FeedbackDAO

# 尝试导入数据库管理器
try:
    from database.db_manager import DatabaseManager
    from database.config import DB_TYPE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
    
    if DB_TYPE == "mysql":
        feedback_db = DatabaseManager(
            db_type="mysql",
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
    else:
        feedback_db = DatabaseManager(db_type="sqlite")
    FEEDBACK_DB_AVAILABLE = True
except Exception as e:
    FEEDBACK_DB_AVAILABLE = False
    feedback_db = None
    print(f"警告: 无法初始化反馈数据库: {str(e)}")


class FeedbackService:
    """反馈服务 - 处理反馈相关的业务逻辑"""
    
    def __init__(self, feedback_dao: FeedbackDAO):
        """
        初始化反馈服务
        
        Args:
            feedback_dao: 反馈数据访问对象
        """
        self.feedback_dao = feedback_dao
    
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
            创建的反馈信息
        """
        # 验证反馈类型
        if feedback_type not in [1, 2, 3, 4]:
            raise ValueError(f"反馈类型必须在 1-4 之间，当前值: {feedback_type}")
        
        # 验证评分
        if rating is not None and (rating < 1 or rating > 5):
            raise ValueError(f"评分必须在 1-5 之间，当前值: {rating}")
        
        # 验证内容
        if not content or not content.strip():
            raise ValueError("反馈内容不能为空")
        
        return self.feedback_dao.create_feedback(
            user_id=user_id,
            feedback_type=feedback_type,
            content=content.strip(),
            order_id=order_id,
            rating=rating
        )
    
    def get_feedbacks_by_user_id(self, user_id: int) -> List[Dict]:
        """
        根据用户ID查询反馈列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            反馈列表
        """
        return self.feedback_dao.get_feedbacks_by_user_id(user_id)
    
    def get_feedbacks_by_order_id(self, order_id: str) -> List[Dict]:
        """
        根据订单ID查询反馈列表
        
        Args:
            order_id: 订单ID
            
        Returns:
            反馈列表
        """
        return self.feedback_dao.get_feedbacks_by_order_id(order_id)
    
    def update_feedback_solution(self, feedback_id: int, solution: str) -> bool:
        """
        更新反馈解决方案
        
        Args:
            feedback_id: 反馈ID
            solution: 解决方案
            
        Returns:
            是否更新成功
        """
        if not solution or not solution.strip():
            raise ValueError("解决方案不能为空")
        
        return self.feedback_dao.update_feedback_solution(feedback_id, solution.strip())
    
    @staticmethod
    def get_feedback_type_text(feedback_type: int) -> str:
        """获取反馈类型文本"""
        type_map = {
            1: "产品反馈",
            2: "服务反馈",
            3: "投诉",
            4: "建议"
        }
        return type_map.get(feedback_type, "未知")
    
    @staticmethod
    def get_rating_text(rating: Optional[int]) -> str:
        """获取评分文本"""
        if rating is None:
            return "未评分"
        return f"{rating}星"


# 初始化服务实例
if FEEDBACK_DB_AVAILABLE:
    feedback_dao = FeedbackDAO(feedback_db)
    feedback_service = FeedbackService(feedback_dao)
else:
    feedback_dao = FeedbackDAO(None)  # 使用内存存储
    feedback_service = FeedbackService(feedback_dao)

