"""
MCP Server - 提供工具给 Agent 使用
"""
import json
import sys
from flask import Flask, request, jsonify
from typing import Dict, List
from .tool import Tool, ToolDefinition
from .request_context import set_request_id
from .access_logger import log_access


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
            # 全链路日志：从 header 读取 req_id，若无则自动生成。重复 header 会合并为逗号分隔，取第一段
            req_id = request.headers.get("X-Request-Id") or request.headers.get("x-request-id")
            if req_id and "," in str(req_id):
                req_id = str(req_id).split(",")[0].strip()
            request_id = set_request_id(req_id)
            data = request.json or {}
            parameters = data.get("parameters", {})
            print(json.dumps({"req_id": request_id, "layer": "mcp_server", "event": "tool_invoke", "tool": tool_name}, ensure_ascii=False), file=sys.stderr, flush=True)

            if tool_name not in self.tools:
                log_access(tool_name, parameters, status="error", error=f"Tool {tool_name} not found")
                return jsonify({
                    "error": f"Tool {tool_name} not found",
                    "status": "error"
                }), 404

            try:
                tool = self.tools[tool_name]
                result = tool.invoke(parameters)
                log_access(tool_name, parameters, status="success", result=result)
                return jsonify({
                    "result": result,
                    "status": "success"
                })
            except Exception as e:
                import traceback
                error_msg = str(e)
                log_access(tool_name, parameters, status="error", error=error_msg)
                traceback.print_exc()
                return jsonify({
                    "error": error_msg,
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
