# OrderAgent 与 LLM 交互内容示例

## 场景：用户查询历史订单

### 用户输入
```
"我想查询我的历史订单"
```

---

## 1. OrderAgent 构建工具描述

OrderAgent 会从 MCP Server 加载所有可用工具，然后构建工具描述字符串。

### 1.1 所有可用工具列表

```python
# 从 order-mcp-server 加载的工具列表
available_tools = [
    {
        "name": "order-get-order",
        "description": "根据订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": "订单ID，格式为ORDER_开头的唯一标识符，例如：ORDER_1693654321000"
                }
            },
            "required": ["orderId"]
        }
    },
    {
        "name": "order-get-order-by-user",
        "description": "根据用户ID和订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "integer",
                    "description": "用户ID，必须为正整数"
                },
                "orderId": {
                    "type": "string",
                    "description": "订单ID，格式为ORDER_开头的唯一标识符"
                }
            },
            "required": ["userId", "orderId"]
        }
    },
    {
        "name": "order-create-order-with-user",
        "description": "为用户创建新的奶茶订单。支持云边奶茶铺的所有产品，包括云边茉莉、桂花云露、云雾观音等经典产品。系统会自动检查库存并计算价格。",
        "parameters": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "integer",
                    "description": "用户ID，必须为正整数"
                },
                "productName": {
                    "type": "string",
                    "description": "产品名称，必须是云边奶茶铺的现有产品"
                },
                "sweetness": {
                    "type": "string",
                    "description": "甜度要求，可选值：标准糖、少糖、半糖、微糖、无糖",
                    "enum": ["无糖", "微糖", "半糖", "少糖", "标准糖"]
                },
                "iceLevel": {
                    "type": "string",
                    "description": "冰量要求，可选值：正常冰、少冰、去冰、温、热",
                    "enum": ["热", "温", "去冰", "少冰", "正常冰"]
                },
                "quantity": {
                    "type": "integer",
                    "description": "购买数量，必须为正整数，默认为1",
                    "minimum": 1
                },
                "remark": {
                    "type": "string",
                    "description": "订单备注，可选"
                }
            },
            "required": ["userId", "productName", "sweetness", "iceLevel", "quantity"]
        }
    },
    {
        "name": "order-get-orders-by-user",
        "description": "根据用户ID获取该用户的所有订单列表，包括订单ID、产品信息、价格和创建时间。用于查看用户的订单历史。",
        "parameters": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "integer",
                    "description": "用户ID，必须为正整数"
                }
            },
            "required": ["userId"]
        }
    },
    {
        "name": "order-delete-order",
        "description": "删除指定用户的订单。只能删除自己的订单，不能删除其他用户的订单。",
        "parameters": {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "integer",
                    "description": "用户ID，必须为正整数"
                },
                "orderId": {
                    "type": "string",
                    "description": "订单ID，格式为ORDER_开头的唯一标识符"
                }
            },
            "required": ["userId", "orderId"]
        }
    }
]
```

### 1.2 构建工具描述字符串

OrderAgent 会将工具列表转换为文本描述：

```python
tools_desc = """- order-get-order: 根据订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。
  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符，例如：ORDER_1693654321000 (类型: string, 必需: True)
- order-get-order-by-user: 根据用户ID和订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符 (类型: string, 必需: True)
- order-create-order-with-user: 为用户创建新的奶茶订单。支持云边奶茶铺的所有产品，包括云边茉莉、桂花云露、云雾观音等经典产品。系统会自动检查库存并计算价格。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
  参数 productName: 产品名称，必须是云边奶茶铺的现有产品 (类型: string, 必需: True)
  参数 sweetness: 甜度要求，可选值：标准糖、少糖、半糖、微糖、无糖 (类型: string, 必需: True)
  参数 iceLevel: 冰量要求，可选值：正常冰、少冰、去冰、温、热 (类型: string, 必需: True)
  参数 quantity: 购买数量，必须为正整数，默认为1 (类型: integer, 必需: True)
  参数 remark: 订单备注，可选 (类型: string, 必需: False)
- order-get-orders-by-user: 根据用户ID获取该用户的所有订单列表，包括订单ID、产品信息、价格和创建时间。用于查看用户的订单历史。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
- order-delete-order: 删除指定用户的订单。只能删除自己的订单，不能删除其他用户的订单。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符 (类型: string, 必需: True)"""
```

---

## 2. OrderAgent 发送给 LLM 的完整 Prompt

### 2.1 完整 Prompt 内容

