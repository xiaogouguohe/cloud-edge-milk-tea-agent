# 方案A - 分进程部署脚本说明

## 部署架构

```
进程1: SupervisorAgent (用户对话入口)
  ↓ A2A 协议 (HTTP)
进程3: OrderAgent (A2A Server)
  ↓ MCP 协议 (HTTP)
进程2: OrderMCPServer (MCP Server) + 数据库 (SQLite)
```

## 启动脚本说明

### 进程2: OrderMCPServer + 数据库

#### 前台运行（推荐开发环境）
```bash
./start_process2_mcp_server.sh
```
- 可以看到实时日志
- Ctrl+C 停止

#### 后台运行（推荐生产环境）
```bash
./start_process2_mcp_server_background.sh
```
- 后台运行，输出到日志文件
- 使用 `./stop_process2_mcp_server.sh` 停止

**停止脚本**:
```bash
./stop_process2_mcp_server.sh
```

### 进程3: OrderAgent

#### 前台运行（推荐开发环境）
```bash
./start_process3_order_agent.sh
```
- 可以看到实时日志
- Ctrl+C 停止

#### 后台运行（推荐生产环境）
```bash
./start_process3_order_agent_background.sh
```
- 后台运行，输出到日志文件
- 使用 `./stop_process3_order_agent.sh` 停止

**停止脚本**:
```bash
./stop_process3_order_agent.sh
```

### 进程1: SupervisorAgent

```bash
./start_process1_supervisor.sh
```
- 前台运行（用户交互）
- 会自动检查前置服务是否启动
- Ctrl+C 停止

## 完整部署流程

### 方式1: 分步启动（推荐）

#### 步骤1: 启动进程2（终端1）
```bash
# 前台运行（开发环境）
./start_process2_mcp_server.sh

# 或后台运行（生产环境）
./start_process2_mcp_server_background.sh
```

#### 步骤2: 启动进程3（终端2）
```bash
# 前台运行（开发环境）
./start_process3_order_agent.sh

# 或后台运行（生产环境）
./start_process3_order_agent_background.sh
```

#### 步骤3: 启动进程1（终端3）
```bash
./start_process1_supervisor.sh
```

### 方式2: 快速启动（后台服务 + 前台对话）

#### 启动后台服务（终端1）
```bash
# 启动进程2（后台）
./start_process2_mcp_server_background.sh

# 启动进程3（后台）
./start_process3_order_agent_background.sh
```

#### 启动用户对话（终端2）
```bash
./start_process1_supervisor.sh
```

## 服务管理

### 查看服务状态

```bash
# 查看进程
ps aux | grep -E "order_mcp_server|business_agent|chat.py"

# 查看端口占用
lsof -i :10002  # OrderMCPServer
lsof -i :10006  # OrderAgent

# 查看日志
tail -f logs/mcp_server.log      # 进程2
tail -f logs/order_agent.log     # 进程3
```

### 健康检查

```bash
# 检查 OrderMCPServer
curl http://localhost:10002/mcp/health

# 检查 OrderAgent
curl http://localhost:10006/a2a/health
```

### 停止服务

```bash
# 停止进程2
./stop_process2_mcp_server.sh

# 停止进程3
./stop_process3_order_agent.sh

# 停止进程1（直接 Ctrl+C）
```

## 脚本文件列表

### 启动脚本
- `start_process1_supervisor.sh` - 启动进程1（前台）
- `start_process2_mcp_server.sh` - 启动进程2（前台）
- `start_process2_mcp_server_background.sh` - 启动进程2（后台）
- `start_process3_order_agent.sh` - 启动进程3（前台）
- `start_process3_order_agent_background.sh` - 启动进程3（后台）

### 停止脚本
- `stop_process2_mcp_server.sh` - 停止进程2
- `stop_process3_order_agent.sh` - 停止进程3

## 注意事项

1. **启动顺序**: 建议先启动进程2，再启动进程3，最后启动进程1
2. **端口冲突**: 确保端口 10002 和 10006 未被占用
3. **日志目录**: 脚本会自动创建 `logs/` 目录
4. **数据库**: SQLite 数据库文件在 `./data/milk_tea.db`
5. **PID 文件**: 后台运行的进程会创建 PID 文件在 `logs/` 目录

## 故障排查

### 问题1: 端口被占用

```bash
# 查看占用端口的进程
lsof -i :10002
lsof -i :10006

# 停止占用端口的进程
./stop_process2_mcp_server.sh
./stop_process3_order_agent.sh
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
