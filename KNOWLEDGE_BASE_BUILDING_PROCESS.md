# 知识库构建过程详解

## 一、整体流程概览

```
原始文档（Markdown/TXT）
    ↓
【步骤1】文档加载（Document Loading）
    ↓
【步骤2】文本分割（Text Splitting）
    ↓
【步骤3】向量化（Embedding）
    ↓
【步骤4】向量存储（Vector Storage）
    ↓
向量数据库（Milvus Lite）
```

---

## 二、详细步骤说明

### 步骤1：文档加载（Document Loading）

**目的**：从文件系统中读取知识库文档

**实现**：`rag/document_loader.py` 中的 `DirectoryLoader`

**流程**：
1. 扫描知识库目录（默认：`knowledge_base/`）
2. 匹配文件模式（默认：`**/*.md`，即所有 Markdown 文件）
3. 读取文件内容（UTF-8 编码）
4. 构建文档对象，包含：
   - `content`: 文件内容（字符串）
   - `metadata`: 元数据（文件路径、文件名、文件类型等）

**代码示例**：
```python
from rag.document_loader import DirectoryLoader

loader = DirectoryLoader(
    directory="knowledge_base",
    glob_pattern="**/*.md"  # 匹配所有 .md 文件
)
documents = loader.load()  # 返回文档列表
```

**输出示例**：
```python
[
    {
        'content': '云边茉莉是云边奶茶铺的经典产品之一...',
        'metadata': {
            'source': 'knowledge_base/products/云边茉莉.txt',
            'filename': '云边茉莉.txt',
            'file_type': '.txt'
        }
    },
    ...
]
```

**特点**：
- ✅ 支持递归扫描子目录
- ✅ 支持多种文件格式（.md, .txt 等）
- ✅ 自动提取文件元数据
- ✅ 错误处理：单个文件加载失败不影响其他文件

---

### 步骤2：文本分割（Text Splitting）

**目的**：将长文档分割成小块，便于向量化和检索

**为什么需要分割**：
- LLM 的上下文窗口有限
- 向量化模型对输入长度有限制
- 小块文档可以提高检索精度

**实现**：`rag/text_splitter.py` 中的 `RecursiveCharacterTextSplitter`

**分割策略**：
- **chunk_size**: 每个块的最大字符数（默认：1000）
- **chunk_overlap**: 块之间的重叠字符数（默认：200）
- **分隔符优先级**：`\n\n` > `\n` > `。` > `！` > `？` > `；` > `，` > ` ` > `""`

**分割流程**：
1. 优先按段落分割（`\n\n`）
2. 如果段落太长，按句子分割
3. 如果句子太长，按字符分割
4. 保持块之间的重叠，确保上下文连续性

**代码示例**：
```python
from rag.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # 每个块最多 1000 字符
    chunk_overlap=200     # 块之间重叠 200 字符
)

split_docs = splitter.split_documents(documents)
```

**输入示例**：
```python
{
    'content': '云边茉莉是云边奶茶铺的经典产品之一。\n\n产品特点：\n- 清新的茉莉花香...',
    'metadata': {...}
}
```

**输出示例**：
```python
[
    {
        'content': '云边茉莉是云边奶茶铺的经典产品之一。\n\n产品特点：\n- 清新的茉莉花香...',
        'metadata': {
            'source': 'knowledge_base/products/云边茉莉.txt',
            'chunk_index': 0,
            'total_chunks': 2
        }
    },
    {
        'content': '制作工艺：\n- 选用优质茉莉花茶...',
        'metadata': {
            'source': 'knowledge_base/products/云边茉莉.txt',
            'chunk_index': 1,
            'total_chunks': 2
        }
    }
]
```

**特点**：
- ✅ 智能分割：优先在段落、句子边界分割
- ✅ 保持上下文：通过重叠确保信息连续性
- ✅ 保留元数据：每个块都包含原始文档的元数据

---

### 步骤3：向量化（Embedding）

**目的**：将文本转换为高维向量，用于相似度计算

**实现**：`rag/dashscope_embeddings.py` 中的 `DashScopeEmbeddings`

**向量化模型**：
- 模型：`text-embedding-v2`（DashScope）
- 向量维度：1536
- API：DashScope TextEmbedding API

**流程**：
1. 调用 DashScope API
2. 传入文本列表（批量处理）
3. 获取向量列表
4. 每个文本对应一个 1536 维的浮点数向量

**代码示例**：
```python
from rag.dashscope_embeddings import DashScopeEmbeddings

embeddings = DashScopeEmbeddings(model="text-embedding-v2")

# 批量向量化
texts = ["云边茉莉是...", "制作工艺：..."]
vectors = embeddings.embed_documents(texts)
# 返回: [[0.1, 0.2, ...], [0.3, 0.4, ...]]
```

**API 调用**：
```python
response = TextEmbedding.call(
    model="text-embedding-v2",
    input=texts  # 文本列表
)
```

**输出示例**：
```python
[
    [0.123, -0.456, 0.789, ..., 0.234],  # 第一个文本的向量（1536维）
    [0.345, -0.567, 0.890, ..., 0.345],  # 第二个文本的向量（1536维）
    ...
]
```

