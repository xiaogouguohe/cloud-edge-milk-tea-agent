# Milvus 常见问题解答

## Q1: Milvus 只能 Docker 部署吗？

**A: 不是！** Milvus 有多种部署方式：

### ✅ 方式 1：Milvus Lite（推荐，无需 Docker）

- **无需 Docker**：作为 Python 库直接使用
- **无需单独服务**：像 SQLite 一样，直接使用
- **本地数据库**：数据存储在本地文件
- **完全免费**：开源软件

```python
from rag.rag_service import RAGService

# 使用 Milvus Lite（无需 Docker）
rag_service = RAGService(
    use_milvus=True,
    milvus_mode="lite"  # 或省略（默认）
)
```

### ⚠️ 方式 2：Milvus Standalone（需要 Docker）

- **需要 Docker**：需要运行 Milvus 服务
- **独立服务**：类似 MySQL，需要单独启动服务
- **使用 gRPC**：不是 HTTP 协议

```python
# 需要先启动 Docker 服务
# docker run -d -p 19530:19530 milvusdb/milvus:latest

rag_service = RAGService(
    use_milvus=True,
    milvus_mode="standalone"
)
```

## Q2: Milvus 能像 MySQL 那样作为 HTTP 服务启动吗？

**A: 不能直接作为 HTTP 服务。**

- **Milvus Standalone**：使用 **gRPC 协议**，不是 HTTP
- **Milvus Lite**：作为 Python 库使用，不需要单独服务

**但是**，Milvus Lite 可以像 SQLite 一样直接使用，不需要任何服务！

## Q3: 推荐使用哪种方式？

### ✅ 推荐：Milvus Lite

**原因**：
- ✅ 最简单：无需 Docker，无需单独服务
- ✅ 足够用：对于大多数场景性能足够
- ✅ 易维护：像 SQLite 一样简单
- ✅ 持久化：数据存储在本地文件

**使用方式**：
```python
# 最简单的方式
rag_service = RAGService(use_milvus=True)  # 默认就是 lite 模式
```

### ⚠️ 使用 Standalone 的场景

- 需要处理超大规模数据（> 1000 万向量）
- 需要分布式部署
- 需要更高的性能

## Q4: Milvus Lite 和 Standalone 的区别？

| 特性 | Milvus Lite | Milvus Standalone |
|------|------------|-------------------|
| **需要 Docker** | ❌ 不需要 | ✅ 需要 |
| **需要单独服务** | ❌ 不需要 | ✅ 需要 |
| **部署方式** | Python 库 | Docker 容器 |
| **数据存储** | 本地文件 | Docker 容器内 |
| **协议** | Python API | gRPC |
| **适用场景** | 开发、测试、中小规模 | 大规模生产环境 |

## Q5: 数据存储在哪里？

### Milvus Lite

- **默认路径**：`data/milvus_lite.db`
- **可自定义**：通过 `milvus_db_path` 参数指定

### Milvus Standalone

- **存储位置**：Docker 容器内的数据卷
- **持久化**：需要配置 Docker 数据卷

## 总结

**Milvus 不是只能 Docker 部署！**

- ✅ **Milvus Lite**：无需 Docker，作为 Python 库直接使用（推荐）
- ✅ **Milvus Standalone**：需要 Docker，适合大规模场景

**对于大多数场景，推荐使用 Milvus Lite，就像使用 SQLite 一样简单！**
