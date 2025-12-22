# 协议报文示例

本文档展示用户下单时，各个组件之间的实际请求和响应报文。

## 场景：用户下单

**用户输入**：`"我要下单，云边茉莉，标准糖，正常冰，1杯，用户ID是12345678901"`

---

## 1. SupervisorAgent → OrderAgent (A2A 协议)

### 请求报文

**HTTP 请求**：
```http
POST http://localhost:10006/a2a/invoke HTTP/1.1
Host: localhost:10006
Content-Type: application/json
Content-Length: 123

{
  "input": "我要下单，云边茉莉，标准糖，正常冰，1杯，用户ID是12345678901",
  "chat_id": "default_chat",
  "user_id": "12345678901"
}
```

**Python 代码构建**（来自 `supervisor_agent.py`）：
```python
a2a_request = {
    "input": user_input,
    "chat_id": self.chat_id,
    "user_id": self.user_id
}
```

### 响应报文

**HTTP 响应**：
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 456

{
  "output": "好的，我已经为您创建了订单！\n\n订单详情：\n- 订单ID: ORDER_1766350475701\n- 产品: 云边茉莉\n- 甜度: 标准糖\n- 冰量: 正常冰\n- 数量: 1杯\n- 总价: ¥18.00\n\n订单已成功创建，感谢您的购买！",
  "status": "success"
}
```

**Python 代码解析**（来自 `supervisor_agent.py`）：
```python
a2a_response = self.a2a_client.call_agent(agent_name, a2a_request)
output = a2a_response.get("output", "")  # 提取 output 字段
```

---

## 2. OrderAgent → OrderMCPServer (MCP 协议)

### 请求报文

**HTTP 请求**：
```http
POST http://localhost:10002/mcp/tools/order-create-order-with-user/invoke HTTP/1.1
Host: localhost:10002
Content-Type: application/json
Content-Length: 156

{
  "parameters": {
    "userId": 12345678901,
    "productName": "云边茉莉",
    "sweetness": "标准糖",
    "iceLevel": "正常冰",
    "quantity": 1
  }
}
```

**Python 代码构建**（来自 `order_agent.py`）：
```python
parameters = {
    "userId": user_id,
    "productName": product_name,
    "sweetness": sweetness,
    "iceLevel": ice_level,
    "quantity": quantity
}
result = self.mcp_client.invoke_tool("order-mcp-server", "order-create-order-with-user", parameters)
```

### 响应报文

**HTTP 响应**：
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 234

{
  "result": "订单创建成功！\n订单ID: ORDER_1766350475701\n用户ID: 12345678901\n产品: 云边茉莉\n甜度: 标准糖\n冰量: 正常冰\n数量: 1\n总价: ¥18.00",
  "status": "success"
}
```

**Python 代码解析**（来自 `mcp/server.py`）：
```python
data = request.json  # {"parameters": {...}}
parameters = data.get("parameters", {})  # 提取参数
result = tool.invoke(parameters)  # 调用工具
return jsonify({"result": result, "status": "success"})
```

---

## 3. OrderAgent 内部处理流程

### 步骤 1: 接收 A2A 请求

```python
# OrderAgent.handle_request() 接收
data = {
    "input": "我要下单，云边茉莉，标准糖，正常冰，1杯，用户ID是12345678901",
    "chat_id": "default_chat",
    "user_id": "12345678901"
}
```

### 步骤 2: LLM 判断并提取参数

```python
# OrderAgent._should_use_tool() 返回
tool_call = {
    "tool": "order-create-order-with-user",
    "mcp_server": "order-mcp-server",
    "parameters": {
        "userId": 12345678901,
        "productName": "云边茉莉",
        "sweetness": "标准糖",
        "iceLevel": "正常冰",
        "quantity": 1
    }
}
```

### 步骤 3: 调用 MCP 工具

```python
# OrderAgent._invoke_tool() 调用
tool_result = "订单创建成功！\n订单ID: ORDER_1766350475701\n..."
```

### 步骤 4: LLM 整合结果并生成回复

```python
# OrderAgent.chat() 最终返回
final_response = "好的，我已经为您创建了订单！\n\n订单详情：\n- 订单ID: ORDER_1766350475701\n..."
```

---

## 完整数据流

```
用户输入
  ↓
SupervisorAgent
  ↓ (A2A 请求)
POST /a2a/invoke
{
  "input": "我要下单...",
  "user_id": "12345678901"
}
  ↓
OrderAgent 接收
  ↓ (LLM 判断需要调用工具)
  ↓ (MCP 请求)
POST /mcp/tools/order-create-order-with-user/invoke
{
  "parameters": {
    "userId": 12345678901,
    "productName": "云边茉莉",
    ...
  }
}
  ↓
OrderMCPServer 接收
  ↓ (调用数据库)
  ↓ (MCP 响应)
{
  "result": "订单创建成功！...",
  "status": "success"
}
  ↓
OrderAgent 整合结果
  ↓ (A2A 响应)
{
  "output": "好的，我已经为您创建了订单！...",
  "status": "success"
}
  ↓
SupervisorAgent 返回给用户
```

---

## 报文格式总结

### A2A 协议

**请求格式**：
```json
{
  "input": "用户输入文本",
  "chat_id": "对话ID",
  "user_id": "用户ID"
}
```

**响应格式**：
```json
{
  "output": "Agent 的回复文本",
  "status": "success"  // 或 "error"
}
```

### MCP 协议

**请求格式**：
```json
{
  "parameters": {
    "参数名1": "参数值1",
    "参数名2": "参数值2",
    ...
  }
}
```

**响应格式**：
```json
{
  "result": "工具执行结果（字符串）",
  "status": "success"  // 或 "error"
}
```

---

## 错误响应示例

### A2A 协议错误响应

```json
{
  "error": "Handler not set",
  "status": "error"
}
```

### MCP 协议错误响应

```json
{
  "error": "Tool order-create-order-with-user not found",
  "status": "error"
}
```

HTTP 状态码：`500 Internal Server Error`
