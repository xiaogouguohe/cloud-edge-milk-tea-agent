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
    
    # 创建业务智能体（作为 order_agent）
    agent = BusinessAgent(
        agent_name="order_agent",
        description="云边奶茶铺订单处理智能体，处理订单相关业务"
    )
    
    # 注册到服务发现（作为 order_agent）
    sd = ServiceDiscovery(method="config")
    sd.register(
        "order_agent",
        host="localhost",
        port=10006,
        url="http://localhost:10006",
        description="云边奶茶铺订单处理智能体"
    )
    
    print(f"业务智能体已注册到服务发现")
    print(f"可用工具: {len(agent.get_available_tools())} 个")
    for tool in agent.get_available_tools():
        print(f"  - {tool['name']}: {tool['description']}")
    print()
    
    # 启动 A2A 服务
    try:
        agent.start_a2a_server(host='0.0.0.0', port=10006, debug=False)
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
