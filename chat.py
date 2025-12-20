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
        
        # 系统提示词（基础对话版本）
        self.system_prompt = """你是云边奶茶铺的智能助手。

重要说明:
当前系统只实现了基础对话功能，以下功能模块尚未实现：
- feedback_agent（反馈处理智能体）- 未实现
- consult_agent（咨询智能体）- 未实现  
- order_agent（订单智能体）- 未实现

约束:
- 不要声称调用了任何 agent 或子智能体
- 不要假装执行任何业务操作（如推荐产品、处理订单等）
- 只能进行一般性的对话交流
- 如果用户询问具体业务功能，请告知："抱歉，该功能正在开发中，目前只能进行基础对话。"
- 保持友好、专业的交流态度，体现云边奶茶铺的品牌形象
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
    print("云边奶茶铺 AI 智能助手")
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
