"""
测试 Milvus Lite 功能（无需 Docker）
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_milvus_lite_rag():
    """测试使用 Milvus Lite 的 RAG 服务"""
    print("=" * 80)
    print("Milvus Lite RAG 测试（无需 Docker）")
    print("=" * 80)
    print()
    
    try:
        from rag.rag_service import RAGService
        
        # 使用 Milvus Lite
        print("初始化 RAG 服务（使用 Milvus Lite）...")
        rag_service = RAGService(
            use_milvus=True,
            milvus_collection_name="test_rag_knowledge_base",
            milvus_db_path=None  # 使用默认路径：data/milvus_lite.db
        )
        
        if not rag_service.use_milvus:
            print("⚠️  Milvus Lite 不可用，已回退到内存存储")
            print("   请安装 pymilvus: pip install pymilvus")
            return False
        
        print(f"✅ 使用 Milvus Lite")
        print(f"   向量存储类型: {type(rag_service.vector_store).__name__}")
        print(f"   数据库路径: {rag_service.vector_store.db_path}")
        print()
        
        # 加载知识库
        print("加载知识库...")
        rag_service.load_knowledge_base()
        print()
        
        # 获取统计信息
        stats = rag_service.vector_store.get_collection_stats()
        print(f"集合统计: {stats}")
        print()
        
        # 测试查询
        print("=" * 80)
        print("测试查询")
        print("=" * 80)
        print()
        
        test_queries = [
            "云边茉莉的特点是什么？",
            "桂花云露的价格是多少？",
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"查询 {i}: {query}")
            print("-" * 80)
            
            result = rag_service.search(query, k=3, score_threshold=0.3)
            print(result[:300] + "..." if len(result) > 300 else result)
            print()
        
        print("=" * 80)
        print("✅ Milvus Lite RAG 测试成功！")
        print("=" * 80)
        print()
        print("说明：")
        print("- 向量数据已持久化到本地数据库文件")
        print("- 重启服务后，数据仍然存在，无需重新生成向量")
        print("- 数据库文件位置:", rag_service.vector_store.db_path)
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {str(e)}")
        print("   请安装 pymilvus: pip install pymilvus")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_milvus_lite_rag()

