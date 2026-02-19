"""
基于任务分解的规划器
将复杂任务分解成多个子任务，并管理子任务之间的依赖关系
"""
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
import dashscope
from dashscope import Generation
import json
import re

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL
from supervisor_agent.api_logger import log_llm

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class SubTask:
    """子任务"""
    
    def __init__(self,
                 task_id: str,
                 description: str,
                 agent: str,
                 input_data: Dict,
                 dependencies: List[str] = None,
                 status: str = "pending"):
        """
        初始化子任务
        
        Args:
            task_id: 任务ID
            description: 任务描述
            agent: 负责处理的智能体名称
            input_data: 输入数据
            dependencies: 依赖的其他任务ID列表
            status: 任务状态 (pending, running, completed, failed)
        """
        self.task_id = task_id
        self.description = description
        self.agent = agent
        self.input_data = input_data
        self.dependencies = dependencies or []
        self.status = status
        self.result: Optional[str] = None
        self.error: Optional[str] = None
    
    def __repr__(self):
        return f"SubTask(id={self.task_id}, agent={self.agent}, status={self.status}, deps={self.dependencies})"


class TaskDecompositionPlanner:
    """任务分解规划器"""
    
    def __init__(self):
        """初始化任务分解规划器"""
        self.available_agents = {
            "order_agent": "处理订单相关业务，包括下单、查询、修改等",
            "consult_agent": "处理产品咨询、活动信息和冲泡指导",
            "feedback_agent": "处理用户反馈、投诉和差评"
        }
    
    def decompose_task(self, user_input: str, req_id: Optional[str] = None) -> List[SubTask]:
        """
        将用户输入分解成多个子任务
        
        Args:
            user_input: 用户输入
            req_id: 请求追踪 ID
            
        Returns:
            子任务列表
        """
        # 使用 LLM 进行任务分解
        prompt = f"""你是一个任务规划专家，需要将用户的复杂请求分解成多个子任务。

用户请求: {user_input}

可用智能体：
1. order_agent - 处理订单相关业务，包括下单、查询、修改等
2. consult_agent - 处理产品咨询、活动信息和冲泡指导
3. feedback_agent - 处理用户反馈、投诉和差评

请分析用户请求，如果包含多个任务，请将其分解成子任务。每个子任务应该：
1. 有明确的描述
2. 指定负责的智能体
3. 包含输入数据（从用户请求中提取）
4. 如果有依赖关系，列出依赖的任务ID

请以 JSON 格式返回，格式如下：
{{
    "is_complex": true/false,
    "tasks": [
        {{
            "task_id": "task_1",
            "description": "任务描述",
            "agent": "order_agent/consult_agent/feedback_agent",
            "input_data": {{"key": "value"}},
            "dependencies": ["task_0"]  // 可选，依赖的任务ID列表
        }},
        ...
    ]
}}

如果用户请求只包含一个简单任务，设置 "is_complex": false，tasks 数组只包含一个任务。

只返回 JSON，不要其他文字。"""
        
        t0 = time.perf_counter()
        try:
            response = Generation.call(
                model=DASHSCOPE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                result_format='message'
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)
            if response.status_code == 200:
                log_llm(req_id or "", "decompose_task", DASHSCOPE_MODEL, "success", duration_ms)
                result_text = response.output.choices[0].message.content.strip()
                # 提取 JSON
                json_match = re.search(r'\{.*?\}', result_text, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                    
                    # 检查是否是复杂任务
                    is_complex = result_json.get("is_complex", False)
                    tasks_data = result_json.get("tasks", [])
                    
                    if not is_complex and len(tasks_data) == 1:
                        # 简单任务，返回单个子任务
                        task_data = tasks_data[0]
                        return [SubTask(
                            task_id=task_data.get("task_id", "task_1"),
                            description=task_data.get("description", ""),
                            agent=task_data.get("agent", ""),
                            input_data=task_data.get("input_data", {}),
                            dependencies=task_data.get("dependencies", [])
                        )]
                    else:
                        # 复杂任务，返回多个子任务
                        subtasks = []
                        for task_data in tasks_data:
                            subtask = SubTask(
                                task_id=task_data.get("task_id", f"task_{len(subtasks) + 1}"),
                                description=task_data.get("description", ""),
                                agent=task_data.get("agent", ""),
                                input_data=task_data.get("input_data", {}),
                                dependencies=task_data.get("dependencies", [])
                            )
                            subtasks.append(subtask)
                        
                        return subtasks
                else:
                    log_llm(req_id or "", "decompose_task", DASHSCOPE_MODEL, "error", duration_ms, "parse_failed")
            else:
                log_llm(req_id or "", "decompose_task", DASHSCOPE_MODEL, "error", duration_ms, str(getattr(response, "message", "")))
        except Exception as e:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            log_llm(req_id or "", "decompose_task", DASHSCOPE_MODEL, "error", duration_ms, str(e))
            print(f"[TaskDecomposition] 任务分解失败: {str(e)}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
        
        # 如果分解失败，返回空列表
        return []
    
    def build_dependency_graph(self, subtasks: List[SubTask]) -> Dict[str, Set[str]]:
        """
        构建依赖关系图
        
        Args:
            subtasks: 子任务列表
            
        Returns:
            依赖关系图 {task_id: {依赖的task_id集合}}
        """
        graph = {}
        task_ids = {task.task_id for task in subtasks}
        
        for task in subtasks:
            # 验证依赖关系是否有效
            valid_dependencies = [
                dep for dep in task.dependencies 
                if dep in task_ids and dep != task.task_id
            ]
            task.dependencies = valid_dependencies
            graph[task.task_id] = set(valid_dependencies)
        
        return graph
    
    def topological_sort(self, subtasks: List[SubTask]) -> List[SubTask]:
        """
        对子任务进行拓扑排序，确定执行顺序
        
        Args:
            subtasks: 子任务列表
            
        Returns:
            排序后的子任务列表
        """
        graph = self.build_dependency_graph(subtasks)
        task_dict = {task.task_id: task for task in subtasks}
        
        # 计算每个任务的入度
        in_degree = {task_id: 0 for task_id in task_dict.keys()}
        for task_id, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0) + 1
        
        # 拓扑排序
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        sorted_tasks = []
        
        while queue:
            task_id = queue.pop(0)
            sorted_tasks.append(task_dict[task_id])
            
            # 更新依赖该任务的其他任务的入度
            for other_id, deps in graph.items():
                if task_id in deps:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)
        
        # 检查是否有循环依赖
        if len(sorted_tasks) != len(subtasks):
            print(f"[TaskDecomposition] 警告: 检测到循环依赖，使用原始顺序", file=sys.stderr, flush=True)
            return subtasks
        
        return sorted_tasks
    
    def format_decomposition(self, subtasks: List[SubTask]) -> str:
        """
        格式化任务分解结果
        
        Args:
            subtasks: 子任务列表
            
        Returns:
            格式化的字符串
        """
        if not subtasks:
            return "未识别到需要执行的任务。"
        
        if len(subtasks) == 1:
            task = subtasks[0]
            return f"识别到单个任务：\n- {task.description} (由 {task.agent} 处理)"
        
        result = f"识别到 {len(subtasks)} 个子任务：\n\n"
        
        for i, task in enumerate(subtasks, 1):
            result += f"任务 {i}: {task.description}\n"
            result += f"  - 负责智能体: {task.agent}\n"
            if task.dependencies:
                dep_names = [f"任务 {subtasks.index(t) + 1}" for t in subtasks if t.task_id in task.dependencies]
                result += f"  - 依赖: {', '.join(dep_names)}\n"
            result += "\n"
        
        return result


