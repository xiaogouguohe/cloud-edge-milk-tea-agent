"""
启动咨询 MCP Server
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from consult_mcp_server import ConsultMCPServer

if __name__ == "__main__":
    print("=" * 60)
    print("启动咨询 MCP Server (ConsultMCPServer)")
    print("=" * 60)
    print()
    print("说明:")
    print("  - 提供咨询相关的工具（产品查询、知识库检索等）")
    print("  - 服务地址: http://localhost:10003")
    print()
    
    # 创建咨询 MCP Server 实例
    consult_mcp_server = ConsultMCPServer(port=10003)
    
    # 启动服务
    consult_mcp_server.run(host='0.0.0.0', debug=False)