**特点**：
- ✅ 批量处理：一次 API 调用可以处理多个文本
- ✅ 高效：减少 API 调用次数
- ✅ 标准化：使用统一的向量空间

**注意事项**：
- ⚠️ 需要网络连接（调用 DashScope API）
- ⚠️ 需要 API Key
- ⚠️ 批量处理时注意 API 限流

---

### 步骤4：向量存储（Vector Storage）

**目的**：将向量和文档内容存储到向量数据库，支持快速检索

**实现**：`rag/milvus_lite_vector_store.py` 中的 `MilvusLiteVectorStore`

**存储内容**：
- `vector`: 文本的向量表示（1536 维浮点数数组）
- `content`: 原始文本内容
- `metadata`: 文档元数据（JSON 字符串）

**流程**：
1. 准备数据：将文档、向量、元数据组合
2. 插入 Milvus Lite：调用 `client.insert()`
3. 自动索引：Milvus Lite 自动创建索引，支持快速检索

**代码示例**：
```python
from rag.milvus_lite_vector_store import MilvusLiteVectorStore

vector_store = MilvusLiteVectorStore(
    embeddings=embeddings,
    collection_name="rag_knowledge_base",
    db_path="./data/milvus_lite.db"
)

# 添加文档（内部会调用向量化）
vector_store.add_documents(split_docs)
```

**内部实现**：
```python
# 1. 提取文本
texts = [doc['content'] for doc in documents]

# 2. 生成向量（调用 DashScope API）
vectors = self.embeddings.embed_documents(texts)

# 3. 准备数据
data = []
for doc, vector in zip(documents, vectors):
    data.append({
        "vector": vector,
        "content": doc['content'],
        "metadata": json.dumps(doc['metadata'])
    })

# 4. 插入 Milvus Lite
self.client.insert(
    collection_name=self.collection_name,
    data=data
)
```

**存储位置**：
- 文件：`./data/milvus_lite.db`（Milvus Lite 数据库文件）
- 集合：`rag_knowledge_base`（默认集合名称）

**特点**：
- ✅ 持久化存储：数据保存在本地文件
- ✅ 自动索引：支持快速相似度搜索
- ✅ 元数据保留：可以追踪文档来源

---

## 三、完整构建流程（代码层面）

### 入口：`RAGService.load_knowledge_base()`

**文件**：`rag/rag_service.py`

**完整流程**：
```python
def load_knowledge_base(self, force_reload: bool = False):
    # 1. 文档加载
    loader = DirectoryLoader(
        directory=str(self.knowledge_base_dir),
        glob_pattern="**/*.md"
    )
    documents = loader.load()
    
    # 2. 文本分割
    split_docs = self.text_splitter.split_documents(documents)
    
    # 3. 向量化 + 存储（在 add_documents 中完成）
    self.vector_store.add_documents(split_docs)
    
    self._loaded = True
```

**调用示例**：
```python
from rag.rag_service import RAGService

# 初始化 RAG 服务
rag_service = RAGService(
    knowledge_base_dir="knowledge_base",
    use_milvus=True,  # 使用 Milvus Lite
    milvus_collection_name="rag_knowledge_base"
)

# 构建知识库（一次性操作）
rag_service.load_knowledge_base()
```

---

## 四、数据流转示例

### 示例：处理 "云边茉莉.txt" 文档

**原始文档**（`knowledge_base/products/云边茉莉.txt`）：
```
云边茉莉是云边奶茶铺的经典产品之一。

产品特点：
- 清新的茉莉花香与醇厚奶茶的完美结合
- 口感层次丰富，既有茉莉花的清香，又有奶茶的醇厚
...

价格：18元/杯
```

**步骤1：文档加载**
```python
{
    'content': '云边茉莉是云边奶茶铺的经典产品之一。\n\n产品特点：...',
    'metadata': {
        'source': 'knowledge_base/products/云边茉莉.txt',
        'filename': '云边茉莉.txt',
        'file_type': '.txt'
    }
}
```

**步骤2：文本分割**（假设文档较长，被分割成2块）
```python
[
    {
        'content': '云边茉莉是云边奶茶铺的经典产品之一。\n\n产品特点：\n- 清新的茉莉花香...',
        'metadata': {
            'source': 'knowledge_base/products/云边茉莉.txt',
            'chunk_index': 0,
            'total_chunks': 2
        }
    },
    {
        'content': '价格：18元/杯\n保质期：30分钟...',
        'metadata': {
            'source': 'knowledge_base/products/云边茉莉.txt',
            'chunk_index': 1,
            'total_chunks': 2
        }
    }
]
```

**步骤3：向量化**（调用 DashScope API）
```python
# 输入文本
texts = [
    '云边茉莉是云边奶茶铺的经典产品之一。\n\n产品特点：...',
    '价格：18元/杯\n保质期：30分钟...'
]

# 调用 DashScope API
vectors = [
    [0.123, -0.456, 0.789, ..., 0.234],  # 1536 维向量
    [0.345, -0.567, 0.890, ..., 0.345]   # 1536 维向量
]
```

