# Consult Agent 实现说明

## 概述

已实现咨询智能体（ConsultAgent），参考 Java 项目的实现，提供产品咨询、活动信息和冲泡指导功能。

## 文件结构

```
consult_agent/
├── __init__.py
├── consult_agent.py          # ConsultAgent 主类
└── run_consult_agent.py      # 启动脚本

consult_mcp_server/
├── __init__.py
├── consult_service.py         # 咨询服务层
├── consult_mcp_server.py     # MCP Server 实现
└── run_consult_mcp_server.py # 启动脚本
```

## 功能特性

### ConsultAgent 功能

1. **产品咨询**：回答用户关于产品的问题
2. **活动信息**：提供活动相关信息
3. **冲泡指导**：提供专业的冲泡建议
4. **工具调用**：通过 MCP 协议调用咨询工具

### ConsultMCPServer 提供的工具

1. **consult-search-knowledge**: 知识库检索
   - 根据查询内容检索产品信息、店铺介绍等
   - 支持模糊匹配

2. **consult-get-products**: 获取所有产品列表
   - 返回所有可用产品的完整列表
   - 包括产品名称、描述、价格、库存等

3. **consult-get-product-info**: 获取产品详细信息
   - 根据产品名称获取详细信息
   - 包括价格、库存、保质期、制作时间等

4. **consult-search-products**: 根据名称模糊搜索产品
   - 支持部分名称搜索
   - 例如搜索"云"可以找到所有包含"云"字的产品

## 启动方式

### 1. 启动 ConsultMCPServer（端口 10003）

```bash
python3 consult_mcp_server/run_consult_mcp_server.py
```

### 2. 启动 ConsultAgent（端口 10005）

```bash
python3 consult_agent/run_consult_agent.py
```

### 3. 通过 SupervisorAgent 使用

启动 `chat.py`，然后输入咨询相关的问题，SupervisorAgent 会自动路由到 ConsultAgent。

## 使用示例

### 示例 1：查询所有产品

**用户输入**：
```
有哪些产品？
```

**流程**：
1. SupervisorAgent 识别为咨询请求
2. 路由到 ConsultAgent
3. ConsultAgent 调用 `consult-get-products` 工具
4. 返回产品列表

### 示例 2：查询产品详情

**用户输入**：
```
云边茉莉的产品信息是什么？
```

**流程**：
1. SupervisorAgent 识别为咨询请求
2. 路由到 ConsultAgent
3. ConsultAgent 调用 `consult-get-product-info` 工具
4. 返回产品详细信息

### 示例 3：搜索产品

**用户输入**：
```
搜索包含"云"的产品
```

**流程**：
1. SupervisorAgent 识别为咨询请求
2. 路由到 ConsultAgent
3. ConsultAgent 调用 `consult-search-products` 工具
4. 返回匹配的产品列表

## 与 Java 项目的对比

### 相同点

1. ✅ 提供相同的工具接口
2. ✅ 支持产品查询功能
3. ✅ 支持知识库检索（简化版）
4. ✅ 使用 MCP 协议暴露工具

### 不同点

1. **知识库检索**：
   - Java 项目：使用 DashScope RAG（文档检索）
   - Python 项目：简化版，直接从数据库查询产品信息

2. **数据库访问**：
   - Java 项目：使用 MyBatis
   - Python 项目：使用 DatabaseManager（SQLite/MySQL）

## 配置

### services.json

已添加以下服务配置：

```json
{
  "consult_agent": {
    "host": "localhost",
    "port": 10005,
    "url": "http://localhost:10005",
    "description": "云边奶茶铺咨询智能体"
  },
  "consult-mcp-server": {
    "host": "localhost",
    "port": 10003,
    "url": "http://localhost:10003",
    "description": "咨询管理 MCP Server"
  }
}
```

### SupervisorAgent

已更新 `supervisor_agent.py`，将 `consult_agent` 标记为已实现：

```python
"consult_agent": {
    "name": "咨询智能体",
    "description": "处理产品咨询、活动信息和冲泡指导",
    "implemented": True  # 已实现
}
```

## 测试

### 手动测试

1. 启动 ConsultMCPServer：
   ```bash
   python3 consult_mcp_server/run_consult_mcp_server.py
   ```

2. 启动 ConsultAgent：
   ```bash
   python3 consult_agent/run_consult_agent.py
   ```

3. 启动 SupervisorAgent：
   ```bash
   python3 chat.py
   ```

4. 测试咨询功能：
   - 输入："有哪些产品？"
   - 输入："云边茉莉的产品信息是什么？"
   - 输入："搜索包含'云'的产品"

### 健康检查

- ConsultMCPServer: `curl http://localhost:10003/mcp/health`
- ConsultAgent: `curl http://localhost:10005/a2a/health`

## 后续改进

1. **知识库检索增强**：
   - 集成 DashScope RAG（如果需要）
   - 支持更多类型的知识检索

2. **活动信息**：
   - 添加活动信息数据库表
   - 实现活动查询工具

3. **冲泡指导**：
   - 添加冲泡方法数据库
   - 实现冲泡指导工具

## 注意事项

1. 确保数据库已初始化（包含 products 表）
2. 确保 ConsultMCPServer 在 ConsultAgent 之前启动
3. 确保端口 10003 和 10005 未被占用
