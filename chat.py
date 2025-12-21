"""
基础对话功能 - 使用监督者智能体
"""
from supervisor_agent import SupervisorAgent


class ChatSession:
    """对话会话管理 - 使用监督者智能体"""
    
    def __init__(self, user_id: str = "default_user", chat_id: str = "default_chat"):
        self.user_id = user_id
        self.chat_id = chat_id
        # 使用监督者智能体
        self.supervisor = SupervisorAgent(user_id=user_id, chat_id=chat_id)
    
    def chat(self, user_input: str) -> str:
        """
        处理用户输入并返回回复
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI 回复
        """
        return self.supervisor.chat(user_input)
    
    def clear_history(self):
        """清空对话历史"""
        self.supervisor.clear_history()


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
