"""
业务智能体 - 处理订单、咨询等业务逻辑
参考原项目的 ReactAgent 设计，支持 A2A 协议和 MCP 工具调用
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
import dashscope
from dashscope import Generation

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL
from mcp.client import MCPClient
from service_discovery import ServiceDiscovery
from a2a.server import A2AServer

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class BusinessAgent:
    """业务智能体 - 使用工具处理业务请求（类似原项目的 ReactAgent）"""
    
    def __init__(self, agent_name: str = "business_agent", 
                 description: str = "业务处理智能体",
                 user_id: str = "default_user", 
                 chat_id: str = "default_chat"):
        """
        初始化业务智能体
        
        Args:
            agent_name: Agent 名称
            description: Agent 描述
            user_id: 用户ID
            chat_id: 对话ID
        """
        self.agent_name = agent_name
        self.description = description
        self.user_id = user_id
        self.chat_id = chat_id
        self.history: List[Dict[str, str]] = []
        
        # MCP 客户端（用于调用工具）
        self.mcp_client = MCPClient()
        self.service_discovery = ServiceDiscovery(method="config")
        
        # 可用工具列表（从 MCP Server 获取）
        self.available_tools: List[Dict] = []
        self._load_tools()
        
        # 系统提示词
        self.system_prompt = self._build_system_prompt()
        
        # 初始化消息历史
        self.history.append({
            "role": "system",
            "content": self.system_prompt
        })
    
    def _load_tools(self):
        """从 MCP Server 加载可用工具"""
        try:
            # 尝试从 order-mcp-server 获取工具
            tools = self.mcp_client.list_tools("order-mcp-server")
            self.available_tools = [tool.to_dict() for tool in tools]
        except Exception as e:
            print(f"警告: 无法加载 MCP 工具: {str(e)}")
            self.available_tools = []
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tools_description = ""
        if self.available_tools:
            tools_description = "\n可用工具:\n"
            for tool in self.available_tools:
                tools_description += f"- {tool['name']}: {tool['description']}\n"
        else:
            tools_description = "\n注意: 当前没有可用的工具，MCP Server 可能未启动。\n"
        
        return f"""角色与职责:
你是云边奶茶铺的业务处理智能体，负责处理各种业务请求，包括订单、咨询、反馈等。

{self.description}

{tools_description}

工作流程:
1. 接收用户请求
2. 分析请求类型，判断需要使用哪个工具
3. 调用相应的工具处理请求
4. 整合工具返回的结果，生成友好的回复

