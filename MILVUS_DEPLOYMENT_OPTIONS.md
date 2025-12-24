# Milvus 部署方式说明

## 概述

Milvus 支持多种部署方式，本项目支持两种模式：

1. **Milvus Lite**（推荐）：无需 Docker，作为 Python 库直接使用
2. **Milvus Standalone**：需要 Docker 或独立服务

## 方式 1：Milvus Lite（推荐，无需 Docker）

### 特点

- ✅ **无需 Docker**：作为 Python 库直接使用
- ✅ **无需单独服务**：像 SQLite 一样，直接使用
- ✅ **本地数据库**：数据存储在本地文件
- ✅ **完全免费**：开源软件
- ✅ **简单易用**：安装 `pymilvus` 即可使用

### 安装和使用

```bash
# 1. 安装依赖（只需要这个）
pip install pymilvus

# 2. 直接使用（无需启动任何服务）
python3
```

```python
from rag.rag_service import RAGService

# 使用 Milvus Lite（无需 Docker）
rag_service = RAGService(
    use_milvus=True,
    milvus_mode="lite",  # 或省略（默认就是 lite）
    milvus_collection_name="rag_knowledge_base",
    milvus_db_path=None  # None 则使用默认路径：data/milvus_lite.db
)

# 加载知识库（向量会存储到本地数据库文件）
rag_service.load_knowledge_base()
```

### 数据存储位置

默认存储在：`data/milvus_lite.db`

可以自定义路径：
```python
rag_service = RAGService(
    use_milvus=True,
    milvus_mode="lite",
    milvus_db_path="/path/to/your/milvus.db"
)
```

## 方式 2：Milvus Standalone（需要 Docker）

### 特点

- ⚠️ **需要 Docker**：需要运行 Milvus 服务
- ✅ **高性能**：适合大规模数据
- ✅ **完全免费**：本地部署免费
- ⚠️ **需要维护**：需要管理 Docker 容器

### 安装和使用

```bash
# 1. 安装依赖
pip install pymilvus

# 2. 启动 Milvus 服务（Docker）
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest
```

```python
from rag.rag_service import RAGService

# 使用 Milvus Standalone（需要 Docker）
rag_service = RAGService(
    use_milvus=True,
    milvus_mode="standalone",
    milvus_host="localhost",
    milvus_port=19530,
    milvus_collection_name="rag_knowledge_base"
)
```

## 对比

| 特性 | Milvus Lite | Milvus Standalone |
|------|------------|-------------------|
| **需要 Docker** | ❌ 不需要 | ✅ 需要 |
| **需要单独服务** | ❌ 不需要 | ✅ 需要 |
| **部署复杂度** | ⭐ 极简单 | ⭐⭐⭐ 中等 |
| **性能** | 好（中小规模） | 优秀（大规模） |
| **数据存储** | 本地文件 | Docker 容器内 |
| **适用场景** | 开发、测试、中小规模生产 | 大规模生产环境 |

## 推荐选择

### 推荐使用 Milvus Lite（默认）

- ✅ 最简单：无需 Docker，无需单独服务
- ✅ 足够用：对于大多数场景性能足够
- ✅ 易维护：像 SQLite 一样简单

### 使用 Milvus Standalone 的场景

- 需要处理超大规模数据（> 1000 万向量）
- 需要分布式部署
- 需要更高的性能

## 使用示例

### 示例 1：使用 Milvus Lite（推荐）

```python
from rag.rag_service import RAGService

# 最简单的方式：使用 Milvus Lite
rag_service = RAGService(use_milvus=True)  # 默认就是 lite 模式

# 加载知识库
rag_service.load_knowledge_base()

# 搜索
result = rag_service.search("查询内容")
```

### 示例 2：使用 Milvus Standalone

```python
from rag.rag_service import RAGService

# 使用 Milvus Standalone（需要先启动 Docker 服务）
rag_service = RAGService(
    use_milvus=True,
    milvus_mode="standalone",
    milvus_host="localhost",
    milvus_port=19530
)

# 加载知识库
rag_service.load_knowledge_base()

# 搜索
result = rag_service.search("查询内容")
```

## 总结

**Milvus 不是只能 Docker 部署！**

- ✅ **Milvus Lite**：无需 Docker，作为 Python 库直接使用（推荐）
- ✅ **Milvus Standalone**：需要 Docker，适合大规模场景

**对于大多数场景，推荐使用 Milvus Lite，就像使用 SQLite 一样简单！**
