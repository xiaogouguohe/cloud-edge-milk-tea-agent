"""
反馈智能体 - 处理用户反馈、投诉和差评
参考原项目的 FeedbackAgent 设计，支持 A2A 协议和 MCP 工具调用
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


class FeedbackAgent:
    """反馈智能体 - 处理用户反馈、投诉和差评，使用 MCP 工具"""
    
    def __init__(self, user_id: str = "default_user", chat_id: str = "default_chat"):
        """
        初始化反馈智能体
        
        Args:
            user_id: 用户ID
            chat_id: 对话ID
        """
        self.agent_name = "feedback_agent"
        self.description = "云边奶茶铺反馈智能体，处理用户反馈、投诉和差评，支持从反馈中提取和记录用户偏好"
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
            # 尝试从 feedback-mcp-server 获取工具
            tools = self.mcp_client.list_tools("feedback-mcp-server")
            self.available_tools = [tool.to_dict() for tool in tools]
            print(f"[FeedbackAgent] 从 feedback-mcp-server 加载了 {len(self.available_tools)} 个工具", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[FeedbackAgent] 警告: 无法从 feedback-mcp-server 加载 MCP 工具: {str(e)}", file=sys.stderr, flush=True)
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
你是云边奶茶铺的反馈处理智能体，专门负责处理用户反馈、投诉和差评。

{self.description}

{tools_description}

工作流程:
1. 接收用户反馈请求
2. 分析反馈类型（产品反馈、服务反馈、投诉、建议）
3. 从用户输入中提取反馈内容、评分等信息
4. 调用相应的工具记录反馈
5. 整合工具返回的结果，生成友好的回复

反馈类型说明:
- 1: 产品反馈 - 关于产品本身的问题或建议
- 2: 服务反馈 - 关于服务质量的问题或建议
- 3: 投诉 - 用户不满意的投诉
- 4: 建议 - 用户的改进建议

约束:
- 只能使用提供的工具处理反馈相关请求
- 如果工具不可用，需要告知用户
- 回答要友好、专业，体现云边奶茶铺的品牌形象
- 保护用户隐私，不要泄露其他用户的信息
- 对于投诉，要表达歉意并承诺改进
- 对于建议，要表示感谢并说明会考虑

注意:
- 如果用户想要提交反馈,必须要用户提供userId,只有用户Id存在时才允许提交反馈。
- 如果用户想要查询反馈,必须要用户提供userId或者订单号,只能根据具体的用户Id或者订单号去查询相应的反馈,绝对不允许查询或操作其他用户反馈。
- 从用户输入中自动识别反馈类型，如果用户明确说明是"投诉"或"不满"，使用类型3；如果是"建议"或"希望"，使用类型4；如果是关于产品的，使用类型1；如果是关于服务的，使用类型2。
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
        
        # 检查是否需要创建反馈
        if "反馈" in user_input or "投诉" in user_input or "建议" in user_input or "差评" in user_input:
            # 提取用户ID
            user_id_match = re.search(r'用户ID[是：:]\s*(\d+)', user_input)
            if user_id_match:
                user_id = int(user_id_match.group(1))
            else:
                # 使用当前会话的用户ID
                user_id = int(self.user_id) if isinstance(self.user_id, str) else self.user_id
            
            # 判断反馈类型
            feedback_type = 4  # 默认建议
            if "投诉" in user_input or "不满" in user_input or "差评" in user_input:
                feedback_type = 3  # 投诉
            elif "产品" in user_input:
                feedback_type = 1  # 产品反馈
            elif "服务" in user_input:
                feedback_type = 2  # 服务反馈
            
            # 提取订单ID
            order_id_match = re.search(r'ORDER[_\d]+', user_input, re.IGNORECASE)
            order_id = order_id_match.group() if order_id_match else None
            
            # 提取评分
            rating_match = re.search(r'(\d+)\s*[星分]', user_input)
            rating = int(rating_match.group(1)) if rating_match else None
            
            # 提取反馈内容（简单处理，取用户输入的主要部分）
            content = user_input.strip()
            
            import sys
            print(f"[FeedbackAgent] 关键词匹配提取参数: userId={user_id}, feedbackType={feedback_type}", file=sys.stderr, flush=True)
            return {
                "tool": "feedback-create-feedback",
                "mcp_server": "feedback-mcp-server",
                "parameters": {
                    "userId": user_id,
                    "feedbackType": feedback_type,
                    "content": content,
                    "orderId": order_id,
                    "rating": rating
                }
            }
        
        # 检查是否需要查询反馈
        if "查询反馈" in user_input or "查看反馈" in user_input or "我的反馈" in user_input:
            # 提取用户ID
            user_id_match = re.search(r'用户ID[是：:]\s*(\d+)', user_input)
            if user_id_match:
                user_id = int(user_id_match.group(1))
            else:
                user_id = int(self.user_id) if isinstance(self.user_id, str) else self.user_id
            
            import sys
            print(f"[FeedbackAgent] 关键词匹配查询反馈: userId={user_id}", file=sys.stderr, flush=True)
            return {
                "tool": "feedback-get-feedback-by-user",
                "mcp_server": "feedback-mcp-server",
                "parameters": {"userId": user_id}
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
        prompt = f"""你是一个反馈处理智能体，需要判断用户请求是否需要调用工具，并提取参数。

