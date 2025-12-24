"""
Dify 知识库服务 - 使用 Dify 知识库 API 进行检索
"""
import sys
import os
import requests
from typing import Optional
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DASHSCOPE_API_KEY


class DifyService:
    """Dify 知识库服务 - 使用 Dify API 检索知识库"""
    
    def __init__(self):
        """初始化 Dify 服务"""
        # 从环境变量读取配置
        self.api_url = os.getenv("DIFY_API_URL", "").rstrip('/')  # 移除末尾的斜杠
        self.api_key = os.getenv("DIFY_API_KEY", "")
        self.dataset_id = os.getenv("DIFY_DATASET_ID", "")  # 知识库/数据集 ID
        self.embedding_model = os.getenv("DIFY_EMBEDDING_MODEL", "")  # Embedding 模型
        
        if not self.api_url or not self.api_key:
            print("[DifyService] 警告: DIFY_API_URL 或 DIFY_API_KEY 未设置，Dify 服务将不可用", file=sys.stderr, flush=True)
            self.available = False
        else:
            self.available = True
            print(f"[DifyService] 初始化完成，API URL: {self.api_url}", file=sys.stderr, flush=True)
            if self.dataset_id:
                print(f"[DifyService] Dataset ID: {self.dataset_id}", file=sys.stderr, flush=True)
    
    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.5) -> str:
        """
        根据查询内容检索 Dify 知识库
        
        Args:
            query: 查询内容
            top_k: 返回最相关的文档数量
            score_threshold: 相似度阈值
            
        Returns:
            检索结果文本
        """
        if not self.available:
            raise ValueError("Dify 服务不可用：未设置 DIFY_API_URL 或 DIFY_API_KEY")
        
        try:
            print(f"[DifyService] 检索 Dify 知识库，查询: {query}", file=sys.stderr, flush=True)
            
            # Dify API 端点（根据 Dify 版本可能不同）
            # 尝试多种 API 格式以兼容不同版本
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Dify API 端点
            # 根据测试，/v1/datasets/{id}/retrieve 是存在的端点
            if self.dataset_id:
                url = f"{self.api_url}/v1/datasets/{self.dataset_id}/retrieve"
            else:
                url = f"{self.api_url}/v1/retrieval"
            
            # 构建请求数据
            payload = {
                "query": query,
                "top_k": top_k,
                "score_threshold": score_threshold
            }
            
            # 如果指定了 embedding 模型，添加到请求中
            # 这可以解决 "Default model not found for text-embedding" 错误
            if self.embedding_model:
                payload["embedding_model"] = self.embedding_model
                print(f"[DifyService] 使用指定的 embedding 模型: {self.embedding_model}", file=sys.stderr, flush=True)
            
            # 发送请求
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # 发送请求
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"Dify 知识库检索失败: HTTP {response.status_code}, {response.text}，查询内容：{query}"
                print(f"[DifyService] {error_msg}", file=sys.stderr, flush=True)
                return error_msg
            
            # 解析响应
            result = response.json()
            
            # 根据 Dify API 响应格式提取文档
            # Dify API 响应格式可能因版本而异，这里提供几种可能的格式
            documents = []
            
            if "data" in result:
                # 格式 1: {"data": [{"content": "...", "score": 0.9}, ...]}
                documents = result.get("data", [])
            elif "documents" in result:
                # 格式 2: {"documents": [{"text": "...", "score": 0.9}, ...]}
                documents = result.get("documents", [])
            elif "results" in result:
                # 格式 3: {"results": [{"content": "...", "score": 0.9}, ...]}
                documents = result.get("results", [])
            elif isinstance(result, list):
                # 格式 4: 直接返回列表
                documents = result
            
            print(f"[DifyService] 检索到 {len(documents)} 个文档", file=sys.stderr, flush=True)
            
            if not documents:
                return f"未找到相关资料，查询内容：{query}"
            
            # 整合所有文档的文本内容
            result_text = ""
            for i, doc in enumerate(documents):
                # 根据实际 API 响应结构调整字段名
                text = doc.get("content", "") or doc.get("text", "") or doc.get("document", "") or str(doc)
                score = doc.get("score", 0)
                
                if text and text.strip():
                    # 可选：添加相似度分数（用于调试）
                    if score > 0:
                        result_text += f"[相似度: {score:.2f}] "
                    result_text += text
                    if i < len(documents) - 1:
                        result_text += "\n\n"
            
            print(f"[DifyService] 返回结果长度: {len(result_text)} 字符", file=sys.stderr, flush=True)
            return result_text.strip()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Dify 知识库检索网络错误: {str(e)}，查询内容：{query}"
            print(f"[DifyService] {error_msg}", file=sys.stderr, flush=True)
            return error_msg
        except Exception as e:
            error_msg = f"Dify 知识库检索异常: {str(e)}，查询内容：{query}"
            print(f"[DifyService] {error_msg}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return error_msg
