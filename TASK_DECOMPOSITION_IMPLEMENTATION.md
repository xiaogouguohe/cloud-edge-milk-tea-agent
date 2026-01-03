# 基于任务分解的规划实现

## 概述

本项目实现了真正的**基于任务分解的规划**功能，能够将用户的复杂请求分解成多个子任务，并按照依赖关系顺序执行。

## 与简单路由的区别

### ❌ 之前的实现（简单路由）

**用户输入**："我想了解一下你们的产品，然后点一杯云边茉莉"

**处理方式**：
- 只识别到一个任务类型（咨询或下单）
- 路由到单个子智能体
- 无法处理多步骤任务

### ✅ 现在的实现（任务分解）

**用户输入**："我想了解一下你们的产品，然后点一杯云边茉莉，最后给个反馈说服务很好"

**处理方式**：
1. **识别复杂任务**：检测到包含多个任务类型
2. **任务分解**：分解成 3 个子任务
   - 任务1：咨询产品信息 → consult_agent
   - 任务2：下单云边茉莉 → order_agent（依赖任务1）
   - 任务3：提交反馈 → feedback_agent（依赖任务2）
3. **依赖管理**：确定子任务之间的依赖关系
4. **顺序执行**：按照拓扑排序后的顺序执行
5. **结果整合**：整合所有子任务的结果

## 核心组件

### 1. SubTask（子任务）

```python
class SubTask:
    task_id: str              # 任务ID
    description: str          # 任务描述
    agent: str               # 负责的智能体
    input_data: Dict          # 输入数据
    dependencies: List[str]   # 依赖的任务ID列表
    status: str              # 任务状态
    result: str              # 执行结果
```

### 2. TaskDecompositionPlanner（任务分解规划器）

主要方法：
- `decompose_task()`: 将用户输入分解成子任务
- `build_dependency_graph()`: 构建依赖关系图
- `topological_sort()`: 拓扑排序，确定执行顺序

## 工作流程

### 步骤 1: 检测复杂任务

```python
def _should_decompose_task(self, user_input: str) -> bool:
    # 检测复杂任务的关键词
    decomposition_keywords = [
        "然后", "接着", "之后", "最后", "先", "再", "同时",
        "和", "以及", "还有", "另外", "顺便"
    ]
    
    # 检测是否包含多个任务类型
    task_type_keywords = {
        "order": ["下单", "点单", "购买", "订单"],
        "consult": ["咨询", "了解", "介绍", "推荐", "价格"],
        "feedback": ["反馈", "投诉", "建议", "评价"]
    }
    
    # 如果包含多个任务类型，或包含分解关键词，则进行任务分解
    if len(task_types_found) > 1:
        return True
```

### 步骤 2: 任务分解

使用 LLM 将用户输入分解成多个子任务：

**LLM Prompt**：
```
你是一个任务规划专家，需要将用户的复杂请求分解成多个子任务。

用户请求: 我想了解一下你们的产品，然后点一杯云边茉莉，最后给个反馈说服务很好

可用智能体：
1. order_agent - 处理订单相关业务
2. consult_agent - 处理产品咨询
3. feedback_agent - 处理用户反馈

请分析用户请求，如果包含多个任务，请将其分解成子任务。
```

**LLM 返回**：
```json
{
    "is_complex": true,
    "tasks": [
        {
            "task_id": "task_1",
            "description": "咨询产品信息",
            "agent": "consult_agent",
            "input_data": {"input": "了解一下你们的产品"},
            "dependencies": []
        },
        {
            "task_id": "task_2",
            "description": "下单云边茉莉",
            "agent": "order_agent",
            "input_data": {"input": "点一杯云边茉莉"},
            "dependencies": ["task_1"]
        },
        {
            "task_id": "task_3",
            "description": "提交反馈",
            "agent": "feedback_agent",
            "input_data": {"input": "给个反馈说服务很好"},
            "dependencies": ["task_2"]
        }
    ]
}
```

### 步骤 3: 构建依赖关系图

```
task_1 (无依赖)
  ↓
task_2 (依赖 task_1)
  ↓
task_3 (依赖 task_2)
```

### 步骤 4: 拓扑排序

确定执行顺序：task_1 → task_2 → task_3

### 步骤 5: 顺序执行

