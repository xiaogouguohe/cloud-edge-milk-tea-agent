# 服务启动指南

## 服务架构

```
SupervisorAgent (主入口)
    ↓ A2A 协议
OrderAgent (业务智能体)
    ↓ MCP 协议
OrderMCPServer (工具提供者)
    ↓
MySQL/SQLite 数据库
```

## 启动顺序

### 1. 启动数据库（如果使用 MySQL）

```bash
# 使用 SQLite（默认，无需启动）
# 或使用 MySQL
mysql -u root -p
# 创建数据库（参考 LOCAL_SETUP.md）
```

### 2. 启动 Order MCP Server

```bash
# 终端 1
python order_mcp_server/run_order_mcp_server.py

# 服务运行在 http://localhost:10002
# 提供订单相关的工具
```

### 3. 启动 Order Agent（A2A Server）

```bash
# 终端 2
python business_agent/run_business_agent.py

# 服务运行在 http://localhost:10006
# 作为 A2A Server，接收 SupervisorAgent 的调用
```

### 4. 启动 Supervisor Agent（主入口）

```bash
# 终端 3
python chat.py

# 或直接运行
python -c "from chat import main; main()"
```

## 完整流程示例

### 用户请求："查询订单 ORDER_001"

```
1. 用户输入 → SupervisorAgent.chat()
   ↓
2. SupervisorAgent.route_to_agent() → 判断需要调用 order_agent
   ↓
3. SupervisorAgent.call_sub_agent() → 使用 A2A Client
   ↓
4. A2A Client → HTTP POST http://localhost:10006/a2a/invoke
   ↓
5. OrderAgent (A2A Server) → 接收请求，调用 chat()
   ↓
6. OrderAgent 分析请求 → 需要调用 order-get-order 工具
   ↓
7. MCP Client → HTTP POST http://localhost:10002/mcp/tools/order-get-order/invoke
   ↓
8. OrderMCPServer → 调用 OrderService.get_order()
   ↓
9. OrderService → 调用 OrderDAO.get_order_by_id()
   ↓
10. OrderDAO → SQL: SELECT * FROM orders WHERE order_id = 'ORDER_001'
   ↓
11. 返回订单数据 → 逐层返回 → 最终返回给用户
```

## 服务发现配置

服务地址配置在 `services.json` 文件中：

```json
{
  "order_agent": {
    "host": "localhost",
    "port": 10006,
    "url": "http://localhost:10006"
  },
  "order-mcp-server": {
    "host": "localhost",
    "port": 10002,
    "url": "http://localhost:10002"
  }
}
```

## 测试

### 测试 A2A 协议通信

```python
from a2a.client import A2AClient

client = A2AClient()
result = client.call_agent("order_agent", {
    "input": "查询订单 ORDER_001",
    "chat_id": "test_chat",
    "user_id": "test_user"
})
print(result)
```

### 测试 MCP 工具调用

```python
from mcp.client import MCPClient

mcp_client = MCPClient()
result = mcp_client.invoke_tool(
    "order-mcp-server",
    "order-get-order",
    {"orderId": "ORDER_001"}
)
print(result)
```

## 注意事项

1. **启动顺序很重要**：必须先启动 MCP Server，再启动 Agent，最后启动 Supervisor
2. **端口不能冲突**：确保端口 10002（MCP Server）和 10006（Order Agent）未被占用
3. **服务发现**：确保 `services.json` 中的地址正确
4. **数据库**：如果使用 MySQL，确保数据库已创建并初始化表结构
