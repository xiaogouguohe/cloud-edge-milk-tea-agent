"""
订单智能体 - 处理订单相关业务
参考原项目的 OrderAgent 设计，支持 A2A 协议和 MCP 工具调用

注意：使用 OpenAI 兼容接口 (chat/completions) 而非 DashScope 原生 Generation API，
以确保 tools 参数正确传递、模型返回 tool_calls 结构而非将工具调用写在 content 文本中。
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import dashscope
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL
from dashscope.aigc.chat_completion import Completions
from mcp.client import MCPClient
from service_discovery import ServiceDiscovery
from a2a.server import A2AServer
from order_agent.skills import SKILLS_BY_ROLE

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY

# 兼容旧版 dashscope：Completions 需要 base_compatible_api_url，部分版本未导出
if not hasattr(dashscope, "base_compatible_api_url"):
    dashscope.base_compatible_api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _message_to_dict(msg) -> Dict:
    """将 ChatCompletionMessage 转为 API 所需的 dict 格式，便于追加到 messages 并再次请求"""
    if isinstance(msg, dict):
        return msg
    content = getattr(msg, "content", None) or ""
    out = {"role": "assistant", "content": content}
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        out["tool_calls"] = []
        for tc in tool_calls:
            if isinstance(tc, dict):
                out["tool_calls"].append(tc)
            else:
                fn = getattr(tc, "function", None)
                out["tool_calls"].append({
                    "id": getattr(tc, "id", ""),
                    "type": "function",
                    "function": {
                        "name": getattr(fn, "name", ""),
                        "arguments": getattr(fn, "arguments", ""),
                    },
                })
    return out


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
3. 如果信息齐全（产品名、糖度、冰度、数量），必须调用 order_create_order 工具，不得跳过或编造结果。同一产品若糖度或冰量不同（如「一杯少糖去冰、一杯标准糖少冰」），需拆成多条 items，每条对应一种规格。
4. 当用户询问「我的订单」「订单记录」「历史订单」时，调用 order_get_orders_by_user 工具查询。
5. 整合工具返回的结果，生成友好的回复。回复中的订单信息必须来自工具返回，不得虚构。

约束:
- 必须收集齐所有必填参数（产品名、冰度、糖度）后才能调用下单工具。
- 回答要友好、专业，体现云边奶茶铺的品牌形象。
- 保护用户隐私，不要泄露其他用户的信息。
- 当工具返回「创建订单失败」或包含「库存不足」「售罄」「缺货」时，请将具体原因如实告知用户，不要用「格式异常」等模糊表述替代。
- 【重要】对于下单请求，必须调用 order_create_order 工具获取真实结果，不得自行编造订单号或订单状态。订单号格式为 ORDER_ 开头的数字时间戳。

注意:
- 必须严格遵守传入的 userId 约束，不得越权操作他人数据。
"""

    def _try_parse_order_tool_from_content(self, content: str) -> Optional[Tuple[str, Dict]]:
        """
        当 LLM 将工具调用以文本形式输出时，尝试解析并转换为标准参数。
        返回 (skill_name, arguments) 或 None
        """
        if not content or "order_create_order" not in content or '"arguments"' not in content:
            return None
        # 查找 "arguments": 后的 JSON 对象（支持嵌套大括号）
        idx = content.find('"arguments"')
        if idx < 0:
            return None
        start = content.find("{", idx)
        if start < 0:
            return None
        depth = 0
        for i in range(start, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        args = json.loads(content[start : i + 1])
                        # 兼容 sugarLevel -> sweetness，并转换为 items 数组格式
                        if "items" not in args:
                            sweetness = args.get("sweetness") or args.get("sugarLevel", "标准糖")
                            args = {
                                "userId": int(args.get("userId", 0)),
                                "items": [{
                                    "productName": args.get("productName", ""),
                                    "sweetness": sweetness,
                                    "iceLevel": args.get("iceLevel", "正常冰"),
                                    "quantity": int(args.get("quantity", 1))
                                }]
                            }
                        return ("order_create_order", args)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        return None
        return None

    def _normalize_order_args(self, arguments: Dict) -> Dict:
        """
        将 LLM 可能输出的扁平格式转为 MCP 期望的 items 数组格式。
        例如 {"userId": 1, "productName": "x", "sweetness": "半糖", "iceLevel": "去冰", "quantity": 2}
        -> {"userId": 1, "items": [{"productName": "x", "sweetness": "半糖", "iceLevel": "去冰", "quantity": 2}]}
        """
        if "items" in arguments and isinstance(arguments.get("items"), list):
            return arguments
        if "productName" in arguments:
            sweetness = arguments.get("sweetness") or arguments.get("sugarLevel", "标准糖")
            return {
                "userId": int(arguments.get("userId", 0)),
                "items": [{
                    "productName": arguments.get("productName", ""),
                    "sweetness": sweetness,
                    "iceLevel": arguments.get("iceLevel", "正常冰"),
                    "quantity": int(arguments.get("quantity", 1)),
                }],
            }
        return arguments

    def _invoke_tool(self, tool_name: str, mcp_server: str, parameters: Dict) -> str:
        """调用工具"""
        try:
            print(f"[OrderAgent] 调用工具: {tool_name}, 参数: {parameters}", file=sys.stderr, flush=True)
            result = self.mcp_client.invoke_tool(mcp_server, tool_name, parameters)
            if result.get("status") == "success":
                tool_result = str(result.get("result", ""))
                print(f"[OrderAgent] 工具返回(成功): {tool_result[:200]}...", file=sys.stderr, flush=True)
                return tool_result
            else:
                err_msg = f"工具调用失败: {result.get('error', '未知错误')}"
                print(f"[OrderAgent] 工具返回(失败): {err_msg}", file=sys.stderr, flush=True)
                return err_msg
        except Exception as e:
            err_msg = f"工具调用异常: {str(e)}"
            print(f"[OrderAgent] 工具异常: {err_msg}", file=sys.stderr, flush=True)
            return err_msg

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
            # 3. 调用 LLM（使用 OpenAI 兼容接口，确保 tools 正确传递、返回 tool_calls 结构）
            completion = Completions.create(
                model=DASHSCOPE_MODEL,
                messages=messages,
                extra_body={"tools": current_skills},
            )
            
            if getattr(completion, "status_code", 200) != 200:
                return {"output": "抱歉，系统繁忙，请稍后再试。", "history": messages}

            message = completion.choices[0].message
            
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
                messages.append(_message_to_dict(message))
                
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

                        # 参数规范化：LLM 可能输出扁平格式，需转为 items 数组
                        if skill_name == "order_create_order":
                            arguments = self._normalize_order_args(arguments)

                        # 执行工具 (统一调用 order-mcp-server)
                        mcp_tool_name = skill_name.replace("_", "-")
                        tool_result = self._invoke_tool(mcp_tool_name, "order-mcp-server", arguments)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": skill_name,
                            "content": tool_result
                        })
                        
                        # 库存不足等业务错误：直接告知用户，避免 LLM 改写为模糊表述
                        is_stock_error = skill_name == "order_create_order" and any(
                            kw in tool_result for kw in ["库存不足", "售罄", "缺货"]
                        )
                        if is_stock_error:
                            print(f"[OrderAgent] 检测到库存不足，直接返回: {tool_result[:100]}...", file=sys.stderr, flush=True)
                            return {"output": tool_result, "history": messages}
                        
                    except Exception as e:
                        messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": skill_name, "content": f"错误: {str(e)}"})

                # 5. 生成最终回复
                print(f"[OrderAgent] 工具执行完成，调用 LLM 生成最终回复", file=sys.stderr, flush=True)
                final_completion = Completions.create(
                    model=DASHSCOPE_MODEL,
                    messages=messages,
                    extra_body={"tools": current_skills},
                )
                if getattr(final_completion, "status_code", 200) == 200:
                    final_msg = final_completion.choices[0].message
                    output = final_msg.content or ""
                    print(f"[OrderAgent] 最终回复: {output[:150]}...", file=sys.stderr, flush=True)
                    messages.append(_message_to_dict(final_msg))
                    return {"output": output, "history": messages}
                else:
                    return {"output": "工具已执行，但回复生成失败。", "history": messages}
            
            else:
                # 回退：LLM 可能将工具调用以文本形式输出，尝试解析并执行
                print(f"[OrderAgent] 无 tool_calls，尝试从 content 解析工具调用", file=sys.stderr, flush=True)
                content = getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else "")
                parsed = self._try_parse_order_tool_from_content(str(content or ""))
                if parsed and "order_create_order" in [s["function"]["name"] for s in current_skills]:
                    skill_name, arguments = parsed
                    if current_role == "customer":
                        arguments["userId"] = int(user_id)
                    try:
                        mcp_tool_name = skill_name.replace("_", "-")
                        tool_result = self._invoke_tool(mcp_tool_name, "order-mcp-server", arguments)
                        if any(kw in tool_result for kw in ["库存不足", "售罄", "缺货"]):
                            print(f"[OrderAgent] 文本解析回退: 检测到库存不足，直接返回", file=sys.stderr, flush=True)
                            return {"output": tool_result, "history": messages}
                        # 成功则让 LLM 生成友好回复
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": f"[工具执行结果]\n{tool_result}\n请根据以上结果生成对用户的友好回复。"})
                        final = Completions.create(model=DASHSCOPE_MODEL, messages=messages)
                        if getattr(final, "status_code", 200) == 200:
                            return {"output": final.choices[0].message.content or "", "history": messages}
                        return {"output": tool_result, "history": messages}
                    except Exception as e:
                        return {"output": f"工具调用异常: {str(e)}", "history": messages}
                messages.append(_message_to_dict(message))
                return {"output": getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else "") or "", "history": messages}
            
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
