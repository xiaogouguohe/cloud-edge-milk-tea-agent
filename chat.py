"""
基础对话功能 - 直接使用 DashScope SDK
"""
import os
from typing import List, Dict, Any, Optional
import dashscope
from dashscope import Generation

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class ChatSession:
    """对话会话管理"""
    
    def __init__(self, user_id: str = "default_user", chat_id: str = "default_chat"):
        self.user_id = user_id
        self.chat_id = chat_id
        # 消息历史格式: [{"role": "system/user/assistant", "content": "..."}]
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
目前子智能体功能还在开发中，你可以先直接回答用户的问题，但要说明这是临时处理方式。
"""
        
        # 添加系统提示词到历史记录
        self.history.append({
            "role": "system",
            "content": self.system_prompt
        })
    
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
            # 调用 DashScope API
            response = Generation.call(
                model=DASHSCOPE_MODEL,
                messages=self.history,
                temperature=0.7,
                result_format='message'  # 使用 message 格式
            )
            
            # 检查响应状态
            if response.status_code == 200:
                # 获取回复内容
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


def main():
    """主函数：Terminal 交互界面"""
    print("=" * 60)
    print("云边奶茶铺智能助手")
    print("基于 Spring AI Alibaba 多智能体系统的 Python 实现")
    print("=" * 60)
    print()
    
    # 创建对话会话
    session = ChatSession()
    
    print("提示: 输入 'quit' 或 'exit' 退出，输入 'clear' 清空对话历史")
    print()
    
    while True:
        try:
            # 获取用户输入
            user_input = input("你: ").strip()
            
            if not user_input:
                continue
            
            # 处理退出命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n再见！")
                break
            
            # 处理清空历史命令
            if user_input.lower() in ['clear', 'reset']:
                session.clear_history()
                print("对话历史已清空\n")
                continue
            
            # 显示思考中
            print("思考中...")
            
            # 获取 AI 回复
            response = session.chat(user_input)
            
            # 显示回复
            print()
            print("-" * 60)
            print("智能助手:")
            print("-" * 60)
            print(response)
            print("-" * 60)
            print()
            
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n发生错误: {str(e)}\n")


if __name__ == "__main__":
    main()
