# 云边奶茶铺 AI 智能助手系统 - 部署架构

## 一、整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                 │
│                    (Terminal / Web / API)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SupervisorAgent                              │
│                    (进程1 - 主入口)                              │
│  - 用户对话入口                                                  │
│  - 请求路由和协调                                                │
│  - 端口: 无（终端交互）或 可配置 HTTP 服务                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ A2A 协议 (HTTP)
                             │ http://localhost:10006/a2a/invoke
                             ↓
        ┌────────────────────┴────────────────────┐
        │                                          │
        ↓                                          ↓
┌───────────────────┐                    ┌───────────────────┐
│   OrderAgent      │                    │  ConsultAgent     │
│   (进程3)         │                    │  (进程4)          │
│   A2A Server      │                    │  A2A Server       │
│   端口: 10006     │                    │  端口: 10005      │
└─────────┬─────────┘                    └─────────┬─────────┘
          │ MCP 协议 (HTTP)                        │ MCP 协议 (HTTP)
          │ http://localhost:10002/...             │ http://localhost:10003/...
          ↓                                        ↓
┌───────────────────┐                    ┌───────────────────┐
│ OrderMCPServer    │                    │ ConsultMCPServer  │
│ (进程2)           │                    │ (进程5)           │
│ MCP Server        │                    │ MCP Server        │
│ 端口: 10002       │                    │ 端口: 10003       │
└─────────┬─────────┘                    └─────────┬─────────┘
          │                                          │
          ↓                                          ↓
