# Tree of Thoughts (ToT) 实现说明

## 概述

本项目实现了基于 **Tree of Thoughts (ToT)** 的个性化推荐功能，用于解决需要多路径探索、评估和回溯的复杂推荐场景。

## 适用场景

### ✅ 适合使用 ToT 的场景

1. **个性化推荐**
   - 用户："我想要一杯适合我的奶茶"
   - 需要探索多个推荐维度（口味、价格、健康、库存等）
   - 评估每个推荐路径的质量
   - 选择最优推荐

2. **健康需求推荐**
   - 用户："我想要一杯低糖的奶茶"
   - 需要探索不同的产品组合
   - 评估是否符合健康要求
   - 选择最合适的推荐

3. **预算优化推荐**
   - 用户："我想花50元，怎么买最划算"
   - 需要探索不同的产品组合
   - 计算每个组合的总价
   - 选择最优方案

### ❌ 不适合使用 ToT 的场景

1. **简单查询**：如"云边茉莉的价格是多少？" - 直接查询即可，不需要多路径探索
2. **明确下单**：如"我要一杯云边茉莉" - 直接下单即可，不需要规划
3. **产品列表**：如"有哪些产品？" - 直接返回列表即可

## 实现原理

### 1. 思维树结构

```
根节点 (初始推荐)
├── 子节点1 (基于价格的推荐)
│   ├── 子节点1.1 (价格+口味)
│   └── 子节点1.2 (价格+健康)
├── 子节点2 (基于口味的推荐)
│   ├── 子节点2.1 (口味+价格)
│   └── 子节点2.2 (口味+健康)
└── 子节点3 (基于健康的推荐)
    ├── 子节点3.1 (健康+价格)
    └── 子节点3.2 (健康+口味)
```

### 2. 搜索流程

1. **生成思维节点**：使用 LLM 生成多个不同的推荐思路
2. **评估节点质量**：使用 LLM 评估每个推荐的质量（0-1分）
3. **选择最优节点**：选择评分最高的推荐节点
4. **回溯路径**：如果需要，可以回溯到父节点查看推理过程

### 3. 核心组件

#### ThoughtNode（思维节点）

```python
class ThoughtNode:
    thought: str          # 思维内容（推荐路径描述）
    products: List[Dict]  # 推荐的产品列表
    reasoning: str        # 推理过程
    score: float         # 评分（0-1）
    parent: ThoughtNode  # 父节点
    children: List[ThoughtNode]  # 子节点
```

#### ToTRecommendationEngine（推荐引擎）

- `generate_thoughts()`: 生成思维节点（探索不同的推荐路径）
- `evaluate_thought()`: 评估思维节点的质量
- `search()`: 使用广度优先搜索找到最优推荐
- `format_recommendation()`: 格式化推荐结果

## 使用方法

### 1. 直接使用 ToT 引擎

```python
from consult_agent.tot_recommendation import ToTRecommendationEngine
from consult_mcp_server.consult_service import ConsultService

# 初始化
consult_service = ConsultService()
engine = ToTRecommendationEngine(consult_service=consult_service)

# 执行搜索
user_query = "我想要一杯适合我的奶茶，我喜欢清淡的口味"
best_node = engine.search(user_query)

# 格式化结果
if best_node:
    recommendation = engine.format_recommendation(best_node)
    print(recommendation)
```

### 2. 通过 ConsultAgent 使用

```python
from consult_agent.consult_agent import ConsultAgent

# 初始化
agent = ConsultAgent()

# 用户输入包含推荐关键词时，自动使用 ToT
response = agent.chat("我想要一杯适合我的奶茶，推荐一下")
print(response)
```

### 3. 触发关键词

当用户输入包含以下关键词时，会自动使用 ToT 推荐：

- "适合我"
- "推荐"
- "个性化"
- "根据"
- "帮我选"
- "帮我挑"
- "不知道选什么"
- "选择困难"
- "推荐一下"
- "有什么好"

## 配置参数

在 `ToTRecommendationEngine` 中可以调整以下参数：

```python
self.max_depth = 3          # 最大搜索深度
self.branching_factor = 3   # 每个节点的分支数
self.max_nodes = 10         # 最大节点数（防止搜索空间过大）
```

## 示例输出

```
🎯 推荐思路：基于价格和口味的推荐

💡 推荐理由：价格适中，口味清淡，适合喜欢清淡口味的用户

📦 推荐产品：
1. 云边茉莉 - ¥18.00
   清香淡雅，适合喜欢清淡口味的用户
2. 桂花云露 - ¥20.00
   花香浓郁，适合喜欢花香的用户

💰 总价：¥38.00
⭐ 推荐评分：0.85/1.0
```

## 优势与局限

### ✅ 优势

1. **多路径探索**：能够探索多个不同的推荐思路
2. **质量评估**：能够评估每个推荐的质量
3. **最优选择**：能够选择评分最高的推荐
4. **可回溯**：可以查看推荐路径的推理过程

### ⚠️ 局限

1. **计算开销大**：需要多次调用 LLM（生成思维节点 + 评估节点）
2. **响应时间较长**：相比直接推荐，响应时间更长
3. **成本较高**：每次推荐需要多次 API 调用

## 测试

运行测试脚本：

```bash
python test_tot_recommendation.py
```

测试场景包括：
1. 基本功能测试
2. 健康需求推荐
3. 预算优化推荐
4. 思维节点评估

## 与 ReAct 的区别

| 特性 | ReAct | ToT |
|------|-------|-----|
| 规划方式 | 隐式（通过提示词） | 显式（构建思维树） |
| 探索能力 | 单一路径 | 多路径并行探索 |
| 评估机制 | 无显式评估 | 显式评估每个节点 |
| 回溯能力 | 无 | 可以回溯到父节点 |
| 适用场景 | 简单任务 | 复杂决策任务 |
| 计算开销 | 低 | 高 |

## 未来改进

1. **缓存机制**：缓存已评估的节点，减少重复计算
2. **并行评估**：并行评估多个节点，提高效率
3. **自适应深度**：根据任务复杂度动态调整搜索深度
4. **用户反馈学习**：根据用户反馈调整评估标准

## 参考

- [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601)
- [Graph of Thoughts: Solving Elaborate Problems with Large Language Models](https://arxiv.org/abs/2308.09687)

