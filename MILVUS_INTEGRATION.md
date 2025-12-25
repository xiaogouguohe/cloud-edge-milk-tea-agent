# Milvus 向量数据库集成说明

## 概述

本项目已支持使用 **Milvus** 向量数据库来持久化存储 RAG 向量化结果。Milvus 是一个开源的向量数据库，专为大规模向量检索设计。

## Milvus 的优势和适用场景

### ✅ 优势

1. **持久化存储**：向量数据存储在磁盘，服务重启后不丢失
2. **高性能检索**：使用 HNSW 等高效索引算法，检索速度快
3. **开源免费**：本地部署完全免费
4. **可扩展性**：支持从小规模到大规模（亿级向量）
5. **生产级**：适合生产环境使用

### ⚠️ 注意事项和限制

1. **需要部署服务**：需要单独部署 Milvus 服务（Docker 或本地安装）
2. **额外依赖**：需要安装 `pymilvus` Python 包
3. **资源消耗**：需要一定的内存和存储空间
4. **小规模数据**：对于少量文档（< 100），可能有点"大材小用"，但依然可以使用

### 💰 成本说明

- **本地部署**：✅ **完全免费**（开源软件）
- **云服务**：⚠️ 可能付费（如 Zilliz Cloud、阿里云 Milvus 服务等）
- **本项目默认**：使用本地部署，完全免费

## 快速开始

### 1. 安装依赖

```bash
pip install pymilvus
```

### 2. 启动 Milvus 服务（Docker 方式，推荐）

```bash
# 方式 1: 使用 Docker Compose（推荐）
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d

# 方式 2: 直接运行 Docker 容器
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest
```

### 3. 验证 Milvus 服务

```bash
# 检查服务是否运行
docker ps | grep milvus

# 或检查健康状态
curl http://localhost:9091/healthz
```

### 4. 使用 Milvus 存储向量

#### 方式 A：在代码中指定

```python
from rag.rag_service import RAGService

# 使用 Milvus（持久化存储）
rag_service = RAGService(
    use_milvus=True,
    milvus_host="localhost",
    milvus_port=19530,
    milvus_collection_name="rag_knowledge_base"
)

# 加载知识库（向量会存储到 Milvus）
rag_service.load_knowledge_base()

# 搜索（从 Milvus 检索）
result = rag_service.search("云边茉莉的特点是什么？")
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

rag_service = RAGService(
    use_milvus=os.getenv("USE_MILVUS", "false").lower() == "true",
    milvus_host=os.getenv("MILVUS_HOST", "localhost"),
    milvus_port=int(os.getenv("MILVUS_PORT", "19530")),
    milvus_collection_name=os.getenv("MILVUS_COLLECTION_NAME", "rag_knowledge_base"),
)
```

## 自动回退机制

如果 Milvus 不可用，系统会自动回退到内存存储：

```python
# 安全：如果 Milvus 连接失败，会自动使用 InMemoryVectorStore
rag_service = RAGService(use_milvus=True)
```

## 性能对比

| 特性 | 内存存储 | Milvus |
|------|---------|--------|
| **持久化** | ❌ 重启丢失 | ✅ 持久化 |
| **启动速度** | 慢（需重新生成向量） | 快（直接加载） |
| **检索速度** | 快（小规模） | 快（大规模更优） |
| **内存占用** | 高（全部在内存） | 低（按需加载） |
| **扩展性** | 差（受内存限制） | 好（支持大规模） |
| **部署复杂度** | 低 | 中（需要部署服务） |
| **成本** | 免费 | 免费（本地部署） |

## 适用场景建议

### ✅ 适合使用 Milvus

- 生产环境
- 文档数量 > 100
- 需要持久化（重启后不丢失）
- 需要高性能检索
- 需要支持大规模扩展
- 希望避免每次启动都重新生成向量

### ✅ 适合使用内存存储

- 开发/测试环境
- 文档数量 < 100
- 快速原型验证
- 不需要持久化
- 不想部署额外服务

## 测试

运行测试脚本：

```bash
python3 test_milvus.py
```

## 故障排查

### 问题 1：无法连接到 Milvus

```
ConnectionError: 无法连接到 Milvus 服务器 localhost:19530
```

**解决方案**：
1. 检查 Milvus 服务是否运行：`docker ps | grep milvus`
2. 检查端口是否正确：默认是 19530
3. 检查防火墙设置
4. 查看 Milvus 日志：`docker logs milvus-standalone`

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

## 与 Java 项目的对比

| 项目 | 向量存储 | 持久化方式 |
|------|---------|-----------|
| **Java 项目** | DashScope 云端 | 云端持久化（通过 Index ID） |
| **Python 项目（内存）** | 本地内存 | ❌ 无持久化 |
| **Python 项目（Milvus）** | Milvus 本地 | ✅ 本地持久化 |

## 总结

- ✅ **Milvus 完全免费**（本地部署）
- ✅ **适合生产环境**使用
- ✅ **自动回退机制**，安全可靠
- ⚠️ **需要部署服务**（但 Docker 方式很简单）
- ⚠️ **小规模数据**可能有点"大材小用"，但依然可以使用

**推荐**：对于生产环境或需要持久化的场景，使用 Milvus 是很好的选择。

