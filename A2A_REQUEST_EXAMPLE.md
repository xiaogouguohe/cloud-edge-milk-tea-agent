# SupervisorAgent 到 OrderAgent 的请求报文示例

## 场景：用户查询历史订单

### 用户输入
```
"我想查询我的历史订单"
```

---

## 1. SupervisorAgent 处理流程

### 1.1 路由判断
SupervisorAgent 识别到这是订单相关请求，路由到 `order_agent`。

### 1.2 构建 A2A 请求

**代码位置**: `supervisor_agent/supervisor_agent.py` 第 140-145 行

```python
a2a_request = {
    "input": user_input,
    "chat_id": self.chat_id,
    "user_id": self.user_id
}
```

---

## 2. HTTP 请求报文

### 2.1 请求 URL
```
POST http://localhost:10006/a2a/invoke
```

**说明**: 
- 从 `services.json` 获取 `order_agent` 的 URL: `http://localhost:10006`
- A2A 协议端点: `/a2a/invoke`

### 2.2 请求头 (Headers)

```http
Content-Type: application/json
```

### 2.3 请求体 (Request Body)

```json
{
    "input": "我想查询我的历史订单",
    "chat_id": "chat_123456",
    "user_id": "user_789012"
}
```

**字段说明**:
- `input`: 用户的原始输入文本
- `chat_id`: 对话ID，用于区分不同的对话会话
- `user_id`: 用户ID，用于标识用户身份（OrderAgent 会使用此 ID 查询该用户的订单）

---

## 3. 完整的 HTTP 请求示例

### 使用 curl 命令

```bash
curl -X POST http://localhost:10006/a2a/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input": "我想查询我的历史订单",
    "chat_id": "chat_123456",
    "user_id": "user_789012"
  }'
```

### 使用 Python requests

```python
import requests

url = "http://localhost:10006/a2a/invoke"
headers = {"Content-Type": "application/json"}
data = {
    "input": "我想查询我的历史订单",
    "chat_id": "chat_123456",
    "user_id": "user_789012"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

---

## 4. OrderAgent 处理流程

### 4.1 接收请求

**代码位置**: `order_agent/order_agent.py` 第 380-410 行

```python
def handle_request(data: Dict) -> str:
    """处理 A2A 协议请求"""
    user_input = data.get("input", "")
    request_user_id = data.get("user_id")
    
    if request_user_id:
        # 使用请求中的 user_id
        self.user_id = str(request_user_id)
    
    # 调用 chat 方法处理
    result = self.chat(user_input)
    return result
```

### 4.2 处理用户输入

OrderAgent 的 `chat` 方法会：
1. 分析用户输入，判断需要调用哪个工具
2. 对于"查询订单"，会调用 `order-get-order` 工具
3. 使用 `user_id` 参数查询该用户的订单

---

## 5. HTTP 响应报文

### 5.1 成功响应

**状态码**: `200 OK`

**响应头**:
```http
Content-Type: application/json
```

**响应体**:
```json
{
    "output": "您有以下历史订单：\n\n1. 订单号: ORD001\n   产品: 云边茉莉\n   数量: 2\n   价格: ¥36.00\n   状态: 已完成\n   下单时间: 2025-01-15 10:30:00\n\n2. 订单号: ORD002\n   产品: 桂花云露\n   数量: 1\n   价格: ¥22.00\n   状态: 已完成\n   下单时间: 2025-01-14 15:20:00",
    "status": "success"
}
```

### 5.2 错误响应

**状态码**: `500 Internal Server Error`

**响应体**:
```json
{
    "error": "工具调用失败: 无法连接到数据库",
    "status": "error"
}
```

---

## 6. 完整通信流程

```
用户: "我想查询我的历史订单"
  ↓
SupervisorAgent.route_to_agent() 
  → 识别为订单相关，返回 "order_agent"
  ↓
SupervisorAgent.call_sub_agent("order_agent", "我想查询我的历史订单")
  ↓
构建 A2A 请求:
{
  "input": "我想查询我的历史订单",
  "chat_id": "chat_123456",
  "user_id": "user_789012"
}
  ↓
A2AClient.call_agent("order_agent", a2a_request)
  ↓
HTTP POST http://localhost:10006/a2a/invoke
  ↓
OrderAgent.handle_request(data)
  → 提取 user_id = "user_789012"
  → 调用 self.chat("我想查询我的历史订单")
  ↓
OrderAgent.chat()
  → 分析输入，判断需要调用工具
  → 调用 MCP 工具: order-get-order
  → 参数: {"userId": "user_789012"}
  ↓
OrderMCPServer 查询数据库
  → SELECT * FROM orders WHERE user_id = 'user_789012'
  ↓
返回订单列表
  ↓
OrderAgent 格式化结果，生成友好回复
  ↓
返回 A2A 响应:
{
  "output": "您有以下历史订单：...",
  "status": "success"
}
  ↓
SupervisorAgent 提取 output 字段
  ↓
返回给用户
```

---

## 7. 关键点说明

### 7.1 user_id 的传递

- **SupervisorAgent** 在构建请求时，会将 `self.user_id` 放入请求的 `user_id` 字段
- **OrderAgent** 接收请求后，会使用请求中的 `user_id` 来查询订单
- 这确保了只能查询当前用户的订单，保护用户隐私

### 7.2 请求格式

A2A 协议的请求格式是固定的：
```json
{
    "input": "用户输入文本",
    "chat_id": "对话ID",
    "user_id": "用户ID"
}
```

### 7.3 响应格式

A2A 协议的响应格式：
```json
{
    "output": "Agent 处理结果",
    "status": "success" | "error"
}
```

---

## 8. 其他场景示例

### 场景 2: 用户下单

**请求**:
```json
{
    "input": "我要下单，一杯云边茉莉，少糖，正常冰",
    "chat_id": "chat_123456",
    "user_id": "user_789012"
}
```

### 场景 3: 用户查询特定订单

**请求**:
```json
{
    "input": "查询订单号 ORD001 的详情",
    "chat_id": "chat_123456",
    "user_id": "user_789012"
}
```

---

## 9. 测试方法

### 9.1 使用测试脚本

```bash
python3 test_supervisor_consult_communication.py
```

### 9.2 手动测试

1. 启动 OrderAgent:
```bash
python3 order_agent/run_order_agent.py
```

2. 使用 curl 测试:
```bash
curl -X POST http://localhost:10006/a2a/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input": "我想查询我的历史订单",
    "chat_id": "test_chat",
    "user_id": "test_user"
  }'
```

3. 使用 SupervisorAgent:
```python
from supervisor_agent.supervisor_agent import SupervisorAgent

supervisor = SupervisorAgent(user_id="test_user", chat_id="test_chat")
response = supervisor.chat("我想查询我的历史订单")
print(response)
```

