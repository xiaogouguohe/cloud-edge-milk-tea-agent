# 服务部署指南

## 部署方案分析

### 你的方案
1. **进程1**: 用户对话 + SupervisorAgent
2. **进程2**: MCP Server
3. **进程3**: OrderAgent + 数据库

### 方案评估

✅ **优点**:
- 职责清晰，服务分离
- 可以独立扩展和维护
- 数据库和 OrderAgent 放在一起，减少网络延迟

⚠️ **需要注意**:
- OrderAgent 需要通过 A2A 协议调用（HTTP），所以需要独立进程
- MCP Server 需要访问数据库，所以数据库应该和 MCP Server 放在一起更合理

### 推荐方案

**方案A（推荐）**: 4个进程
1. **进程1**: 用户对话 + SupervisorAgent（主入口）
2. **进程2**: OrderAgent（A2A Server）
3. **进程3**: OrderMCPServer（MCP Server）+ 数据库
4. **数据库**: 可以独立部署（MySQL）或与 MCP Server 一起（SQLite）

**方案B（你的方案，也合理）**: 3个进程
1. **进程1**: 用户对话 + SupervisorAgent
2. **进程2**: OrderMCPServer
3. **进程3**: OrderAgent + 数据库（SQLite 本地文件）

## 部署步骤（方案B - 你的方案）

### 进程1: 用户对话 + SupervisorAgent

**文件**: `chat.py`

```bash
# 终端 1
cd /Users/xiaogouguohe/workspace/cloud-edge-milk-tea-agent
python chat.py
```

**功能**:
- 接收用户输入
- SupervisorAgent 路由请求
- 通过 A2A 协议调用 OrderAgent

**端口**: 无（终端交互）

### 进程2: OrderMCPServer

**文件**: `order_mcp_server/run_order_mcp_server.py`

```bash
# 终端 2
cd /Users/xiaogouguohe/workspace/cloud-edge-milk-tea-agent
python order_mcp_server/run_order_mcp_server.py
```

**功能**:
- 提供订单相关的 MCP 工具
- 处理订单的 CRUD 操作

**端口**: 10002

### 进程3: OrderAgent + 数据库

**文件**: `order_agent/run_order_agent.py`

```bash
# 终端 3
cd /Users/xiaogouguohe/workspace/cloud-edge-milk-tea-agent
python order_agent/run_order_agent.py
```

**功能**:
- 作为 A2A Server，接收 SupervisorAgent 的调用
- 通过 MCP 协议调用 OrderMCPServer 的工具
- 数据库文件（SQLite）存储在本地

**端口**: 10006

**数据库**: `./data/milk_tea.db` (SQLite)

## 完整启动脚本

创建 `start_all.sh`:

```bash
#!/bin/bash

# 启动所有服务

echo "启动云边奶茶铺 AI Agent 服务..."

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "错误: 端口 $1 已被占用"
        exit 1
    fi
}

check_port 10002
check_port 10006

# 启动 OrderMCPServer（后台运行）
echo "启动 OrderMCPServer (端口 10002)..."
python order_mcp_server/run_order_mcp_server.py > logs/mcp_server.log 2>&1 &
MCP_PID=$!
echo "OrderMCPServer PID: $MCP_PID"

# 等待 MCP Server 启动
sleep 2

# 启动 OrderAgent（后台运行）
echo "启动 OrderAgent (端口 10006)..."
python order_agent/run_order_agent.py > logs/order_agent.log 2>&1 &
AGENT_PID=$!
echo "OrderAgent PID: $AGENT_PID"

# 等待 OrderAgent 启动
sleep 2

# 启动 SupervisorAgent（前台运行）
echo "启动 SupervisorAgent..."
echo "================================"
python chat.py

# 清理：当 SupervisorAgent 退出时，停止其他服务
echo "停止所有服务..."
kill $MCP_PID $AGENT_PID 2>/dev/null
```