约束:
- 只能使用提供的工具处理业务请求
- 如果工具不可用，需要告知用户
- 回答要友好、专业，体现云边奶茶铺的品牌形象
- 保护用户隐私，不要泄露其他用户的信息
"""
    
    def _extract_tool_call(self, llm_response: str) -> Optional[Dict]:
        """
        从 LLM 响应中提取工具调用信息
        
        这是一个简化的实现，实际可以使用更智能的方式（如函数调用）
        
        Args:
            llm_response: LLM 的响应文本
            
        Returns:
            工具调用信息，格式: {"tool": "tool_name", "parameters": {...}}
        """
        # 简单的关键词匹配（后续可以改进为更智能的解析）
        response_lower = llm_response.lower()
        
        # 检查是否需要调用工具
        if "order-get-order" in response_lower or "查询订单" in response_lower:
            # 尝试提取订单ID
            import re
            order_id_match = re.search(r'ORDER[_\d]+', llm_response, re.IGNORECASE)
            if order_id_match:
                return {
                    "tool": "order-get-order",
                    "mcp_server": "order-mcp-server",
                    "parameters": {"orderId": order_id_match.group()}
                }
        
        if "order-create-order" in response_lower or "创建订单" in response_lower or "下单" in response_lower:
            # 这里需要更复杂的参数提取，暂时返回 None，让 LLM 继续处理
            return None
        
        return None
    
    def _invoke_tool(self, tool_name: str, mcp_server: str, parameters: Dict) -> str:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            mcp_server: MCP Server 名称
            parameters: 工具参数
            
        Returns:
            工具执行结果
        """
        try:
            result = self.mcp_client.invoke_tool(mcp_server, tool_name, parameters)
            if result.get("status") == "success":
                return str(result.get("result", ""))
            else:
                return f"工具调用失败: {result.get('error', '未知错误')}"
        except Exception as e:
            return f"工具调用异常: {str(e)}"
    
    def _should_use_tool(self, user_input: str) -> Optional[Dict]:
        """
        使用 LLM 判断是否需要调用工具，并提取参数
        
        Args:
            user_input: 用户输入
            
        Returns:
            工具调用信息，如果不需要则返回 None
        """
        # 构建工具列表描述
        tools_desc = ""
        for tool in self.available_tools:
            tools_desc += f"- {tool['name']}: {tool['description']}\n"
            if 'parameters' in tool and 'properties' in tool['parameters']:
                props = tool['parameters']['properties']
                for param_name, param_info in props.items():
                    tools_desc += f"  参数 {param_name}: {param_info.get('description', '')}\n"
        
        # 使用 LLM 判断是否需要调用工具
        prompt = f"""你是一个智能助手，需要判断用户请求是否需要调用工具，并提取参数。

可用工具列表:
{tools_desc}

用户请求: {user_input}

请判断：
1. 是否需要调用工具？如果需要，返回工具名称
2. 如果需要，提取所有必需的参数

请以 JSON 格式返回，格式如下：
- 如果不需要工具: {{"use_tool": false}}
- 如果需要工具: {{"use_tool": true, "tool_name": "工具名称", "mcp_server": "order-mcp-server", "parameters": {{"参数名": "参数值"}}}}

只返回 JSON，不要其他文字。"""
        
        try:
            response = Generation.call(
                model=DASHSCOPE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                result_format='message'
            )
            
            if response.status_code == 200:
                result_text = response.output.choices[0].message.content.strip()
                # 尝试解析 JSON（可能包含代码块标记）
                import json
                import re
                
                # 提取 JSON 部分
                json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                    if result_json.get("use_tool"):
                        return {
                            "tool": result_json.get("tool_name"),
                            "mcp_server": result_json.get("mcp_server", "order-mcp-server"),
                            "parameters": result_json.get("parameters", {})
                        }
        except Exception as e:
            print(f"LLM 工具判断失败: {str(e)}")
        
        return None
    
    def chat(self, user_input: str) -> str:
        """
        处理用户输入并返回回复
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI 回复
        """
        # 添加用户输入到历史记录
        self.history.append({
            "role": "user",
            "content": user_input
        })
        
        try:
            # 使用 LLM 判断是否需要调用工具
            tool_call = self._should_use_tool(user_input)
            
            # 如果 LLM 判断失败，尝试简单的关键词匹配
            if not tool_call:
                tool_call = self._extract_tool_call(user_input)
            
            if tool_call:
                # 调用工具
                tool_result = self._invoke_tool(
                    tool_call["tool"],
                    tool_call["mcp_server"],
                    tool_call["parameters"]
                )
                
                # 将工具结果添加到对话历史
                self.history.append({
                    "role": "assistant",
                    "content": f"工具调用结果: {tool_result}"
                })
                
                # 使用 LLM 整合工具结果，生成友好回复
                response = Generation.call(
                    model=DASHSCOPE_MODEL,
                    messages=self.history + [{
                        "role": "user",
                        "content": f"请根据工具调用结果，生成友好的回复给用户。工具结果: {tool_result}"
                    }],
                    temperature=0.7,
                    result_format='message'
                )
                
                if response.status_code == 200:
                    ai_message = response.output.choices[0].message.content
                    self.history.append({
                        "role": "assistant",
                        "content": ai_message
                    })
                    return ai_message
                else:
                    return tool_result  # 如果 LLM 调用失败，直接返回工具结果
            else:
                # 一般性对话，直接使用 LLM 处理
                response = Generation.call(
                    model=DASHSCOPE_MODEL,
                    messages=self.history,
                    temperature=0.7,
                    result_format='message'
                )
                
                if response.status_code == 200:
                    ai_message = response.output.choices[0].message.content
                    self.history.append({
                        "role": "assistant",
                        "content": ai_message
                    })
                    return ai_message
                else:
                    error_msg = f"API 调用失败: {response.message}"
                    print(f"错误: {error_msg}")
                    return "抱歉，处理您的请求时出现了问题，请稍后再试。"
            
        except Exception as e:
            error_msg = f"处理请求时出现错误: {str(e)}"
            print(f"错误: {error_msg}")
            return "抱歉，处理您的请求时出现了问题，请稍后再试。"
    
    def clear_history(self):
        """清空对话历史"""
        self.history = [{
            "role": "system",
            "content": self.system_prompt
        }]
    
    def get_available_tools(self) -> List[Dict]:
        """获取可用工具列表"""
        return self.available_tools.copy()
    
    def start_a2a_server(self, host: str = '0.0.0.0', port: int = 10006, debug: bool = False):
        """
        启动 A2A 服务端，使其他 Agent 可以通过 A2A 协议调用
        
        Args:
            host: 监听地址
            port: 服务端口
            debug: 是否开启调试模式
        """
        # 创建 A2A Server
        a2a_server = A2AServer(agent_name=self.agent_name, port=port)
        
        # 设置处理函数
        def handle_request(data: Dict) -> str:
            """处理 A2A 协议请求"""
            user_input = data.get("input", "")
            # 移除 userId 标签（如果存在）
            if "<userId>" in user_input:
                user_input = user_input.split("<userId>")[0].strip()
            
            # 调用 chat 方法处理
            return self.chat(user_input)
        
        a2a_server.set_handler(handle_request)
        
        print(f"{self.agent_name} A2A Server 启动在 http://{host}:{port}")
        print(f"可用工具: {len(self.available_tools)} 个")
        
        # 启动服务
        a2a_server.run(host=host, debug=debug)