```python
prompt = """你是一个订单处理智能体，需要判断用户请求是否需要调用工具，并提取参数。

可用工具列表:
- order-get-order: 根据订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。
  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符，例如：ORDER_1693654321000 (类型: string, 必需: True)
- order-get-order-by-user: 根据用户ID和订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符 (类型: string, 必需: True)
- order-create-order-with-user: 为用户创建新的奶茶订单。支持云边奶茶铺的所有产品，包括云边茉莉、桂花云露、云雾观音等经典产品。系统会自动检查库存并计算价格。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
  参数 productName: 产品名称，必须是云边奶茶铺的现有产品 (类型: string, 必需: True)
  参数 sweetness: 甜度要求，可选值：标准糖、少糖、半糖、微糖、无糖 (类型: string, 必需: True)
  参数 iceLevel: 冰量要求，可选值：正常冰、少冰、去冰、温、热 (类型: string, 必需: True)
  参数 quantity: 购买数量，必须为正整数，默认为1 (类型: integer, 必需: True)
  参数 remark: 订单备注，可选 (类型: string, 必需: False)
- order-get-orders-by-user: 根据用户ID获取该用户的所有订单列表，包括订单ID、产品信息、价格和创建时间。用于查看用户的订单历史。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
- order-delete-order: 删除指定用户的订单。只能删除自己的订单，不能删除其他用户的订单。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符 (类型: string, 必需: True)

用户请求: 我想查询我的历史订单

重要提示:
- 当前用户ID是: 789012（整数类型）
- 如果工具需要 userId 参数，必须使用整数类型: 789012
- 从用户输入中提取产品名称、甜度、冰量、数量等信息
- 如果用户输入中包含用户ID，使用用户输入中的ID；否则使用当前会话的用户ID: 789012

请判断：
1. 是否需要调用工具？如果需要，返回工具名称
2. 如果需要，提取所有必需的参数（userId 必须是整数类型）

请以 JSON 格式返回，格式如下：
- 如果不需要工具: {"use_tool": false}
- 如果需要工具: {"use_tool": true, "tool_name": "工具名称", "mcp_server": "order-mcp-server", "parameters": {"userId": 789012, "productName": "产品名称", "sweetness": "甜度", "iceLevel": "冰量", "quantity": 数量}}

注意：userId 和 quantity 必须是数字类型，不是字符串。

只返回 JSON，不要其他文字。"""
```

---

## 3. LLM 的响应

### 3.1 期望的 LLM 响应

```json
{
    "use_tool": true,
    "tool_name": "order-get-orders-by-user",
    "mcp_server": "order-mcp-server",
    "parameters": {
        "userId": 789012
    }
}
```

### 3.2 LLM 响应说明

对于"我想查询我的历史订单"这个请求，LLM 应该：
1. 识别这是查询订单的请求
2. 选择 `order-get-orders-by-user` 工具（因为要查询"所有订单"）
3. 提取 `userId` 参数，使用当前会话的用户ID: `789012`
4. 返回 JSON 格式的工具调用信息

---

## 4. 完整的 HTTP 请求（OrderAgent → DashScope API）

### 4.1 请求 URL
```
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
```

### 4.2 请求头
```http
Authorization: Bearer {DASHSCOPE_API_KEY}
Content-Type: application/json
```

### 4.3 请求体
```json
{
    "model": "qwen-plus",
    "messages": [
        {
            "role": "user",
            "content": "你是一个订单处理智能体，需要判断用户请求是否需要调用工具，并提取参数。\n\n可用工具列表:\n- order-get-order: 根据订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。\n  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符，例如：ORDER_1693654321000 (类型: string, 必需: True)\n- order-get-order-by-user: 根据用户ID和订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。\n  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)\n  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符 (类型: string, 必需: True)\n- order-create-order-with-user: 为用户创建新的奶茶订单。支持云边奶茶铺的所有产品，包括云边茉莉、桂花云露、云雾观音等经典产品。系统会自动检查库存并计算价格。\n  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)\n  参数 productName: 产品名称，必须是云边奶茶铺的现有产品 (类型: string, 必需: True)\n  参数 sweetness: 甜度要求，可选值：标准糖、少糖、半糖、微糖、无糖 (类型: string, 必需: True)\n  参数 iceLevel: 冰量要求，可选值：正常冰、少冰、去冰、温、热 (类型: string, 必需: True)\n  参数 quantity: 购买数量，必须为正整数，默认为1 (类型: integer, 必需: True)\n  参数 remark: 订单备注，可选 (类型: string, 必需: False)\n- order-get-orders-by-user: 根据用户ID获取该用户的所有订单列表，包括订单ID、产品信息、价格和创建时间。用于查看用户的订单历史。\n  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)\n- order-delete-order: 删除指定用户的订单。只能删除自己的订单，不能删除其他用户的订单。\n  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)\n  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符 (类型: string, 必需: True)\n\n用户请求: 我想查询我的历史订单\n\n重要提示:\n- 当前用户ID是: 789012（整数类型）\n- 如果工具需要 userId 参数，必须使用整数类型: 789012\n- 从用户输入中提取产品名称、甜度、冰量、数量等信息\n- 如果用户输入中包含用户ID，使用用户输入中的ID；否则使用当前会话的用户ID: 789012\n\n请判断：\n1. 是否需要调用工具？如果需要，返回工具名称\n2. 如果需要，提取所有必需的参数（userId 必须是整数类型）\n\n请以 JSON 格式返回，格式如下：\n- 如果不需要工具: {\"use_tool\": false}\n- 如果需要工具: {\"use_tool\": true, \"tool_name\": \"工具名称\", \"mcp_server\": \"order-mcp-server\", \"parameters\": {\"userId\": 789012, \"productName\": \"产品名称\", \"sweetness\": \"甜度\", \"iceLevel\": \"冰量\", \"quantity\": 数量}}\n\n注意：userId 和 quantity 必须是数字类型，不是字符串。\n\n只返回 JSON，不要其他文字。"
        }
    ],
    "temperature": 0.3,
    "result_format": "message"
}
```

