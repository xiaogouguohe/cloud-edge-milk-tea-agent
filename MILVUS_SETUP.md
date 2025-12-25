# Milvus 向量数据库集成指南

## 概述

本项目支持使用 Milvus 向量数据库来持久化存储 RAG 向量化结果。Milvus 是一个开源的向量数据库，专为大规模向量检索设计。

## Milvus 的优势

### ✅ 优点

1. **持久化存储**：向量数据存储在磁盘，服务重启后不丢失
2. **高性能检索**：使用 HNSW 等高效索引算法，检索速度快
3. **开源免费**：本地部署完全免费
4. **可扩展性**：支持从小规模到大规模（亿级向量）
5. **生产级**：适合生产环境使用

### ⚠️ 注意事项

1. **需要部署服务**：需要单独部署 Milvus 服务（Docker 或本地安装）
2. **额外依赖**：需要安装 `pymilvus` Python 包
3. **资源消耗**：需要一定的内存和存储空间
4. **小规模数据**：对于少量文档（< 1000），可能有点"大材小用"

## 安装和部署

### 方式 1：使用 Docker（推荐）

```bash
# 拉取 Milvus 镜像
docker pull milvusdb/milvus:latest

# 启动 Milvus（使用 Docker Compose）
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d

# 或者直接运行（简单模式）
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest
```

### 方式 2：本地安装

参考 [Milvus 官方文档](https://milvus.io/docs/install_standalone-docker.md)

## Python 依赖

```bash
pip install pymilvus
```

## 使用方法

### 1. 启动 Milvus 服务

确保 Milvus 服务正在运行：

```bash
# 检查 Milvus 是否运行
docker ps | grep milvus
# 或
curl http://localhost:9091/healthz
```

### 2. 配置 RAG 服务使用 Milvus

#### 方式 A：在代码中指定

```python
from rag.rag_service import RAGService

# 使用 Milvus
rag_service = RAGService(
    use_milvus=True,
    milvus_host="localhost",
    milvus_port=19530,
    milvus_collection_name="rag_knowledge_base"
)

# 加载知识库（向量会存储到 Milvus）
rag_service.load_knowledge_base()
```

#### 方式 B：通过环境变量配置

在 `.env` 文件中添加：

```env
# Milvus 配置
USE_MILVUS=true
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=rag_knowledge_base
```

然后在代码中：

```python
import os
from rag.rag_service import RAGService

use_milvus = os.getenv("USE_MILVus", "false").lower() == "true"
rag_service = RAGService(
    use_milvus=use_milvus,
    milvus_host=os.getenv("MILVUS_HOST", "localhost"),
    milvus_port=int(os.getenv("MILVUS_PORT", "19530")),
    milvus_collection_name=os.getenv("MILVUS_COLLECTION_NAME", "rag_knowledge_base"),
)
```

### 3. 自动回退机制

如果 Milvus 不可用，系统会自动回退到内存存储：

```python
# 如果 Milvus 连接失败，会自动使用 InMemoryVectorStore
rag_service = RAGService(use_milvus=True)  # 安全，会自动回退
```

## 验证

### 测试 Milvus 连接

```python
from rag.milvus_vector_store import MilvusVectorStore
from rag.dashscope_embeddings import DashScopeEmbeddings

# 测试连接
embeddings = DashScopeEmbeddings()
vector_store = MilvusVectorStore(
    embeddings=embeddings,
    collection_name="test_collection"
)

# 获取统计信息
stats = vector_store.get_collection_stats()
print(f"集合中的文档数: {stats.get('num_entities', 0)}")
```

## 成本分析

### 本地部署（免费）

- ✅ **完全免费**：Milvus 是开源软件
- ✅ **无使用限制**：可以存储任意数量的向量
- ⚠️ **需要自己维护**：需要管理服务器、备份等

### 云服务（付费）

- Zilliz Cloud（Milvus 的云服务）
- 阿里云 Milvus 服务
- 其他云服务商的 Milvus 托管服务

**注意**：本项目默认使用本地部署，完全免费。

## 性能对比

| 特性 | 内存存储 | Milvus |
|------|---------|--------|
| 持久化 | ❌ | ✅ |
| 启动速度 | 快（需重新生成向量） | 快（直接加载） |
| 检索速度 | 快（小规模） | 快（大规模更优） |
| 内存占用 | 高（全部在内存） | 低（按需加载） |
| 扩展性 | 差（受内存限制） | 好（支持大规模） |
| 部署复杂度 | 低 | 中（需要部署服务） |

## 适用场景

### 适合使用 Milvus

- ✅ 生产环境
- ✅ 文档数量 > 1000
- ✅ 需要持久化
- ✅ 需要高性能检索
- ✅ 需要支持大规模扩展

### 适合使用内存存储

- ✅ 开发/测试环境
- ✅ 文档数量 < 100
- ✅ 快速原型验证
- ✅ 不需要持久化

## 故障排查

### 问题 1：无法连接到 Milvus

```
ConnectionError: 无法连接到 Milvus 服务器 localhost:19530
```

**解决方案**：
1. 检查 Milvus 服务是否运行：`docker ps | grep milvus`
2. 检查端口是否正确：默认是 19530
3. 检查防火墙设置

### 问题 2：pymilvus 未安装

```
ImportError: pymilvus 未安装
```

**解决方案**：
```bash
pip install pymilvus
```

### 问题 3：集合已存在但无法访问

**解决方案**：
```python
# 清空并重新创建集合
vector_store.clear()
```

## 下一步

1. 安装 Milvus（Docker 方式最简单）
2. 安装 pymilvus：`pip install pymilvus`
3. 修改代码使用 Milvus：`RAGService(use_milvus=True)`
4. 测试验证

## 参考资源

- [Milvus 官方文档](https://milvus.io/docs)
- [pymilvus Python SDK](https://milvus.io/api-reference/pymilvus/v2.3.x/About.md)
- [Milvus Docker 部署](https://milvus.io/docs/install_standalone-docker.md)

