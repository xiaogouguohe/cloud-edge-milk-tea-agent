"""
文档加载器 - 从本地文件加载文档，不依赖 LangChain
"""
import sys
from pathlib import Path
from typing import List, Dict


class DirectoryLoader:
    """目录加载器 - 从目录加载所有文档"""
    
    def __init__(self, directory: str, glob_pattern: str = "**/*.md", encoding: str = "utf-8"):
        """
        初始化目录加载器
        
        Args:
            directory: 目录路径
            glob_pattern: 文件匹配模式
            encoding: 文件编码
        """
        self.directory = Path(directory)
        self.glob_pattern = glob_pattern
        self.encoding = encoding
    
    def load(self) -> List[Dict]:
        """
        加载所有匹配的文档
        
        Returns:
            文档列表，每个文档包含 'content' 和 'metadata'
        """
        documents = []
        
        if not self.directory.exists():
            print(f"[DirectoryLoader] 警告: 目录不存在: {self.directory}", file=sys.stderr, flush=True)
            return documents
        
        # 查找所有匹配的文件
        files = list(self.directory.glob(self.glob_pattern))
        
        print(f"[DirectoryLoader] 找到 {len(files)} 个文件", file=sys.stderr, flush=True)
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding=self.encoding) as f:
                    content = f.read()
                
                # 构建文档
                doc = {
                    'content': content,
                    'metadata': {
                        'source': str(file_path),
                        'filename': file_path.name,
                        'file_type': file_path.suffix
                    }
                }
                documents.append(doc)
                
            except Exception as e:
                print(f"[DirectoryLoader] 加载文件失败 {file_path}: {str(e)}", file=sys.stderr, flush=True)
        
        return documents


class FileLoader:
    """文件加载器 - 加载单个文件"""
    
    def __init__(self, file_path: str, encoding: str = "utf-8"):
        """
        初始化文件加载器
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
        """
        self.file_path = Path(file_path)
        self.encoding = encoding
    
    def load(self) -> List[Dict]:
        """
        加载文件
        
        Returns:
            文档列表（单个文档）
        """
        if not self.file_path.exists():
            print(f"[FileLoader] 警告: 文件不存在: {self.file_path}", file=sys.stderr, flush=True)
            return []
        
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                content = f.read()
            
            doc = {
                'content': content,
                'metadata': {
                    'source': str(self.file_path),
                    'filename': self.file_path.name,
                    'file_type': self.file_path.suffix
                }
            }
            
            return [doc]
            
        except Exception as e:
            print(f"[FileLoader] 加载文件失败 {self.file_path}: {str(e)}", file=sys.stderr, flush=True)
            return []
