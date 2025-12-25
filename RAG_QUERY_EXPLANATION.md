# RAG 查询流程说明

## 查询知识库时，是查询 Milvus 数据库还是内存？

**答案：查询 Milvus 数据库（持久化存储）**

## 详细流程

### 1. 使用 Milvus Lite 时（当前配置）

```python
# rag/milvus_lite_vector_store.py
def similarity_search(self, query: str, k: int = 4, score_threshold: float = 0.0):
    # 步骤 1: 生成查询向量（调用 DashScope API）
    query_vector = self.embeddings.embed_query(query)
    
    # 步骤 2: 在 Milvus 数据库中搜索（从本地文件读取）
    results = self.client.search(
        collection_name=self.collection_name,
        data=[query_vector],
        limit=k,
        output_fields=["content", "metadata"],
    )
    
    return documents
```

**数据存储位置：**
- 数据库文件：`data/milvus_lite.db`（本地文件）
- 向量数据：持久化存储在文件中
- 文档内容：存储在 Milvus 集合中

**查询过程：**
1. 生成查询向量（调用 DashScope API，网络请求）
2. 在 Milvus 数据库中执行向量相似度搜索（从本地文件读取）
3. 返回匹配的文档内容

### 2. 使用内存存储时（不使用 Milvus）

```python
# rag/vector_store.py
def similarity_search(self, query: str, k: int = 4, score_threshold: float = 0.0):
    # 步骤 1: 生成查询向量（调用 DashScope API）
    query_vector = self.embeddings.embed_query(query)
    
    # 步骤 2: 在内存中搜索（self.vectors 列表）
    similarities = self._compute_similarities(query_vector, self.vectors)
    
    return documents
```

**数据存储位置：**
- 内存：`self.vectors` 列表
- 文档：`self.documents` 列表
- **注意：重启后数据会丢失**

## 性能分析

### 当前测试结果（使用 Milvus Lite）

- **每个查询耗时：约 75 秒**
- **主要时间消耗：**
  1. **生成查询向量（DashScope API 调用）**：约 1-2 秒（网络请求）
  2. **Milvus 数据库搜索**：毫秒级（本地文件读取，非常快）
  3. **其他操作**：格式化结果等（毫秒级）

### 为什么查询这么慢？

**问题不在 Milvus 数据库查询，而在 DashScope API 调用！**

从代码可以看到，每次查询都会：
1. 调用 `self.embeddings.embed_query(query)` → 这会调用 DashScope API
2. 如果网络慢或 API 响应慢，就会导致查询很慢

**75 秒的耗时异常，可能原因：**
- 网络连接问题（超时、重试）
- DashScope API 限流或响应慢
- 其他阻塞操作

## 优化建议

### 1. 检查网络连接

```bash
# 测试 DashScope API 响应时间
python3 -c "
import time
from rag.dashscope_embeddings import DashScopeEmbeddings
emb = DashScopeEmbeddings()
start = time.time()
result = emb.embed_query('test')
print(f'API 调用耗时: {time.time() - start:.2f} 秒')
"
```

### 2. 使用缓存（如果查询重复）

可以考虑缓存查询向量，避免重复调用 API。

### 3. 批量查询优化

如果多个查询，可以考虑批量生成向量。

## 总结

- ✅ **查询 Milvus 数据库**（持久化存储，本地文件）
- ❌ **不是查询内存**（除非使用 `InMemoryVectorStore`）
- ⚠️ **主要耗时在 DashScope API 调用**，不在数据库查询
- 💡 **Milvus 查询本身很快**（毫秒级），瓶颈在网络 API 调用