### 4.4 LLM 响应
```json
{
    "status_code": 200,
    "output": {
        "choices": [
            {
                "message": {
                    "content": "{\"use_tool\": true, \"tool_name\": \"order-get-orders-by-user\", \"mcp_server\": \"order-mcp-server\", \"parameters\": {\"userId\": 789012}}"
                }
            }
        ]
    }
}
```

---

## 5. 关键点说明

### 5.1 order-get-orders-by-user 工具描述

**工具名称**: `order-get-orders-by-user`

**工具描述**: 
```
根据用户ID获取该用户的所有订单列表，包括订单ID、产品信息、价格和创建时间。用于查看用户的订单历史。
```

**参数**:
- `userId` (integer, 必需): 用户ID，必须为正整数

**在工具列表中的完整描述**:
```
- order-get-orders-by-user: 根据用户ID获取该用户的所有订单列表，包括订单ID、产品信息、价格和创建时间。用于查看用户的订单历史。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
```

### 5.2 LLM 如何识别这个工具

当用户说"我想查询我的历史订单"时，LLM 会：
1. 识别关键词："查询"、"历史订单"、"所有订单"
2. 匹配工具描述："获取该用户的所有订单列表"、"查看用户的订单历史"
3. 选择工具：`order-get-orders-by-user`
4. 提取参数：使用当前会话的 `userId: 789012`

---

## 6. 完整交互流程

```
用户: "我想查询我的历史订单"
  ↓
OrderAgent.chat("我想查询我的历史订单")
  ↓
OrderAgent._should_use_tool("我想查询我的历史订单")
  ↓
构建工具描述字符串（包含所有5个工具）
  ↓
构建完整的 Prompt（包含工具列表、用户请求、重要提示）
  ↓
调用 DashScope API (Generation.call)
  Request: POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
  Body: {
    "model": "qwen-plus",
    "messages": [{"role": "user", "content": "完整的 prompt..."}],
    "temperature": 0.3
  }
  ↓
LLM 响应:
{
  "use_tool": true,
  "tool_name": "order-get-orders-by-user",
  "mcp_server": "order-mcp-server",
  "parameters": {"userId": 789012}
}
  ↓
OrderAgent 解析 JSON，提取工具调用信息
  ↓
OrderAgent._invoke_tool("order-get-orders-by-user", "order-mcp-server", {"userId": 789012})
  ↓
调用 MCP Server: POST http://localhost:10002/mcp/tools/order-get-orders-by-user/invoke
  ↓
返回订单列表
```

---

## 7. 其他工具的描述示例

### 7.1 order-create-order-with-user（创建订单）

```
- order-create-order-with-user: 为用户创建新的奶茶订单。支持云边奶茶铺的所有产品，包括云边茉莉、桂花云露、云雾观音等经典产品。系统会自动检查库存并计算价格。
  参数 userId: 用户ID，必须为正整数 (类型: integer, 必需: True)
  参数 productName: 产品名称，必须是云边奶茶铺的现有产品 (类型: string, 必需: True)
  参数 sweetness: 甜度要求，可选值：标准糖、少糖、半糖、微糖、无糖 (类型: string, 必需: True)
  参数 iceLevel: 冰量要求，可选值：正常冰、少冰、去冰、温、热 (类型: string, 必需: True)
  参数 quantity: 购买数量，必须为正整数，默认为1 (类型: integer, 必需: True)
  参数 remark: 订单备注，可选 (类型: string, 必需: False)
```

### 7.2 order-get-order（根据订单ID查询）

```
- order-get-order: 根据订单ID查询订单的详细信息，包括产品名称、甜度、冰量、数量、价格和创建时间等完整信息。
  参数 orderId: 订单ID，格式为ORDER_开头的唯一标识符，例如：ORDER_1693654321000 (类型: string, 必需: True)
```

