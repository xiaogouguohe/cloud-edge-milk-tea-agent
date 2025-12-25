"""
Milvus Lite 向量存储 - 使用 Milvus Lite（无需 Docker，作为 Python 库直接使用）
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
import json

try:
    from pymilvus import MilvusClient
    MILVUS_LITE_AVAILABLE = True
except ImportError:
    MILVUS_LITE_AVAILABLE = False
    print("[MilvusLiteVectorStore] 警告: pymilvus 未安装，请运行: pip install pymilvus", file=sys.stderr, flush=True)


class MilvusLiteVectorStore:
    """Milvus Lite 向量存储 - 使用 Milvus Lite（无需 Docker）"""
    
    def __init__(
        self,
        embeddings: Optional[object] = None,
        collection_name: str = "rag_knowledge_base",
        db_path: str = None,
        dimension: int = 1536,  # text-embedding-v2 的维度
    ):
        """
        初始化 Milvus Lite 向量存储
        
        Args:
            embeddings: Embeddings 对象，用于生成向量
            collection_name: Milvus 集合名称
            db_path: 数据库文件路径（如果为 None，则使用默认路径）
            dimension: 向量维度（text-embedding-v2 是 1536）
        """
        if not MILVUS_LITE_AVAILABLE:
            raise ImportError("pymilvus 未安装，请运行: pip install pymilvus")
        
        self.embeddings = embeddings
        self.collection_name = collection_name
        
        # 确定数据库路径
        if db_path is None:
            # 默认路径：项目根目录下的 data 文件夹
            project_root = Path(__file__).parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "milvus_lite.db")
        
        self.db_path = db_path
        
        # 连接 Milvus Lite（本地数据库）
        try:
            self.client = MilvusClient(uri=db_path)
            print(f"[MilvusLiteVectorStore] 已连接到 Milvus Lite 数据库: {db_path}", file=sys.stderr, flush=True)
        except Exception as e:
            raise ConnectionError(f"无法连接到 Milvus Lite 数据库 {db_path}: {str(e)}")
        
        # 创建或获取集合
        self._ensure_collection(dimension)
        
        print(f"[MilvusLiteVectorStore] 集合名称: {collection_name}", file=sys.stderr, flush=True)
    
    def _ensure_collection(self, dimension: int):
        """确保集合存在"""
        # 检查集合是否存在
        if self.client.has_collection(self.collection_name):
            print(f"[MilvusLiteVectorStore] 集合 '{self.collection_name}' 已存在", file=sys.stderr, flush=True)
        else:
            # 创建新集合
            print(f"[MilvusLiteVectorStore] 创建新集合 '{self.collection_name}'", file=sys.stderr, flush=True)
            
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=dimension,
                metric_type="COSINE",  # 使用余弦相似度
                auto_id=True,  # 自动生成 ID，这样插入数据时不需要提供 id 字段
            )
            print(f"[MilvusLiteVectorStore] 集合创建成功", file=sys.stderr, flush=True)
    
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
        print(f"[MilvusLiteVectorStore] 正在生成 {len(texts)} 个文档的向量...", file=sys.stderr, flush=True)
        vectors = self.embeddings.embed_documents(texts)
        
        # 准备数据（Milvus Lite 的格式）
        data = []
        for doc, vector in zip(documents, vectors):
            # 将 metadata 序列化为 JSON 字符串
            metadata = doc.get('metadata', {})
            metadata_str = json.dumps(metadata, ensure_ascii=False)
            
            data.append({
                "vector": vector,
                "content": doc.get('content', doc.get('page_content', '')),
                "metadata": metadata_str,
            })
        
        # 插入数据
        try:
            # Milvus Lite 的 insert 方法
            self.client.insert(
                collection_name=self.collection_name,
                data=data
            )
            print(f"[MilvusLiteVectorStore] 已添加 {len(documents)} 个文档到 Milvus Lite", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[MilvusLiteVectorStore] 插入数据失败: {str(e)}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
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
        
        # 执行搜索
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                limit=k,
                output_fields=["content", "metadata"],
            )
            
            # 处理结果（Milvus Lite 的返回格式）
            documents = []
            if results and len(results) > 0:
                for hit in results[0]:
                    # Milvus 返回的距离是越小越相似，需要转换为相似度分数
                    # 对于余弦相似度，距离 = 1 - 相似度，所以相似度 = 1 - 距离
                    distance = hit.get("distance", 0)
                    similarity = 1 - distance if distance <= 1 else 1 / (1 + distance)
                    
                    if similarity >= score_threshold:
                        # Milvus Lite 的返回格式可能不同
                        content = hit.get("content", hit.get("entity", {}).get("content", ""))
                        metadata_str = hit.get("metadata", hit.get("entity", {}).get("metadata", "{}"))
                        
                        # 解析 metadata
                        try:
                            metadata = json.loads(metadata_str)
                        except:
                            metadata = {}
                        
                        doc = {
                            "content": content,
                            "metadata": metadata,
                            "score": float(similarity),
                        }
                        documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"[MilvusLiteVectorStore] 搜索失败: {str(e)}", file=sys.stderr, flush=True)
            raise
    
    def clear(self):
        """清空集合中的所有数据"""
        try:
            # 删除集合
            if self.client.has_collection(self.collection_name):
                self.client.drop_collection(self.collection_name)
                print(f"[MilvusLiteVectorStore] 已删除集合 '{self.collection_name}'", file=sys.stderr, flush=True)
            
            # 重新创建集合
            test_vector = self.embeddings.embed_query("test")
            dimension = len(test_vector)
            self._ensure_collection(dimension)
        except Exception as e:
            print(f"[MilvusLiteVectorStore] 清空集合失败: {str(e)}", file=sys.stderr, flush=True)
            raise
    
    def get_collection_stats(self) -> Dict:
        """获取集合统计信息"""
        try:
            # Milvus Lite 的统计信息获取方式
            # 注意：Milvus Lite 可能没有 get_collection_stats 方法
            # 尝试查询集合信息
            try:
                stats = self.client.describe_collection(self.collection_name)
                num_entities = stats.get("num_entities", 0) if isinstance(stats, dict) else 0
            except:
                # 如果无法获取统计信息，返回基本信息
                num_entities = 0
            
            return {
                "collection_name": self.collection_name,
                "num_entities": num_entities,
                "db_path": self.db_path,
                "mode": "lite",
            }
        except Exception as e:
            print(f"[MilvusLiteVectorStore] 获取统计信息失败: {str(e)}", file=sys.stderr, flush=True)
            return {
                "collection_name": self.collection_name,
                "db_path": self.db_path,
                "mode": "lite",
            }
    
    def __del__(self):
        """清理连接"""
        try:
            if hasattr(self, 'client'):
                self.client.close()
        except:
            pass
