# 进程启动顺序说明

## 依赖关系分析

```
进程1: SupervisorAgent
  ↓ 依赖（通过 A2A 协议调用）
进程3: OrderAgent
  ↓ 依赖（通过 MCP 协议调用）
进程2: OrderMCPServer + 数据库
  ↓ 无依赖（最底层）
```

## 启动顺序要求

### ✅ 推荐顺序（必须）

```
1. 进程2: OrderMCPServer + 数据库
   ↓ 等待启动完成
2. 进程3: OrderAgent
   ↓ 等待启动完成
3. 进程1: SupervisorAgent
```

### 原因分析

1. **进程2 必须最先启动**
   - OrderMCPServer 提供 MCP 工具
   - OrderAgent 需要通过 MCP 协议调用这些工具
   - 如果进程2未启动，进程3无法正常工作

2. **进程3 必须在进程1之前启动**
   - SupervisorAgent 需要通过 A2A 协议调用 OrderAgent
   - 如果进程3未启动，进程1无法调用 OrderAgent

3. **进程1 最后启动**
   - 依赖进程3（OrderAgent）
   - 是用户交互入口，可以最后启动

## 启动顺序验证

### 错误顺序示例

❌ **错误1**: 先启动进程1
```
进程1 → 尝试调用进程3 → 失败（进程3未启动）
```

❌ **错误2**: 先启动进程3，再启动进程1，最后启动进程2
```
进程3 → 尝试调用进程2的工具 → 失败（进程2未启动）
进程1 → 尝试调用进程3 → 可能失败（进程3无法正常工作）
```

### ✅ 正确顺序

```
进程2 → 启动成功 → 提供 MCP 工具
  ↓
进程3 → 启动成功 → 可以调用进程2的工具
  ↓
进程1 → 启动成功 → 可以调用进程3
```

## 启动脚本的检查机制

### 进程1的检查

`start_process1_supervisor.sh` 会自动检查：
- OrderAgent (进程3) 是否启动
- OrderMCPServer (进程2) 是否启动

如果未启动，会提示用户。

### 进程3的检查

`start_process3_order_agent.sh` 会检查：
- OrderMCPServer (进程2) 是否启动（可选，但建议）

## 实际启动示例

### 方式1: 手动按顺序启动

```bash
# 终端1: 启动进程2
./start_process2_mcp_server.sh

# 终端2: 等待进程2启动后，启动进程3
./start_process3_order_agent.sh

# 终端3: 等待进程3启动后，启动进程1
./start_process1_supervisor.sh
```

### 方式2: 使用后台脚本（自动等待）

```bash
# 终端1: 启动后台服务（会自动等待）
./start_process2_mcp_server_background.sh
sleep 3  # 等待进程2启动
./start_process3_order_agent_background.sh
sleep 3  # 等待进程3启动

# 终端2: 启动用户对话
./start_process1_supervisor.sh
```

### 方式3: 使用一键启动脚本

```bash
# 自动按正确顺序启动
./start_all.sh
```

## 启动时间建议

- **进程2**: 启动后等待 2-3 秒（确保服务就绪）
- **进程3**: 启动后等待 2-3 秒（确保服务就绪）
- **进程1**: 可以立即启动（会自动检查前置服务）

## 健康检查

启动后可以验证服务是否就绪：

```bash
# 检查进程2
curl http://localhost:10002/mcp/health

# 检查进程3
curl http://localhost:10006/a2a/health
```

## 总结

**必须的启动顺序**: 进程2 → 进程3 → 进程1

**原因**:
1. 进程2 是底层服务，无依赖
2. 进程3 依赖进程2
3. 进程1 依赖进程3

**建议**: 使用提供的启动脚本，它们已经包含了检查和等待机制。
