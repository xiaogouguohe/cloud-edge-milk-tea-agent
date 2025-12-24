"""
启动咨询智能体 A2A Server
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from consult_agent import ConsultAgent

if __name__ == "__main__":
    print("=" * 60)
    print("启动咨询智能体 (ConsultAgent)")
    print("=" * 60)
    print()
    print("说明:")
    print("  - 作为 A2A Server，接收 SupervisorAgent 的调用")
    print("  - 通过 MCP 协议调用 ConsultMCPServer 的工具")
    print("  - 服务地址: http://localhost:10005")
    print()
    
    # 创建咨询智能体实例
    consult_agent = ConsultAgent(
        agent_name="consult_agent",
        description="云边奶茶铺咨询智能体，处理产品咨询、活动信息和冲泡指导",
        user_id="default_user",
        chat_id="default_chat"
    )
    
    # 启动 A2A Server
    consult_agent.start_a2a_server(host='0.0.0.0', port=10005, debug=False)
