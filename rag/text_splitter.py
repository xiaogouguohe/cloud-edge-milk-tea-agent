"""
文本分割器 - 将长文本分割成小块，不依赖 LangChain
"""
import re
from typing import List


class RecursiveCharacterTextSplitter:
    """递归字符文本分割器"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, separators: List[str] = None):
        """
        初始化文本分割器
        
        Args:
            chunk_size: 每个块的最大字符数
            chunk_overlap: 块之间的重叠字符数
            separators: 分隔符列表，按优先级排序
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 默认分隔符（按优先级排序）
        if separators is None:
            self.separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        else:
            self.separators = separators
    
    def split_text(self, text: str) -> List[str]:
        """
        分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            文本块列表
        """
        if not text:
            return []
        
        # 如果文本长度小于 chunk_size，直接返回
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # 按段落分割（优先使用 \n\n）
        paragraphs = re.split(r'\n\n+', text)
        
        for paragraph in paragraphs:
            # 如果当前块加上新段落不超过 chunk_size，添加到当前块
            if len(current_chunk) + len(paragraph) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                # 当前块已满，保存并开始新块
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果段落本身超过 chunk_size，需要进一步分割
                if len(paragraph) > self.chunk_size:
                    sub_chunks = self._split_long_text(paragraph)
                    chunks.extend(sub_chunks[:-1])  # 除了最后一个
                    current_chunk = sub_chunks[-1]  # 最后一个作为新块的开始
                else:
                    current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_long_text(self, text: str) -> List[str]:
        """分割超长文本"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # 计算当前块的结束位置
            end = min(start + self.chunk_size, len(text))
            
            # 如果不是最后一块，尝试在分隔符处分割
            if end < len(text):
                # 从后往前找分隔符
                best_split = end
                for sep in self.separators:
                    if sep:
                        # 在 [end - chunk_overlap, end] 范围内找分隔符
                        search_start = max(start, end - self.chunk_overlap)
                        pos = text.rfind(sep, search_start, end)
                        if pos != -1:
                            best_split = pos + len(sep)
                            break
                
                chunk = text[start:best_split]
                chunks.append(chunk)
                start = best_split - self.chunk_overlap  # 重叠
            else:
                # 最后一块
                chunks.append(text[start:])
                break
        
        return chunks
    
    def split_documents(self, documents: List[dict]) -> List[dict]:
        """
        分割文档列表
        
        Args:
            documents: 文档列表，每个文档是包含 'content' 和 'metadata' 的字典
            
        Returns:
            分割后的文档列表
        """
        all_chunks = []
        
        for doc in documents:
            content = doc.get('content', doc.get('page_content', ''))
            metadata = doc.get('metadata', {})
            
            chunks = self.split_text(content)
            
            for i, chunk in enumerate(chunks):
                chunk_doc = {
                    'content': chunk,
                    'metadata': {
                        **metadata,
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                }
                all_chunks.append(chunk_doc)
        
        return all_chunks