**步骤4：向量存储**（插入 Milvus Lite）
```python
data = [
    {
        "vector": [0.123, -0.456, 0.789, ..., 0.234],
        "content": "云边茉莉是云边奶茶铺的经典产品之一。\n\n产品特点：...",
        "metadata": '{"source": "knowledge_base/products/云边茉莉.txt", "chunk_index": 0, ...}'
    },
    {
        "vector": [0.345, -0.567, 0.890, ..., 0.345],
        "content": "价格：18元/杯\n保质期：30分钟...",
        "metadata": '{"source": "knowledge_base/products/云边茉莉.txt", "chunk_index": 1, ...}'
    }
]

# 插入 Milvus Lite
client.insert(collection_name="rag_knowledge_base", data=data)
```

---

## 五、关键参数说明

### 文本分割参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 1000 | 每个块的最大字符数 |
| `chunk_overlap` | 200 | 块之间的重叠字符数 |
| `separators` | `["\n\n", "\n", "。", ...]` | 分割符优先级列表 |

**调整建议**：
- 如果文档较短：可以增大 `chunk_size`
- 如果需要更多上下文：可以增大 `chunk_overlap`
- 如果文档结构特殊：可以自定义 `separators`

### 向量化参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `model` | `text-embedding-v2` | DashScope Embedding 模型 |
| `dimension` | 1536 | 向量维度（由模型决定） |

### 向量存储参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `collection_name` | `rag_knowledge_base` | Milvus 集合名称 |
| `db_path` | `./data/milvus_lite.db` | Milvus Lite 数据库路径 |
| `metric_type` | `COSINE` | 相似度计算方式（余弦相似度） |

---

## 六、性能优化建议

### 1. 批量处理

**问题**：逐个文档向量化会非常慢

**解决**：批量处理多个文档
```python
# ✅ 推荐：批量处理
vectors = embeddings.embed_documents(texts)  # 一次处理多个

# ❌ 不推荐：逐个处理
for text in texts:
    vector = embeddings.embed_query(text)  # 多次 API 调用
```

### 2. 增量更新

**问题**：每次重新构建整个知识库很慢

**解决**：只处理新增或修改的文档
```python
# 检查文档是否已存在
if not document_exists(doc_id):
    vector_store.add_documents([new_doc])
```

### 3. 缓存机制

**问题**：相同文档重复向量化

**解决**：缓存已向量化的文档
```python
# 使用文档哈希作为缓存键
doc_hash = hash(document_content)
if doc_hash in cache:
    vector = cache[doc_hash]
else:
    vector = embeddings.embed_query(document_content)
    cache[doc_hash] = vector
```

---

## 七、常见问题

### Q1: 为什么需要文本分割？

**A**: 
- LLM 上下文窗口有限（通常几千到几万 token）
- 向量化模型对输入长度有限制
- 小块文档可以提高检索精度（更精确匹配）

### Q2: 分割后的块太小会丢失信息吗？

**A**: 
- 通过 `chunk_overlap` 保持上下文连续性
- 检索时会返回多个相关块，可以组合使用
- 元数据中保留了原始文档信息

### Q3: 向量化需要多长时间？

**A**: 
- 取决于文档数量和 DashScope API 响应速度
- 批量处理可以显著提高速度
- 通常每个文档需要 1-3 秒（包括网络延迟）

### Q4: 数据会持久化吗？

**A**: 
- ✅ 使用 Milvus Lite：数据持久化到本地文件
- ❌ 使用内存存储：重启后数据丢失

### Q5: 如何更新知识库？

**A**: 
```python
# 方式1：强制重新加载
rag_service.load_knowledge_base(force_reload=True)

# 方式2：清空后重新加载
rag_service.clear()
rag_service.load_knowledge_base()

# 方式3：增量添加
rag_service.add_documents([new_doc])
```

---

## 八、完整示例代码

```python
from rag.rag_service import RAGService

# 1. 初始化 RAG 服务
rag_service = RAGService(
    knowledge_base_dir="knowledge_base",  # 知识库目录
    embedding_model="text-embedding-v2",  # Embedding 模型
    use_milvus=True,                      # 使用 Milvus Lite
    milvus_collection_name="rag_knowledge_base",
    milvus_db_path="./data/milvus_lite.db"
)

# 2. 构建知识库（一次性操作）
print("开始构建知识库...")
rag_service.load_knowledge_base()
print("知识库构建完成！")

# 3. 使用知识库进行检索
result = rag_service.search("云边茉莉的特点是什么？", k=3)
print(result)
```

---

## 九、总结

知识库构建是一个**多步骤的流水线过程**：

1. **文档加载**：从文件系统读取文档
2. **文本分割**：将长文档分割成小块
3. **向量化**：将文本转换为向量（调用 DashScope API）
4. **向量存储**：存储到 Milvus Lite 向量数据库

**关键特点**：
- ✅ 自动化：一键构建整个知识库
- ✅ 持久化：数据保存在本地文件
- ✅ 可扩展：支持增量更新
- ✅ 高效：批量处理，减少 API 调用

**适用场景**：
- 产品知识库
- 文档检索
- 问答系统
- 智能客服

