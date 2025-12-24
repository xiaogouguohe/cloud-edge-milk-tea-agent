"""
测试 Dify 知识库连接和检索功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from consult_mcp_server.dify_service import DifyService
from consult_mcp_server.consult_service import ConsultService


def test_dify_service():
    """测试 DifyService 直接调用"""
    print("=" * 80)
    print("测试 1: DifyService 直接调用")
    print("=" * 80)
    print()
    
    try:
        # 初始化 DifyService
        dify_service = DifyService()
        
        if not dify_service.available:
            print("❌ Dify 服务不可用")
            print("   请检查 .env 文件中的配置：")
            print("   - DIFY_API_URL")
            print("   - DIFY_API_KEY")
            print("   - DIFY_DATASET_ID (可选)")
            return False
        
        print("✅ Dify 服务已初始化")
        print(f"   API URL: {dify_service.api_url}")
        print(f"   Dataset ID: {dify_service.dataset_id or '(未设置，使用默认)'}")
        print()
        
        # 测试查询
        test_query = "云边茉莉的特点是什么？"
        print(f"测试查询: {test_query}")
        print()
        print("正在检索...")
        
        result = dify_service.search(test_query)
        
        print()
        print("=" * 80)
        print("检索结果:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        print()
        
        # 判断是否成功
        if result and "失败" not in result and "异常" not in result and "网络错误" not in result:
            print("✅ Dify 知识库检索成功！")
            return True
        else:
            print("⚠️  Dify 知识库检索返回了错误信息")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_consult_service():
    """测试 ConsultService 的知识库检索（包含优先级逻辑）"""
    print()
    print("=" * 80)
    print("测试 2: ConsultService 知识库检索（完整流程）")
    print("=" * 80)
    print()
    
    try:
        # 初始化 ConsultService
        consult_service = ConsultService()
        
        print("服务状态:")
        print(f"   Dify 服务: {'✅ 可用' if consult_service.dify_available else '❌ 不可用'}")
        print(f"   DashScope RAG: {'✅ 可用' if consult_service.rag_available else '❌ 不可用'}")
        print(f"   数据库: {'✅ 可用' if consult_service.db else '❌ 不可用'}")
        print()
        
        # 测试查询
        test_query = "云边茉莉的特点是什么？"
        print(f"测试查询: {test_query}")
        print()
        print("正在检索（会按优先级尝试：Dify > DashScope RAG > 数据库）...")
        
        result = consult_service.search_knowledge(test_query)
        
        print()
        print("=" * 80)
        print("检索结果:")
        print("=" * 80)
        print(result)
        print("=" * 80)
        print()
        
        # 判断是否成功
        if result and "失败" not in result and "异常" not in result:
            print("✅ 知识库检索成功！")
            return True
        else:
            print("⚠️  知识库检索返回了错误信息")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_dify_api_connection():
    """测试 Dify API 连接（基础连接测试）"""
    print()
    print("=" * 80)
    print("测试 0: Dify API 基础连接测试")
    print("=" * 80)
    print()
    
    import os
    import requests
    
    api_url = os.getenv("DIFY_API_URL", "").rstrip('/')
    api_key = os.getenv("DIFY_API_KEY", "")
    dataset_id = os.getenv("DIFY_DATASET_ID", "")
    
    if not api_url or not api_key:
        print("❌ 配置不完整")
        print(f"   DIFY_API_URL: {'✅ 已设置' if api_url else '❌ 未设置'}")
        print(f"   DIFY_API_KEY: {'✅ 已设置' if api_key else '❌ 未设置'}")
        return False
    
    print("✅ 配置检查通过")
    print(f"   API URL: {api_url}")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
    print(f"   Dataset ID: {dataset_id or '(未设置)'}")
    print()
    
    # 尝试连接 API（测试健康检查或简单请求）
    try:
        # 方式 1: 尝试检索 API
        if dataset_id:
            url = f"{api_url}/v1/datasets/{dataset_id}/retrieve"
        else:
            url = f"{api_url}/v1/retrieval"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": "测试",
            "top_k": 1
        }
        
        print(f"测试连接: {url}")
        print("发送测试请求...")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API 连接成功！")
            result = response.json()
            print(f"响应格式: {type(result)}")
            if isinstance(result, dict):
                print(f"响应键: {list(result.keys())}")
            return True
        elif response.status_code == 401:
            print("❌ 认证失败：API Key 可能不正确")
            print(f"响应: {response.text[:200]}")
            return False
        elif response.status_code == 404:
            print("⚠️  API 端点不存在：可能是 URL 不正确或 API 版本不匹配")
            print(f"响应: {response.text[:200]}")
            return False
        else:
            print(f"⚠️  连接失败，状态码: {response.status_code}")
            print(f"响应: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误：无法连接到 {api_url}")
        print(f"   请检查：")
        print(f"   1. API URL 是否正确")
        print(f"   2. 网络连接是否正常")
        print(f"   3. Dify 服务是否正在运行")
        return False
    except requests.exceptions.Timeout:
        print("❌ 连接超时：API 响应时间过长")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("Dify 知识库连接测试")
    print("=" * 80)
    print()
    
    # 测试 0: 基础连接
    connection_ok = test_dify_api_connection()
    
    if not connection_ok:
        print()
        print("⚠️  基础连接测试失败，请检查配置后再继续")
        print()
        # 非交互式环境，自动继续
        print("自动继续测试...")
    
    print()
    
    # 测试 1: DifyService
    service_ok = test_dify_service()
    
    print()
    
    # 测试 2: ConsultService
    consult_ok = test_consult_service()
    
    print()
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print()
    print(f"基础连接测试: {'✅ 通过' if connection_ok else '❌ 失败'}")
    print(f"DifyService 测试: {'✅ 通过' if service_ok else '❌ 失败'}")
    print(f"ConsultService 测试: {'✅ 通过' if consult_ok else '❌ 失败'}")
    print()
    
    if connection_ok and service_ok and consult_ok:
        print("🎉 所有测试通过！Dify 知识库可以正常使用。")
    else:
        print("⚠️  部分测试失败，请检查配置和日志信息。")
    print()