┌───────────────────┐                    ┌───────────────────┐
│   数据库层         │                    │   向量数据库        │
│                   │                    │                   │
│ SQLite/MySQL      │                    │ Milvus Lite       │
│ (订单数据)        │                    │ (知识库向量)       │
│ 文件: milk_tea.db │                    │ 文件: milvus_lite.db│
└───────────────────┘                    └───────────────────┘
```

---

## 二、服务组件详解

### 1. SupervisorAgent（监督者智能体）

**部署方式**: 进程1（主入口）

**功能**:
- 接收用户输入（Terminal 交互）
- 智能路由：判断用户请求类型，路由到合适的子智能体
- 协调管理：统一管理所有子智能体

**技术实现**:
- Python 脚本：`chat.py`
- 无独立端口（终端交互）或可配置 HTTP 服务

**依赖关系**:
- 依赖 OrderAgent（端口 10006）
- 依赖 ConsultAgent（端口 10005）

**启动命令**:
```bash
python chat.py
```

---

### 2. OrderAgent（订单智能体）

**部署方式**: 进程3（A2A Server）

**功能**:
- 处理订单相关业务逻辑
- 接收 SupervisorAgent 的 A2A 协议调用
- 调用 OrderMCPServer 的 MCP 工具

**技术实现**:
- Flask HTTP 服务
- 端口: **10006**
- 文件: `order_agent/run_order_agent.py`

**依赖关系**:
- 依赖 OrderMCPServer（端口 10002）
- 依赖 DashScope API（LLM 调用）

**启动命令**:
```bash
python order_agent/run_order_agent.py
```

**健康检查**:
```bash
curl http://localhost:10006/a2a/health
```

---

### 3. ConsultAgent（咨询智能体）

**部署方式**: 进程4（A2A Server）

**功能**:
- 处理产品咨询、活动信息、冲泡指导
- 接收 SupervisorAgent 的 A2A 协议调用
- 调用 ConsultMCPServer 的 MCP 工具（RAG 检索）

**技术实现**:
- Flask HTTP 服务
- 端口: **10005**
- 文件: `consult_agent/run_consult_agent.py`

**依赖关系**:
- 依赖 ConsultMCPServer（端口 10003）
- 依赖 DashScope API（LLM 调用）
- 依赖 Milvus Lite（向量数据库）

**启动命令**:
```bash
python consult_agent/run_consult_agent.py
```

**健康检查**:
```bash
curl http://localhost:10005/a2a/health
```

---

### 4. OrderMCPServer（订单工具服务器）

**部署方式**: 进程2（MCP Server）

**功能**:
- 提供订单相关的 MCP 工具
- 订单 CRUD 操作：创建、查询、修改、删除
- 数据库访问层

**技术实现**:
- Flask HTTP 服务
- 端口: **10002**
- 文件: `order_mcp_server/run_order_mcp_server.py`

**依赖关系**:
- 依赖数据库（SQLite/MySQL）
- 无其他服务依赖（最底层服务）

**启动命令**:
```bash
python order_mcp_server/run_order_mcp_server.py
```

**健康检查**:
```bash
curl http://localhost:10002/mcp/health
```

**提供的工具**:
- `order-create-order-with-user`: 创建订单
- `order-get-order`: 根据订单ID查询
- `order-get-orders-by-user`: 查询用户所有订单
- `order-delete-order`: 删除订单
- `order-update-remark`: 更新订单备注

---

### 5. ConsultMCPServer（咨询工具服务器）

**部署方式**: 进程5（MCP Server）

**功能**:
- 提供咨询相关的 MCP 工具
- RAG 检索增强生成
- 知识库管理

**技术实现**:
- Flask HTTP 服务
- 端口: **10003**
- 文件: `consult_mcp_server/run_consult_mcp_server.py`

**依赖关系**:
- 依赖 Milvus Lite（向量数据库）
- 依赖 DashScope API（向量化）
- 无其他服务依赖

**启动命令**:
```bash
python consult_mcp_server/run_consult_mcp_server.py
```

**健康检查**:
```bash
curl http://localhost:10003/mcp/health
```

**提供的工具**:
- RAG 检索工具
- 知识库查询工具

---

### 6. 数据库层

#### 6.1 关系数据库（订单数据）

**类型**: SQLite（开发）或 MySQL（生产）

**存储内容**:
- 订单数据（orders 表）
- 用户数据（可选）

**文件位置**:
- SQLite: `./data/milk_tea.db`
- MySQL: 独立数据库服务器

**访问方式**:
- OrderMCPServer 直接访问
- 通过 OrderDAO 数据访问层

**是否需要单独进程**:
- **SQLite**: ❌ **不需要** - 文件数据库，通过 Python `sqlite3` 库直接访问文件
- **MySQL**: ✅ **需要** - 需要启动 MySQL 服务（mysqld），这是外部服务，不是项目代码的一部分

**说明**:
- SQLite 是嵌入式数据库，作为 Python 库直接使用，无需单独进程
- MySQL 是独立服务，需要单独启动和维护（通常在系统级别，如 systemd 或 Docker）

#### 6.2 向量数据库（知识库）

**类型**: Milvus Lite（本地文件）

**存储内容**:
- 知识库文档的向量化结果
- 文档元数据

**文件位置**:
- `./data/milvus_lite.db`（默认）

**访问方式**:
- ConsultMCPServer 通过 RAGService 访问
- 使用 `pymilvus` 客户端的 `MilvusClient`

**是否需要单独进程**:
- **Milvus Lite**: ❌ **不需要** - 嵌入式向量数据库，通过 Python `pymilvus` 库直接访问本地文件

**说明**:
- Milvus Lite 是嵌入式版本，作为 Python 库直接使用，无需 Docker 或单独服务进程
- 数据存储在本地文件系统中，通过 `MilvusClient(uri=db_path)` 直接访问
- 与 Milvus Standalone（需要 Docker）不同，Milvus Lite 是轻量级嵌入式版本

---

## 三、服务端口分配

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| SupervisorAgent | 无 | Terminal | 用户交互入口 |
| OrderAgent | 10006 | HTTP (A2A) | 订单智能体服务 |
| ConsultAgent | 10005 | HTTP (A2A) | 咨询智能体服务 |
| OrderMCPServer | 10002 | HTTP (MCP) | 订单工具服务 |
| ConsultMCPServer | 10003 | HTTP (MCP) | 咨询工具服务 |
| FeedbackAgent | 10007 | HTTP (A2A) | 反馈智能体（规划中） |

---

## 四、服务启动顺序

### 依赖关系图

```
SupervisorAgent (进程1)
  ↓ 依赖
OrderAgent (进程3) + ConsultAgent (进程4)
  ↓ 依赖
OrderMCPServer (进程2) + ConsultMCPServer (进程5)
  ↓ 无依赖
