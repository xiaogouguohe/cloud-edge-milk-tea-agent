"""
简单的 Dify 知识库连接测试
直接测试 API 调用，不依赖其他模块
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

print("=" * 80)
print("Dify 知识库连接测试（简化版）")
print("=" * 80)
print()

# 检查配置
if not api_url or not api_key:
    print("❌ 配置不完整")
    print(f"   DIFY_API_URL: {'✅' if api_url else '❌'}")
    print(f"   DIFY_API_KEY: {'✅' if api_key else '❌'}")
    sys.exit(1)

print("✅ 配置检查通过")
print(f"   API URL: {api_url}")
print(f"   API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
print(f"   Dataset ID: {dataset_id or '(未设置)'}")
print()

# 测试不同的 API 端点和格式
test_cases = [
    {
        "name": "方式 1: /v1/retrieval (knowledge_id)",
        "url": f"{api_url}/v1/retrieval",
        "payload": {
            "knowledge_id": dataset_id,
            "query": "测试查询",
            "retrieval_setting": {
                "top_k": 1,
                "score_threshold": 0.5
            }
        }
    },
    {
        "name": "方式 2: /v1/retrieval (dataset_id)",
        "url": f"{api_url}/v1/retrieval",
        "payload": {
            "dataset_id": dataset_id,
            "query": "测试查询",
            "retrieval_setting": {
                "top_k": 1,
                "score_threshold": 0.5
            }
        }
    },
    {
        "name": "方式 3: /v1/datasets/{id}/retrieve",
        "url": f"{api_url}/v1/datasets/{dataset_id}/retrieve" if dataset_id else None,
        "payload": {
            "query": "测试查询",
            "top_k": 1,
            "score_threshold": 0.5
        }
    },
]

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

success = False

for i, test_case in enumerate(test_cases, 1):
    if not test_case["url"]:
        continue
        
    print(f"测试 {i}: {test_case['name']}")
    print(f"   URL: {test_case['url']}")
    print(f"   请求: {test_case['payload']}")
    print()
    
    try:
        response = requests.post(
            test_case["url"],
            json=test_case["payload"],
            headers=headers,
            timeout=10
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ 成功！")
            result = response.json()
            print(f"   响应: {result}")
            success = True
            print()
            print("=" * 80)
            print("✅ 找到可用的 API 格式！")
            print("=" * 80)
            break
        else:
            print(f"   ❌ 失败")
            error_text = response.text[:200]
            print(f"   错误: {error_text}")
            print()
    except Exception as e:
        print(f"   ❌ 异常: {str(e)}")
        print()

if not success:
    print("=" * 80)
    print("⚠️  所有测试方式都失败了")
    print("=" * 80)
    print()
    print("可能的原因：")
    print("1. API URL 不正确")
    print("2. API Key 无效或权限不足")
    print("3. Dataset ID 不正确")
    print("4. Dify 知识库未配置 embedding 模型")
    print("5. API 版本不匹配")
    print()
    print("建议：")
    print("1. 检查 Dify 控制台中的 API 文档")
    print("2. 确认知识库已正确配置 embedding 模型")
    print("3. 尝试在 Dify 控制台手动测试 API 调用")
