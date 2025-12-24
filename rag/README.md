# RAG 模块说明

本模块实现了完整的 RAG（检索增强生成）功能，**不依赖 LangChain**，直接使用 DashScope API。

## 功能特性

- ✅ 直接调用 DashScope API 生成 embeddings（不依赖 LangChain）
- ✅ 内存向量存储（支持 numpy 加速）
- ✅ 文档分块和加载
- ✅ 相似度搜索
- ✅ 完整的 RAG 服务封装

## 模块结构

```
rag/
├── __init__.py              # 模块导出
├── dashscope_embeddings.py  # DashScope Embeddings（直接调用 API）
├── vector_store.py          # 内存向量存储
├── text_splitter.py         # 文本分割器
├── document_loader.py       # 文档加载器
└── rag_service.py           # RAG 服务（完整封装）
```

## 使用方法

### 1. 基本使用

```python
from rag.rag_service import RAGService

# 初始化 RAG 服务
rag_service = RAGService()

# 加载知识库（从 knowledge_base 目录）
rag_service.load_knowledge_base()

# 搜索
result = rag_service.search("云边茉莉的特点是什么？", k=5, score_threshold=0.5)
print(result)
```

### 2. 自定义知识库目录

```python
rag_service = RAGService(knowledge_base_dir="/path/to/your/knowledge_base")
rag_service.load_knowledge_base()
```

### 3. 手动添加文档

```python
documents = [
    {
        'content': '文档内容...',
        'metadata': {'source': 'file1.md'}
    }
]
rag_service.add_documents(documents)
```

### 4. 单独使用各个组件

```python
from rag.dashscope_embeddings import DashScopeEmbeddings
from rag.vector_store import InMemoryVectorStore
from rag.text_splitter import RecursiveCharacterTextSplitter
from rag.document_loader import DirectoryLoader

# 初始化组件
embeddings = DashScopeEmbeddings(model="text-embedding-v2")
vector_store = InMemoryVectorStore(embeddings=embeddings)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
loader = DirectoryLoader(directory="./knowledge_base", glob_pattern="**/*.md")

# 加载和分割文档
documents = loader.load()
split_docs = text_splitter.split_documents(documents)

# 添加到向量存储
vector_store.add_documents(split_docs)

# 搜索
results = vector_store.similarity_search("查询内容", k=5)
```

## 与 LangChain 的区别

| 特性 | 本实现 | LangChain |
|------|-------|-----------|
| 依赖 | 仅 dashscope | langchain + langchain-community |
| Embeddings | 直接调用 DashScope API | DashScopeEmbeddings 封装 |
| 向量存储 | 纯 Python + numpy | InMemoryVectorStore |
| 文本分割 | 自定义实现 | RecursiveCharacterTextSplitter |
| 文档加载 | 自定义实现 | 多种 Loader |

## 性能优化

- **numpy 加速**：如果安装了 numpy，向量相似度计算会使用 numpy 加速
- **批量处理**：支持批量生成 embeddings，减少 API 调用次数

## 依赖要求

- `dashscope>=1.17.0`：用于调用 DashScope API
- `numpy>=1.24.0`（可选但推荐）：用于向量计算加速

## 测试

运行测试脚本：

```bash
python3 test_rag.py
```

## 集成到 ConsultService

RAG 服务已集成到 `consult_mcp_server/consult_service.py` 中，作为 Dify 知识库的备选方案：

1. **优先级 1**：Dify 知识库（如果配置了）
2. **优先级 2**：本地 RAG 服务（本模块）
3. **优先级 3**：数据库查询（回退方案）

## 注意事项

1. **知识库目录**：默认从 `knowledge_base/` 目录加载 `.md` 文件
2. **相似度阈值**：建议设置为 0.3-0.5，太低会返回不相关结果，太高可能找不到结果
3. **chunk_size**：建议设置为 500-1000，根据文档长度调整
4. **API 调用**：每次搜索会调用 DashScope API 生成查询向量，注意 API 调用次数限制
