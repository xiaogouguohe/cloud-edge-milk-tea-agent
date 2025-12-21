# 订单 MCP Server

订单 MCP Server 提供订单相关的工具，供 Agent 调用。

## 架构

```
OrderAgent
    ↓ (MCP 协议)
OrderMCPServer (提供工具)
    ↓
OrderService (业务逻辑)
    ↓
OrderDAO (数据访问)
    ↓
MySQL/SQLite 数据库
```

## 提供的工具

1. **order-get-order** - 根据订单ID查询订单
2. **order-get-order-by-user** - 根据用户ID和订单ID查询订单
3. **order-create-order-with-user** - 创建订单
4. **order-get-orders-by-user** - 获取用户的所有订单
5. **order-delete-order** - 删除订单
6. **order-update-remark** - 更新订单备注

## 启动方式

```bash
# 启动订单 MCP Server
python order_mcp_server/run_order_mcp_server.py

# 服务运行在 http://localhost:10002
```

## 数据库支持

- **SQLite**: 默认使用，无需配置
- **MySQL**: 需要配置环境变量（见 `LOCAL_SETUP.md`）

## 使用示例

```python
from mcp.client import MCPClient

# 创建 MCP 客户端
mcp_client = MCPClient()

# 调用工具
result = mcp_client.invoke_tool(
    "order-mcp-server",
    "order-get-order",
    {"orderId": "ORDER_001"}
)
```
