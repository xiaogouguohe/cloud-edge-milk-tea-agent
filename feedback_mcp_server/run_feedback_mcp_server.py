"""
启动反馈 MCP Server
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from feedback_mcp_server.feedback_mcp_server import FeedbackMCPServer

def main():
    """启动反馈 MCP Server"""
    print("=" * 60)
    print("反馈 MCP Server")
    print("=" * 60)
    print()
    
    # 创建反馈 MCP Server
    server = FeedbackMCPServer(port=10004)
    
    print(f"反馈 MCP Server 已启动")
    print(f"监听地址: http://0.0.0.0:10004")
    print(f"可用工具:")
    print(f"  - feedback-create-feedback: 创建用户反馈记录")
    print(f"  - feedback-get-feedback-by-user: 根据用户ID查询反馈记录")
    print(f"  - feedback-get-feedback-by-order: 根据订单ID查询反馈记录")
    print(f"  - feedback-update-solution: 更新反馈解决方案")
    print()
    
    # 启动服务
    try:
        server.start(host='0.0.0.0', debug=False)
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()

