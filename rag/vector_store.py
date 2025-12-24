"""
内存向量存储 - 不依赖 LangChain，使用 numpy 进行相似度计算
"""
import sys
from typing import List, Dict, Optional
import numpy as np

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("[VectorStore] 警告: numpy 未安装，将使用纯 Python 实现（性能较慢）", file=sys.stderr, flush=True)


class InMemoryVectorStore:
    """内存向量存储 - 使用 numpy 进行相似度搜索"""
    
    def __init__(self, embeddings: Optional[object] = None):
        """
        初始化向量存储
        
        Args:
            embeddings: Embeddings 对象，用于生成向量
        """
        self.embeddings = embeddings
        self.documents: List[Dict] = []  # 存储文档内容
        self.vectors: List[List[float]] = []  # 存储向量
        
        if not NUMPY_AVAILABLE:
            print("[VectorStore] 建议安装 numpy 以获得更好的性能: pip install numpy", file=sys.stderr, flush=True)
    
    def add_documents(self, documents: List[Dict]):
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表，每个文档是包含 'content' 和 'metadata' 的字典
        """
        if not self.embeddings:
            raise ValueError("需要提供 embeddings 对象才能添加文档")
        
        # 提取文本内容
        texts = [doc.get('content', doc.get('page_content', '')) for doc in documents]
        
        # 生成向量
        vectors = self.embeddings.embed_documents(texts)
        
        # 存储文档和向量
        for doc, vector in zip(documents, vectors):
            self.documents.append(doc)
            self.vectors.append(vector)
        
        print(f"[VectorStore] 已添加 {len(documents)} 个文档", file=sys.stderr, flush=True)
    
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
        
        if not self.vectors:
            return []
        
        # 生成查询向量
        query_vector = self.embeddings.embed_query(query)
        
        # 计算相似度
        similarities = self._compute_similarities(query_vector, self.vectors)
        
        # 获取 top-k
        if NUMPY_AVAILABLE:
            # 使用 numpy 快速排序
            similarities_array = np.array(similarities)
            top_k_indices = np.argsort(similarities_array)[-k:][::-1]
            top_k_scores = similarities_array[top_k_indices].tolist()
            top_k_indices = top_k_indices.tolist()
        else:
            # 纯 Python 实现
            indexed_scores = [(i, score) for i, score in enumerate(similarities)]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
            top_k_indices = [i for i, _ in indexed_scores[:k]]
            top_k_scores = [score for _, score in indexed_scores[:k]]
        
        # 构建结果
        results = []
        for idx, score in zip(top_k_indices, top_k_scores):
            if score >= score_threshold:
                doc = self.documents[idx].copy()
                doc['score'] = float(score)
                results.append(doc)
        
        return results
    
    def _compute_similarities(self, query_vector: List[float], vectors: List[List[float]]) -> List[float]:
        """计算相似度（余弦相似度）"""
        if NUMPY_AVAILABLE:
            # 使用 numpy 快速计算
            query_vec = np.array(query_vector)
            vecs = np.array(vectors)
            
            # 归一化
            query_vec = query_vec / np.linalg.norm(query_vec)
            vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
            
            # 计算余弦相似度（点积）
            similarities = np.dot(vecs, query_vec)
            return similarities.tolist()
        else:
            # 纯 Python 实现
            def cosine_similarity(a, b):
                dot_product = sum(x * y for x, y in zip(a, b))
                norm_a = sum(x * x for x in a) ** 0.5
                norm_b = sum(x * x for x in b) ** 0.5
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                return dot_product / (norm_a * norm_b)
            
            return [cosine_similarity(query_vector, vec) for vec in vectors]
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None):
        """
        直接添加文本（便捷方法）
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表（可选）
        """
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        documents = [
            {'content': text, 'metadata': metadata}
            for text, metadata in zip(texts, metadatas)
        ]
        
        self.add_documents(documents)
    
    def clear(self):
        """清空向量存储"""
        self.documents = []
        self.vectors = []
