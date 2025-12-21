"""
MCP Client - Agent 调用 MCP Server 的工具
"""
import requests
from typing import Dict, List, Optional
from service_discovery import ServiceDiscovery
from .tool import ToolDefinition


class MCPClient:
    """MCP 协议客户端 - 用于调用 MCP Server 的工具"""
    
    def __init__(self, service_discovery: Optional[ServiceDiscovery] = None):
        """
        初始化 MCP 客户端
        
        Args:
            service_discovery: 服务发现实例
        """
        self.sd = service_discovery or ServiceDiscovery(method="config")
    
    def list_tools(self, mcp_server_name: str) -> List[ToolDefinition]:
        """
        获取 MCP Server 的工具列表
        
        Args:
            mcp_server_name: MCP Server 名称
            
        Returns:
            工具定义列表
        """
        service = self.sd.discover(mcp_server_name)
        if not service:
            raise ValueError(f"MCP Server {mcp_server_name} not found")
        
        url = f"{service['url']}/mcp/tools"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 转换为 ToolDefinition 对象
            tools = []
            for tool_dict in data.get("tools", []):
                tools.append(ToolDefinition(
                    name=tool_dict["name"],
                    description=tool_dict["description"],
                    parameters=tool_dict["parameters"]
                ))
            return tools
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to list tools from {mcp_server_name}: {str(e)}")
    
    def invoke_tool(self, mcp_server_name: str, tool_name: str, 
                   parameters: Dict, timeout: int = 30) -> Dict:
        """
        调用 MCP Server 的工具
        
        Args:
            mcp_server_name: MCP Server 名称
            tool_name: 工具名称
            parameters: 工具参数
            timeout: 超时时间（秒）
            
        Returns:
            工具执行结果
        """
        service = self.sd.discover(mcp_server_name)
        if not service:
            raise ValueError(f"MCP Server {mcp_server_name} not found")
        
        url = f"{service['url']}/mcp/tools/{tool_name}/invoke"
        
        try:
            response = requests.post(
                url,
                json={"parameters": parameters},
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to invoke tool {tool_name}: {str(e)}")
