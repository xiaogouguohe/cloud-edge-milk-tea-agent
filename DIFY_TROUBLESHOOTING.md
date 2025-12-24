# Dify 知识库连接问题排查

## 当前错误

测试时遇到错误：
```
{"code":"invalid_param","message":"Default model not found for text-embedding","status":400}
```

## 问题分析

这个错误说明：
1. ✅ API URL 和 API Key 是正确的（否则会返回 401 认证错误）
2. ✅ Dataset ID 是正确的（否则会返回 404 或其他错误）
3. ❌ **知识库没有配置默认的 embedding 模型**

## 解决方案

### 方案 1：在 Dify 控制台配置 Embedding 模型（推荐）

1. 登录 Dify 控制台
2. 进入您的知识库设置页面
3. 找到 "Embedding 模型" 或 "向量模型" 配置
4. 选择一个 embedding 模型（例如：`text-embedding-v2`）
5. 保存配置

### 方案 2：在 API 请求中指定 Embedding 模型

如果无法在控制台配置，可以在 `.env` 文件中添加：

```env
DIFY_EMBEDDING_MODEL=text-embedding-v2
```

然后在 API 请求中指定该模型。

### 方案 3：使用 Dify 的对话 API（如果支持）

某些 Dify 版本可能支持通过对话 API 访问知识库，而不是直接使用检索 API。

## 测试步骤

### 1. 检查 Dify 控制台配置

- 确认知识库已创建
- 确认知识库已上传文档
- **确认知识库已配置 embedding 模型**

### 2. 查看 Dify API 文档

在 Dify 控制台的"API"或"开发者"页面查看：
- 正确的 API 端点
- 请求格式
- 是否需要指定 embedding 模型

### 3. 使用测试脚本

运行测试脚本：
```bash
python3 test_dify_simple.py
```

查看详细的错误信息。

## 常见 Embedding 模型

Dify 可能支持的 embedding 模型：
- `text-embedding-v2`（通义千问）
- `text-embedding-v1`（通义千问）
- `text-embedding-ada-002`（OpenAI）
- 其他自定义模型

## 临时解决方案

如果暂时无法配置 embedding 模型，系统会自动回退到：
1. DashScope RAG（如果配置了 `DASHSCOPE_INDEX_ID`）
2. 数据库查询（从 products 表查询）

这样至少可以保证基本功能可用。
