# Human-in-the-Loop 业务场景分析

## 适合引入 Human-in-the-Loop 的场景

### 1. **高风险订单确认** ⭐⭐⭐⭐⭐

**场景**：大额订单或异常订单需要人工确认

**触发条件**：
- 订单金额超过阈值（如 ¥200）
- 订单数量异常（如单次购买超过 10 杯）
- 短时间内重复下单（如 5 分钟内下单 3 次以上）

**实现方式**：
```python
def _create_order(self, userId: int, productName: str, ...):
    # 计算订单金额
    total_price = unit_price * quantity
    
    # 检查是否需要人工确认
    if total_price > 200 or quantity > 10:
        # 触发 human-in-the-loop
        approval = interrupt({
            "type": "order_approval",
            "message": f"检测到大额订单（总价：¥{total_price}，数量：{quantity}），请确认是否继续？",
            "order_info": {
                "userId": userId,
                "productName": productName,
                "quantity": quantity,
                "totalPrice": total_price
            }
        })
        
        if approval != "approved":
            return "订单已取消"
    
    # 继续创建订单
    return self.order_service.create_order(...)
```

**业务价值**：
- 防止误操作或恶意下单
- 保护用户资金安全
- 可以人工审核异常订单

---

### 2. **投诉处理人工介入** ⭐⭐⭐⭐⭐

**场景**：用户投诉或差评时，需要人工审核和安抚

**触发条件**：
- 用户反馈类型为"投诉"
- 评分低于 3 星
- 反馈内容包含敏感词（如"退款"、"投诉"、"差评"）

**实现方式**：
```python
def handle_feedback(self, user_id: int, feedback_type: int, content: str):
    # 检查是否需要人工介入
    if feedback_type == 1 or "退款" in content or "投诉" in content:
        # 触发 human-in-the-loop
        human_response = interrupt({
            "type": "feedback_review",
            "message": "检测到用户投诉，需要人工处理",
            "feedback_info": {
                "user_id": user_id,
                "type": feedback_type,
                "content": content
            },
            "suggested_response": "AI 生成的建议回复..."
        })
        
        # 使用人工回复
        return human_response.get("response")
    
    # 普通反馈，AI 自动处理
    return self.ai_process_feedback(...)
```

**业务价值**：
- 提升客户满意度
- 避免 AI 回复不当引发更大问题
- 重要投诉需要人工跟进

---

### 3. **订单修改/取消确认** ⭐⭐⭐⭐

**场景**：已支付订单的修改或取消需要确认

**触发条件**：
- 修改已支付订单
- 取消已支付订单
- 订单状态为"已制作"或"配送中"

**实现方式**：
```python
def update_order(self, user_id: int, order_id: str, changes: dict):
    # 查询订单状态
    order = self.get_order(order_id)
    
    if order.status in ["paid", "preparing", "delivering"]:
        # 需要人工确认
        approval = interrupt({
            "type": "order_modification",
            "message": f"订单 {order_id} 已支付/制作中，修改需要人工确认",
            "order_info": order,
            "requested_changes": changes
        })
        
        if approval != "approved":
            return "订单修改已取消"
    
    # 继续修改订单
    return self.order_service.update_order(...)
```

**业务价值**：
- 避免已制作订单被误修改
- 需要协调门店和配送
- 保护商家利益

---

### 4. **个性化推荐确认** ⭐⭐⭐

**场景**：基于用户记忆的推荐，让用户确认是否真的想要

**触发条件**：
- AI 基于用户历史行为推荐新产品
- 推荐的产品价格较高（如 ¥30+）
- 用户之前从未购买过该产品

**实现方式**：
```python
def recommend_product(self, user_id: int):
    # AI 生成推荐
    recommendation = self.ai_recommend(user_id)
    
    # 如果推荐的是高价新品，需要确认
    if recommendation.price > 30 and recommendation.is_new_to_user:
        user_choice = interrupt({
            "type": "product_recommendation",
            "message": f"根据您的喜好，为您推荐：{recommendation.name}（¥{recommendation.price}）",
            "reason": recommendation.reason,
            "options": ["确认下单", "查看详情", "换一个"]
        })
        
        if user_choice == "确认下单":
            return self.create_order(user_id, recommendation.name, ...)
        elif user_choice == "查看详情":
            return self.show_product_details(recommendation)
    
    return recommendation
```

**业务价值**：
- 提升推荐准确性
- 避免用户对推荐不满
- 增加用户参与感

---

### 5. **异常库存处理** ⭐⭐⭐

**场景**：库存不足时，提供替代方案需要确认

**触发条件**：
- 用户下单的产品库存不足
- 有相似产品可以替代

