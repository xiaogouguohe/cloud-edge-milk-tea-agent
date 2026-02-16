"""
订单智能体 - 处理订单相关业务
参考原项目的 OrderAgent 设计，支持 A2A 协议和 MCP 工具调用
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
import dashscope
from dashscope import Generation
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL
from mcp.client import MCPClient
from service_discovery import ServiceDiscovery
from a2a.server import A2AServer
from order_agent.skills import SKILLS_BY_ROLE

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class OrderAgent:
    """订单智能体 - 处理订单相关业务，使用 MCP 工具"""
    
    def __init__(self):
        """
        初始化订单智能体 (无状态设计)
        """
        self.agent_name = "order_agent"
        self.description = "云边奶茶铺订单处理智能体，处理订单相关业务，包括下单、查询、修改等"
        
        # MCP 客户端（用于调用订单工具）
        self.mcp_client = MCPClient()
        self.service_discovery = ServiceDiscovery(method="config")
        
        # 基础系统提示词模板
        self.base_system_prompt = """角色与职责:
你是云边奶茶铺的订单处理智能体，专门负责处理订单相关业务。

{description}

工作流程:
1. 接收用户请求。
2. 检查下单所需的必要信息：
   - 如果用户想要下单但缺少【冰度】或【糖度】，请礼貌地追问用户。
   - 支持用户在后续对话中直接补充信息（如只说“半糖”），请结合历史对话完成下单。
3. 如果信息齐全，请调用相应的工具 (Skills)。
4. 整合工具返回的结果，生成友好的回复。

约束:
- 必须收集齐所有必填参数（产品名、冰度、糖度）后才能调用下单工具。
- 回答要友好、专业，体现云边奶茶铺的品牌形象。
- 保护用户隐私，不要泄露其他用户的信息

注意:
- 必须严格遵守传入的 userId 约束，不得越权操作他人数据。
"""

    def _invoke_tool(self, tool_name: str, mcp_server: str, parameters: Dict) -> str:
        """调用工具"""
        try:
            print(f"[DEBUG] 调用工具: {tool_name}, 参数: {parameters}", file=sys.stderr, flush=True)
            result = self.mcp_client.invoke_tool(mcp_server, tool_name, parameters)
            if result.get("status") == "success":
                return str(result.get("result", ""))
            else:
                return f"工具调用失败: {result.get('error', '未知错误')}"
        except Exception as e:
            return f"工具调用异常: {str(e)}"

    def chat(self, user_input: str, user_id: str, role: str = "customer", history: List[Dict] = None) -> Dict:
        """
        处理用户输入并返回回复（请求级无状态实现）
        """
        # 1. 确定本次请求的权限和技能
        current_role = role if role in SKILLS_BY_ROLE else "customer"
        current_skills = SKILLS_BY_ROLE[current_role]
        
        # 2. 构建本次请求的上下文
        system_content = self.base_system_prompt.format(description=self.description)
        system_content += f"\n当前操作上下文: 用户ID={user_id}, 角色={current_role}"
        
        messages = [{"role": "system", "content": system_content}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})
        
        try:
            # 3. 调用 LLM
            response = Generation.call(
                model=DASHSCOPE_MODEL,
                messages=messages,
                tools=current_skills,
                result_format='message'
            )
            
            if response.status_code != 200:
                return {"output": "抱歉，系统繁忙，请稍后再试。", "history": messages}

            # 打印响应结构以便调试
            # print(f"[DEBUG] LLM Response: {response}", file=sys.stderr)

            message = response.output.choices[0].message
            
            # 4. 处理工具调用
            # 兼容不同版本的 DashScope SDK 返回结构
            tool_calls = None
            try:
                if hasattr(message, 'tool_calls'):
                    tool_calls = message.tool_calls
                elif isinstance(message, dict) and 'tool_calls' in message:
                    tool_calls = message['tool_calls']
                elif hasattr(message, 'get') and message.get('tool_calls'):
                    tool_calls = message.get('tool_calls')
            except Exception:
                tool_calls = None

            if tool_calls:
                messages.append(message)
                
                for tool_call in tool_calls:
                    # 兼容处理：DashScope 返回的可能是对象也可能是字典
                    if isinstance(tool_call, dict):
                        skill_name = tool_call.get("function", {}).get("name")
                        tool_call_id = tool_call.get("id")
                        arguments_str = tool_call.get("function", {}).get("arguments")
                    else:
                        # 增加对对象属性的防御性获取
                        function_attr = getattr(tool_call, 'function', None)
                        skill_name = getattr(function_attr, 'name', None) if function_attr else None
                        tool_call_id = getattr(tool_call, 'id', None)
                        arguments_str = getattr(function_attr, 'arguments', None) if function_attr else None
                    
                    if not skill_name:
                        continue
                    
                    # 权限校验
                    allowed_skill_names = [s['function']['name'] for s in current_skills]
                    if skill_name not in allowed_skill_names:
                        content = f"权限拒绝：角色 {current_role} 无权调用 {skill_name}"
                        messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": skill_name, "content": content})
                        continue

                    try:
                        arguments = json.loads(arguments_str)
                        
                        # 数据级越权校验
                        if current_role == "customer":
                            if "userId" in arguments and str(arguments["userId"]) != str(user_id):
                                content = f"安全警告：您无权操作用户 {arguments['userId']} 的数据。"
                                messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": skill_name, "content": content})
                                continue
                            if "userId" in arguments:
                                arguments["userId"] = int(user_id)

                        # 执行工具 (统一调用 order-mcp-server)
                        mcp_tool_name = skill_name.replace("_", "-")
                        tool_result = self._invoke_tool(mcp_tool_name, "order-mcp-server", arguments)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": skill_name,
                            "content": tool_result
                        })
                        
                    except Exception as e:
                        messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": skill_name, "content": f"错误: {str(e)}"})

                # 5. 生成最终回复
                final_response = Generation.call(model=DASHSCOPE_MODEL, messages=messages, result_format='message')
                if final_response.status_code == 200:
                    final_msg = final_response.output.choices[0].message
                    messages.append(final_msg)
                    return {"output": final_msg.content, "history": messages}
                else:
                    return {"output": "工具已执行，但回复生成失败。", "history": messages}
            
            else:
                messages.append(message)
                return {"output": message.content, "history": messages}
            
        except Exception as e:
            # 打印详细堆栈以便排查
            import traceback
            traceback.print_exc(file=sys.stderr)
            print(f"[OrderAgent] 异常: {str(e)}", file=sys.stderr)
            return {"output": "处理请求时出错。", "history": messages}

    def start_a2a_server(self, host: str = '0.0.0.0', port: int = 10006):
        """启动 A2A 服务端"""
        a2a_server = A2AServer(agent_name=self.agent_name, port=port)
        sessions = {}

        def handle_request(data: Dict) -> str:
            user_input = data.get("input", "")
            user_id = str(data.get("user_id", "unknown"))
            role = data.get("role", "customer")
            chat_id = data.get("chat_id", "default")
            
            session_key = f"{user_id}_{chat_id}"
            history = sessions.get(session_key, [])
            
            result = self.chat(user_input, user_id, role, history)
            sessions[session_key] = result["history"][-20:]
            
            return result["output"]
        
        a2a_server.set_handler(handle_request)
        print(f"{self.agent_name} A2A Server (Stateless) 启动在 http://{host}:{port}", file=sys.stderr, flush=True)
        a2a_server.run(host=host)
