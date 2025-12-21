"""
启动业务智能体服务
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from business_agent import BusinessAgent
from service_discovery import ServiceDiscovery

def main():
    """启动业务智能体"""
    print("=" * 60)
    print("业务智能体服务")
    print("=" * 60)
    print()
    
    # 创建业务智能体
    agent = BusinessAgent(
        agent_name="business_agent",
        description="云边奶茶铺业务处理智能体，处理订单、咨询等业务"
    )
    
    # 注册到服务发现（可选）
    sd = ServiceDiscovery(method="config")
    sd.register(
        "business_agent",
        host="localhost",
        port=10009,
        url="http://localhost:10009",
        description="云边奶茶铺业务处理智能体"
    )
    
    print(f"业务智能体已注册到服务发现")
    print(f"可用工具: {len(agent.get_available_tools())} 个")
    for tool in agent.get_available_tools():
        print(f"  - {tool['name']}: {tool['description']}")
    print()
    
    # 启动 A2A 服务
    try:
        agent.start_a2a_server(host='0.0.0.0', port=10009, debug=False)
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
