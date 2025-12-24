# Dify 知识库集成指南

## 概述

本文档说明如何将 Dify 知识库集成到 `consult_agent` 中，使其能够使用 Dify 平台上的知识库进行检索。

---

## 配置步骤

### 步骤 1：获取 Dify API 配置信息

在 Dify 控制台中获取以下信息：

1. **API URL**：
   - 登录 Dify 控制台
   - 进入"设置" → "API" 页面
   - 查看 API 服务器地址（例如：`https://api.dify.ai` 或您的自部署地址）

2. **API Key**：
   - 在 Dify 控制台的"API Access"页面
   - 生成新的 API 密钥
   - **重要**：请妥善保存，因为它仅显示一次

3. **Dataset ID（可选）**：
   - 如果您有多个知识库，需要指定 Dataset ID
   - 在知识库详情页面可以找到 Dataset ID
   - 如果只有一个知识库或使用默认知识库，可以不设置

### 步骤 2：配置环境变量

在 `.env` 文件中添加：

```env
# Dify 知识库配置
DIFY_API_URL=https://api.dify.ai          # 您的 Dify API 地址
DIFY_API_KEY=app-xxxxxxxxxxxxxxxx          # 您的 Dify API Key
DIFY_DATASET_ID=dataset-1234567890        # 知识库/数据集 ID（可选）
```

**注意**：
- `DIFY_API_URL` 和 `DIFY_API_KEY` 是必需的
- `DIFY_DATASET_ID` 是可选的，如果不设置，将使用默认知识库

### 步骤 3：验证配置

启动服务后，查看日志确认 Dify 服务是否已启用：

```bash
python3 consult_mcp_server/run_consult_mcp_server.py
```

如果看到以下日志，说明配置成功：
```
[DifyService] 初始化完成，API URL: https://api.dify.ai
[ConsultService] Dify 知识库服务已启用
```

---

## 工作原理

### 检索优先级

`ConsultService.search_knowledge()` 方法的检索优先级：

1. **Dify 知识库**（最高优先级）
   - 如果 `DIFY_API_URL` 和 `DIFY_API_KEY` 已配置
   - 调用 Dify API 检索知识库

2. **DashScope RAG**（备选方案）
   - 如果 Dify 不可用，且 `DASHSCOPE_INDEX_ID` 已配置
   - 使用 DashScope 文档检索

3. **数据库查询**（回退方案）
   - 如果以上都不可用
   - 从本地数据库查询产品信息

### API 调用流程

```
用户查询
    ↓
ConsultService.search_knowledge(query)
    ↓
检查 Dify 服务是否可用
    ├─ 可用 → 调用 DifyService.search(query)
    │         ↓
    │      发送 POST 请求到 Dify API
    │         ↓
    │      解析响应，返回文档内容
    │
    └─ 不可用 → 尝试 DashScope RAG
                ↓
              如果也不可用 → 数据库查询
```

---

## Dify API 调用示例

### API 端点

根据 Dify 版本，API 端点可能不同：

**方式 1：使用数据集 ID**
```
POST {DIFY_API_URL}/v1/datasets/{dataset_id}/retrieve
```

**方式 2：通用检索 API**
```
POST {DIFY_API_URL}/v1/retrieval
```

### 请求格式

```json
{
  "query": "云边茉莉的特点是什么？",
  "top_k": 5,
  "score_threshold": 0.5
}
```

### 响应格式

Dify API 可能返回以下格式之一：

**格式 1**：
```json
{
  "data": [
    {
      "content": "云边茉莉是...",
      "score": 0.95
    }
  ]
}
```

**格式 2**：
```json
{
  "documents": [
    {
      "text": "云边茉莉是...",
      "score": 0.95
    }
  ]
}
```

**格式 3**：
```json
{
  "results": [
    {
      "content": "云边茉莉是...",
      "score": 0.95
    }
  ]
}
```

`DifyService` 会自动适配这些格式。

---

## 测试

### 测试 Dify 知识库检索

```python
from consult_mcp_server.consult_service import ConsultService

service = ConsultService()

# 测试检索
result = service.search_knowledge("云边茉莉的特点是什么？")
print(result)
```

### 测试完整流程

1. 启动 ConsultMCPServer：
   ```bash
   python3 consult_mcp_server/run_consult_mcp_server.py
   ```

2. 启动 ConsultAgent：
   ```bash
   python3 consult_agent/run_consult_agent.py
   ```

3. 通过 SupervisorAgent 测试：
   ```bash
   python3 chat.py
   # 输入："云边茉莉的特点是什么？"
   ```

---

## 常见问题

### Q1: 如何知道 Dify API 的地址？

A: 
- 如果是 Dify Cloud：通常是 `https://api.dify.ai`
- 如果是自部署：查看您的 Dify 部署地址，API 地址通常是 `http://your-domain/v1` 或 `https://your-domain/v1`

### Q2: Dataset ID 在哪里找？

A: 
- 在 Dify 控制台进入知识库详情页面
- 查看 URL 或知识库设置，通常格式为 `dataset-xxxxx`
- 如果不确定，可以先不设置，使用默认知识库

### Q3: API Key 格式是什么？

A: 
- Dify API Key 通常以 `app-` 开头
- 例如：`app-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Q4: 如何测试 API 是否可用？

A: 可以使用 curl 测试：

```bash
curl -X POST "https://api.dify.ai/v1/retrieval" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "top_k": 5
  }'
```

### Q5: 如果 Dify API 返回错误怎么办？

A: 
- 检查 API URL 和 API Key 是否正确
- 检查网络连接
- 查看 DifyService 的日志输出
- 系统会自动回退到 DashScope RAG 或数据库查询

---

## 配置示例

### 完整 .env 配置示例

```env
# DashScope API 配置
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
DASHSCOPE_MODEL=qwen-plus

# DashScope 文档检索配置（可选）
DASHSCOPE_INDEX_ID=index-1234567890

# Dify 知识库配置（优先使用）
DIFY_API_URL=https://api.dify.ai
DIFY_API_KEY=app-xxxxxxxxxxxxxxxx
DIFY_DATASET_ID=dataset-1234567890
```

---

## 代码结构

### 新增文件

- `consult_mcp_server/dify_service.py`：Dify 知识库服务类

### 修改文件

- `consult_mcp_server/consult_service.py`：集成 Dify 服务
- `config.py`：添加 Dify 配置项

### 调用链

```
ConsultAgent
    ↓
ConsultMCPServer._search_knowledge()
    ↓
ConsultService.search_knowledge()
    ↓
DifyService.search()  # 优先
    ↓
DashScope RAG 或 数据库查询  # 备选
```

---

## 总结

通过以上配置，`consult_agent` 将能够：

1. ✅ 优先使用 Dify 知识库进行检索
2. ✅ 如果 Dify 不可用，自动回退到 DashScope RAG
3. ✅ 如果都不可用，回退到数据库查询
4. ✅ 提供完整的错误处理和日志记录

**配置要点**：
- 设置 `DIFY_API_URL` 和 `DIFY_API_KEY`
- 可选设置 `DIFY_DATASET_ID`（如果有多个知识库）
- 系统会自动选择可用的检索方式
