"""
订单智能体 - 处理订单相关业务
参考原项目的 OrderAgent 设计，支持 A2A 协议和 MCP 工具调用
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


class OrderAgent:
    """订单智能体 - 处理订单相关业务，使用 MCP 工具"""
    
    def __init__(self, user_id: str = "default_user", chat_id: str = "default_chat"):
        """
        初始化订单智能体
        
        Args:
            user_id: 用户ID
            chat_id: 对话ID
        """
        self.agent_name = "order_agent"
        self.description = "云边奶茶铺订单处理智能体，处理订单相关业务，包括下单、查询、修改等"
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
            print(f"[OrderAgent] 从 order-mcp-server 加载了 {len(self.available_tools)} 个工具", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[OrderAgent] 警告: 无法从 order-mcp-server 加载 MCP 工具: {str(e)}", file=sys.stderr, flush=True)
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
你是云边奶茶铺的订单处理智能体，专门负责处理订单相关业务。

{self.description}

{tools_description}

工作流程:
1. 接收用户请求
2. 分析请求类型，判断需要使用哪个工具
3. 调用相应的工具处理请求
4. 整合工具返回的结果，生成友好的回复

约束:
- 只能使用提供的工具处理订单相关请求
- 如果工具不可用，需要告知用户
- 回答要友好、专业，体现云边奶茶铺的品牌形象
- 保护用户隐私，不要泄露其他用户的信息

注意:
- 如果用户想要下单,必须要用户提供userId,只有用户Id存在时才允许下单。
- 如果用户想要查询订单,必须要用户提供userId或者订单号,只能根据具体的用户Id或者订单号去查询相应的订单,绝对不允许查询或操作其他用户订单。
- 如果用户想要修改或删除订单,必须要和用户确认用户ID和订单号,确保用户ID和订单号匹配且唯一后才允许修改或删除订单，一次只允许修改一个订单。
"""
    
    def _extract_tool_call(self, user_input: str) -> Optional[Dict]:
        """
        从用户输入中提取工具调用信息（关键词匹配，作为 LLM 的备选方案）
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            工具调用信息，格式: {"tool": "tool_name", "parameters": {...}}
        """
        import re
        user_input_lower = user_input.lower()
        
        # 检查是否需要调用工具
        if "order-get-order" in user_input_lower or "查询订单" in user_input_lower:
            # 尝试提取订单ID
            order_id_match = re.search(r'ORDER[_\d]+', user_input, re.IGNORECASE)
            if order_id_match:
                return {
                    "tool": "order-get-order",
                    "mcp_server": "order-mcp-server",
                    "parameters": {"orderId": order_id_match.group()}
                }
        
        if "order-create-order" in user_input_lower or "创建订单" in user_input_lower or "下单" in user_input_lower:
            # 从用户输入中提取参数
            # 提取用户ID
            user_id_match = re.search(r'用户ID[是：:]\s*(\d+)', user_input)
            if user_id_match:
                user_id = int(user_id_match.group(1))
            else:
                # 使用当前会话的用户ID
                user_id = int(self.user_id) if isinstance(self.user_id, str) else self.user_id
            
            # 提取产品名称（简单匹配）
            products = ["云边茉莉", "桂花云露", "云雾观音", "珍珠奶茶", "红豆奶茶"]
            found_products = []
            for p in products:
                if p in user_input:
                    found_products.append(p)
            
            # 提取甜度
            sweetness_map = {
                "无糖": "无糖", "微糖": "微糖", "半糖": "半糖",
                "少糖": "少糖", "标准糖": "标准糖"
            }
            sweetness = "标准糖"
            for key in sweetness_map:
                if key in user_input:
                    sweetness = key
                    break
            
            # 提取冰量
            ice_level_map = {
                "热": "热", "温": "温", "去冰": "去冰",
                "少冰": "少冰", "正常冰": "正常冰"
            }
            ice_level = "正常冰"
            for key in ice_level_map:
                if key in user_input:
                    ice_level = key
                    break
            
            # 提取数量
            quantity_match = re.search(r'(\d+)\s*[杯份]', user_input)
            quantity = int(quantity_match.group(1)) if quantity_match else 1
            
            # 统一使用 items 数组格式（支持单个或多个产品）
            if len(found_products) > 0:
                import sys
                items = []
                for product_name in found_products:
                    items.append({
                        "productName": product_name,
                        "sweetness": sweetness,
                        "iceLevel": ice_level,
                        "quantity": quantity
                    })
                print(f"[OrderAgent] 关键词匹配提取订单: userId={user_id}, products={found_products}, items={len(items)}", file=sys.stderr, flush=True)
                return {
                    "tool": "order-create-order",
                    "mcp_server": "order-mcp-server",
                    "parameters": {
                        "userId": user_id,
                        "items": items
                    }
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
        prompt = f"""你是一个订单处理智能体，需要判断用户请求是否需要调用工具，并提取参数。

可用工具列表:
{tools_desc}

用户请求: {user_input}

重要提示:
- 当前用户ID是: {self.user_id}（整数类型）
- 如果工具需要 userId 参数，必须使用整数类型: {self.user_id}
- 从用户输入中提取产品名称、甜度、冰量、数量等信息
- 如果用户输入中包含用户ID，使用用户输入中的ID；否则使用当前会话的用户ID: {self.user_id}
- **创建订单统一使用 order-create-order 工具，支持单个或多个产品**

请判断：
1. 是否需要调用工具？如果需要，返回工具名称
2. 如果需要，提取所有必需的参数（userId 必须是整数类型）

请以 JSON 格式返回，格式如下：
- 如果不需要工具: {{"use_tool": false}}
- 如果需要创建订单: {{"use_tool": true, "tool_name": "order-create-order", "mcp_server": "order-mcp-server", "parameters": {{"userId": {self.user_id}, "items": [{{"productName": "产品名称", "sweetness": "甜度", "iceLevel": "冰量", "quantity": 数量, "remark": "备注"}}], "remark": "订单整体备注"}}}}
  - 如果用户只点一个产品，items 数组包含一个订单项
  - 如果用户点多个产品，items 数组包含多个订单项

注意：
- userId 和 quantity 必须是数字类型，不是字符串
- items 数组中的每个订单项都必须包含 productName, sweetness, iceLevel, quantity

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
                
                # 提取 JSON 部分（支持多行 JSON）
                json_match = re.search(r'\{.*?\}', result_text, re.DOTALL)
                if json_match:
                    try:
                        result_json = json.loads(json_match.group())
                        if result_json.get("use_tool"):
                            tool_info = {
                                "tool": result_json.get("tool_name"),
                                "mcp_server": result_json.get("mcp_server", "order-mcp-server"),
                                "parameters": result_json.get("parameters", {})
                            }
                            # 确保 userId 是整数类型
                            if "userId" in tool_info["parameters"]:
                                userId = tool_info["parameters"]["userId"]
                                if isinstance(userId, str):
                                    tool_info["parameters"]["userId"] = int(userId)
                                elif not isinstance(userId, int):
                                    tool_info["parameters"]["userId"] = int(userId)
                            # 确保 quantity 是整数类型（单产品订单）
                            if "quantity" in tool_info["parameters"]:
                                quantity = tool_info["parameters"]["quantity"]
                                if isinstance(quantity, str):
                                    tool_info["parameters"]["quantity"] = int(quantity)
                                elif not isinstance(quantity, int):
                                    tool_info["parameters"]["quantity"] = int(quantity)
                            
                            # 确保 items 数组中的 quantity 是整数类型（多产品订单）
                            if "items" in tool_info["parameters"] and isinstance(tool_info["parameters"]["items"], list):
                                for item in tool_info["parameters"]["items"]:
                                    if "quantity" in item:
                                        quantity = item["quantity"]
                                        if isinstance(quantity, str):
                                            item["quantity"] = int(quantity)
                                        elif not isinstance(quantity, int):
                                            item["quantity"] = int(quantity)
                            
                            import sys
                            print(f"[OrderAgent] LLM 提取的工具调用: {tool_info}", file=sys.stderr, flush=True)
                            return tool_info
                    except json.JSONDecodeError as e:
                        import sys
                        print(f"[OrderAgent] JSON 解析失败: {e}, 原始文本: {result_text[:200]}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[OrderAgent] LLM 工具判断失败: {str(e)}", file=sys.stderr, flush=True)
        
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
                print(f"[OrderAgent] 检测到工具调用: {tool_call}", file=sys.stderr, flush=True)
                # 调用工具
                tool_result = self._invoke_tool(
                    tool_call["tool"],
                    tool_call["mcp_server"],
                    tool_call["parameters"]
                )
                
                # 将工具结果添加到对话历史
                import sys
                print(f"[OrderAgent] 工具调用结果: {tool_result[:200]}", file=sys.stderr, flush=True)
                
                # 检查工具调用是否成功
                if "失败" in tool_result or "错误" in tool_result or "异常" in tool_result:
                    # 工具调用失败，直接返回错误信息
                    print(f"[OrderAgent] 工具调用失败，返回错误信息", file=sys.stderr, flush=True)
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
                    
                    # 添加到历史记录
                    self.history.append({
                        "role": "assistant",
                        "content": ai_message
                    })
                    
                    return ai_message
                else:
                    error_msg = f"API 调用失败: {response.message}"
                    print(f"[OrderAgent] 错误: {error_msg}", file=sys.stderr, flush=True)
                    return "抱歉，处理您的请求时出现了问题，请稍后再试。"
            
        except Exception as e:
            error_msg = f"处理请求时出现错误: {str(e)}"
            print(f"[OrderAgent] 错误: {error_msg}", file=sys.stderr, flush=True)
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
            # 从 A2A 请求中获取 user_id（如果存在）
            request_user_id = data.get("user_id")
            if request_user_id:
                # 临时更新 user_id（用于本次请求）
                original_user_id = self.user_id
                self.user_id = str(request_user_id)  # 确保是字符串类型
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
