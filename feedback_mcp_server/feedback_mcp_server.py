"""
反馈 MCP Server - 提供反馈相关的工具
参考原项目的 FeedbackMcpTools
"""
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import MCPServer, Tool, ToolDefinition
from .feedback_service import FeedbackService
from .database import FeedbackDAO

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


class FeedbackMCPServer:
    """反馈 MCP Server - 提供反馈相关的工具"""
    
    def __init__(self, port: int = 10004):
        """
        初始化反馈 MCP Server
        
        Args:
            port: 服务端口
        """
        self.port = port
        
        # 初始化数据访问层和服务层
        feedback_dao = FeedbackDAO(db_manager=db_manager)
        self.feedback_service = FeedbackService(feedback_dao)
        
        # 创建 MCP Server
        self.mcp_server = MCPServer(server_name="feedback-mcp-server", port=port)
        
        # 注册工具
        self._register_tools()
    
    def _register_tools(self):
        """注册所有反馈相关的工具"""
        
        # 1. 创建用户反馈
        self.mcp_server.register_tool_func(
            name="feedback-create-feedback",
            description="创建用户反馈记录，userId是必填项。支持产品反馈、服务反馈、投诉和建议四种类型。",
            parameters={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "integer",
                        "description": "用户ID，必填，必须为正整数"
                    },
                    "feedbackType": {
                        "type": "integer",
                        "description": "反馈类型：1-产品反馈，2-服务反馈，3-投诉，4-建议",
                        "enum": [1, 2, 3, 4]
                    },
                    "content": {
                        "type": "string",
                        "description": "反馈内容，必填"
                    },
                    "orderId": {
                        "type": "string",
                        "description": "关联订单ID，可选，格式为ORDER_开头的唯一标识符"
                    },
                    "rating": {
                        "type": "integer",
                        "description": "评分1-5星，可选",
                        "minimum": 1,
                        "maximum": 5
                    }
                },
                "required": ["userId", "feedbackType", "content"]
            },
            handler=self._create_feedback
        )
        
        # 2. 根据用户ID查询反馈记录
        self.mcp_server.register_tool_func(
            name="feedback-get-feedback-by-user",
            description="根据用户ID查询反馈记录，返回该用户的所有反馈列表，包括反馈类型、评分、内容和创建时间。",
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
            handler=self._get_feedbacks_by_user
        )
        
        # 3. 根据订单ID查询反馈记录
        self.mcp_server.register_tool_func(
            name="feedback-get-feedback-by-order",
            description="根据订单ID查询反馈记录，返回该订单的所有反馈列表，包括反馈类型、评分、内容和创建时间。",
            parameters={
                "type": "object",
                "properties": {
                    "orderId": {
                        "type": "string",
                        "description": "订单ID，格式为ORDER_开头的唯一标识符"
                    }
                },
                "required": ["orderId"]
            },
            handler=self._get_feedbacks_by_order
        )
        
        # 4. 更新反馈解决方案
        self.mcp_server.register_tool_func(
            name="feedback-update-solution",
            description="更新反馈解决方案，用于记录对用户反馈的处理结果。",
            parameters={
                "type": "object",
                "properties": {
                    "feedbackId": {
                        "type": "integer",
                        "description": "反馈ID，必须为正整数"
                    },
                    "solution": {
                        "type": "string",
                        "description": "解决方案内容"
                    }
                },
                "required": ["feedbackId", "solution"]
            },
            handler=self._update_solution
        )
    
    def _create_feedback(self, parameters: Dict) -> str:
        """创建反馈记录"""
        try:
            user_id = parameters.get("userId")
            feedback_type = parameters.get("feedbackType")
            content = parameters.get("content")
            order_id = parameters.get("orderId")
            rating = parameters.get("rating")
            
            if user_id is None:
                return "错误: userId 是必填项"
            if feedback_type is None:
                return "错误: feedbackType 是必填项"
            if not content:
                return "错误: content 是必填项"
            
            feedback = self.feedback_service.create_feedback(
                user_id=user_id,
                feedback_type=feedback_type,
                content=content,
                order_id=order_id,
                rating=rating
            )
            
            feedback_type_text = self.feedback_service.get_feedback_type_text(feedback_type)
            rating_text = self.feedback_service.get_rating_text(rating)
            
            result = f"反馈记录创建成功！\n"
            result += f"反馈ID: {feedback['id']}\n"
            result += f"用户ID: {feedback['user_id']}\n"
            result += f"反馈类型: {feedback_type_text}\n"
            if rating:
                result += f"评分: {rating_text}\n"
            result += f"内容: {feedback['content']}\n"
            if order_id:
                result += f"关联订单: {order_id}"
            
            return result
        except ValueError as e:
            return f"创建反馈记录失败: {str(e)}"
        except Exception as e:
            import traceback
            return f"创建反馈记录失败: {str(e)}\n{traceback.format_exc()}"
    
    def _get_feedbacks_by_user(self, parameters: Dict) -> str:
        """根据用户ID查询反馈记录"""
        try:
            user_id = parameters.get("userId")
            if user_id is None:
                return "错误: userId 是必填项"
            
            feedbacks = self.feedback_service.get_feedbacks_by_user_id(user_id)
            
            if not feedbacks:
                return f"用户 {user_id} 暂无反馈记录"
            
            result = f"用户 {user_id} 的反馈记录（共 {len(feedbacks)} 条）：\n\n"
            
            for feedback in feedbacks:
                feedback_type_text = self.feedback_service.get_feedback_type_text(feedback['feedback_type'])
                rating_text = self.feedback_service.get_rating_text(feedback.get('rating'))
                
                result += f"- 反馈ID: {feedback['id']}\n"
                result += f"  类型: {feedback_type_text}\n"
                result += f"  评分: {rating_text}\n"
                result += f"  内容: {feedback['content']}\n"
                if feedback.get('order_id'):
                    result += f"  关联订单: {feedback['order_id']}\n"
                if feedback.get('solution'):
                    result += f"  解决方案: {feedback['solution']}\n"
                result += f"  时间: {feedback['created_at']}\n\n"
            
            return result.strip()
        except Exception as e:
            import traceback
            return f"查询用户反馈记录失败: {str(e)}\n{traceback.format_exc()}"
    
    def _get_feedbacks_by_order(self, parameters: Dict) -> str:
        """根据订单ID查询反馈记录"""
        try:
            order_id = parameters.get("orderId")
            if not order_id:
                return "错误: orderId 是必填项"
            
            feedbacks = self.feedback_service.get_feedbacks_by_order_id(order_id)
            
            if not feedbacks:
                return f"订单 {order_id} 暂无反馈记录"
            
            result = f"订单 {order_id} 的反馈记录（共 {len(feedbacks)} 条）：\n\n"
            
            for feedback in feedbacks:
                feedback_type_text = self.feedback_service.get_feedback_type_text(feedback['feedback_type'])
                rating_text = self.feedback_service.get_rating_text(feedback.get('rating'))
                
                result += f"- 反馈ID: {feedback['id']}\n"
                result += f"  用户ID: {feedback['user_id']}\n"
                result += f"  类型: {feedback_type_text}\n"
                result += f"  评分: {rating_text}\n"
                result += f"  内容: {feedback['content']}\n"
                if feedback.get('solution'):
                    result += f"  解决方案: {feedback['solution']}\n"
                result += f"  时间: {feedback['created_at']}\n\n"
            
            return result.strip()
        except Exception as e:
            import traceback
            return f"查询订单反馈记录失败: {str(e)}\n{traceback.format_exc()}"
    
    def _update_solution(self, parameters: Dict) -> str:
        """更新反馈解决方案"""
        try:
            feedback_id = parameters.get("feedbackId")
            solution = parameters.get("solution")
            
            if feedback_id is None:
                return "错误: feedbackId 是必填项"
            if not solution:
                return "错误: solution 是必填项"
            
            success = self.feedback_service.update_feedback_solution(feedback_id, solution)
            
            if success:
                return f"反馈ID {feedback_id} 的解决方案更新成功：{solution}"
            else:
                return f"反馈ID {feedback_id} 的解决方案更新失败，可能是反馈ID不存在"
        except ValueError as e:
            return f"更新反馈解决方案失败: {str(e)}"
        except Exception as e:
            import traceback
            return f"更新反馈解决方案失败: {str(e)}\n{traceback.format_exc()}"
    
    def start(self, host: str = "0.0.0.0", debug: bool = False):
        """
        启动 MCP Server
        
        Args:
            host: 监听地址
            debug: 是否开启调试模式
        """
        print(f"[FeedbackMCPServer] 启动反馈 MCP Server，端口: {self.port}")
        self.mcp_server.start(host=host, port=self.port, debug=debug)