数据库层（SQLite/MySQL + Milvus Lite）
```

### 推荐启动顺序

```
1. 启动数据库（仅当使用 MySQL 时需要）
   - SQLite: 无需启动，文件数据库自动创建
   - MySQL: 需要启动 MySQL 服务（外部服务）
   ↓
2. 启动 OrderMCPServer (进程2, 端口 10002)
   - 自动连接 SQLite 文件或 MySQL 服务
   ↓ 等待 2-3 秒
3. 启动 ConsultMCPServer (进程5, 端口 10003)
   - 自动连接 Milvus Lite 文件（无需单独进程）
   ↓ 等待 2-3 秒
4. 启动 OrderAgent (进程3, 端口 10006)
   ↓ 等待 2-3 秒
5. 启动 ConsultAgent (进程4, 端口 10005)
   ↓ 等待 2-3 秒
6. 启动 SupervisorAgent (进程1)
```

**重要说明**:
- **SQLite**: 无需单独进程，文件数据库，自动创建和使用
- **Milvus Lite**: 无需单独进程，嵌入式向量数据库，自动创建和使用
- **MySQL**: 需要单独启动 MySQL 服务（这是外部服务，不是项目代码的一部分）

### 一键启动脚本

```bash
# 使用提供的启动脚本
./start_all.sh

# 或手动启动
python order_mcp_server/run_order_mcp_server.py &      # 进程2
python consult_mcp_server/run_consult_mcp_server.py &  # 进程5
sleep 3
python order_agent/run_order_agent.py &               # 进程3
python consult_agent/run_consult_agent.py &            # 进程4
sleep 3
python chat.py                                         # 进程1
```

---

## 五、通信协议

### 1. A2A 协议（Agent-to-Agent）

**用途**: 智能体之间的通信

**协议格式**:
- 请求: `POST http://{host}:{port}/a2a/invoke`
- 请求体: `{"input": "用户输入", "chat_id": "...", "user_id": "..."}`
- 响应: `{"output": "处理结果", "status": "success"}`

**使用场景**:
- SupervisorAgent → OrderAgent
- SupervisorAgent → ConsultAgent

**实现**:
- 客户端: `a2a/client.py`
- 服务端: `a2a/server.py`

### 2. MCP 协议（Model Context Protocol）

**用途**: 智能体与业务工具之间的通信

**协议格式**:
- 请求: `POST http://{host}:{port}/mcp/tools/{tool_name}/invoke`
- 请求体: `{"parameters": {...}}`
- 响应: `{"result": "工具执行结果", "status": "success"}`

**使用场景**:
- OrderAgent → OrderMCPServer
- ConsultAgent → ConsultMCPServer

**实现**:
- 客户端: `mcp/client.py`
- 服务端: `mcp/server.py`

---

## 六、服务发现机制

### 配置文件方式（当前实现）

**文件**: `services.json`

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
  },
  "consult_agent": {
    "host": "localhost",
    "port": 10005,
    "url": "http://localhost:10005"
  },
  "consult-mcp-server": {
    "host": "localhost",
    "port": 10003,
    "url": "http://localhost:10003"
  }
}
```

**实现**: `service_discovery.py`

### 可扩展方式

- Redis 服务发现（规划中）
- Consul 服务发现（规划中）
- Kubernetes Service Discovery（生产环境）

---

## 七、部署方案

### 方案1: 本地开发部署（当前）

**特点**:
- 所有服务运行在同一台机器
- 使用 SQLite 和 Milvus Lite（本地文件）
- 适合开发和测试

**启动方式**:
```bash
# 手动启动多个终端
# 或使用启动脚本
./start_all.sh
```

### 方案2: Docker Compose 部署

**特点**:
- 容器化部署
- 服务隔离
- 便于扩展和维护

**文件**: `docker-compose.yml`（需要创建）

**启动方式**:
```bash
docker-compose up -d
```

### 方案3: 生产环境部署

**特点**:
- 使用 systemd 管理服务
- MySQL 独立部署
- Milvus 集群部署（可选）
- 负载均衡和监控

**部署方式**:
- 使用 systemd service 文件
- 或使用 Kubernetes

---

## 八、数据流示例

### 示例1: 用户下单

```
用户输入: "我要下单，一杯云边茉莉，少糖，正常冰"
  ↓
