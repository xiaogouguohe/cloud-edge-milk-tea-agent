"""
配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# DashScope API 配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

# DashScope 文档检索配置（RAG）
DASHSCOPE_INDEX_ID = os.getenv("DASHSCOPE_INDEX_ID", "")
DASHSCOPE_ENABLE_RERANKING = os.getenv("DASHSCOPE_ENABLE_RERANKING", "true").lower() == "true"
DASHSCOPE_RERANK_TOP_N = int(os.getenv("DASHSCOPE_RERANK_TOP_N", "5"))
DASHSCOPE_RERANK_MIN_SCORE = float(os.getenv("DASHSCOPE_RERANK_MIN_SCORE", "0.5"))

# Dify 知识库配置
DIFY_API_URL = os.getenv("DIFY_API_URL", "")
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "")
DIFY_DATASET_ID = os.getenv("DIFY_DATASET_ID", "")  # 知识库/数据集 ID（可选）

# 验证必要的配置
if not DASHSCOPE_API_KEY:
    raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量或在 .env 文件中配置")
