# SupervisorAgent 路由改进方案

## 问题分析

### 当前问题

用户输入："我要一杯云雾观音，标准糖，热饮，备注：不要珍珠"

**当前关键词匹配**：
```python
order_keywords = ["下单", "订单", "点单", "购买", "结账", "支付", "购物车", "取消订单", "修改订单", "查询订单"]
```

**匹配结果**：❌ **False** - 无法识别为订单请求

**原因**：用户没有明确说"下单"、"点单"等关键词，只是直接说"我要一杯..."

---

## 解决方案

### 方案1：使用 LLM 进行智能路由（推荐）⭐

**优点**：
- ✅ 能理解用户真实意图
- ✅ 不需要维护关键词列表
- ✅ 可以处理各种表达方式

**实现**：

```python
def route_to_agent(self, user_input: str) -> Optional[str]:
    """
    使用 LLM 分析用户输入，判断应该路由到哪个子智能体
    """
    # 构建路由判断的 Prompt
    prompt = f"""你是云边奶茶铺的监督者智能体，需要分析用户请求并路由到合适的子智能体。

可用子智能体：
1. order_agent - 处理订单相关业务，包括下单、查询、修改等
2. consult_agent - 处理产品咨询、活动信息和冲泡指导
3. feedback_agent - 处理用户反馈、投诉和差评

用户请求: {user_input}

请判断这个请求应该路由到哪个子智能体。如果用户想要：
- 下单、点单、购买、查询订单、修改订单、取消订单 → order_agent
- 咨询产品、了解活动、询问价格、推荐产品 → consult_agent
- 反馈、投诉、建议、差评 → feedback_agent
- 一般性对话 → 返回 None

请只返回智能体名称（order_agent、consult_agent、feedback_agent）或 None，不要其他文字。"""

    try:
        response = Generation.call(
            model=DASHSCOPE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 低温度，确保路由准确性
            result_format='message'
        )
        
        if response.status_code == 200:
            result = response.output.choices[0].message.content.strip()
            # 清理可能的格式问题
            result = result.lower().replace(" ", "_")
            
            if result in ["order_agent", "consult_agent", "feedback_agent"]:
                return result
            elif result == "none" or result == "null":
                return None
    except Exception as e:
        print(f"[SupervisorAgent] LLM 路由判断失败: {str(e)}", file=sys.stderr, flush=True)
    
    # LLM 失败时，回退到关键词匹配
    return self._route_by_keywords(user_input)
```

---

### 方案2：扩展关键词列表 + 产品名称检测

**优点**：
- ✅ 实现简单
- ✅ 不需要调用 LLM
- ✅ 性能好

**缺点**：
- ❌ 需要维护关键词和产品名称列表
- ❌ 可能遗漏某些表达方式

**实现**：

```python
def route_to_agent(self, user_input: str) -> Optional[str]:
    """
    分析用户输入，判断应该路由到哪个子智能体
    """
    user_input_lower = user_input.lower()
    
    # 订单相关关键词（扩展版）
    order_keywords = [
        "下单", "订单", "点单", "购买", "结账", "支付", "购物车",
        "取消订单", "修改订单", "查询订单", "我要", "给我", "来一杯",
        "来一份", "要一杯", "要一份", "点一杯", "点一份"
    ]
    
    # 产品名称列表
    product_names = [
        "云边茉莉", "桂花云露", "云雾观音", "珍珠奶茶", "红豆奶茶",
        "奶茶", "茉莉", "桂花", "观音"
    ]
    
    # 订单相关关键词匹配
    if any(keyword in user_input_lower for keyword in order_keywords):
        return "order_agent"
    
    # 产品名称 + 数量/规格匹配（如"一杯"、"一份"、"少糖"等）
    has_product = any(product in user_input for product in product_names)
    has_quantity = any(word in user_input for word in ["一杯", "一份", "两杯", "两份", "1杯", "2杯"])
    has_spec = any(word in user_input for word in ["少糖", "半糖", "微糖", "无糖", "标准糖", 
                                                    "正常冰", "少冰", "去冰", "温", "热"])
    
    # 如果包含产品名称 + (数量或规格)，认为是下单请求
    if has_product and (has_quantity or has_spec):
        return "order_agent"
    
    # 反馈相关关键词
    feedback_keywords = ["反馈", "投诉", "建议", "差评", "不满意", "问题", "意见"]
    if any(keyword in user_input_lower for keyword in feedback_keywords):
        return "feedback_agent"
    
    # 咨询相关关键词
    consult_keywords = ["咨询", "介绍", "推荐", "产品", "活动", "优惠", "价格", "口味", "什么", "怎么", "如何"]
    if any(keyword in user_input_lower for keyword in consult_keywords):
        return "consult_agent"
    
    return None
```

---

### 方案3：混合方案（推荐用于生产环境）⭐⭐

**结合方案1和方案2**：
- 先用关键词快速匹配（性能好）
- 如果匹配不上，再用 LLM 判断（准确性高）

**实现**：

