"""
监督者智能体 - 负责路由和协调子智能体
使用结构化输出（Pydantic + Function Calling）进行意图识别，与 AgentScope 方式一致
"""
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import dashscope
from dashscope.aigc.chat_completion import Completions

# 添加项目根目录到路径，以便导入 config
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL
from supervisor_agent.route_schema import ROUTE_TOOL, RouteResult

# 兼容旧版 dashscope：Completions 需要 base_compatible_api_url
if not hasattr(dashscope, "base_compatible_api_url"):
    dashscope.base_compatible_api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
from service_discovery import ServiceDiscovery
from a2a.client import A2AClient
from supervisor_agent.api_logger import log_llm, log_backend

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class SupervisorAgent:
    """监督者智能体 - 负责协调和管理其他子智能体的工作"""
    
    def __init__(self, user_id: str = "default_user", chat_id: str = "default_chat"):
        self.user_id = user_id
        self.chat_id = chat_id
        self.role: Optional[str] = None  # 当前会话的角色身份
        self.history: List[Dict[str, str]] = []
        
        # 系统提示词（监督者智能体的角色定义）
        self.system_prompt = """角色与职责:
你是云边奶茶铺的监督者智能体，负责协调和管理其他子智能体的工作。

身份验证流程:
1. 在开始任何业务之前，你必须先确认用户的身份。
2. 如果当前身份未知（role 为 None），你必须礼貌地要求用户输入身份。
3. 接受的身份包括："顾客" (customer), "店员" (staff), "管理员" (admin)。
4. 一旦身份确认，你将根据身份路由请求。

子智能体调用:
- feedback_agent: 处理用户反馈、投诉和差评
- consult_agent: 处理产品咨询、活动信息和冲泡指导
- order_agent: 处理订单相关业务（支持权限传递）

约束:
- 只有在身份确认后才能调用业务智能体。
- 传递给 order_agent 时必须包含用户的 role 信息。
"""
        
        # 添加系统提示词到历史记录
        self.history.append({
            "role": "system",
            "content": self.system_prompt
        })
        
        # 服务发现（用于查找子智能体地址）
        self.service_discovery = ServiceDiscovery(method="config")
        
        # 子智能体配置
        self.sub_agents = {
            "consult_agent": {
                "name": "咨询智能体",
                "description": "处理产品咨询、活动信息和冲泡指导",
                "implemented": True  # 已实现，可以通过 A2A 协议调用
            },
            "order_agent": {
                "name": "订单智能体",
                "description": "处理订单相关业务，包括下单、查询、修改等",
                "implemented": True  # 已实现，可以通过 A2A 协议调用
            },
            "feedback_agent": {
                "name": "反馈智能体",
                "description": "处理用户反馈、投诉和差评",
                "implemented": True  # 已实现，可以通过 A2A 协议调用
            }
        }
        
        # A2A 客户端（用于调用子智能体）
        self.a2a_client = A2AClient(service_discovery=self.service_discovery)
    
    def route_to_agent(self, user_input: str, req_id: Optional[str] = None) -> str:
        """
        使用 LLM 分析用户输入及对话上下文，判断应路由到哪个子智能体。
        与 Alibaba demo 一致：闲聊也走 consult_agent，无 None/general_chat。
        """
        return self._route_by_llm(user_input, req_id=req_id)
    
    def _route_by_llm(self, user_input: str, req_id: Optional[str] = None) -> str:
        """
        使用 LLM 进行智能路由判断，结合对话上下文以识别确认类回复。
        采用结构化输出（Pydantic + Function Calling），与 AgentScope 方式一致。
        """
        # 提取最近 6 条对话作为上下文（排除 system）
        context_parts = []
        for msg in self.history[-6:]:
            if msg.get("role") == "system":
                continue
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                if content.startswith("[") and "]" in content:
                    content = content.split("]", 1)[-1].strip()
                context_parts.append(f"- {role}：{content[:200]}{'...' if len(content) > 200 else ''}")
        context_str = "\n".join(context_parts) if context_parts else "（无历史）"
        
        user_content = f"""你是云边奶茶铺的监督者，需要根据用户请求和对话上下文，判断应路由到哪个子智能体。

【可用子智能体】
1. order_agent - 菜单/库存/订单：查菜单、有哪些奶茶、在售、在卖、库存、价格（菜单价）、下单、点单、购买、查订单
2. consult_agent - 产品咨询、闲聊：产品介绍、口感、冲泡方法、活动信息、推荐、纯问候、一般性对话
3. feedback_agent - 反馈、投诉、建议、差评

【对话上下文】
{context_str}

【当前用户】{user_input}

【路由规则】
- 菜单/库存查询（有哪些奶茶、在售、在卖、有货吗、库存、菜单、价格表）→ order_agent
- 下单、点单、购买、查订单、改订单、确认规格（糖度/冰度）→ order_agent
- 上一轮助手在询问订单/规格确认，用户回复是确认/肯定（是的、好、一样、可以、嗯嗯）→ order_agent
- 产品咨询（某款奶茶的口感、冲泡方法、活动介绍、推荐理由）→ consult_agent
- 用户反馈、投诉、建议 → feedback_agent
- 纯问候、闲聊、一般性对话、无法判断 → consult_agent

【重要】菜单/库存 vs 产品咨询 vs 闲聊：
- 「有哪些奶茶」「在卖什么」「库存」「有货吗」→ order_agent（查数据）
- 「桂花云露好喝吗」「怎么冲泡」「有什么活动」→ consult_agent（咨询介绍）
- 「你好」「嗨」「在吗」等纯问候、闲聊 → consult_agent"""

        t0 = time.perf_counter()
        try:
            completion = Completions.create(
                model=DASHSCOPE_MODEL,
                messages=[{"role": "user", "content": user_content}],
                temperature=0.1,
                extra_body={
                    "tools": [ROUTE_TOOL],
                    "tool_choice": {"type": "function", "function": {"name": "generate_structured_output"}},
                },
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)
            
            if getattr(completion, "status_code", 200) != 200:
                log_llm(req_id or "", "route_by_llm", DASHSCOPE_MODEL, "error", duration_ms,
                        str(getattr(completion, "message", "")), input_content=user_input, output_content="")
                return "consult_agent"
            
            message = completion.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []
            
            if tool_calls:
                tc = tool_calls[0]
                fn = tc.get("function", {}) if isinstance(tc, dict) else getattr(tc, "function", None)
                if fn is None:
                    fn = {}
                args_str = fn.get("arguments", "") if isinstance(fn, dict) else getattr(fn, "arguments", "")
                try:
                    args = json.loads(args_str or "{}")
                    parsed = RouteResult.model_validate(args)
                    result = parsed.target_agent
                    log_llm(req_id or "", "route_by_llm", DASHSCOPE_MODEL, "success", duration_ms,
                            input_content=user_input, output_content=result)
                    return result
                except (json.JSONDecodeError, Exception) as e:
                    log_llm(req_id or "", "route_by_llm", DASHSCOPE_MODEL, "error", duration_ms, str(e),
                            input_content=user_input, output_content=args_str or "")
            
            log_llm(req_id or "", "route_by_llm", DASHSCOPE_MODEL, "error", duration_ms, "no tool_calls",
                    input_content=user_input, output_content="")
        except Exception as e:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            log_llm(req_id or "", "route_by_llm", DASHSCOPE_MODEL, "error", duration_ms, str(e),
                    input_content=user_input, output_content="")
        return "consult_agent"
    
    def call_sub_agent(self, agent_name: str, user_input: str, force_role: Optional[str] = None, req_id: Optional[str] = None) -> str:
        """
        调用子智能体处理请求（使用 A2A 协议）
        
        Args:
            agent_name: 子智能体名称
            user_input: 用户输入
            force_role: 强制使用的角色（如 "base" 用于未登录用户的 BASE_SKILLS 查询）
            
        Returns:
            子智能体的响应
        """
        if agent_name not in self.sub_agents:
            return f"错误：未知的子智能体 {agent_name}"
        
        agent_info = self.sub_agents[agent_name]
        
        # 如果子智能体未实现，返回提示信息
        if not agent_info["implemented"]:
            return f"我理解您的需求，这需要 {agent_info['name']} 来处理。该功能正在开发中，敬请期待。"
        
        # 使用 A2A 协议调用子智能体
        try:
            # 构建 A2A 协议请求数据
            a2a_request = {
                "input": user_input,
                "chat_id": self.chat_id,
                "user_id": self.user_id
            }
            
            # 特殊处理：如果是 order_agent，传递角色权限
            if agent_name == "order_agent":
                role = force_role or self.role or "base"
                a2a_request["role"] = role
            
            # 全链路日志：传递 req_id
            if req_id:
                a2a_request["req_id"] = req_id
            
            # 回源：通过 A2A 调用子智能体
            t0 = time.perf_counter()
            try:
                a2a_response = self.a2a_client.call_agent(agent_name, a2a_request)
                duration_ms = int((time.perf_counter() - t0) * 1000)
                log_backend(req_id or "", agent_name, "chat", "success", duration_ms=duration_ms, request_body=a2a_request, response_body=a2a_response)
            except Exception as e:
                duration_ms = int((time.perf_counter() - t0) * 1000)
                log_backend(req_id or "", agent_name, "chat", "error", duration_ms=duration_ms, error=str(e), request_body=a2a_request, response_body={"error": str(e)})
                raise
            
            # 提取响应内容
            if isinstance(a2a_response, dict):
                output = a2a_response.get("output", "")
                pending_action = a2a_response.get("pending_action")
                if pending_action:
                    return {"output": output or str(a2a_response), "pending_action": pending_action}
                if output:
                    return output
                return str(a2a_response)
            return str(a2a_response)
                
        except ValueError as e:
            # 服务未找到
            return f"抱歉，{agent_info['name']} 服务暂时不可用，请稍后再试。"
        except ConnectionError as e:
            # 连接错误
            return f"抱歉，无法连接到 {agent_info['name']}，请确保服务已启动。"
        except Exception as e:
            # 其他错误
            error_msg = str(e)
            print(f"调用 {agent_name} 时出现错误: {error_msg}")
            return f"抱歉，调用 {agent_info['name']} 时出现了问题，请稍后再试。"
    
    def _should_decompose_task(self, user_input: str) -> bool:
        """
        判断是否应该进行任务分解
        
        Args:
            user_input: 用户输入
            
        Returns:
            是否应该进行任务分解
        """
        # 检测复杂任务的关键词
        decomposition_keywords = [
            "然后", "接着", "之后", "最后", "先", "再", "同时",
            "和", "以及", "还有", "另外", "顺便"
        ]
        
        # 检测是否包含多个任务类型的关键词
        task_type_keywords = {
            "order": ["下单", "点单", "购买", "订单"],
            "consult": ["咨询", "了解", "介绍", "推荐", "价格"],
            "feedback": ["反馈", "投诉", "建议", "评价"]
        }
        
        user_input_lower = user_input.lower()
        
        # 检查是否包含多个任务类型
        task_types_found = []
        for task_type, keywords in task_type_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                task_types_found.append(task_type)
        
        # 如果包含多个任务类型，或者包含分解关键词，则进行任务分解
        if len(task_types_found) > 1:
            return True
        
        if any(keyword in user_input for keyword in decomposition_keywords):
            return True
        
        return False
    
    def _execute_decomposed_tasks(self, subtasks, a2a_client, req_id: Optional[str] = None) -> str:
        """
        执行分解后的子任务
        
        Args:
            subtasks: 子任务列表（已排序）
            a2a_client: A2A 客户端
            
        Returns:
            整合后的结果
        """
        results = []
        
        for i, task in enumerate(subtasks, 1):
            print(f"[SupervisorAgent] 执行任务 {i}/{len(subtasks)}: {task.description}", file=sys.stderr, flush=True)
            
            # 检查依赖是否已完成
            if task.dependencies:
                for dep_id in task.dependencies:
                    dep_task = next((t for t in subtasks if t.task_id == dep_id), None)
                    if dep_task and dep_task.status != "completed":
                        error_msg = f"依赖任务 {dep_id} 未完成，无法执行任务 {task.task_id}"
                        print(f"[SupervisorAgent] 错误: {error_msg}", file=sys.stderr, flush=True)
                        task.status = "failed"
                        task.error = error_msg
                        continue
            
            # 执行任务
            try:
                task.status = "running"
                
                # 构建输入数据
                input_data = task.input_data.copy()
                if "input" not in input_data:
                    input_data["input"] = task.description
                
                # 调用子智能体
                a2a_request = {
                    "input": input_data.get("input", task.description),
                    "chat_id": self.chat_id,
                    "user_id": self.user_id
                }
                
                # 合并其他输入数据
                a2a_request.update({k: v for k, v in input_data.items() if k != "input"})
                
                # 全链路日志：传递 req_id
                if req_id:
                    a2a_request["req_id"] = req_id
                
                # 回源：调用子智能体
                t0 = time.perf_counter()
                try:
                    a2a_response = a2a_client.call_agent(task.agent, a2a_request)
                    duration_ms = int((time.perf_counter() - t0) * 1000)
                    log_backend(req_id or "", task.agent, "chat", "success", duration_ms=duration_ms, request_body=a2a_request, response_body=a2a_response)
                except Exception as e:
                    duration_ms = int((time.perf_counter() - t0) * 1000)
                    log_backend(req_id or "", task.agent, "chat", "error", duration_ms=duration_ms, error=str(e), request_body=a2a_request, response_body={"error": str(e)})
                    raise
                
                # 提取响应
                if isinstance(a2a_response, dict):
                    output = a2a_response.get("output", "")
                    if output:
                        task.result = output
                        task.status = "completed"
                        results.append(f"【任务 {i}】{task.description}\n结果: {output}\n")
                    else:
                        task.result = str(a2a_response)
                        task.status = "completed"
                        results.append(f"【任务 {i}】{task.description}\n结果: {task.result}\n")
                else:
                    task.result = str(a2a_response)
                    task.status = "completed"
                    results.append(f"【任务 {i}】{task.description}\n结果: {task.result}\n")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"[SupervisorAgent] 执行任务 {task.task_id} 失败: {error_msg}", file=sys.stderr, flush=True)
                task.status = "failed"
                task.error = error_msg
                results.append(f"【任务 {i}】{task.description}\n执行失败: {error_msg}\n")
        
        # 整合所有结果
        if results:
            final_result = "已完成所有任务：\n\n" + "\n".join(results)
            return final_result
        else:
            return "任务执行失败，请稍后再试。"
    
    def chat(self, user_input: str, req_id: Optional[str] = None) -> str:
        """
        处理用户输入并返回回复
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI 回复
        """
        # 1. 身份识别：用户明确说身份时设置 role，否则不阻塞，交给子 agent 根据权限判断
        if self.role is None:
            input_lower = user_input.lower()
            if "顾客" in input_lower or "customer" in input_lower:
                self.role = "customer"
                return "身份已确认为【顾客】。请问有什么可以帮您？您可以咨询产品或直接下单。"
            elif "店员" in input_lower or "staff" in input_lower:
                self.role = "staff"
                return "身份已确认为【店员】。您可以处理订单状态。"
            elif "管理员" in input_lower or "admin" in input_lower:
                self.role = "admin"
                return "身份已确认为【管理员】。您拥有所有管理权限，包括退款和删除订单。"
            # 未明确身份时不阻塞，继续路由；order_agent 会以 role=base 处理，权限不足时由其返回提示

        # 添加用户输入到历史记录（未登录时 role 为 None，call_sub_agent 会传 base）
        self.history.append({
            "role": "user",
            "content": f"[{self.role or 'base'}] {user_input}"
        })
        
        try:
            # 2. 检查是否应该进行任务分解
            if self._should_decompose_task(user_input):
                try:
                    from supervisor_agent.task_decomposition import TaskDecompositionPlanner
                    
                    planner = TaskDecompositionPlanner()
                    subtasks = planner.decompose_task(user_input, req_id=req_id)
                    
                    if subtasks and len(subtasks) > 1:
                        # 复杂任务，进行分解和执行
                        print(f"[SupervisorAgent] 检测到复杂任务，分解为 {len(subtasks)} 个子任务", file=sys.stderr, flush=True)
                        
                        # 拓扑排序，确定执行顺序
                        sorted_tasks = planner.topological_sort(subtasks)
                        
                        # 执行所有子任务
                        final_result = self._execute_decomposed_tasks(sorted_tasks, self.a2a_client, req_id=req_id)
                        
                        # 添加到历史记录
                        self.history.append({
                            "role": "assistant",
                            "content": final_result
                        })
                        
                        return final_result
                    elif subtasks and len(subtasks) == 1:
                        # 单个任务，直接执行
                        task = subtasks[0]
                        print(f"[SupervisorAgent] 单个任务: {task.description} ({task.agent})", file=sys.stderr, flush=True)
                        agent_response = self.call_sub_agent(task.agent, task.input_data.get("input", user_input), req_id=req_id)
                        
                        self.history.append({
                            "role": "assistant",
                            "content": agent_response
                        })
                        
                        return agent_response
                except Exception as e:
                    print(f"[SupervisorAgent] 任务分解失败，回退到简单路由: {str(e)}", file=sys.stderr, flush=True)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    # 失败时回退到简单路由
            
            # 简单路由（与 Alibaba demo 一致：闲聊也走 consult_agent，无 general_chat）
            target_agent = self.route_to_agent(user_input, req_id=req_id)
            agent_response = self.call_sub_agent(target_agent, user_input, req_id=req_id)
            content = agent_response.get("output", agent_response) if isinstance(agent_response, dict) else agent_response
            self.history.append({"role": "assistant", "content": content})
            return content
            
        except Exception as e:
            error_msg = f"处理请求时出现错误: {str(e)}"
            print(f"错误: {error_msg}")
            return "抱歉，处理您的请求时出现了问题，请稍后再试。"
    
    def clear_history(self):
        """清空对话历史"""
        self.role = None  # 重置身份
        self.history = [{
            "role": "system",
            "content": self.system_prompt
        }]
    
    def register_sub_agent(self, agent_name: str, agent_info: Dict):
        """
        注册子智能体（用于后续扩展）
        
        Args:
            agent_name: 子智能体名称
            agent_info: 子智能体信息，包含 name, description, implemented 等
        """
        self.sub_agents[agent_name] = agent_info
    
    def get_sub_agent_status(self) -> Dict:
        """
        获取所有子智能体的状态
        
        Returns:
            子智能体状态字典
        """
        return {
            name: {
                "name": info["name"],
                "description": info["description"],
                "implemented": info["implemented"]
            }
            for name, info in self.sub_agents.items()
        }
