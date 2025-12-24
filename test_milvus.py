"""
测试 Milvus 向量存储功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_milvus_connection():
    """测试 Milvus 连接"""
    print("=" * 80)
    print("测试 Milvus 连接")
    print("=" * 80)
    print()
    
    try:
        from pymilvus import connections, utility
        
        # 尝试连接
        print("尝试连接到 Milvus (localhost:19530)...")
        connections.connect(
            alias="default",
            host="localhost",
            port=19530,
        )
        print("✅ Milvus 连接成功！")
        
        # 列出所有集合
        collections = utility.list_collections()
        print(f"当前集合数量: {len(collections)}")
        if collections:
            print(f"集合列表: {collections}")
        
        connections.disconnect("default")
        return True
        
    except ImportError:
        print("❌ pymilvus 未安装")
        print("   请运行: pip install pymilvus")
        return False
    except Exception as e:
        print(f"❌ Milvus 连接失败: {str(e)}")
        print()
        print("可能的原因：")
        print("1. Milvus 服务未启动")
        print("2. 端口不正确（默认 19530）")
        print("3. 防火墙阻止连接")
        print()
        print("解决方案：")
        print("1. 启动 Milvus: docker run -d -p 19530:19530 milvusdb/milvus:latest")
        print("2. 或使用 Docker Compose 启动")
        return False


def test_milvus_rag():
    """测试使用 Milvus 的 RAG 服务"""
    print()
    print("=" * 80)
    print("测试 Milvus RAG 服务")
    print("=" * 80)
    print()
    
    try:
        from rag.rag_service import RAGService
        
        # 使用 Milvus
        print("初始化 RAG 服务（使用 Milvus）...")
        rag_service = RAGService(
            use_milvus=True,
            milvus_host="localhost",
            milvus_port=19530,
            milvus_collection_name="test_rag_knowledge_base"
        )
        
        print("加载知识库...")
        rag_service.load_knowledge_base()
        
        print()
        print("测试查询...")
        query = "云边茉莉的特点是什么？"
        print(f"查询: {query}")
        
        result = rag_service.search(query, k=3, score_threshold=0.3)
        print()
        print("结果:")
        print("-" * 80)
        print(result[:500] + "..." if len(result) > 500 else result)
        print("-" * 80)
        
        # 获取统计信息
        if rag_service.use_milvus:
            stats = rag_service.vector_store.get_collection_stats()
            print()
            print(f"Milvus 集合统计: {stats}")
        
        print()
        print("✅ Milvus RAG 测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("Milvus 向量存储测试")
    print("=" * 80)
    print()
    
    # 测试连接
    connection_ok = test_milvus_connection()
    
    if connection_ok:
        print()
        # 测试 RAG
        rag_ok = test_milvus_rag()
        
        print()
        print("=" * 80)
        print("测试总结")
        print("=" * 80)
        print(f"Milvus 连接: {'✅ 通过' if connection_ok else '❌ 失败'}")
        print(f"Milvus RAG: {'✅ 通过' if rag_ok else '❌ 失败'}")
        print()
    else:
        print()
        print("⚠️  请先解决 Milvus 连接问题，然后再测试 RAG 功能")
        print()