SupervisorAgent.chat()
  ↓ 路由判断
SupervisorAgent.call_sub_agent("order_agent", ...)
  ↓ A2A 协议
HTTP POST http://localhost:10006/a2a/invoke
  ↓
OrderAgent.handle_request()
  ↓ LLM 判断
OrderAgent 调用工具: order-create-order-with-user
  ↓ MCP 协议
HTTP POST http://localhost:10002/mcp/tools/order-create-order-with-user/invoke
  ↓
OrderMCPServer._create_order()
  ↓
OrderService.create_order()
  ↓
OrderDAO.create_order()
  ↓ SQL
INSERT INTO orders ...
  ↓
逐层返回结果
  ↓
用户收到: "订单创建成功！订单ID: ORDER_xxx..."
```

### 示例2: 产品咨询

```
用户输入: "云边茉莉的特点是什么？"
  ↓
SupervisorAgent.chat()
  ↓ 路由判断
SupervisorAgent.call_sub_agent("consult_agent", ...)
  ↓ A2A 协议
HTTP POST http://localhost:10005/a2a/invoke
  ↓
ConsultAgent.handle_request()
  ↓ RAG 检索
ConsultAgent 调用 RAG 工具
  ↓ MCP 协议
HTTP POST http://localhost:10003/mcp/tools/rag-search/invoke
  ↓
ConsultMCPServer RAG 检索
  ↓
RAGService.search()
  ↓ 向量检索
Milvus Lite 相似度搜索
  ↓
返回相关文档
  ↓ LLM 生成
ConsultAgent 基于检索结果生成回答
  ↓
用户收到: "云边茉莉是我们的人气产品，特点包括..."
```

---

## 九、监控和日志

### 日志文件

```
logs/
├── mcp_server.log          # OrderMCPServer 日志
├── consult_mcp_server.log  # ConsultMCPServer 日志
├── order_agent.log         # OrderAgent 日志
├── consult_agent.log       # ConsultAgent 日志
└── supervisor_agent.log   # SupervisorAgent 日志
```

### 健康检查

```bash
# 检查 OrderMCPServer
curl http://localhost:10002/mcp/health

# 检查 ConsultMCPServer
curl http://localhost:10003/mcp/health

# 检查 OrderAgent
curl http://localhost:10006/a2a/health

# 检查 ConsultAgent
curl http://localhost:10005/a2a/health
```

---

## 十、扩展性设计

### 水平扩展

- **OrderAgent**: 可以部署多个实例，使用负载均衡
- **ConsultAgent**: 可以部署多个实例，使用负载均衡
- **MCP Server**: 可以部署多个实例，但需要共享数据库

### 垂直扩展

- **数据库**: SQLite → MySQL → MySQL 集群
- **向量数据库**: Milvus Lite → Milvus Standalone → Milvus Cluster

### 服务拆分

- 每个智能体可以独立部署和扩展
- MCP Server 可以按业务域拆分
- 数据库可以按业务域拆分

---

## 十一、安全考虑

### 1. 服务间通信

- 当前：HTTP（本地部署）
- 生产环境：建议使用 HTTPS
- 可以添加认证机制（API Key、Token）

### 2. 数据安全

- 用户数据隔离（通过 user_id）
- 数据库访问控制
- 敏感信息加密

### 3. 服务隔离

- 容器化部署，服务隔离
- 网络隔离（Docker network）
- 资源限制（CPU、内存）

---

## 十二、总结

### 架构特点

1. **分层架构**: 用户层 → 智能体层 → 工具层 → 数据层
2. **服务化**: 每个组件独立部署，松耦合
3. **协议标准化**: A2A 和 MCP 协议，便于扩展
4. **可扩展性**: 支持水平扩展和垂直扩展

### 部署要点

1. **启动顺序**: 数据库 → MCP Server → Agent → Supervisor
2. **端口配置**: 确保端口不冲突
3. **服务发现**: 配置文件或服务注册中心
4. **监控日志**: 完善的日志和健康检查

### 适用场景

- **开发环境**: 本地部署，SQLite + Milvus Lite
- **测试环境**: Docker Compose，MySQL + Milvus Lite
- **生产环境**: Kubernetes，MySQL 集群 + Milvus 集群

