"""
批量上传知识库文档到 DashScope
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

import dashscope
from config import DASHSCOPE_API_KEY

dashscope.api_key = DASHSCOPE_API_KEY

DASHSCOPE_INDEX_ID = os.getenv("DASHSCOPE_INDEX_ID", "")

if not DASHSCOPE_INDEX_ID:
    print("错误: 请设置 DASHSCOPE_INDEX_ID 环境变量")
    print("在 .env 文件中添加: DASHSCOPE_INDEX_ID=your_index_id")
    sys.exit(1)


def upload_documents(directory: str):
    """
    上传目录中的所有文档到 DashScope
    
    Args:
        directory: 文档目录路径
    """
    knowledge_base_dir = Path(directory)
    
    if not knowledge_base_dir.exists():
        print(f"错误: 目录不存在: {directory}")
        return
    
    print(f"开始上传文档，目录: {directory}")
    print(f"Index ID: {DASHSCOPE_INDEX_ID}")
    print()
    
    # 统计
    total_files = 0
    success_count = 0
    fail_count = 0
    
    # 遍历所有文件
    for file_path in knowledge_base_dir.rglob("*.txt"):
        total_files += 1
        print(f"[{total_files}] 上传文件: {file_path.relative_to(knowledge_base_dir)}")
        
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                print(f"  警告: 文件为空，跳过")
                continue
            
            # 上传文档
            # 注意：DashScope 的文档上传 API 可能在不同版本中有不同的调用方式
            # 这里提供两种方式
            
            # 方式 1：使用 dashscope.rag 模块（如果可用）
            try:
                from dashscope import RAG
                
                response = RAG.upload_document(
                    index_id=DASHSCOPE_INDEX_ID,
                    document={
                        'title': file_path.stem,
                        'text': content
                    }
                )
                
                if response.status_code == 200:
                    print(f"  ✓ 上传成功")
                    success_count += 1
                else:
                    print(f"  ✗ 上传失败: {response.message}")
                    fail_count += 1
                    
            except ImportError:
                # 方式 2：使用 HTTP 请求直接调用 API
                import requests
                
                url = "https://dashscope.aliyuncs.com/api/v1/rag/documents"
                headers = {
                    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "index_id": DASHSCOPE_INDEX_ID,
                    "document": {
                        "title": file_path.stem,
                        "text": content
                    }
                }
                
                response = requests.post(url, json=data, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    print(f"  ✓ 上传成功")
                    success_count += 1
                else:
                    print(f"  ✗ 上传失败: {response.text}")
                    fail_count += 1
                    
        except Exception as e:
            print(f"  ✗ 上传异常: {str(e)}")
            fail_count += 1
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 60)
    print(f"上传完成:")
    print(f"  总计: {total_files} 个文件")
    print(f"  成功: {success_count} 个")
    print(f"  失败: {fail_count} 个")
    print("=" * 60)


if __name__ == "__main__":
    # 上传知识库文档
    knowledge_base_dir = project_root / "knowledge_base"
    upload_documents(str(knowledge_base_dir))
