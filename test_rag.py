"""
测试 RAG 功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag.rag_service import RAGService


def test_rag():
    """测试 RAG 功能"""
    print("=" * 80)
    print("RAG 功能测试")
    print("=" * 80)
    print()
    
    # 初始化 RAG 服务
    print("初始化 RAG 服务...")
    rag_service = RAGService()
    
    # 加载知识库
    print("加载知识库...")
    rag_service.load_knowledge_base()
    
    print()
    print("=" * 80)
    print("测试查询")
    print("=" * 80)
    print()
    
    # 测试查询
    test_queries = [
        "云边茉莉的特点是什么？",
        "桂花云露的价格是多少？",
        "有哪些冬季限定的产品？",
        "云边奶茶铺的品牌理念是什么？",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"查询 {i}: {query}")
        print("-" * 80)
        
        result = rag_service.search(query, k=3, score_threshold=0.3)  # 降低阈值以获得更多结果
        
        print(result)
        print()
        print("=" * 80)
        print()


if __name__ == "__main__":
    test_rag()
