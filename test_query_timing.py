"""
测试查询耗时分析 - 找出慢在哪里
"""
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_query_timing():
    """详细分析查询耗时"""
    print("=" * 80)
    print("查询耗时详细分析")
    print("=" * 80)
    print()
    
    try:
        from rag.dashscope_embeddings import DashScopeEmbeddings
        from rag.milvus_lite_vector_store import MilvusLiteVectorStore
        
        # 1. 测试 DashScope API 调用耗时
        print("1. 测试 DashScope API 调用耗时")
        print("-" * 80)
        embeddings = DashScopeEmbeddings()
        
        api_start = time.time()
        query_vector = embeddings.embed_query("测试查询")
        api_time = time.time() - api_start
        
        print(f"✅ DashScope API 调用耗时: {api_time:.2f} 秒")
        print(f"   向量维度: {len(query_vector)}")
        print()
        
        # 2. 测试 Milvus 查询耗时（需要先有数据）
        print("2. 测试 Milvus 查询耗时")
        print("-" * 80)
        
        # 初始化 Milvus
        vector_store = MilvusLiteVectorStore(
            embeddings=embeddings,
            collection_name="test_timing",
            db_path=None,
            dimension=1536
        )
        
        # 检查是否有数据
        try:
            stats = vector_store.get_collection_stats()
            num_entities = stats.get("num_entities", 0)
            print(f"   集合中的文档数量: {num_entities}")
            
            if num_entities > 0:
                # 有数据，测试查询
                print("   执行查询测试...")
                milvus_start = time.time()
                results = vector_store.similarity_search("测试查询", k=3)
                milvus_time = time.time() - milvus_start
                
                print(f"✅ Milvus 查询耗时: {milvus_time:.2f} 秒")
                print(f"   返回结果数量: {len(results)}")
            else:
                print("   ⚠️  集合中没有数据，无法测试查询耗时")
                print("   提示: 需要先加载知识库才能测试查询")
        except Exception as e:
            print(f"   ❌ 查询测试失败: {str(e)}")
        print()
        
        # 3. 综合分析
        print("=" * 80)
        print("综合分析")
        print("=" * 80)
        print(f"DashScope API 调用: {api_time:.2f} 秒")
        if num_entities > 0:
            print(f"Milvus 数据库查询: {milvus_time:.2f} 秒")
            print(f"总耗时: {api_time + milvus_time:.2f} 秒")
            print()
            print("💡 结论:")
            if api_time > milvus_time * 10:
                print("   - DashScope API 调用是主要耗时操作")
                print("   - Milvus 查询本身很快（毫秒级）")
            else:
                print("   - 两者耗时相近，需要进一步优化")
        else:
            print()
            print("💡 结论:")
            print("   - 查询耗时主要来自 DashScope API 调用（生成查询向量）")
            print("   - 如果 API 调用很慢（>5秒），可能是网络问题或 API 限流")
        print()
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_query_timing()

