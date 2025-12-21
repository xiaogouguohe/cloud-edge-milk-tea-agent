# A2A 和 MCP 协议实现指南

## 重要概念

**A2A 和 MCP 是协议，不是部署方式！**

- 协议定义了**通信格式和接口规范**
- 部署方式（Docker/直接安装）只影响**服务发现**，不影响协议本身
- 只要实现了协议规定的接口，就可以通信

## A2A (Agent-to-Agent) 协议

### 协议本质

A2A 协议本质上是：
1. **服务注册**：Agent 注册自己的信息（AgentCard）
2. **服务发现**：通过服务注册中心（Nacos/配置文件等）发现其他 Agent
3. **服务调用**：通过 HTTP API 调用其他 Agent

### Python 实现方案

#### 1. AgentCard 定义

```python
# a2a/agent_card.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentCard:
    """Agent 卡片信息"""
    name: str  # agent 名称，如 "order_agent"
    description: str  # 描述
    version: str = "1.0.0"
    url: Optional[str] = None  # Agent 服务地址
    provider: Optional[dict] = None  # 提供者信息
```

#### 2. A2A Server（Agent 服务端）

每个 Agent 需要暴露 HTTP 接口供其他 Agent 调用：

```python
# a2a/server.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/a2a/invoke', methods=['POST'])
def invoke():
    """A2A 协议调用接口"""
    data = request.json
    # {
    #   "input": "用户输入",
    #   "chat_id": "chat_123",
    #   "user_id": "user_456"
    # }
    
    # 处理请求
    result = process_request(data)
    
    return jsonify({
        "output": result,
        "status": "success"
    })
```

#### 3. A2A Client（Agent 客户端）

SupervisorAgent 调用其他 Agent：

```python
# a2a/client.py
import requests
from service_discovery import ServiceDiscovery

class A2AClient:
    def __init__(self):
        self.sd = ServiceDiscovery(method="config")
    
    def call_agent(self, agent_name: str, input_data: dict) -> dict:
        """调用其他 Agent"""
        # 1. 发现服务
        service = self.sd.discover(agent_name)
        if not service:
            raise ValueError(f"Agent {agent_name} not found")
        
        # 2. 调用 A2A 接口
        url = f"{service['url']}/a2a/invoke"
        response = requests.post(url, json=input_data)
        return response.json()
```

#### 4. AgentCard 注册

```python
# 注册 AgentCard（可以使用配置文件、Redis、数据库等）
from service_discovery import ServiceDiscovery

sd = ServiceDiscovery(method="config")
sd.register(
    "order_agent",
    host="localhost",
    port=10006,
    url="http://localhost:10006",
    # 可以添加 AgentCard 信息
    agent_card={
        "name": "order_agent",
        "description": "云边奶茶铺智能订单处理助手",
        "version": "1.0.1"
    }
)
```

## MCP (Model Context Protocol) 协议

### 协议本质

MCP 协议本质上是：
1. **工具注册**：MCP Server 注册提供的工具列表
2. **工具发现**：Agent 发现可用的工具
3. **工具调用**：Agent 通过 HTTP API 调用工具

### Python 实现方案

#### 1. MCP Server（工具提供者）

```python
# mcp/server.py
from flask import Flask, request, jsonify

app = Flask(__name__)

# 工具列表
TOOLS = {
    "order-get-order": {
        "name": "order-get-order",
        "description": "根据订单ID查询订单",
        "parameters": {
            "type": "object",
            "properties": {
                "orderId": {"type": "string", "description": "订单ID"}
            },
            "required": ["orderId"]
        }
    },
    "order-create-order": {
        "name": "order-create-order",
        "description": "创建订单",
        "parameters": {...}
    }
}

@app.route('/mcp/tools', methods=['GET'])
def list_tools():
    """列出所有工具"""
    return jsonify({"tools": list(TOOLS.values())})

@app.route('/mcp/tools/<tool_name>/invoke', methods=['POST'])
def invoke_tool(tool_name: str):
    """调用工具"""
    if tool_name not in TOOLS:
        return jsonify({"error": "Tool not found"}), 404
    
    params = request.json.get("parameters", {})
    
    # 执行工具逻辑
    if tool_name == "order-get-order":
        result = get_order(params["orderId"])
    elif tool_name == "order-create-order":
        result = create_order(params)
    else:
        return jsonify({"error": "Unknown tool"}), 400
    
    return jsonify({
        "result": result,
        "status": "success"
    })
```

#### 2. MCP Client（工具调用者）

```python
# mcp/client.py
import requests
from service_discovery import ServiceDiscovery

class MCPClient:
    def __init__(self):
        self.sd = ServiceDiscovery(method="config")
    
    def list_tools(self, mcp_server_name: str) -> list:
        """获取工具列表"""
        service = self.sd.discover(mcp_server_name)
        url = f"{service['url']}/mcp/tools"
        response = requests.get(url)
        return response.json()["tools"]
    
    def invoke_tool(self, mcp_server_name: str, tool_name: str, parameters: dict) -> dict:
        """调用工具"""
        service = self.sd.discover(mcp_server_name)
        url = f"{service['url']}/mcp/tools/{tool_name}/invoke"
        response = requests.post(url, json={"parameters": parameters})
        return response.json()
```

#### 3. Agent 使用工具

```python
# order_agent.py
from mcp.client import MCPClient

class OrderAgent:
    def __init__(self):
        self.mcp_client = MCPClient()
        # 获取可用工具
        self.tools = self.mcp_client.list_tools("order-mcp-server")
    
    def handle_request(self, user_input: str):
        # LLM 判断需要调用哪个工具
        if "查询订单" in user_input:
            # 调用工具
            result = self.mcp_client.invoke_tool(
                "order-mcp-server",
                "order-get-order",
                {"orderId": "ORDER_001"}
            )
            return result["result"]
```

## 完整架构（不使用 Nacos）

```
┌─────────────────────────────────────┐
│  服务发现（配置文件/Redis）          │
│  - order_agent: localhost:10006    │
│  - order-mcp-server: localhost:10002│
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  SupervisorAgent                    │
│  └─ A2AClient                       │
│     └─ 调用 order_agent             │
└─────────────────────────────────────┘
         ↓ (A2A 协议)
┌─────────────────────────────────────┐
│  OrderAgent                         │
│  └─ MCPClient                       │
│     └─ 调用 order-mcp-server 工具   │
└─────────────────────────────────────┘
         ↓ (MCP 协议)
┌─────────────────────────────────────┐
│  OrderMCPServer                     │
│  └─ 提供工具: order-get-order       │
│     └─ 调用 OrderService            │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  MySQL 数据库                        │
└─────────────────────────────────────┘
```

## 关键点

1. **协议是接口规范**，不是部署方式
2. **服务发现只是找到地址**，可以用配置文件、Redis、数据库等
3. **A2A 和 MCP 本质是 HTTP API**，只要实现相应接口即可
4. **不需要 Nacos**，可以用任何服务发现方式

## 实现步骤

1. ✅ 实现服务发现模块（已完成：`service_discovery.py`）
2. 🔲 实现 A2A Server（Agent 暴露接口）
3. 🔲 实现 A2A Client（Agent 调用其他 Agent）
4. 🔲 实现 MCP Server（提供工具）
5. 🔲 实现 MCP Client（调用工具）

## 总结

**可以！** 只要实现了 A2A 和 MCP 协议的接口，无论使用什么部署方式（Docker/直接安装）和服务发现方式（Nacos/配置文件/Redis），都可以正常通信。