可用工具列表:
{tools_desc}

用户请求: {user_input}

重要提示:
- 当前用户ID是: {self.user_id}（整数类型）
- 如果工具需要 userId 参数，必须使用整数类型: {self.user_id}
- 反馈类型：1-产品反馈，2-服务反馈，3-投诉，4-建议
- 从用户输入中识别反馈类型：如果用户明确说明是"投诉"或"不满"，使用类型3；如果是"建议"或"希望"，使用类型4；如果是关于产品的，使用类型1；如果是关于服务的，使用类型2
- 如果用户输入中包含用户ID，使用用户输入中的ID；否则使用当前会话的用户ID: {self.user_id}
- 如果用户提到订单号（ORDER_开头），提取为 orderId 参数

请判断：
1. 是否需要调用工具？如果需要，返回工具名称
2. 如果需要，提取所有必需的参数（userId 必须是整数类型，feedbackType 必须是 1-4 之间的整数）

请以 JSON 格式返回，格式如下：
- 如果不需要工具: {{"use_tool": false}}
- 如果需要工具: {{"use_tool": true, "tool_name": "工具名称", "mcp_server": "feedback-mcp-server", "parameters": {{"userId": {self.user_id}, "feedbackType": 反馈类型, "content": "反馈内容", "orderId": "订单ID", "rating": 评分}}}}

注意：userId、feedbackType 和 rating 必须是数字类型，不是字符串。

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
                                "mcp_server": result_json.get("mcp_server", "feedback-mcp-server"),
                                "parameters": result_json.get("parameters", {})
                            }
                            # 确保 userId 是整数类型
                            if "userId" in tool_info["parameters"]:
                                userId = tool_info["parameters"]["userId"]
                                if isinstance(userId, str):
                                    tool_info["parameters"]["userId"] = int(userId)
                                elif not isinstance(userId, int):
                                    tool_info["parameters"]["userId"] = int(userId)
                            # 确保 feedbackType 是整数类型
                            if "feedbackType" in tool_info["parameters"]:
                                feedback_type = tool_info["parameters"]["feedbackType"]
                                if isinstance(feedback_type, str):
                                    tool_info["parameters"]["feedbackType"] = int(feedback_type)
                                elif not isinstance(feedback_type, int):
                                    tool_info["parameters"]["feedbackType"] = int(feedback_type)
                            # 确保 rating 是整数类型（如果存在）
                            if "rating" in tool_info["parameters"] and tool_info["parameters"]["rating"] is not None:
                                rating = tool_info["parameters"]["rating"]
                                if isinstance(rating, str):
                                    tool_info["parameters"]["rating"] = int(rating)
                                elif not isinstance(rating, int):
                                    tool_info["parameters"]["rating"] = int(rating)
                            
                            import sys
                            print(f"[FeedbackAgent] LLM 提取的工具调用: {tool_info}", file=sys.stderr, flush=True)
                            return tool_info
                    except json.JSONDecodeError as e:
                        import sys
                        print(f"[FeedbackAgent] JSON 解析失败: {e}, 原始文本: {result_text[:200]}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[FeedbackAgent] LLM 工具判断失败: {str(e)}", file=sys.stderr, flush=True)
        
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
                print(f"[FeedbackAgent] 检测到工具调用: {tool_call}", file=sys.stderr, flush=True)
                # 调用工具
                tool_result = self._invoke_tool(
                    tool_call["tool"],
                    tool_call["mcp_server"],
                    tool_call["parameters"]
                )
                
                # 将工具结果添加到对话历史
                import sys
                print(f"[FeedbackAgent] 工具调用结果: {tool_result[:200]}", file=sys.stderr, flush=True)
                
                # 检查工具调用是否成功
                if "失败" in tool_result or "错误" in tool_result or "异常" in tool_result:
                    # 工具调用失败，直接返回错误信息
                    print(f"[FeedbackAgent] 工具调用失败，返回错误信息", file=sys.stderr, flush=True)
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
                    return "抱歉，我暂时无法处理您的请求，请稍后再试。"
        except Exception as e:
            import traceback
            error_msg = f"处理请求时发生错误: {str(e)}"
            print(f"[FeedbackAgent] {error_msg}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            return error_msg
    
    def get_available_tools(self) -> List[Dict]:
        """获取可用工具列表"""
        return self.available_tools
    
    def start_a2a_server(self, host: str = "0.0.0.0", port: int = 10007, debug: bool = False):
        """
        启动 A2A 服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            debug: 是否开启调试模式
        """
        print(f"[FeedbackAgent] 启动 A2A 服务器，端口: {port}")
        
        # 创建 A2A Server
        a2a_server = A2AServer(
            agent_name=self.agent_name,
            agent_description=self.description,
            host=host,
            port=port
        )
        
        # 注册处理函数
        def handle_a2a_request(request: Dict) -> Dict:
            """处理 A2A 请求"""
            user_input = request.get("input", "")
            chat_id = request.get("chat_id", self.chat_id)
            user_id = request.get("user_id", self.user_id)
            
            # 更新会话信息
            self.chat_id = chat_id
            self.user_id = user_id
            
            # 处理用户输入
            output = self.chat(user_input)
            
            return {
                "output": output,
                "status": "success"
            }
        
        a2a_server.register_handler(handle_a2a_request)
        
        # 启动服务器
        a2a_server.start(debug=debug)

