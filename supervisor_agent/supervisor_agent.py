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
from service_discovery import ServiceDiscovery
from a2a.client import A2AClient

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
        
        # 服务发现（用于查找子智能体地址）
        self.service_discovery = ServiceDiscovery(method="config")
        
        # 子智能体配置
        self.sub_agents = {
            "consult_agent": {
                "name": "咨询智能体",
                "description": "处理产品咨询、活动信息和冲泡指导",
                "implemented": True  # 已实现，可以通过 A2A 协议调用
            },
            "order_agent": {
                "name": "订单智能体",
                "description": "处理订单相关业务，包括下单、查询、修改等",
                "implemented": True  # 已实现，可以通过 A2A 协议调用
            },
            "feedback_agent": {
                "name": "反馈智能体",
                "description": "处理用户反馈、投诉和差评",
                "implemented": True  # 已实现，可以通过 A2A 协议调用
            }
        }
        
        # A2A 客户端（用于调用子智能体）
        self.a2a_client = A2AClient(service_discovery=self.service_discovery)
    
    def route_to_agent(self, user_input: str) -> Optional[str]:
        """
        分析用户输入，判断应该路由到哪个子智能体
        
        Args:
            user_input: 用户输入
            
        Returns:
            应该调用的子智能体名称，如果不需要特定智能体则返回 None
        """
        # 第一步：快速关键词匹配
        result = self._route_by_keywords(user_input)
        if result:
            return result
        
        # 第二步：如果关键词匹配失败，使用 LLM 判断（更智能）
        return self._route_by_llm(user_input)
    
    def _route_by_keywords(self, user_input: str) -> Optional[str]:
        """
        使用关键词匹配进行路由（快速但可能不够准确）
        """
        user_input_lower = user_input.lower()
        
        # 订单相关关键词（扩展版）
        order_keywords = [
            "下单", "订单", "点单", "购买", "结账", "支付", "购物车",
            "取消订单", "修改订单", "查询订单", "我要", "给我", "来一杯",
            "来一份", "要一杯", "要一份", "点一杯", "点一份"
        ]
        if any(keyword in user_input_lower for keyword in order_keywords):
            return "order_agent"
        
        # 产品名称列表
        product_names = ["云边茉莉", "桂花云露", "云雾观音", "珍珠奶茶", "红豆奶茶", "奶茶"]
        
        # 产品名称 + 数量/规格匹配（如"一杯"、"一份"、"少糖"等）
        has_product = any(product in user_input for product in product_names)
        has_quantity = any(word in user_input for word in ["一杯", "一份", "两杯", "两份", "1杯", "2杯", "三杯", "四杯"])
        has_spec = any(word in user_input for word in ["少糖", "半糖", "微糖", "无糖", "标准糖", 
                                                        "正常冰", "少冰", "去冰", "温", "热", "热饮"])
        
        # 如果包含产品名称 + (数量或规格)，认为是下单请求
        if has_product and (has_quantity or has_spec):
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
    
    def _route_by_llm(self, user_input: str) -> Optional[str]:
        """
        使用 LLM 进行智能路由判断（准确但需要 API 调用）
        """
        prompt = f"""你是云边奶茶铺的监督者智能体，需要分析用户请求并路由到合适的子智能体。

可用子智能体：
1. order_agent - 处理订单相关业务，包括下单、查询、修改等
2. consult_agent - 处理产品咨询、活动信息和冲泡指导
3. feedback_agent - 处理用户反馈、投诉和差评

用户请求: {user_input}

请判断这个请求应该路由到哪个子智能体。如果用户想要：
- 下单、点单、购买、查询订单、修改订单、取消订单 → order_agent
- 咨询产品、了解活动、询问价格、推荐产品 → consult_agent
- 反馈、投诉、建议、差评 → feedback_agent
- 一般性对话 → 返回 None

请只返回智能体名称（order_agent、consult_agent、feedback_agent）或 None，不要其他文字。"""

        try:
            response = Generation.call(
                model=DASHSCOPE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 低温度，确保路由准确性
                result_format='message'
            )
            
            if response.status_code == 200:
                result = response.output.choices[0].message.content.strip()
                # 清理可能的格式问题
                result = result.lower().replace(" ", "_").replace("\"", "").replace("'", "")
                
                if result in ["order_agent", "consult_agent", "feedback_agent"]:
                    print(f"[SupervisorAgent] LLM 路由判断: {user_input[:50]}... → {result}", file=sys.stderr, flush=True)
                    return result
                elif result == "none" or result == "null":
                    return None
        except Exception as e:
            print(f"[SupervisorAgent] LLM 路由判断失败: {str(e)}", file=sys.stderr, flush=True)
        
        return None
    
    def call_sub_agent(self, agent_name: str, user_input: str) -> str:
        """
        调用子智能体处理请求（使用 A2A 协议）
        
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
        
        # 使用 A2A 协议调用子智能体
        try:
            # 构建 A2A 协议请求数据
            a2a_request = {
                "input": user_input,
                "chat_id": self.chat_id,
                "user_id": self.user_id
            }
            
            # 通过 A2A Client 调用子智能体
            a2a_response = self.a2a_client.call_agent(agent_name, a2a_request)
            
            # 提取响应内容
            if isinstance(a2a_response, dict):
                output = a2a_response.get("output", "")
                if output:
                    return output
                # 如果没有 output 字段，尝试直接返回整个响应
                return str(a2a_response)
            else:
                return str(a2a_response)
                
        except ValueError as e:
            # 服务未找到
            return f"抱歉，{agent_info['name']} 服务暂时不可用，请稍后再试。"
        except ConnectionError as e:
            # 连接错误
            return f"抱歉，无法连接到 {agent_info['name']}，请确保服务已启动。"
        except Exception as e:
            # 其他错误
            error_msg = str(e)
            print(f"调用 {agent_name} 时出现错误: {error_msg}")
            return f"抱歉，调用 {agent_info['name']} 时出现了问题，请稍后再试。"
    
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
