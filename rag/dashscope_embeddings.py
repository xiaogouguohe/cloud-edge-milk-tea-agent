"""
DashScope Embeddings - 直接调用 DashScope API，不依赖 LangChain
"""
import sys
from pathlib import Path
from typing import List, Union
import dashscope
from dashscope import TextEmbedding

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY

# 设置 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class DashScopeEmbeddings:
    """DashScope Embeddings - 直接调用 DashScope API"""
    
    def __init__(self, model: str = "text-embedding-v2", api_key: str = None):
        """
        初始化 DashScope Embeddings
        
        Args:
            model: 模型名称，默认为 "text-embedding-v2"
            api_key: API Key，如果为 None 则使用环境变量中的 DASHSCOPE_API_KEY
        """
        self.model = model
        if api_key:
            dashscope.api_key = api_key
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        将多个文本转换为向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表，每个向量是一个浮点数列表
        """
        if not texts:
            return []
        
        try:
            # 调用 DashScope API
            response = TextEmbedding.call(
                model=self.model,
                input=texts
            )
            
            if response.status_code == 200:
                # 提取 embeddings
                embeddings = []
                for item in response.output['embeddings']:
                    embeddings.append(item['embedding'])
                return embeddings
            else:
                raise Exception(f"DashScope API 调用失败: {response.message}")
                
        except Exception as e:
            print(f"[DashScopeEmbeddings] 错误: {str(e)}", file=sys.stderr, flush=True)
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """
        将单个查询文本转换为向量
        
        Args:
            text: 查询文本
            
        Returns:
            向量（浮点数列表）
        """
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else []
    
    def embed(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        通用的 embedding 方法
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            单个向量或向量列表
        """
        if isinstance(texts, str):
            return self.embed_query(texts)
        else:
            return self.embed_documents(texts)

