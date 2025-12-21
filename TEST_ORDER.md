# 订单功能测试指南

## 测试脚本

使用 `test_order.py` 脚本测试订单功能。

## 测试前准备

### 1. 确保服务已启动

按照方案A部署，确保以下服务已启动：

```bash
# 进程2: OrderMCPServer
./start_process2_mcp_server_background.sh

# 进程3: OrderAgent
./start_process3_order_agent_background.sh
```

### 2. 验证服务健康

```bash
curl http://localhost:10002/mcp/health
curl http://localhost:10006/a2a/health
```

## 运行测试

### 完整测试（推荐）

```bash
python3 test_order.py
```

或指定测试类型：

```bash
# 只测试创建订单
python3 test_order.py --test create

# 只测试查询订单
python3 test_order.py --test query

# 测试全部（默认）
python3 test_order.py --test all
```

## 测试流程

### 测试1: 创建订单

测试脚本会：

1. **验证前查询数据库**
   - 查询当前订单总数
   - 查询最新3条订单

2. **执行下单操作**
   - 通过 SupervisorAgent 发送下单请求
   - 用户ID在对话中携带：`"我要下单，云边茉莉，标准糖，正常冰，1杯，用户ID是12345678901"`

3. **验证后查询数据库**
   - 查询更新后的订单总数
   - 查询最新5条订单

4. **对比结果**
   - 对比订单数量变化
   - 验证新增订单的用户ID是否正确

### 测试2: 查询订单

测试脚本会：

1. **发送查询请求**
   - `"查询我的订单，用户ID是12345678901"`

2. **验证响应**
   - 检查是否返回订单信息

## 测试用例

### 用例1: 创建订单 - 云边茉莉

**输入**:
```
我要下单，云边茉莉，标准糖，正常冰，1杯，用户ID是12345678901
```

**预期结果**:
- 订单数量增加1
- 数据库中新增一条订单
- 订单的用户ID为 12345678901
- 订单产品为"云边茉莉"

### 用例2: 创建订单 - 桂花云露

**输入**:
```
帮我下单：桂花云露，少糖，少冰，2杯，用户ID是12345678901
```

**预期结果**:
- 订单数量增加1
- 数据库中新增一条订单
- 订单数量为2

### 用例3: 查询订单

**输入**:
```
查询我的订单，用户ID是12345678901
```

**预期结果**:
- 返回该用户的所有订单列表

## 手动测试

如果不想使用测试脚本，也可以手动测试：

### 1. 启动服务

```bash
# 终端1: 启动进程2
./start_process2_mcp_server_background.sh

# 终端2: 启动进程3
./start_process3_order_agent_background.sh

# 终端3: 启动进程1
python3 chat.py
```

### 2. 执行下单

在 chat.py 中输入：
```
我要下单，云边茉莉，标准糖，正常冰，1杯，用户ID是12345678901
```

### 3. 验证数据库

```bash
# SQLite
sqlite3 data/milk_tea.db

# 查询最新订单
SELECT * FROM orders ORDER BY created_at DESC LIMIT 1;

# 查询订单总数
SELECT COUNT(*) FROM orders;
```

## 验证要点

1. **订单数量变化**: 下单后订单总数应该增加
2. **订单信息正确**: 产品名称、甜度、冰量、数量、价格等应该正确
3. **用户ID正确**: 订单的用户ID应该与请求中的用户ID一致
4. **订单ID生成**: 应该生成唯一的订单ID（格式：ORDER_xxx）

## 故障排查

### 问题1: 订单未创建

- 检查 OrderMCPServer 是否启动
- 检查 OrderAgent 是否启动
- 查看服务日志：`logs/mcp_server.log`, `logs/order_agent.log`

### 问题2: 用户ID不正确

- 检查对话中是否正确携带用户ID
- 检查 OrderAgent 是否正确提取用户ID
- 检查工具调用时是否正确传递用户ID

### 问题3: 数据库连接失败

- 检查数据库文件是否存在：`data/milk_tea.db`
- 检查数据库权限
- 检查数据库表结构是否正确
