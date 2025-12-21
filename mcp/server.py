"""
MCP Server - 提供工具给 Agent 使用
"""
from flask import Flask, request, jsonify
from typing import Dict, List
from .tool import Tool, ToolDefinition


class MCPServer:
    """MCP 协议服务端 - 提供工具给 Agent"""
    
    def __init__(self, server_name: str, port: int = 10002):
        """
        初始化 MCP 服务端
        
        Args:
            server_name: MCP Server 名称
            port: 服务端口
        """
        self.server_name = server_name
        self.port = port
        self.app = Flask(__name__)
        self.tools: Dict[str, Tool] = {}
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册 MCP 协议路由"""
        
        @self.app.route('/mcp/tools', methods=['GET'])
        def list_tools():
            """列出所有工具"""
            tools_list = [tool.definition.to_dict() for tool in self.tools.values()]
            return jsonify({
                "tools": tools_list,
                "server": self.server_name
            })
        
        @self.app.route('/mcp/tools/<tool_name>/invoke', methods=['POST'])
        def invoke_tool(tool_name: str):
            """调用工具"""
            if tool_name not in self.tools:
                return jsonify({
                    "error": f"Tool {tool_name} not found",
                    "status": "error"
                }), 404
            
            try:
                data = request.json or {}
                parameters = data.get("parameters", {})
                
                # 调用工具
                tool = self.tools[tool_name]
                result = tool.invoke(parameters)
                
                return jsonify({
                    "result": result,
                    "status": "success"
                })
            except Exception as e:
                return jsonify({
                    "error": str(e),
                    "status": "error"
                }), 500
        
        @self.app.route('/mcp/health', methods=['GET'])
        def health():
            """健康检查接口"""
            return jsonify({
                "status": "healthy",
                "server": self.server_name,
                "tools_count": len(self.tools)
            })
    
    def register_tool(self, tool: Tool):
        """
        注册工具
        
        Args:
            tool: Tool 对象
        """
        self.tools[tool.definition.name] = tool
    
    def register_tool_func(self, name: str, description: str, 
                           parameters: Dict, handler: callable):
        """
        注册工具（便捷方法）
        
        Args:
            name: 工具名称
            description: 工具描述
            parameters: 参数定义（JSON Schema）
            handler: 工具执行函数
        """
        definition = ToolDefinition(name=name, description=description, parameters=parameters)
        tool = Tool(definition=definition, handler=handler)
        self.register_tool(tool)
    
    def run(self, host: str = '0.0.0.0', debug: bool = False):
        """
        启动 MCP 服务
        
        Args:
            host: 监听地址
            debug: 是否开启调试模式
        """
        self.app.run(host=host, port=self.port, debug=debug)
