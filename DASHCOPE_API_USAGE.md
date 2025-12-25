# DashScope API 调用说明

## 是的，有两个阶段都会调用 DashScope API

### 阶段 1：加载知识库时（文档向量化）

```python
# rag/rag_service.py - load_knowledge_base()
def load_knowledge_base(self):
    # 1. 加载文档
    documents = loader.load()  # 加载 Markdown 文件
    
    # 2. 分割文档
    split_docs = self.text_splitter.split_documents(documents)
    
    # 3. 添加到向量存储（这里会调用 DashScope API）
    self.vector_store.add_documents(split_docs)  # ← 调用 DashScope API
```

```python
# rag/milvus_lite_vector_store.py - add_documents()
def add_documents(self, documents):
    # 提取文本内容
    texts = [doc.get('content', '') for doc in documents]
    
    # 生成向量（调用 DashScope API）← 这里！
    vectors = self.embeddings.embed_documents(texts)  # ← 调用 DashScope API
    
    # 存入 Milvus 数据库
    self.client.insert(data)
```

**调用时机：** 只在第一次加载知识库时调用，或者强制重新加载时调用  
**调用次数：** 等于文档块的数量（例如 9 个文档块 = 9 次 API 调用，或者批量调用）  
**结果：** 向量存入 Milvus 数据库（持久化）

---

### 阶段 2：查询时（查询向量化）

```python
# rag/milvus_lite_vector_store.py - similarity_search()
def similarity_search(self, query: str):
    # 生成查询向量（调用 DashScope API）← 这里！
    query_vector = self.embeddings.embed_query(query)  # ← 调用 DashScope API
    
    # 在 Milvus 中搜索相似向量（本地查询，很快）
    results = self.client.search(data=[query_vector])
    
    return results
```

**调用时机：** 每次查询时都会调用  
**调用次数：** 每次查询 = 1 次 API 调用  
**结果：** 用于在 Milvus 中搜索相似向量

---

## 完整的 RAG 流程

### 第一次使用（加载知识库）

```
1. 加载文档（Markdown 文件）
   ↓
2. 分割文档（分成多个块）
   ↓
3. 调用 DashScope API 生成文档向量 ← API 调用 1
   - 文档块 1 → 向量 1
   - 文档块 2 → 向量 2
   - ...
   - 文档块 9 → 向量 9
   ↓
4. 将向量存入 Milvus 数据库（持久化存储）
```

### 后续查询

```
1. 用户输入查询："云边茉莉的特点是什么？"
   ↓
2. 调用 DashScope API 生成查询向量 ← API 调用 2（每次查询都调用）
   - 查询文本 → 查询向量
   ↓
3. 在 Milvus 数据库中搜索相似向量（本地查询，很快）
   ↓
4. 返回最相似的文档内容
```

---

## 为什么查询时也要调用 API？

因为：

1. **查询向量需要实时生成**：用户每次的查询文本都不同，无法预先缓存
2. **向量相似度计算需要**：只有将查询文本转换为向量，才能在向量空间中计算相似度
3. **这是 RAG 的标准流程**：查询向量和文档向量需要在同一个向量空间中

---

## 性能优化建议

### 1. 查询向量缓存（如果查询重复）

```python
# 如果相同的查询重复出现，可以缓存查询向量
query_vector_cache = {}

def get_query_vector(query: str):
    if query not in query_vector_cache:
        query_vector_cache[query] = embeddings.embed_query(query)
    return query_vector_cache[query]
```

### 2. 批量生成文档向量（如果可能）

DashScope API 支持批量处理，可以减少 API 调用次数。

### 3. 检查网络环境

如果 DashScope API 调用很慢（>5秒），可能是网络问题，需要检查网络连接。

---

## 总结

✅ **文档向量化时调用 DashScope API**（加载知识库时，一次性的）  
✅ **查询向量化时也调用 DashScope API**（每次查询时，每次都调用）  

**这就是为什么查询会慢的原因**：每次查询都需要等待 DashScope API 响应（如果网络慢，就会很慢）。

