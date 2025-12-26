"""
RAG 服务 - 完整的 RAG 实现，不依赖 LangChain
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag.dashscope_embeddings import DashScopeEmbeddings
from rag.text_splitter import RecursiveCharacterTextSplitter
from rag.document_loader import DirectoryLoader, FileLoader

# 导入 Milvus Lite 向量存储（无需 Docker）
try:
    from rag.milvus_lite_vector_store import MilvusLiteVectorStore, MILVUS_LITE_AVAILABLE
except ImportError:
    MILVUS_LITE_AVAILABLE = False
    MilvusLiteVectorStore = None


class RAGService:
    """RAG 服务 - 提供检索增强生成功能"""
    
    def __init__(
        self,
        knowledge_base_dir: str = None,
        embedding_model: str = "text-embedding-v2",
        use_milvus: bool = True,
        milvus_collection_name: str = "rag_knowledge_base",
        milvus_db_path: str = None,
    ):
        """
        初始化 RAG 服务
        
        Args:
            knowledge_base_dir: 知识库目录路径，如果为 None 则使用默认路径
            embedding_model: Embedding 模型名称
            use_milvus: 是否使用 Milvus Lite 向量数据库（默认 True）
            milvus_collection_name: Milvus 集合名称
            milvus_db_path: Milvus Lite 数据库路径（None 则使用默认路径：data/milvus_lite.db）
        """
        # 初始化 embeddings
        self.embeddings = DashScopeEmbeddings(model=embedding_model)
        
        # 初始化向量存储（使用 Milvus Lite）
        self.use_milvus = False
        if use_milvus:
            if not MILVUS_LITE_AVAILABLE:
                raise ImportError(
                    "pymilvus 未安装，无法使用 Milvus Lite。"
                    "请安装: pip install pymilvus[milvus_lite]"
                )
            
            try:
                # 使用默认向量维度（text-embedding-v2 是 1536）
                # 避免在初始化时调用 API，防止网络问题导致阻塞
                dimension = 1536  # text-embedding-v2 的默认维度
                
                # 如果使用其他模型，可以根据模型名称设置不同的维度
                if embedding_model != "text-embedding-v2":
                    print(f"[RAGService] 警告: 使用默认维度 {dimension}，如果模型维度不同，请手动指定", file=sys.stderr, flush=True)
                
                self.vector_store = MilvusLiteVectorStore(
                    embeddings=self.embeddings,
                    collection_name=milvus_collection_name,
                    db_path=milvus_db_path,
                    dimension=dimension,
                )
                self.use_milvus = True
                print("[RAGService] ✅ 使用 Milvus Lite（无需 Docker，本地数据库持久化）", file=sys.stderr, flush=True)
            except Exception as e:
                error_msg = f"Milvus Lite 初始化失败: {str(e)}"
                print(f"[RAGService] ❌ {error_msg}", file=sys.stderr, flush=True)
                import traceback
                traceback.print_exc(file=sys.stderr)
                raise RuntimeError(error_msg) from e
        else:
            raise ValueError(
                "use_milvus=False 已不再支持。"
                "请使用 Milvus Lite: RAGService(use_milvus=True)"
            )
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # 确定知识库目录
        if knowledge_base_dir is None:
            # 默认使用项目根目录下的 knowledge_base 文件夹
            self.knowledge_base_dir = project_root / "knowledge_base"
        else:
            self.knowledge_base_dir = Path(knowledge_base_dir)
        
        # 是否已加载知识库
        self._loaded = False
    
    def load_knowledge_base(self, force_reload: bool = False):
        """
        加载知识库
        
        Args:
            force_reload: 是否强制重新加载
        """
        if self._loaded and not force_reload:
            print("[RAGService] 知识库已加载，跳过", file=sys.stderr, flush=True)
            return
        
        print(f"[RAGService] 开始加载知识库: {self.knowledge_base_dir}", file=sys.stderr, flush=True)
        
        # 加载文档
        loader = DirectoryLoader(
            directory=str(self.knowledge_base_dir),
            glob_pattern="**/*.md"
        )
        documents = loader.load()
        
        if not documents:
            print(f"[RAGService] 警告: 未找到任何文档", file=sys.stderr, flush=True)
            return
        
        # 分割文档
        print(f"[RAGService] 分割文档...", file=sys.stderr, flush=True)
        split_docs = self.text_splitter.split_documents(documents)
        print(f"[RAGService] 文档已分割为 {len(split_docs)} 个块", file=sys.stderr, flush=True)
        
        # 添加到向量存储
        print(f"[RAGService] 生成向量并添加到向量存储...", file=sys.stderr, flush=True)
        self.vector_store.add_documents(split_docs)
        
        self._loaded = True
        print(f"[RAGService] 知识库加载完成", file=sys.stderr, flush=True)
    
    def search(self, query: str, k: int = 5, score_threshold: float = 0.5) -> str:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            k: 返回最相似的 k 个文档
            score_threshold: 相似度阈值
            
        Returns:
            检索到的文档内容（格式化后的字符串）
        """
        # 确保知识库已加载
        if not self._loaded:
            self.load_knowledge_base()
        
        # 执行搜索
        results = self.vector_store.similarity_search(
            query=query,
            k=k,
            score_threshold=score_threshold
        )
        
        if not results:
            return f"未找到相关资料，查询内容：{query}"
        
        # 格式化结果
        result_text = ""
        for i, doc in enumerate(results, 1):
            content = doc.get('content', '')
            score = doc.get('score', 0)
            metadata = doc.get('metadata', {})
            source = metadata.get('source', metadata.get('filename', '未知来源'))
            
            result_text += f"[相似度: {score:.2f}] {content}\n"
            result_text += f"来源: {source}\n"
            if i < len(results):
                result_text += "\n"
        
        return result_text.strip()
    
    def add_documents(self, documents: List[Dict]):
        """
        手动添加文档到知识库
        
        Args:
            documents: 文档列表，每个文档包含 'content' 和 'metadata'
        """
        # 分割文档
        split_docs = self.text_splitter.split_documents(documents)
        
        # 添加到向量存储
        self.vector_store.add_documents(split_docs)
        
        self._loaded = True
    
    def clear(self):
        """清空知识库"""
        self.vector_store.clear()
        self._loaded = False
