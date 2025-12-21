"""
A2A Server - Agent 服务端，暴露 A2A 协议接口
"""
from flask import Flask, request, jsonify, Response
from typing import Dict, Callable, Optional
import json


class A2AServer:
    """A2A 协议服务端 - 用于接收其他 Agent 的调用"""
    
    def __init__(self, agent_name: str, port: int = 10006):
        """
        初始化 A2A 服务端
        
        Args:
            agent_name: Agent 名称
            port: 服务端口
        """
        self.agent_name = agent_name
        self.port = port
        self.app = Flask(__name__)
        self.handler: Optional[Callable] = None
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册 A2A 协议路由"""
        
        @self.app.route('/a2a/invoke', methods=['POST'])
        def invoke():
            """A2A 协议调用接口"""
            try:
                data = request.json
                if not data:
                    return jsonify({"error": "Invalid request"}), 400
                
                # 调用处理函数
                if self.handler:
                    result = self.handler(data)
                    return jsonify({
                        "output": result,
                        "status": "success"
                    })
                else:
                    return jsonify({"error": "Handler not set"}), 500
                    
            except Exception as e:
                return jsonify({
                    "error": str(e),
                    "status": "error"
                }), 500
        
        @self.app.route('/a2a/stream', methods=['POST'])
        def stream():
            """A2A 协议流式调用接口（SSE）"""
            def generate():
                try:
                    data = request.json
                    if self.handler:
                        # 如果 handler 支持流式，调用它
                        if hasattr(self.handler, '__iter__'):
                            for chunk in self.handler(data):
                                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        else:
                            result = self.handler(data)
                            yield f"data: {json.dumps({'output': result}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            
            return Response(generate(), mimetype='text/event-stream')
        
        @self.app.route('/a2a/health', methods=['GET'])
        def health():
            """健康检查接口"""
            return jsonify({
                "status": "healthy",
                "agent": self.agent_name
            })
    
    def set_handler(self, handler: Callable[[Dict], str]):
        """
        设置请求处理函数
        
        Args:
            handler: 处理函数，接收输入数据，返回处理结果
        """
        self.handler = handler
    
    def run(self, host: str = '0.0.0.0', debug: bool = False):
        """
        启动 A2A 服务
        
        Args:
            host: 监听地址
            debug: 是否开启调试模式
        """
        self.app.run(host=host, port=self.port, debug=debug)
