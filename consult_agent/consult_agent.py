"""
咨询智能体 - 处理产品咨询、活动信息和冲泡指导
参考原项目的 ConsultAgent 设计，支持 A2A 协议和 MCP 工具调用
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
import dashscope
from dashscope import Generation
import json
import re

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL
from mcp.client import MCPClient
from service_discovery import ServiceDiscovery
from a2a.server import A2AServer

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class ConsultAgent:
    """咨询智能体 - 处理产品咨询、活动信息和冲泡指导，使用 MCP 工具"""
    
    def __init__(self, agent_name: str = "consult_agent", 
                 description: str = "云边奶茶铺咨询智能体，处理产品咨询、活动信息和冲泡指导",
                 user_id: str = "default_user", 
                 chat_id: str = "default_chat"):
        """
        初始化咨询智能体
        
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
            # 尝试从 consult-mcp-server 获取工具
            tools = self.mcp_client.list_tools("consult-mcp-server")
            self.available_tools = [tool.to_dict() for tool in tools]
            print(f"[ConsultAgent] 从 consult-mcp-server 加载了 {len(self.available_tools)} 个工具", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[ConsultAgent] 警告: 无法从 consult-mcp-server 加载 MCP 工具: {str(e)}", file=sys.stderr, flush=True)
            self.available_tools = []
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tools_description = ""
        if self.available_tools:
            tools_description = "\n可用工具:\n"
            for tool in self.available_tools:
                tools_description += f"- {tool['name']}: {tool['description']}\n"
                if 'parameters' in tool and 'properties' in tool['parameters']:
                    props = tool['parameters']['properties']
                    for param_name, param_info in props.items():
                        tools_description += f"  参数 {param_name}: {param_info.get('description', '')} (类型: {param_info.get('type', 'string')}, 必需: {'required' in tool['parameters'] and param_name in tool['parameters']['required']})\n"
        else:
            tools_description = "\n注意: 当前没有可用的工具，MCP Server 可能未启动。\n"
        
        return f"""角色与职责:
你是云边奶茶铺的咨询智能体，专门负责处理产品咨询、活动信息和冲泡指导。

{self.description}

{tools_description}

工作流程:
1. 接收用户咨询请求
2. 分析请求类型，判断是否需要调用工具获取信息
3. 如果需要，调用相应的工具获取产品信息、活动信息等
4. 整合工具返回的结果，生成友好、专业的回复

约束:
- 优先使用提供的工具获取准确的产品信息
- 如果工具不可用，可以基于已有知识回答，但要告知用户信息可能不完整
- 回答要友好、专业，体现云边奶茶铺的品牌形象
- 对于产品咨询，要详细介绍产品的特点、口感、适合人群等
- 对于活动信息，要准确说明活动内容、时间、参与方式等
- 对于冲泡指导，要提供详细的步骤和注意事项

注意:
- 如果用户询问产品信息，优先使用工具查询准确的产品数据
- 如果用户询问活动信息，可以使用知识库检索工具
- 如果用户询问冲泡方法，可以提供专业的冲泡指导
"""
    
    def _extract_tool_call(self, user_input: str) -> Optional[Dict]:
        """
        从用户输入中提取工具调用信息（关键词匹配，作为 LLM 的备选方案）
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            工具调用信息，格式: {"tool": "tool_name", "parameters": {...}}
        """
        user_input_lower = user_input.lower()
        
        # 检查是否需要调用工具
        if "产品列表" in user_input or "所有产品" in user_input or "有哪些产品" in user_input:
            return {
                "tool": "consult-get-products",
                "mcp_server": "consult-mcp-server",
                "parameters": {}
            }
        
        if "产品信息" in user_input or "产品详情" in user_input:
            # 尝试提取产品名称
            products = ["云边茉莉", "桂花云露", "云雾观音", "红茶拿铁", "抹茶相思"]
            for p in products:
                if p in user_input:
                    return {
                        "tool": "consult-get-product-info",
                        "mcp_server": "consult-mcp-server",
                        "parameters": {"productName": p}
                    }
        
        if "搜索" in user_input or "查找" in user_input:
            # 尝试提取搜索关键词
            for p in products:
                if p in user_input:
                    return {
                        "tool": "consult-search-products",
                        "mcp_server": "consult-mcp-server",
                        "parameters": {"productName": p}
                    }
        
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
            print(f"[DEBUG] 调用工具: {tool_name}, 参数: {parameters}", file=sys.stderr, flush=True)
            result = self.mcp_client.invoke_tool(mcp_server, tool_name, parameters)
            print(f"[DEBUG] 工具调用结果: {result}", file=sys.stderr, flush=True)
            if result.get("status") == "success":
                return str(result.get("result", ""))
            else:
                error_msg = f"工具调用失败: {result.get('error', '未知错误')}"
                print(f"[ERROR] {error_msg}", file=sys.stderr, flush=True)
                return error_msg
        except Exception as e:
            error_msg = f"工具调用异常: {str(e)}"
            print(f"[ERROR] {error_msg}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return error_msg
    
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
                    tools_desc += f"  参数 {param_name}: {param_info.get('description', '')} (类型: {param_info.get('type', 'string')}, 必需: {'required' in tool['parameters'] and param_name in tool['parameters']['required']})\n"
        
        # 使用 LLM 判断是否需要调用工具
        prompt = f"""你是一个咨询智能体，需要判断用户请求是否需要调用工具，并提取参数。

可用工具列表:
{tools_desc}

用户请求: {user_input}

请判断：
1. 是否需要调用工具？如果需要，返回工具名称
2. 如果需要，提取所有必需的参数

请以 JSON 格式返回，格式如下：
- 如果不需要工具: {{"use_tool": false}}
- 如果需要工具: {{"use_tool": true, "tool_name": "工具名称", "mcp_server": "consult-mcp-server", "parameters": {{...}}}}

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
                json_match = re.search(r'\{.*?\}', result_text, re.DOTALL)
                if json_match:
                    try:
                        result_json = json.loads(json_match.group())
                        if result_json.get("use_tool"):
                            tool_info = {
                                "tool": result_json.get("tool_name"),
                                "mcp_server": result_json.get("mcp_server", "consult-mcp-server"),
                                "parameters": result_json.get("parameters", {})
                            }
                            import sys
                            print(f"[ConsultAgent] LLM 提取的工具调用: {tool_info}", file=sys.stderr, flush=True)
                            return tool_info
                    except json.JSONDecodeError as e:
                        import sys
                        print(f"[ConsultAgent] JSON 解析失败: {e}, 原始文本: {result_text[:200]}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[ConsultAgent] LLM 工具判断失败: {str(e)}", file=sys.stderr, flush=True)
        
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
                # 输出到 stderr，确保能看到（即使后台运行）
                import sys
                print(f"[ConsultAgent] 检测到工具调用: {tool_call}", file=sys.stderr, flush=True)
                # 调用工具
                tool_result = self._invoke_tool(
                    tool_call["tool"],
                    tool_call["mcp_server"],
                    tool_call["parameters"]
                )
                
                # 将工具结果添加到对话历史
                import sys
                print(f"[ConsultAgent] 工具调用结果: {tool_result[:200]}", file=sys.stderr, flush=True)
                
                # 检查工具调用是否成功
                if "失败" in tool_result or "错误" in tool_result or "异常" in tool_result:
                    # 工具调用失败，直接返回错误信息
                    print(f"[ConsultAgent] 工具调用失败，返回错误信息", file=sys.stderr, flush=True)
                    self.history.append({
                        "role": "assistant",
                        "content": tool_result
                    })
                    return tool_result
                
                self.history.append({
                    "role": "assistant",
                    "content": f"工具调用结果: {tool_result}"
                })
                
                # 使用 LLM 整合工具结果，生成友好回复
                response = Generation.call(
                    model=DASHSCOPE_MODEL,
                    messages=self.history + [{
                        "role": "user",
                        "content": f"请根据工具调用结果，生成友好、专业的咨询回复给用户。工具结果: {tool_result}"
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
                    
                    # 添加到历史记录
                    self.history.append({
                        "role": "assistant",
                        "content": ai_message
                    })
                    
                    return ai_message
                else:
                    error_msg = f"API 调用失败: {response.message}"
                    print(f"[ConsultAgent] 错误: {error_msg}", file=sys.stderr, flush=True)
                    return "抱歉，处理您的请求时出现了问题，请稍后再试。"
                
        except Exception as e:
            error_msg = f"处理请求时出现错误: {str(e)}"
            print(f"[ConsultAgent] 错误: {error_msg}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
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
    
    def start_a2a_server(self, host: str = '0.0.0.0', port: int = 10005, debug: bool = False):
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
            # 从 A2A 请求中获取 user_id（如果存在）
            request_user_id = data.get("user_id")
            if request_user_id:
                # 临时更新 user_id（用于本次请求）
                original_user_id = self.user_id
                self.user_id = str(request_user_id)
                try:
                    # 调用 chat 方法处理
                    result = self.chat(user_input)
                    return result
                finally:
                    # 恢复原始 user_id
                    self.user_id = original_user_id
            else:
                # 如果没有提供 user_id，使用默认值
                return self.chat(user_input)
        
        a2a_server.set_handler(handle_request)
        
        print(f"{self.agent_name} A2A Server 启动在 http://{host}:{port}", file=sys.stderr, flush=True)
        print(f"可用工具: {len(self.available_tools)} 个", file=sys.stderr, flush=True)
        
        # 启动服务
        a2a_server.run(host=host, debug=debug)
