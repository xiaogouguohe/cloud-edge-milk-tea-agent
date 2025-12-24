# 知识库文档

本目录包含云边奶茶铺的知识库文档，用于 DashScope RAG 文档检索。

## 目录结构

```
knowledge_base/
├── products/          # 产品介绍文档
│   ├── 云边茉莉.txt
│   ├── 桂花云露.txt
│   └── ...
├── store/            # 店铺介绍文档
│   ├── 品牌介绍.txt
│   └── ...
├── activities/       # 活动信息文档
│   └── ...
└── guides/           # 冲泡指导文档
    └── ...
```

## 文档格式

- 文件格式：TXT（UTF-8 编码）
- 内容要求：
  - 清晰分段
  - 使用简洁明了的语言
  - 包含关键信息（产品特点、价格、推荐人群等）

## 上传到 DashScope

### 方式 1：通过控制台上传

1. 登录 [DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 进入您的索引页面
3. 点击"上传文档"
4. 选择本目录中的文件上传

### 方式 2：使用上传脚本

```bash
python3 scripts/upload_knowledge_base.py
```

## 注意事项

1. 文档内容要准确、完整
2. 定期更新文档内容
3. 确保文档编码为 UTF-8
4. 单个文档建议不超过 10MB
