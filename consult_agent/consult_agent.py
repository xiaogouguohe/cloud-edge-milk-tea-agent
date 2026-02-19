"""
咨询智能体 - 处理产品咨询、活动信息和冲泡指导
参考 order_agent 设计，使用 skills 定义工具，通过 OpenAI 兼容接口调用 LLM
"""
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import dashscope

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL
from dashscope.aigc.chat_completion import Completions
from mcp.client import MCPClient
from service_discovery import ServiceDiscovery
from a2a.server import A2AServer
from consult_agent.skills import CONSULT_SKILLS

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY

# 兼容旧版 dashscope：Completions 需要 base_compatible_api_url
if not hasattr(dashscope, "base_compatible_api_url"):
    dashscope.base_compatible_api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _message_to_dict(msg) -> Dict:
    """将 ChatCompletionMessage 转为 API 所需的 dict 格式"""
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


class ConsultAgent:
    """咨询智能体 - 处理产品咨询、活动信息和冲泡指导，使用 skills 定义工具"""
    
    def __init__(self, agent_name: str = "consult_agent", 
                 description: str = "云边奶茶铺咨询智能体，处理产品咨询、活动信息和冲泡指导",
                 user_id: str = "default_user", 
                 chat_id: str = "default_chat"):
        self.agent_name = agent_name
        self.description = description
        self.user_id = user_id
        self.chat_id = chat_id
        self.history: List[Dict[str, str]] = []
        
        self.mcp_client = MCPClient()
        self.service_discovery = ServiceDiscovery(method="config")
        
        self.system_prompt = f"""角色与职责:
你是云边奶茶铺的咨询智能体，专门负责处理产品咨询、活动信息和冲泡指导。

{self.description}

工作流程:
1. 接收用户咨询请求
2. 分析请求类型，判断是否需要调用工具获取信息
3. 如果需要，调用相应的工具获取产品信息、活动信息等
4. 整合工具返回的结果，生成友好、专业的回复

约束:
- 优先使用提供的工具获取准确的产品信息
- 回答要友好、专业，体现云边奶茶铺的品牌形象
- 对于产品咨询，要详细介绍产品的特点、口感、适合人群等
- 对于活动信息，要准确说明活动内容、时间、参与方式等
- 对于冲泡指导，要提供详细的步骤和注意事项

注意:
- 如果用户询问产品信息，优先使用工具查询准确的产品数据
- 如果用户询问活动信息，可以使用知识库检索工具
- 如果用户询问冲泡方法，可以提供专业的冲泡指导
"""
        
        self.history.append({"role": "system", "content": self.system_prompt})
    
    def _invoke_tool(self, tool_name: str, mcp_server: str, parameters: Dict, req_id: Optional[str] = None) -> str:
        """调用 MCP 工具"""
        t0 = time.perf_counter()
        try:
            print(f"[ConsultAgent] 调用工具: {tool_name}, 参数: {parameters}", file=sys.stderr, flush=True)
            result = self.mcp_client.invoke_tool(mcp_server, tool_name, parameters, req_id=req_id)
            duration_ms = int((time.perf_counter() - t0) * 1000)
            if result.get("status") == "success":
                tool_result = str(result.get("result", ""))
                print(f"[ConsultAgent] 工具返回(成功): {tool_result[:200]}...", file=sys.stderr, flush=True)
                return tool_result
            else:
                error_msg = f"工具调用失败: {result.get('error', '未知错误')}"
                print(f"[ConsultAgent] 工具返回(失败): {error_msg}", file=sys.stderr, flush=True)
                return error_msg
        except Exception as e:
            error_msg = f"工具调用异常: {str(e)}"
            print(f"[ConsultAgent] 工具异常: {error_msg}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return error_msg
    
    def _should_use_tot_recommendation(self, user_input: str) -> bool:
        """判断是否应该使用 ToT 推荐功能"""
        tot_keywords = [
            "适合我", "推荐", "个性化", "根据", "帮我选", "帮我挑",
            "不知道选什么", "选择困难", "推荐一下", "有什么好"
        ]
        return any(keyword in user_input.lower() for keyword in tot_keywords)
    
    def chat(self, user_input: str, req_id: Optional[str] = None) -> str:
        """
        处理用户输入并返回回复
        
        Args:
            user_input: 用户输入
            req_id: 请求追踪 ID
            
        Returns:
            AI 回复
        """
        self.history.append({"role": "user", "content": user_input})
        
        try:
            # 1. ToT 推荐优先（个性化推荐场景）
            if self._should_use_tot_recommendation(user_input):
                try:
                    tot_module_path = Path(__file__).parent / "tot_recommendation.py"
                    if tot_module_path.exists():
                        from consult_agent.tot_recommendation import ToTRecommendationEngine
                        from consult_mcp_server.consult_service import ConsultService
                        
                        consult_service = ConsultService()
                        engine = ToTRecommendationEngine(consult_service=consult_service)
                        best_node = engine.search(user_input)
                        
                        if best_node and best_node.products:
                            recommendation = engine.format_recommendation(best_node)
                            self.history.append({"role": "assistant", "content": recommendation})
                            return recommendation
                except Exception as e:
                    print(f"[ConsultAgent] ToT 推荐失败: {str(e)}", file=sys.stderr, flush=True)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
            
            # 2. 构建本次请求的 messages（不含 system，Completions 会单独处理）
            messages = []
            for msg in self.history:
                if msg.get("role") == "system":
                    continue
                messages.append({"role": msg["role"], "content": msg.get("content", "")})
            
            # 确保最后一条是 user
            if not messages or messages[-1].get("role") != "user":
                messages.append({"role": "user", "content": user_input})
            
            # 3. 调用 LLM（带 tools）
            t0 = time.perf_counter()
            try:
                completion = Completions.create(
                    model=DASHSCOPE_MODEL,
                    messages=[{"role": "system", "content": self.system_prompt}] + messages,
                    extra_body={"tools": CONSULT_SKILLS},
                )
            except Exception as e:
                print(f"[ConsultAgent] LLM 调用失败: {str(e)}", file=sys.stderr, flush=True)
                return "抱歉，处理您的请求时出现了问题，请稍后再试。"
            
            if getattr(completion, "status_code", 200) != 200:
                return "抱歉，系统繁忙，请稍后再试。"
            
            message = completion.choices[0].message
            
            # 4. 处理工具调用
            tool_calls = None
            if hasattr(message, 'tool_calls'):
                tool_calls = message.tool_calls
            elif isinstance(message, dict) and 'tool_calls' in message:
                tool_calls = message['tool_calls']
            elif hasattr(message, 'get') and message.get('tool_calls'):
                tool_calls = message.get('tool_calls')
            
            if tool_calls:
                # 追加 assistant 消息（含 tool_calls）
                assistant_msg = _message_to_dict(message)
                messages.append(assistant_msg)
                
                # 执行每个工具调用
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict):
                        skill_name = tool_call.get("function", {}).get("name")
                        tool_call_id = tool_call.get("id", "")
                        arguments_str = tool_call.get("function", {}).get("arguments", "{}")
                    else:
                        fn = getattr(tool_call, "function", None)
                        skill_name = getattr(fn, "name", None) if fn else None
                        tool_call_id = getattr(tool_call, "id", "")
                        arguments_str = getattr(fn, "arguments", "{}") if fn else "{}"
                    
                    if not skill_name:
                        continue
                    
                    # 校验 skill 是否在 CONSULT_SKILLS 中
                    allowed = [s["function"]["name"] for s in CONSULT_SKILLS]
                    if skill_name not in allowed:
                        continue
                    
                    try:
                        arguments = json.loads(arguments_str)
                    except json.JSONDecodeError:
                        arguments = {}
                    
                    # skill 名转为 MCP 工具名（consult_search_knowledge -> consult-search-knowledge）
                    mcp_tool_name = skill_name.replace("_", "-")
                    tool_result = self._invoke_tool(mcp_tool_name, "consult-mcp-server", arguments, req_id=req_id)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": skill_name,
                        "content": tool_result
                    })
                
                # 5. 生成最终回复
                t0 = time.perf_counter()
                final_completion = Completions.create(
                    model=DASHSCOPE_MODEL,
                    messages=[{"role": "system", "content": self.system_prompt}] + messages,
                    extra_body={"tools": CONSULT_SKILLS},
                )
                
                if getattr(final_completion, "status_code", 200) == 200:
                    final_msg = final_completion.choices[0].message
                    output = final_msg.content or ""
                    self.history.append({"role": "assistant", "content": output})
                    return output
                else:
                    # 若最终回复失败，返回最后一个工具结果
                    last_tool = next((m for m in reversed(messages) if m.get("role") == "tool"), None)
                    if last_tool:
                        return last_tool.get("content", "工具已执行，但回复生成失败。")
                    return "工具已执行，但回复生成失败。"
            else:
                # 无工具调用，直接使用 LLM 回复
                output = message.content or ""
                self.history.append({"role": "assistant", "content": output})
                return output
                
        except Exception as e:
            error_msg = f"处理请求时出现错误: {str(e)}"
            print(f"[ConsultAgent] 错误: {error_msg}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return "抱歉，处理您的请求时出现了问题，请稍后再试。"
    
    def clear_history(self):
        """清空对话历史"""
        self.history = [
            {"role": "system", "content": self.system_prompt}
        ]
    
    def get_available_tools(self) -> List[Dict]:
        """获取可用技能列表（兼容旧接口）"""
        return CONSULT_SKILLS.copy()
    
    def start_a2a_server(self, host: str = '0.0.0.0', port: int = 10005, debug: bool = False):
        """启动 A2A 服务端"""
        a2a_server = A2AServer(agent_name=self.agent_name, port=port)
        
        def handle_request(data: Dict) -> str:
            user_input = data.get("input", "")
            request_user_id = data.get("user_id")
            if request_user_id:
                original_user_id = self.user_id
                self.user_id = str(request_user_id)
                try:
                    return self.chat(user_input, req_id=data.get("req_id"))
                finally:
                    self.user_id = original_user_id
            else:
                return self.chat(user_input, req_id=data.get("req_id"))
        
        a2a_server.set_handler(handle_request)
        
        print(f"{self.agent_name} A2A Server 启动在 http://{host}:{port}", file=sys.stderr, flush=True)
        print(f"可用技能: {len(CONSULT_SKILLS)} 个", file=sys.stderr, flush=True)
        
        a2a_server.run(host=host, debug=debug)
