"""
Milvus 向量存储 - 使用 Milvus 向量数据库进行持久化存储
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
import json

try:
    from pymilvus import (
        connections,
        Collection,
        FieldSchema,
        CollectionSchema,
        DataType,
        utility,
    )
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    # 定义占位符，避免类型注解错误
    Collection = type(None)
    print("[MilvusVectorStore] 警告: pymilvus 未安装，请运行: pip install pymilvus", file=sys.stderr, flush=True)


class MilvusVectorStore:
    """Milvus 向量存储 - 使用 Milvus 向量数据库"""
    
    def __init__(
        self,
        embeddings: Optional[object] = None,
        collection_name: str = "rag_knowledge_base",
        host: str = "localhost",
        port: int = 19530,
        dimension: int = 1536,  # text-embedding-v2 的维度
        auto_id: bool = True,
    ):
        """
        初始化 Milvus 向量存储
        
        Args:
            embeddings: Embeddings 对象，用于生成向量
            collection_name: Milvus 集合名称
            host: Milvus 服务器地址
            port: Milvus 服务器端口
            dimension: 向量维度（text-embedding-v2 是 1536）
            auto_id: 是否自动生成 ID
        """
        if not MILVUS_AVAILABLE:
            raise ImportError("pymilvus 未安装，请运行: pip install pymilvus")
        
        self.embeddings = embeddings
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.dimension = dimension
        self.auto_id = auto_id
        
        # 连接 Milvus
        self._connect()
        
        # 创建或获取集合
        self.collection = self._get_or_create_collection()
        
        print(f"[MilvusVectorStore] 已连接到 Milvus: {host}:{port}", file=sys.stderr, flush=True)
        print(f"[MilvusVectorStore] 集合名称: {collection_name}", file=sys.stderr, flush=True)
    
    def _connect(self):
        """连接到 Milvus 服务器"""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
            )
            print(f"[MilvusVectorStore] 成功连接到 Milvus 服务器", file=sys.stderr, flush=True)
        except Exception as e:
            raise ConnectionError(f"无法连接到 Milvus 服务器 {self.host}:{self.port}: {str(e)}")
    
    def _get_or_create_collection(self):
        """获取或创建集合"""
        # 检查集合是否存在
        if utility.has_collection(self.collection_name):
            print(f"[MilvusVectorStore] 集合 '{self.collection_name}' 已存在", file=sys.stderr, flush=True)
            collection = Collection(self.collection_name)
            # 加载集合到内存（如果未加载）
            if not collection.has_index():
                print(f"[MilvusVectorStore] 警告: 集合 '{self.collection_name}' 没有索引，将创建默认索引", file=sys.stderr, flush=True)
                self._create_index(collection)
            collection.load()
            return collection
        
        # 创建新集合
        print(f"[MilvusVectorStore] 创建新集合 '{self.collection_name}'", file=sys.stderr, flush=True)
        
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=self.auto_id),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
        ]
        
        # 创建集合模式
        schema = CollectionSchema(
            fields=fields,
            description="RAG 知识库向量存储"
        )
        
        # 创建集合
        collection = Collection(
            name=self.collection_name,
            schema=schema,
        )
        
        # 创建索引
        self._create_index(collection)
        
        # 加载集合
        collection.load()
        
        return collection
    
    def _create_index(self, collection: Collection):
        """创建向量索引"""
        index_params = {
            "metric_type": "COSINE",  # 使用余弦相似度
            "index_type": "HNSW",     # 使用 HNSW 索引（高性能）
            "params": {
                "M": 16,              # HNSW 参数
                "efConstruction": 200, # HNSW 参数
            }
        }
        
        collection.create_index(
            field_name="vector",
            index_params=index_params
        )
        print(f"[MilvusVectorStore] 已创建向量索引", file=sys.stderr, flush=True)
    
    def add_documents(self, documents: List[Dict]):
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表，每个文档是包含 'content' 和 'metadata' 的字典
        """
        if not self.embeddings:
            raise ValueError("需要提供 embeddings 对象才能添加文档")
        
        if not documents:
            return
        
        # 提取文本内容
        texts = [doc.get('content', doc.get('page_content', '')) for doc in documents]
        
        # 生成向量
        print(f"[MilvusVectorStore] 正在生成 {len(texts)} 个文档的向量...", file=sys.stderr, flush=True)
        vectors = self.embeddings.embed_documents(texts)
        
        # 准备数据
        contents = []
        metadatas = []
        vector_list = []
        
        for doc, vector in zip(documents, vectors):
            contents.append(doc.get('content', doc.get('page_content', '')))
            # 将 metadata 序列化为 JSON 字符串
            metadata = doc.get('metadata', {})
            metadatas.append(json.dumps(metadata, ensure_ascii=False))
            vector_list.append(vector)
        
        # 插入数据
        data = [
            contents,
            metadatas,
            vector_list,
        ]
        
        try:
            self.collection.insert(data)
            self.collection.flush()  # 确保数据写入
            print(f"[MilvusVectorStore] 已添加 {len(documents)} 个文档到 Milvus", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[MilvusVectorStore] 插入数据失败: {str(e)}", file=sys.stderr, flush=True)
            raise
    
    def similarity_search(self, query: str, k: int = 4, score_threshold: float = 0.0) -> List[Dict]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回最相似的 k 个文档
            score_threshold: 相似度阈值，低于此值的文档将被过滤
            
        Returns:
            文档列表，每个文档包含 'content', 'metadata', 'score'
        """
        if not self.embeddings:
            raise ValueError("需要提供 embeddings 对象才能进行搜索")
        
        # 生成查询向量
        query_vector = self.embeddings.embed_query(query)
        
        # 搜索参数
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 64},  # HNSW 搜索参数
        }
        
        # 执行搜索
        try:
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=k,
                output_fields=["content", "metadata"],
            )
            
            # 处理结果
            documents = []
            if results and len(results) > 0:
                for hit in results[0]:
                    # Milvus 返回的距离是越小越相似，需要转换为相似度分数
                    # 对于余弦相似度，距离 = 1 - 相似度，所以相似度 = 1 - 距离
                    similarity = 1 - hit.distance
                    
                    if similarity >= score_threshold:
                        # 解析 metadata
                        try:
                            metadata = json.loads(hit.entity.get("metadata", "{}"))
                        except:
                            metadata = {}
                        
                        doc = {
                            "content": hit.entity.get("content", ""),
                            "metadata": metadata,
                            "score": float(similarity),
                        }
                        documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"[MilvusVectorStore] 搜索失败: {str(e)}", file=sys.stderr, flush=True)
            raise
    
    def clear(self):
        """清空集合中的所有数据"""
        try:
            # 删除集合
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
                print(f"[MilvusVectorStore] 已删除集合 '{self.collection_name}'", file=sys.stderr, flush=True)
            
            # 重新创建集合
            self.collection = self._get_or_create_collection()
        except Exception as e:
            print(f"[MilvusVectorStore] 清空集合失败: {str(e)}", file=sys.stderr, flush=True)
            raise
    
    def get_collection_stats(self) -> Dict:
        """获取集合统计信息"""
        try:
            stats = self.collection.num_entities
            return {
                "collection_name": self.collection_name,
                "num_entities": stats,
            }
        except Exception as e:
            print(f"[MilvusVectorStore] 获取统计信息失败: {str(e)}", file=sys.stderr, flush=True)
            return {}
    
    def __del__(self):
        """清理连接"""
        try:
            connections.disconnect("default")
        except:
            pass
