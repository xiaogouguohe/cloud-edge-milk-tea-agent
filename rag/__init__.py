"""
RAG 模块 - 提供检索增强生成功能，不依赖 LangChain
"""
from .rag_service import RAGService
from .dashscope_embeddings import DashScopeEmbeddings
from .vector_store import InMemoryVectorStore
from .text_splitter import RecursiveCharacterTextSplitter
from .document_loader import DirectoryLoader, FileLoader

__all__ = [
    "RAGService",
    "DashScopeEmbeddings",
    "InMemoryVectorStore",
    "RecursiveCharacterTextSplitter",
    "DirectoryLoader",
    "FileLoader"
]
