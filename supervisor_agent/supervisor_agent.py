"""
监督者智能体 - 负责路由和协调子智能体
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
import dashscope
from dashscope import Generation

# 添加项目根目录到路径，以便导入 config
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class SupervisorAgent:
    """监督者智能体 - 负责协调和管理其他子智能体的工作"""
    
    def __init__(self, user_id: str = "default_user", chat_id: str = "default_chat"):
        self.user_id = user_id
        self.chat_id = chat_id
        self.history: List[Dict[str, str]] = []
        
        # 系统提示词（监督者智能体的角色定义）
        self.system_prompt = """角色与职责:
你是云边奶茶铺的监督者智能体，负责协调和管理其他子智能体的工作。
你可以调用以下子智能体来处理不同类型的用户请求：
- feedback_agent: 处理用户反馈、投诉和差评
- consult_agent: 处理产品咨询、活动信息和冲泡指导
- order_agent: 处理订单相关业务，包括下单、查询、修改等

工作流程:
1. 接收用户请求
2. 分析请求类型，判断应该调用哪个子智能体
3. 调用相应的子智能体处理请求
4. 整合子智能体的响应，返回给用户

约束:
- 只负责协调和路由，不直接处理具体业务
- 确保每个请求都能找到合适的子智能体处理
- 如果子智能体不可用，需要提供友好的错误提示
- 回答要友好、专业，体现云边奶茶铺的品牌形象

当前阶段说明:
目前子智能体功能还在开发中。当用户请求需要特定子智能体处理时，请告知用户：
"我理解您的需求，这需要 [子智能体名称] 来处理。该功能正在开发中，敬请期待。"

对于一般性对话，你可以直接回答。
"""
        
        # 添加系统提示词到历史记录
        self.history.append({
            "role": "system",
            "content": self.system_prompt
        })
        
        # 子智能体配置（目前都是未实现状态）
        self.sub_agents = {
            "consult_agent": {
                "name": "咨询智能体",
                "description": "处理产品咨询、活动信息和冲泡指导",
                "implemented": False
            },
            "order_agent": {
                "name": "订单智能体",
                "description": "处理订单相关业务，包括下单、查询、修改等",
                "implemented": False
            },
            "feedback_agent": {
                "name": "反馈智能体",
                "description": "处理用户反馈、投诉和差评",
                "implemented": False
            }
        }
    
    def route_to_agent(self, user_input: str) -> Optional[str]:
        """
        分析用户输入，判断应该路由到哪个子智能体
        
        Args:
            user_input: 用户输入
            
        Returns:
            应该调用的子智能体名称，如果不需要特定智能体则返回 None
        """
        # 简单的关键词匹配（后续可以用 LLM 来更智能地判断）
        user_input_lower = user_input.lower()
        
        # 订单相关关键词
        order_keywords = ["下单", "订单", "点单", "购买", "结账", "支付", "购物车", "取消订单", "修改订单", "查询订单"]
        if any(keyword in user_input_lower for keyword in order_keywords):
            return "order_agent"
        
        # 反馈相关关键词
        feedback_keywords = ["反馈", "投诉", "建议", "差评", "不满意", "问题", "意见"]
        if any(keyword in user_input_lower for keyword in feedback_keywords):
            return "feedback_agent"
        
        # 咨询相关关键词
        consult_keywords = ["咨询", "介绍", "推荐", "产品", "活动", "优惠", "价格", "口味", "什么", "怎么", "如何"]
        if any(keyword in user_input_lower for keyword in consult_keywords):
            return "consult_agent"
        
        return None
    
    def call_sub_agent(self, agent_name: str, user_input: str) -> str:
        """
        调用子智能体处理请求
        
        Args:
            agent_name: 子智能体名称
            user_input: 用户输入
            
        Returns:
            子智能体的响应
        """
        if agent_name not in self.sub_agents:
            return f"错误：未知的子智能体 {agent_name}"
        
        agent_info = self.sub_agents[agent_name]
        
        # 如果子智能体未实现，返回提示信息
        if not agent_info["implemented"]:
            return f"我理解您的需求，这需要 {agent_info['name']} 来处理。该功能正在开发中，敬请期待。"
        
        # TODO: 后续实现实际的子智能体调用逻辑
        # 例如：HTTP 请求、直接函数调用等
        return f"[{agent_info['name']}] 处理中..."
    
    def chat(self, user_input: str) -> str:
        """
        处理用户输入并返回回复
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI 回复
        """
        # 添加用户输入到历史记录
        self.history.append({
            "role": "user",
            "content": user_input
        })
        
        try:
            # 先判断是否需要路由到特定子智能体
            target_agent = self.route_to_agent(user_input)
            
            if target_agent:
                # 需要特定子智能体处理
                agent_response = self.call_sub_agent(target_agent, user_input)
                
                # 将路由决策和子智能体响应添加到历史记录
                self.history.append({
                    "role": "assistant",
                    "content": agent_response
                })
                
                return agent_response
            else:
                # 一般性对话，直接使用 LLM 处理
                response = Generation.call(
                    model=DASHSCOPE_MODEL,
                    messages=self.history,
                    temperature=0.7,
                    result_format='message'
                )
                
                if response.status_code == 200:
                    ai_message = response.output.choices[0].message.content
                    
                    # 添加到历史记录
                    self.history.append({
                        "role": "assistant",
                        "content": ai_message
                    })
                    
                    return ai_message
                else:
                    error_msg = f"API 调用失败: {response.message}"
                    print(f"错误: {error_msg}")
                    return "抱歉，处理您的请求时出现了问题，请稍后再试。"
            
        except Exception as e:
            error_msg = f"处理请求时出现错误: {str(e)}"
            print(f"错误: {error_msg}")
            return "抱歉，处理您的请求时出现了问题，请稍后再试。"
    
    def clear_history(self):
        """清空对话历史"""
        self.history = [{
            "role": "system",
            "content": self.system_prompt
        }]
    
    def register_sub_agent(self, agent_name: str, agent_info: Dict):
        """
        注册子智能体（用于后续扩展）
        
        Args:
            agent_name: 子智能体名称
            agent_info: 子智能体信息，包含 name, description, implemented 等
        """
        self.sub_agents[agent_name] = agent_info
    
    def get_sub_agent_status(self) -> Dict:
        """
        获取所有子智能体的状态
        
        Returns:
            子智能体状态字典
        """
        return {
            name: {
                "name": info["name"],
                "description": info["description"],
                "implemented": info["implemented"]
            }
            for name, info in self.sub_agents.items()
        }
