# A2A 协议实现说明

## 协议概述

A2A (Agent-to-Agent) 协议是基于 **HTTP** 的通信协议，用于 Agent 之间的调用。

## 请求格式

### HTTP 请求

```
POST /a2a/invoke HTTP/1.1
Host: localhost:10006
Content-Type: application/json
Content-Length: <length>

{
  "input": "用户输入内容",
  "chat_id": "chat_123",
  "user_id": "user_456"
}
```

### 请求头

- **Content-Type**: `application/json` (必需)
- **Accept**: `application/json` (可选，推荐)
- 其他标准 HTTP 头（如 `User-Agent` 等）

### 请求体（JSON）

```json
{
  "input": "查询订单 ORDER_001",
  "chat_id": "chat_123",
  "user_id": "user_456"
}
```

**字段说明**:
- `input`: 用户输入内容（必需）
- `chat_id`: 对话ID（可选）
- `user_id`: 用户ID（可选）
- 其他自定义字段（可选）

## 响应格式

### HTTP 响应

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: <length>

{
  "output": "订单信息...",
  "status": "success"
}
```

### 响应头

- **Content-Type**: `application/json` (必需)
- 其他标准 HTTP 头

### 响应体（JSON）

**成功响应**:
```json
{
  "output": "订单信息: ORDER_001, 产品: 云边茉莉, 价格: ¥18.00",
  "status": "success"
}
```

**错误响应**:
```json
{
  "error": "错误信息",
  "status": "error"
}
```

**字段说明**:
- `output`: Agent 处理结果（成功时）
- `error`: 错误信息（失败时）
- `status`: 状态（"success" 或 "error"）

## 流式响应（SSE）

对于长时间运行的任务，支持 Server-Sent Events (SSE) 流式传输：

### 请求

```
POST /a2a/stream HTTP/1.1
Host: localhost:10006
Content-Type: application/json
Accept: text/event-stream

{
  "input": "查询订单 ORDER_001",
  "chat_id": "chat_123",
  "user_id": "user_456"
}
```

### 响应

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"output": "正在查询", "status": "processing"}

data: {"output": "订单信息...", "status": "success"}

```

## 当前实现

### 客户端（A2AClient）

```python
# 发送请求
response = requests.post(
    url,
    json=input_data,  # JSON 格式
    headers={"Content-Type": "application/json"}
)
```

### 服务端（A2AServer）

```python
@app.route('/a2a/invoke', methods=['POST'])
def invoke():
    data = request.json  # Flask 自动解析 JSON
    result = handler(data)
    return jsonify({
        "output": result,
        "status": "success"
    })
```

## 关键点

1. **标准 HTTP**: 使用标准 HTTP POST 请求，没有特殊的协议头
2. **JSON 格式**: 请求和响应都使用 JSON 格式
3. **Content-Type**: 必须设置为 `application/json`
4. **无特殊头**: 不使用特殊的请求头或响应头来标识 A2A 协议
5. **路径标识**: 通过 URL 路径（如 `/a2a/invoke`）来标识 A2A 协议端点

## 与原 Java 项目的对比

原 Java 项目使用 Spring AI Alibaba 框架，A2A 协议的实现可能：
- 使用 Spring Web 框架处理 HTTP 请求
- 可能使用 JSON-RPC 2.0 格式（更规范）
- 可能包含认证头（如 OAuth 2.0）

当前 Python 实现采用简化版本：
- 使用标准 HTTP + JSON
- 不使用 JSON-RPC 2.0（可以后续改进）
- 不使用认证（可以后续添加）

## 改进建议

如果需要更规范的实现，可以考虑：

1. **使用 JSON-RPC 2.0 格式**:
```json
{
  "jsonrpc": "2.0",
  "method": "invoke",
  "params": {
    "input": "...",
    "chat_id": "..."
  },
  "id": 1
}
```

2. **添加认证头**:
```
Authorization: Bearer <token>
X-Agent-Name: order_agent
```

3. **添加版本头**:
```
X-A2A-Version: 1.0
```

但目前简化版本已经足够使用。
