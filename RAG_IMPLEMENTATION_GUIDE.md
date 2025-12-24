# RAG 实现指南

## 概述

本文档说明如何在 Python 项目中实现 RAG（检索增强生成）功能，使用 DashScope 的文档检索服务。

## 步骤 1：创建 DashScope 知识库索引

### 1.1 登录 DashScope 控制台

1. 访问 [DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 登录您的阿里云账号
3. 进入"文档检索"或"知识库"页面

### 1.2 创建索引

1. 点击"创建索引"或"新建知识库"
2. 填写索引信息：
   - **索引名称**：例如 `milk-tea-knowledge-base`
   - **描述**：云边奶茶铺知识库
   - **模型**：选择适合的嵌入模型（如 `text-embedding-v2`）

3. 记录下生成的 **Index ID**（后续配置需要）

### 1.3 上传文档

准备知识库文档，可以包括：

1. **产品介绍文档**：
   - 云边茉莉：清新的茉莉花香与醇厚奶茶的完美结合，口感层次丰富...
   - 桂花云露：淡雅桂花香，口感清甜，适合喜欢淡雅口味的顾客...
   - 云雾观音：铁观音茶底，回甘悠长，茶香浓郁...
   - 等等

2. **店铺介绍**：
   - 云边奶茶铺品牌故事
   - 店铺特色
   - 服务理念

3. **活动信息**：
   - 当前活动
   - 优惠信息
   - 会员权益

4. **冲泡指导**：
   - 不同产品的冲泡方法
   - 温度控制
   - 时间控制

**文档格式**：
- 支持 TXT、PDF、DOCX 等格式
- 建议使用 TXT 格式，每段内容清晰

**上传方式**：
- 在 DashScope 控制台直接上传
- 或使用 API 批量上传

## 步骤 2：安装依赖

确保已安装 DashScope SDK：

```bash
pip install dashscope>=1.17.0
```

## 步骤 3：配置环境变量

在 `.env` 文件中添加：

```env
# DashScope API Key（已有）
DASHSCOPE_API_KEY=your_api_key_here

# DashScope 文档检索配置
DASHSCOPE_INDEX_ID=your_index_id_here
DASHSCOPE_ENABLE_RERANKING=true
DASHSCOPE_RERANK_TOP_N=5
DASHSCOPE_RERANK_MIN_SCORE=0.5
```

## 步骤 4：实现 RAG 服务

创建 `consult_mcp_server/rag_service.py`：

```python
"""
RAG 服务 - 使用 DashScope 文档检索
"""
import dashscope
from dashscope import DocumentRetriever
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# 配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_INDEX_ID = os.getenv("DASHSCOPE_INDEX_ID", "")
DASHSCOPE_ENABLE_RERANKING = os.getenv("DASHSCOPE_ENABLE_RERANKING", "true").lower() == "true"
DASHSCOPE_RERANK_TOP_N = int(os.getenv("DASHSCOPE_RERANK_TOP_N", "5"))
DASHSCOPE_RERANK_MIN_SCORE = float(os.getenv("DASHSCOPE_RERANK_MIN_SCORE", "0.5"))

# 设置 API Key
dashscope.api_key = DASHSCOPE_API_KEY


class RAGService:
    """RAG 服务 - 使用 DashScope 文档检索"""
    
    def __init__(self):
        """初始化 RAG 服务"""
        self.index_id = DASHSCOPE_INDEX_ID
        if not self.index_id:
            raise ValueError("请设置 DASHSCOPE_INDEX_ID 环境变量")
    
    def search(self, query: str) -> str:
        """
        根据查询内容检索知识库
        
        Args:
            query: 查询内容
            
        Returns:
            检索结果文本
        """
        try:
            # 构建检索选项
            options = {}
            if DASHSCOPE_ENABLE_RERANKING:
                options['rerank'] = {
                    'enable': True,
                    'top_n': DASHSCOPE_RERANK_TOP_N,
                    'min_score': DASHSCOPE_RERANK_MIN_SCORE
                }
            
            # 调用 DashScope 文档检索 API
            response = DocumentRetriever.call(
                index_id=self.index_id,
                query=query,
                **options
            )
            
            if response.status_code != 200:
                return f"知识库检索失败: {response.message}，查询内容：{query}"
            
            # 提取文档内容
            documents = response.output.get('documents', [])
            
            if not documents:
                return f"未找到相关资料，查询内容：{query}"
            
            # 整合所有文档的文本内容
            result_text = ""
            for i, doc in enumerate(documents):
                text = doc.get('text', '')
                if text and text.strip():
                    result_text += text
                    if i < len(documents) - 1:
                        result_text += "\n\n"
            
            return result_text.strip()
            
        except Exception as e:
            return f"知识库检索异常: {str(e)}，查询内容：{query}"
```

## 步骤 5：更新 ConsultService

修改 `consult_mcp_server/consult_service.py`，集成 RAG 服务：

```python
from .rag_service import RAGService

class ConsultService:
    def __init__(self):
        self.db = db_manager
        # 初始化 RAG 服务
        try:
            self.rag_service = RAGService()
            self.rag_available = True
        except Exception as e:
            print(f"[ConsultService] RAG 服务不可用: {str(e)}")
            self.rag_service = None
            self.rag_available = False
    
    def search_knowledge(self, query: str) -> str:
        """
        根据查询内容检索知识库
        优先使用 RAG，如果不可用则回退到数据库查询
        """
        # 优先使用 RAG
        if self.rag_available and self.rag_service:
            try:
                result = self.rag_service.search(query)
                if result and "未找到相关资料" not in result:
                    return result
            except Exception as e:
                print(f"[ConsultService] RAG 检索失败，回退到数据库查询: {str(e)}")
        
        # 回退到数据库查询
        return self._search_from_database(query)
    
    def _search_from_database(self, query: str) -> str:
        """从数据库查询（原有逻辑）"""
        # ... 原有代码 ...
```

## 步骤 6：准备知识库文档

创建 `knowledge_base/` 目录，准备文档：

```
knowledge_base/
├── products/
│   ├── 云边茉莉.txt
│   ├── 桂花云露.txt
│   ├── 云雾观音.txt
│   └── ...
├── store/
│   ├── 品牌介绍.txt
│   ├── 店铺特色.txt
│   └── ...
├── activities/
│   ├── 当前活动.txt
│   └── ...
└── guides/
    ├── 冲泡方法.txt
    └── ...
```

### 示例文档内容

**knowledge_base/products/云边茉莉.txt**：
```
云边茉莉是云边奶茶铺的经典产品之一。

产品特点：
- 清新的茉莉花香与醇厚奶茶的完美结合
- 口感层次丰富，既有茉莉花的清香，又有奶茶的醇厚
- 适合喜欢花香类饮品的顾客

制作工艺：
- 选用优质茉莉花茶作为茶底
- 配以新鲜牛奶和淡奶油
- 经过精心调配，确保口感平衡

推荐人群：
- 喜欢花香类饮品的顾客
- 喜欢清新口感的顾客
- 适合下午茶时光

价格：18元/杯
```

## 步骤 7：上传文档到 DashScope

### 方式 1：通过控制台上传

1. 登录 DashScope 控制台
2. 进入您的索引页面
3. 点击"上传文档"
4. 选择文件或文件夹上传

### 方式 2：使用 API 上传（推荐）

创建 `scripts/upload_knowledge_base.py`：

```python
"""
批量上传知识库文档到 DashScope
"""
import os
import dashscope
from dashscope import DocumentUploader
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_INDEX_ID = os.getenv("DASHSCOPE_INDEX_ID", "")

dashscope.api_key = DASHSCOPE_API_KEY


def upload_documents(directory: str):
    """
    上传目录中的所有文档
    
    Args:
        directory: 文档目录路径
    """
    knowledge_base_dir = Path(directory)
    
    if not knowledge_base_dir.exists():
        print(f"目录不存在: {directory}")
        return
    
    # 遍历所有文件
    for file_path in knowledge_base_dir.rglob("*.txt"):
        print(f"上传文件: {file_path}")
        
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 上传文档
            response = DocumentUploader.call(
                index_id=DASHSCOPE_INDEX_ID,
                document={
                    'title': file_path.stem,
                    'text': content
                }
            )
            
            if response.status_code == 200:
                print(f"  ✓ 上传成功: {file_path.name}")
            else:
                print(f"  ✗ 上传失败: {response.message}")
                
        except Exception as e:
            print(f"  ✗ 上传异常: {str(e)}")


if __name__ == "__main__":
    # 上传知识库文档
    upload_documents("knowledge_base")
```

运行脚本：

```bash
python3 scripts/upload_knowledge_base.py
```

## 步骤 8：测试 RAG 功能

1. 确保已配置 `DASHSCOPE_INDEX_ID`
2. 启动 ConsultMCPServer
3. 测试知识库检索：

```python
from consult_mcp_server.rag_service import RAGService

rag = RAGService()
result = rag.search("云边茉莉的特点是什么？")
print(result)
```

## 注意事项

1. **Index ID**：必须先在 DashScope 控制台创建索引，获取 Index ID
2. **文档格式**：建议使用 TXT 格式，内容清晰分段
3. **文档大小**：单个文档建议不超过 10MB
4. **费用**：DashScope 文档检索服务可能产生费用，请查看定价
5. **回退机制**：如果 RAG 不可用，会自动回退到数据库查询

## 后续优化

1. **文档更新**：定期更新知识库文档
2. **检索优化**：调整 rerank 参数，提高检索准确性
3. **缓存机制**：对常见查询结果进行缓存
4. **混合检索**：结合 RAG 和数据库查询，提供更全面的结果
