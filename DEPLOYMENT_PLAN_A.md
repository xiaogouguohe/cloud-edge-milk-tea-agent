# 部署方案A - 详细步骤

## 方案A架构

```
进程1: SupervisorAgent (用户对话入口)
  ↓ A2A 协议 (HTTP)
进程3: OrderAgent (A2A Server)
  ↓ MCP 协议 (HTTP)
进程2: OrderMCPServer (MCP Server) + 数据库 (SQLite)
```

## 部署步骤

### 方式1: 一键启动（推荐）

```bash
# 启动所有服务（包括 SupervisorAgent）
./start_all.sh
```

### 方式2: 分步启动

#### 步骤1: 启动进程2 - OrderMCPServer + 数据库

**终端1**:
```bash
cd /Users/xiaogouguohe/workspace/cloud-edge-milk-tea-agent
python3 order_mcp_server/run_order_mcp_server.py
```

**说明**:
- 服务运行在: `http://localhost:10002`
- 数据库文件: `./data/milk_tea.db` (SQLite)
- 提供订单相关的 MCP 工具

**验证**:
```bash
curl http://localhost:10002/mcp/health
```

#### 步骤2: 启动进程3 - OrderAgent

**终端2**:
```bash
cd /Users/xiaogouguohe/workspace/cloud-edge-milk-tea-agent
python3 order_agent/run_order_agent.py
```

**说明**:
- 服务运行在: `http://localhost:10006`
- 作为 A2A Server，接收 SupervisorAgent 的调用
- 通过 MCP 协议调用 OrderMCPServer 的工具

**验证**:
```bash
curl http://localhost:10006/a2a/health
```

#### 步骤3: 启动进程1 - SupervisorAgent

**终端3**:
```bash
cd /Users/xiaogouguohe/workspace/cloud-edge-milk-tea-agent
python3 chat.py
```

**说明**:
- 用户对话入口
- 路由请求到 OrderAgent
- 通过 A2A 协议调用 OrderAgent

### 方式3: 后台服务 + 前台对话

#### 启动后台服务（进程2和进程3）

```bash
./start_background.sh
```

#### 启动用户对话（进程1）

**新终端**:
```bash
cd /Users/xiaogouguohe/workspace/cloud-edge-milk-tea-agent
python3 chat.py
```

## 进程管理

### 查看服务状态

```bash
# 查看进程
ps aux | grep -E "order_mcp_server|order_agent|chat.py"

# 查看端口占用
lsof -i :10002
lsof -i :10006

# 查看日志
tail -f logs/mcp_server.log
tail -f logs/order_agent.log
```

### 停止服务

```bash
# 停止所有服务
./stop_all.sh

# 或手动停止
kill $(cat logs/mcp_server.pid)
kill $(cat logs/order_agent.pid)
```

## 服务健康检查

### 检查 OrderMCPServer

```bash
curl http://localhost:10002/mcp/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "server": "order-mcp-server",
  "tools_count": 6
}
```

### 检查 OrderAgent

```bash
curl http://localhost:10006/a2a/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "agent": "order_agent"
}
```

### 测试工具列表

```bash
curl http://localhost:10002/mcp/tools
```

## 数据存储

### SQLite 数据库位置

```
./data/milk_tea.db
```

### 查看数据库

```bash
# 使用 sqlite3 命令行工具
sqlite3 data/milk_tea.db

# 查看表
.tables

# 查看订单
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;

# 查看产品
SELECT * FROM products;
```

## 故障排查

### 问题1: 端口被占用

```bash
# 查看占用端口的进程
lsof -i :10002
lsof -i :10006

# 停止占用端口的进程
kill -9 <PID>
```

### 问题2: 服务无法启动

```bash
# 查看日志
tail -f logs/mcp_server.log
tail -f logs/order_agent.log

# 检查依赖
pip3 install -r requirements.txt
```

### 问题3: 服务无法通信

```bash
# 检查服务发现配置
cat services.json

# 测试 HTTP 连接
curl http://localhost:10002/mcp/health
curl http://localhost:10006/a2a/health
```

## 生产环境部署

### 使用 systemd（Linux）

参考 `DEPLOYMENT.md` 中的 systemd 配置。

### 使用 Docker Compose

参考 `DEPLOYMENT.md` 中的 Docker Compose 配置。

## 监控建议

1. **日志监控**: 定期检查日志文件
2. **健康检查**: 定期调用健康检查接口
3. **资源监控**: 监控 CPU、内存使用情况
4. **数据库监控**: 监控数据库文件大小和性能

## 扩展建议

如果需要扩展，可以考虑：

1. **多实例部署**: 
   - OrderMCPServer 可以部署多个实例（负载均衡）
   - OrderAgent 可以部署多个实例（负载均衡）

2. **数据库升级**:
   - 从 SQLite 升级到 MySQL（支持并发）

3. **服务发现**:
   - 从配置文件升级到 Consul 或 Nacos

4. **监控和日志**:
   - 集成 Prometheus + Grafana
   - 使用 ELK 栈进行日志分析