**实现方式**：
```python
def create_order(self, user_id: int, product_name: str, ...):
    # 检查库存
    stock = self.check_stock(product_name)
    
    if stock < quantity:
        # 查找替代产品
        alternatives = self.find_alternatives(product_name)
        
        if alternatives:
            # 需要用户选择
            choice = interrupt({
                "type": "stock_alternative",
                "message": f"{product_name} 库存不足（剩余：{stock}），为您推荐替代产品：",
                "alternatives": alternatives,
                "options": ["选择替代产品", "等待补货", "取消订单"]
            })
            
            if choice.get("action") == "select_alternative":
                product_name = choice.get("selected_product")
            elif choice.get("action") == "wait":
                return "已为您加入补货通知列表"
            else:
                return "订单已取消"
    
    # 继续创建订单
    return self.order_service.create_order(...)
```

**业务价值**：
- 提升用户体验
- 减少订单取消率
- 智能推荐替代方案

---

### 6. **特殊需求处理** ⭐⭐⭐

**场景**：用户有特殊需求（如过敏、特殊要求）需要人工确认

**触发条件**：
- 备注中包含"过敏"、"无糖"、"特殊要求"等关键词
- 用户要求与标准流程不符

**实现方式**：
```python
def create_order(self, user_id: int, product_name: str, remark: str, ...):
    # 检查特殊需求
    special_keywords = ["过敏", "无糖", "特殊", "定制", "要求"]
    
    if any(keyword in remark for keyword in special_keywords):
        # 需要人工确认是否能满足
        confirmation = interrupt({
            "type": "special_request",
            "message": f"用户有特殊需求：{remark}",
            "order_info": {
                "product": product_name,
                "remark": remark
            },
            "options": ["可以满足", "需要调整", "无法满足"]
        })
        
        if confirmation == "无法满足":
            return "抱歉，无法满足您的特殊需求，请联系客服"
        elif confirmation == "需要调整":
            adjusted_order = confirmation.get("adjusted_info")
            # 使用调整后的订单信息
            return self.create_order_with_adjustment(...)
    
    # 继续创建订单
    return self.order_service.create_order(...)
```

**业务价值**：
- 满足用户个性化需求
- 避免订单完成后无法满足要求
- 提升服务质量

---

## 实现优先级建议

### 高优先级（建议先实现）
1. **投诉处理人工介入** - 直接影响客户满意度
2. **高风险订单确认** - 保护用户和商家利益

### 中优先级
3. **订单修改/取消确认** - 避免已支付订单被误操作
4. **异常库存处理** - 提升用户体验

### 低优先级（可选）
5. **个性化推荐确认** - 锦上添花的功能
6. **特殊需求处理** - 根据业务量决定

---

## 实现建议

### 1. 渐进式引入
- 先实现 1-2 个核心场景
- 根据实际使用情况调整
- 逐步扩展到其他场景

### 2. 用户体验设计
- 中断提示要友好、清晰
- 提供明确的选项
- 支持快速审批（如管理员一键通过）

### 3. 技术实现
- 使用状态持久化（支持异步审批）
- 提供审批历史记录
- 支持批量审批

### 4. 业务规则
- 定义清晰的触发条件
- 设置审批超时机制
- 记录审批日志

---

## 示例：实现高风险订单确认

```python
# 在 order_agent.py 中添加
def _should_interrupt_for_approval(self, parameters: Dict) -> Optional[Dict]:
    """判断是否需要人工审批"""
    total_price = self._calculate_price(parameters)
    quantity = parameters.get("quantity", 1)
    
    # 触发条件
    if total_price > 200 or quantity > 10:
        return {
            "type": "order_approval",
            "message": f"大额订单需要确认（总价：¥{total_price}，数量：{quantity}）",
            "order_info": parameters
        }
    return None

def _invoke_tool_with_approval(self, tool_name: str, mcp_server: str, parameters: Dict):
    """带审批的工具调用"""
    # 检查是否需要审批
    approval_request = self._should_interrupt_for_approval(parameters)
    
    if approval_request:
        # 触发 human-in-the-loop
        from langgraph.types import interrupt
        
        approval = interrupt(approval_request)
        
        if approval.get("action") != "approved":
            return f"订单已取消：{approval.get('reason', '用户取消')}"
    
    # 继续调用工具
    return self._invoke_tool(tool_name, mcp_server, parameters)
```

---

## 总结

Human-in-the-loop 在奶茶店业务中最适合的场景是：
1. **保护性场景**：大额订单、异常操作
2. **服务性场景**：投诉处理、特殊需求
3. **体验性场景**：推荐确认、库存替代

建议从**投诉处理**和**高风险订单确认**开始实现，这两个场景业务价值最高，也最容易看到效果。