```python
def _execute_decomposed_tasks(self, subtasks, a2a_client) -> str:
    results = []
    
    for task in subtasks:
        # 检查依赖是否已完成
        if task.dependencies:
            for dep_id in task.dependencies:
                dep_task = next((t for t in subtasks if t.task_id == dep_id), None)
                if dep_task and dep_task.status != "completed":
                    # 依赖未完成，跳过
                    continue
        
        # 执行任务
        a2a_response = a2a_client.call_agent(task.agent, a2a_request)
        task.result = extract_result(a2a_response)
        task.status = "completed"
        results.append(f"【任务】{task.description}\n结果: {task.result}\n")
    
    # 整合所有结果
    return "已完成所有任务：\n\n" + "\n".join(results)
```

### 步骤 6: 结果整合

```
已完成所有任务：

【任务 1】咨询产品信息
结果: 我们有以下产品：云边茉莉、桂花云露、云雾观音...

【任务 2】下单云边茉莉
结果: 订单创建成功，订单号：ORDER_xxx

【任务 3】提交反馈
结果: 感谢您的反馈，我们会继续努力提供更好的服务
```

## 实际示例

### 示例 1: 多步骤任务

**用户输入**："先查询一下我的历史订单，然后根据订单信息给我推荐一款新产品"

**任务分解**：
1. 任务1：查询历史订单 → order_agent
2. 任务2：根据订单信息推荐新产品 → consult_agent（依赖任务1）

**执行顺序**：
1. 先执行任务1，获取历史订单
2. 将订单信息传递给任务2
3. 执行任务2，基于订单信息推荐

### 示例 2: 并行任务

**用户输入**："我想了解一下产品价格，同时查询一下我的订单状态"

**任务分解**：
1. 任务1：了解产品价格 → consult_agent
2. 任务2：查询订单状态 → order_agent

**执行顺序**：
- 两个任务无依赖关系，可以并行执行（当前实现是顺序执行，但可以优化为并行）

### 示例 3: 简单任务（不分解）

**用户输入**："我要一杯云边茉莉"

**任务分解**：
- `is_complex: false`
- 单个任务：下单云边茉莉 → order_agent

**处理方式**：
- 直接路由到 order_agent，不进行任务分解

## 优势

1. **真正的任务分解**：能够识别和分解复杂任务
2. **依赖管理**：支持子任务之间的依赖关系
3. **顺序执行**：按照依赖关系确定执行顺序
4. **结果整合**：整合所有子任务的结果
5. **智能识别**：自动识别简单任务和复杂任务

## 与简单路由的对比

| 特性 | 简单路由 | 任务分解 |
|------|---------|---------|
| 任务识别 | 单个任务类型 | 多个任务类型 |
| 处理方式 | 路由到单个智能体 | 分解成多个子任务 |
| 依赖关系 | 不支持 | 支持 |
| 执行顺序 | 无顺序概念 | 拓扑排序确定顺序 |
| 结果整合 | 单个结果 | 整合多个结果 |
| 适用场景 | 简单请求 | 复杂多步骤请求 |

## 使用场景

### ✅ 适合任务分解的场景

1. **多步骤任务**
   - "先咨询产品，然后下单"
   - "查询订单，然后给反馈"

2. **组合任务**
   - "了解产品价格，同时查询订单状态"
   - "下单并提交反馈"

3. **依赖任务**
   - "根据我的订单历史推荐新产品"
   - "先了解产品，再决定下单"

### ❌ 不适合任务分解的场景

1. **简单任务**
   - "我要一杯云边茉莉" → 直接路由
   - "产品价格是多少？" → 直接路由

2. **单一类型任务**
   - "我想了解一下你们的产品" → 直接路由到 consult_agent

## 未来改进

1. **并行执行**：对于无依赖关系的任务，可以并行执行
2. **任务重试**：失败的任务可以重试
3. **任务取消**：支持取消正在执行的任务
4. **进度反馈**：实时反馈任务执行进度
5. **任务缓存**：缓存已执行的任务结果

## 参考

- [Task Decomposition in AI Planning](https://en.wikipedia.org/wiki/Automated_planning_and_scheduling)
- [Dependency Graph](https://en.wikipedia.org/wiki/Dependency_graph)
- [Topological Sorting](https://en.wikipedia.org/wiki/Topological_sorting)