```python
def route_to_agent(self, user_input: str) -> Optional[str]:
    """
    混合路由：先关键词匹配，失败则使用 LLM
    """
    # 第一步：快速关键词匹配
    result = self._route_by_keywords(user_input)
    if result:
        return result
    
    # 第二步：如果关键词匹配失败，使用 LLM 判断
    return self._route_by_llm(user_input)

def _route_by_keywords(self, user_input: str) -> Optional[str]:
    """关键词匹配路由"""
    user_input_lower = user_input.lower()
    
    # 订单相关关键词（扩展版）
    order_keywords = [
        "下单", "订单", "点单", "购买", "结账", "支付", "购物车",
        "取消订单", "修改订单", "查询订单", "我要", "给我", "来一杯",
        "来一份", "要一杯", "要一份", "点一杯", "点一份"
    ]
    
    # 产品名称列表
    product_names = ["云边茉莉", "桂花云露", "云雾观音", "珍珠奶茶", "红豆奶茶"]
    
    # 订单相关关键词匹配
    if any(keyword in user_input_lower for keyword in order_keywords):
        return "order_agent"
    
    # 产品名称 + 数量/规格匹配
    has_product = any(product in user_input for product in product_names)
    has_quantity = any(word in user_input for word in ["一杯", "一份", "两杯", "两份"])
    has_spec = any(word in user_input for word in ["少糖", "半糖", "微糖", "无糖", "标准糖", 
                                                    "正常冰", "少冰", "去冰", "温", "热"])
    
    if has_product and (has_quantity or has_spec):
        return "order_agent"
    
    # 反馈相关关键词
    feedback_keywords = ["反馈", "投诉", "建议", "差评", "不满意", "问题", "意见"]
    if any(keyword in user_input_lower for keyword in feedback_keywords):
        return "feedback_agent"
    
    # 咨询相关关键词
    consult_keywords = ["咨询", "介绍", "推荐", "产品", "活动", "优惠", "价格", "口味", "什么", "怎么", "如何"]
    if any(keyword in user_input_lower for keyword in consult_keywords):
        return "consult_agent"
    
    return None

def _route_by_llm(self, user_input: str) -> Optional[str]:
    """使用 LLM 进行路由判断"""
    prompt = f"""你是云边奶茶铺的监督者智能体，需要分析用户请求并路由到合适的子智能体。

可用子智能体：
1. order_agent - 处理订单相关业务，包括下单、查询、修改等
2. consult_agent - 处理产品咨询、活动信息和冲泡指导
3. feedback_agent - 处理用户反馈、投诉和差评

用户请求: {user_input}

请判断这个请求应该路由到哪个子智能体。如果用户想要：
- 下单、点单、购买、查询订单、修改订单、取消订单 → order_agent
- 咨询产品、了解活动、询问价格、推荐产品 → consult_agent
- 反馈、投诉、建议、差评 → feedback_agent
- 一般性对话 → 返回 None

请只返回智能体名称（order_agent、consult_agent、feedback_agent）或 None，不要其他文字。"""

    try:
        response = Generation.call(
            model=DASHSCOPE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            result_format='message'
        )
        
        if response.status_code == 200:
            result = response.output.choices[0].message.content.strip().lower()
            result = result.replace(" ", "_")
            
            if result in ["order_agent", "consult_agent", "feedback_agent"]:
                return result
    except Exception as e:
        print(f"[SupervisorAgent] LLM 路由判断失败: {str(e)}", file=sys.stderr, flush=True)
    
    return None
```

---

## 测试验证

### 测试用例

```python
test_cases = [
    ("我要一杯云雾观音，标准糖，热饮，备注：不要珍珠", "order_agent"),
    ("给我来一杯云边茉莉，少糖，正常冰", "order_agent"),
    ("点一份桂花云露，半糖，去冰", "order_agent"),
    ("查询订单 ORDER_xxx", "order_agent"),
    ("云边茉莉多少钱？", "consult_agent"),
    ("推荐一款奶茶", "consult_agent"),
    ("我要投诉，订单太慢了", "feedback_agent"),
    ("你好", None),  # 一般性对话
]
```

---

## 推荐方案

### 对于当前项目

**推荐使用方案3（混合方案）**：

1. **性能优化**：大部分请求可以通过关键词快速匹配，避免 LLM 调用
2. **准确性保证**：关键词匹配失败时，使用 LLM 确保准确性
3. **成本控制**：减少 LLM 调用次数，降低 API 成本
4. **用户体验**：快速响应 + 准确路由

### 实现优先级

1. **短期**：先实现方案2（扩展关键词 + 产品名称检测），快速解决问题
2. **中期**：升级到方案3（混合方案），提升准确性和性能
3. **长期**：如果关键词维护成本高，可以考虑完全使用 LLM（方案1）

---

## 总结

**问题**：用户说"我要一杯云雾观音..."无法匹配到 order_agent

**原因**：当前关键词列表不包含"我要"、"一杯"等表达方式

**解决方案**：
1. ✅ 扩展关键词列表（添加"我要"、"一杯"等）
2. ✅ 添加产品名称检测
3. ✅ 使用 LLM 进行智能路由（推荐）
4. ✅ 混合方案（关键词 + LLM，最佳实践）