def test_task_decomposition():
    """测试任务分解功能"""
    planner = TaskDecompositionPlanner()
    
    # 测试场景1：复杂任务
    print("\n" + "="*60)
    print("测试场景1：复杂任务分解")
    print("="*60)
    user_input = "我想了解一下你们的产品，然后点一杯云边茉莉，最后给个反馈说服务很好"
    
    print(f"\n用户请求: {user_input}\n")
    
    subtasks = planner.decompose_task(user_input)
    
    if subtasks:
        print("任务分解结果:")
        print(planner.format_decomposition(subtasks))
        
        # 拓扑排序
        sorted_tasks = planner.topological_sort(subtasks)
        print("\n执行顺序:")
        for i, task in enumerate(sorted_tasks, 1):
            print(f"{i}. {task.description} ({task.agent})")
    
    # 测试场景2：简单任务
    print("\n" + "="*60)
    print("测试场景2：简单任务（不分解）")
    print("="*60)
    user_input = "我要一杯云边茉莉"
    
    print(f"\n用户请求: {user_input}\n")
    
    subtasks = planner.decompose_task(user_input)
    
    if subtasks:
        print("任务分解结果:")
        print(planner.format_decomposition(subtasks))
    
    # 测试场景3：多步骤任务
    print("\n" + "="*60)
    print("测试场景3：多步骤任务")
    print("="*60)
    user_input = "先查询一下我的历史订单，然后根据订单信息给我推荐一款新产品"
    
    print(f"\n用户请求: {user_input}\n")
    
    subtasks = planner.decompose_task(user_input)
    
    if subtasks:
        print("任务分解结果:")
        print(planner.format_decomposition(subtasks))
        
        # 拓扑排序
        sorted_tasks = planner.topological_sort(subtasks)
        print("\n执行顺序:")
        for i, task in enumerate(sorted_tasks, 1):
            deps = [f"任务 {subtasks.index(t) + 1}" for t in subtasks if t.task_id in task.dependencies]
            dep_str = f" (依赖: {', '.join(deps)})" if deps else ""
            print(f"{i}. {task.description} ({task.agent}){dep_str}")


if __name__ == "__main__":
    test_task_decomposition()