## 使用 systemd 部署（生产环境）

### 1. OrderMCPServer 服务

创建 `/etc/systemd/system/order-mcp-server.service`:

```ini
[Unit]
Description=Order MCP Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/cloud-edge-milk-tea-agent
ExecStart=/usr/bin/python3 order_mcp_server/run_order_mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. OrderAgent 服务

创建 `/etc/systemd/system/order-agent.service`:

```ini
[Unit]
Description=Order Agent (A2A Server)
After=network.target order-mcp-server.service
Requires=order-mcp-server.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/cloud-edge-milk-tea-agent
ExecStart=/usr/bin/python3 order_agent/run_order_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. SupervisorAgent 服务

创建 `/etc/systemd/system/supervisor-agent.service`:

```ini
[Unit]
Description=Supervisor Agent
After=network.target order-agent.service
Requires=order-agent.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/cloud-edge-milk-tea-agent
ExecStart=/usr/bin/python3 chat.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 启动服务

```bash
sudo systemctl start order-mcp-server
sudo systemctl start order-agent
sudo systemctl start supervisor-agent

# 查看状态
sudo systemctl status order-mcp-server
sudo systemctl status order-agent
sudo systemctl status supervisor-agent

# 设置开机自启
sudo systemctl enable order-mcp-server
sudo systemctl enable order-agent
sudo systemctl enable supervisor-agent
```

## 使用 Docker Compose 部署（推荐）

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # OrderMCPServer
  order-mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    container_name: order-mcp-server
    ports:
      - "10002:10002"
    volumes:
      - ./data:/app/data  # SQLite 数据库文件
      - ./logs:/app/logs
    environment:
      - DB_TYPE=sqlite
    restart: unless-stopped
    networks:
      - agent-network

  # OrderAgent
  order-agent:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: order-agent
    ports:
      - "10006:10006"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - DASHSCOPE_MODEL=${DASHSCOPE_MODEL}
    depends_on:
      - order-mcp-server
    restart: unless-stopped
    networks:
      - agent-network

  # SupervisorAgent
  supervisor-agent:
    build:
      context: .
      dockerfile: Dockerfile.supervisor
    container_name: supervisor-agent
    volumes:
      - ./logs:/app/logs
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - DASHSCOPE_MODEL=${DASHSCOPE_MODEL}
    depends_on:
      - order-agent
    restart: unless-stopped
    networks:
      - agent-network
    stdin_open: true
    tty: true

networks:
  agent-network:
    driver: bridge
```

## 进程间通信

```
┌─────────────────────┐
│ SupervisorAgent     │ 进程1
│ (用户对话入口)       │
└──────────┬──────────┘
           │ A2A 协议 (HTTP)
           │ http://localhost:10006/a2a/invoke
           ↓
┌─────────────────────┐
│ OrderAgent          │ 进程3
│ (A2A Server)        │
└──────────┬──────────┘
           │ MCP 协议 (HTTP)
           │ http://localhost:10002/mcp/tools/xxx/invoke
           ↓
┌─────────────────────┐
│ OrderMCPServer      │ 进程2
│ (MCP Server)        │
└──────────┬──────────┘
           │ 数据库访问
           ↓
┌─────────────────────┐
│ SQLite/MySQL        │
│ (数据存储)          │
└─────────────────────┘
```

## 注意事项

1. **启动顺序**: MCP Server → OrderAgent → SupervisorAgent
2. **端口配置**: 确保端口 10002 和 10006 未被占用
3. **服务发现**: 确保 `services.json` 中的地址正确
4. **数据库**: SQLite 文件需要共享（如果使用 Docker）
5. **日志**: 建议为每个服务配置日志文件

## 监控和日志

```bash
# 查看日志
tail -f logs/mcp_server.log
tail -f logs/order_agent.log
tail -f logs/supervisor_agent.log

# 检查服务状态
curl http://localhost:10002/mcp/health
curl http://localhost:10006/a2a/health
```
