"""
最终版本的 Dify 知识库测试脚本
包含详细的错误诊断和建议
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
load_dotenv(project_root / ".env")

# 读取配置
api_url = os.getenv("DIFY_API_URL", "").rstrip('/')
api_key = os.getenv("DIFY_API_KEY", "")
dataset_id = os.getenv("DIFY_DATASET_ID", "")
embedding_model = os.getenv("DIFY_EMBEDDING_MODEL", "")

print("=" * 80)
print("Dify 知识库连接测试")
print("=" * 80)
print()

# 检查配置
print("配置检查:")
print(f"   DIFY_API_URL: {'✅ ' + api_url if api_url else '❌ 未设置'}")
print(f"   DIFY_API_KEY: {'✅ ' + api_key[:10] + '...' + api_key[-4:] if api_key and len(api_key) > 14 else '❌ 未设置' if not api_key else '✅ 已设置'}")
print(f"   DIFY_DATASET_ID: {'✅ ' + dataset_id if dataset_id else '⚠️  未设置（将使用默认知识库）'}")
print(f"   DIFY_EMBEDDING_MODEL: {'✅ ' + embedding_model if embedding_model else '⚠️  未设置（可能需要在 Dify 控制台配置）'}")
print()

if not api_url or not api_key:
    print("❌ 配置不完整，请检查 .env 文件")
    sys.exit(1)

# 测试 API 调用
print("=" * 80)
print("测试 API 调用")
print("=" * 80)
print()

if not dataset_id:
    print("⚠️  未设置 DIFY_DATASET_ID，将尝试通用检索 API")
    url = f"{api_url}/v1/retrieval"
else:
    url = f"{api_url}/v1/datasets/{dataset_id}/retrieve"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "query": "云边茉莉的特点",
    "top_k": 3,
    "score_threshold": 0.5
}

# 如果指定了 embedding 模型，添加到请求中
if embedding_model:
    payload["embedding_model"] = embedding_model
    print(f"使用指定的 embedding 模型: {embedding_model}")
    print()

print(f"请求 URL: {url}")
print(f"请求参数: {payload}")
print()
print("发送请求...")
print()

try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    print(f"响应状态码: {response.status_code}")
    print()
    
    if response.status_code == 200:
        print("=" * 80)
        print("✅ 成功！Dify 知识库可以正常访问")
        print("=" * 80)
        print()
        
        result = response.json()
        print("响应内容:")
        print("-" * 80)
        
        # 格式化输出
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("-" * 80)
        print()
        
        # 提取文档内容
        documents = []
        if "data" in result:
            documents = result.get("data", [])
        elif "documents" in result:
            documents = result.get("documents", [])
        elif "results" in result:
            documents = result.get("results", [])
        elif isinstance(result, list):
            documents = result
        
        if documents:
            print(f"检索到 {len(documents)} 个文档:")
            for i, doc in enumerate(documents, 1):
                text = doc.get("content", "") or doc.get("text", "") or str(doc)
                score = doc.get("score", 0)
                print(f"\n文档 {i} (相似度: {score:.2f}):")
                print(text[:200] + "..." if len(text) > 200 else text)
        
    elif response.status_code == 400:
        error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        error_msg = error_data.get("message", response.text)
        
        print("=" * 80)
        print("❌ 请求失败（400 Bad Request）")
        print("=" * 80)
        print()
        print(f"错误信息: {error_msg}")
        print()
        
        if "embedding" in error_msg.lower() or "model" in error_msg.lower():
            print("问题诊断: 知识库缺少 embedding 模型配置")
            print()
            print("解决方案:")
            print("1. 在 Dify 控制台配置知识库的默认 embedding 模型")
            print("2. 或者在 .env 文件中设置 DIFY_EMBEDDING_MODEL")
            print("   例如: DIFY_EMBEDDING_MODEL=text-embedding-v2")
            print()
            print("常见的 embedding 模型:")
            print("  - text-embedding-v2 (通义千问)")
            print("  - text-embedding-v1 (通义千问)")
            print("  - text-embedding-ada-002 (OpenAI)")
            print("  - 或其他 Dify 支持的模型")
        
    elif response.status_code == 401:
        print("=" * 80)
        print("❌ 认证失败（401 Unauthorized）")
        print("=" * 80)
        print()
        print("请检查:")
        print("1. DIFY_API_KEY 是否正确")
        print("2. API Key 是否已过期")
        print("3. API Key 是否有访问该知识库的权限")
        
    elif response.status_code == 404:
        print("=" * 80)
        print("❌ 资源未找到（404 Not Found）")
        print("=" * 80)
        print()
        print("请检查:")
        print("1. DIFY_API_URL 是否正确")
        print("2. DIFY_DATASET_ID 是否正确")
        print("3. API 端点路径是否正确")
        print(f"   当前使用的 URL: {url}")
        
    else:
        print("=" * 80)
        print(f"❌ 请求失败（状态码: {response.status_code}）")
        print("=" * 80)
        print()
        print(f"响应: {response.text[:500]}")
        
except requests.exceptions.ConnectionError:
    print("=" * 80)
    print("❌ 连接错误")
    print("=" * 80)
    print()
    print(f"无法连接到: {api_url}")
    print("请检查:")
    print("1. API URL 是否正确")
    print("2. 网络连接是否正常")
    print("3. Dify 服务是否正在运行")
    
except requests.exceptions.Timeout:
    print("=" * 80)
    print("❌ 请求超时")
    print("=" * 80)
    print()
    print("API 响应时间过长，请检查网络连接")
    
except Exception as e:
    print("=" * 80)
    print(f"❌ 发生异常: {str(e)}")
    print("=" * 80)
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("测试完成")
print("=" * 80)
