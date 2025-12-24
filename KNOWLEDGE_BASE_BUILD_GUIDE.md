# 知识库构建指南

## 概述

本文档说明如何在应用上线前构建知识库。参考 Java 项目的实现方式，知识库的构建分为两个阶段：

1. **准备知识库文档**：在项目中准备 Markdown 格式的知识库文档
2. **上传到 DashScope**：在 DashScope 控制台创建知识库并上传文档

---

## Java 项目的知识库构建方式

### 1. 知识库文档位置

Java 项目中的知识库文档位于：
```
consult-sub-agent/src/main/resources/kownledge/
├── brand-overview.md    # 品牌概览和理念
└── products.md         # 产品详细介绍
```

### 2. 文档内容

#### brand-overview.md
包含：
- 品牌理念
- 核心产品系列
- 品牌优势与特色
- 服务特色
- 品牌愿景
- 联系方式

#### products.md
包含：
- 产品详细介绍（每个产品的特点、价格、制作时间、保质期等）
- 甜度选择说明
- 冰量选择说明
- 季节限定说明
- 地区限定说明
- 产品价格汇总

### 3. 构建流程

根据 `build.sh` 和 `README.md`，Java 项目的知识库构建流程是：

1. **准备文档**：在 `consult-sub-agent/src/main/resources/kownledge/` 目录下准备 Markdown 文件
2. **创建知识库**：访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/) 创建知识库
3. **上传文档**：在控制台手动上传 `brand-overview.md` 和 `products.md` 文件
4. **获取 Index ID**：上传完成后，获取知识库的 Index ID
5. **配置环境变量**：将 Index ID 配置到 `.env` 文件中的 `DASHSCOPE_INDEX_ID`

---

## Python 项目的知识库构建方式

### 方式 1：参考 Java 项目（手动上传）

#### 步骤 1：准备知识库文档

在 `knowledge_base/` 目录下准备文档（已提供示例）：

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

**文档格式建议**：
- 使用 Markdown 或 TXT 格式
- UTF-8 编码
- 内容清晰分段
- 包含关键信息（产品特点、价格、推荐人群等）

#### 步骤 2：在 DashScope 控制台创建知识库

1. 访问 [DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 登录您的阿里云账号
3. 进入"文档检索"或"知识库"页面
4. 点击"创建索引"或"新建知识库"
5. 填写索引信息：
   - **索引名称**：例如 `milk-tea-knowledge-base`
   - **描述**：云边奶茶铺知识库
   - **模型**：选择适合的嵌入模型（如 `text-embedding-v2`）
6. 记录下生成的 **Index ID**

#### 步骤 3：上传文档

**方式 A：通过控制台上传**

1. 在 DashScope 控制台进入您的索引页面
2. 点击"上传文档"
3. 选择 `knowledge_base/` 目录下的文件上传
4. 等待文档解析完成（通常需要几分钟）

**方式 B：使用上传脚本**

```bash
# 确保已配置 DASHSCOPE_INDEX_ID
python3 scripts/upload_knowledge_base.py
```

#### 步骤 4：配置环境变量

在 `.env` 文件中添加：

```env
DASHSCOPE_INDEX_ID=your_index_id_here
DASHSCOPE_ENABLE_RERANKING=true
DASHSCOPE_RERANK_TOP_N=5
DASHSCOPE_RERANK_MIN_SCORE=0.5
```

---

### 方式 2：使用 Java 项目的原始文档

如果您想直接使用 Java 项目的知识库文档：

#### 步骤 1：复制 Java 项目的文档

```bash
# 从 Java 项目复制文档
cp spring-ai-alibaba-multi-agent-demo/consult-sub-agent/src/main/resources/kownledge/*.md knowledge_base/
```

#### 步骤 2：转换为适合的格式

Java 项目使用 Markdown 格式，DashScope 也支持 Markdown，可以直接上传。

#### 步骤 3：上传到 DashScope

按照"方式 1"的步骤 2-4 操作。

---

## 知识库文档内容建议

### 1. 产品介绍文档

每个产品一个文档，包含：
- 产品名称
- 产品特点
- 制作工艺
- 推荐人群
- 价格
- 保质期
- 制作时间
- 冲泡建议

**示例**（`knowledge_base/products/云边茉莉.txt`）：
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
保质期：30分钟
制作时间：5分钟

冲泡建议：
- 建议温度：60-70度
- 建议甜度：标准糖或半糖
- 建议冰量：正常冰或去冰
```

### 2. 品牌介绍文档

包含：
- 品牌故事
- 品牌理念
- 品牌特色
- 服务承诺

### 3. 活动信息文档

包含：
- 当前活动
- 优惠信息
- 会员权益

### 4. 冲泡指导文档

包含：
- 不同产品的冲泡方法
- 温度控制
- 时间控制

---

## 完整构建流程示例

### 场景：从零开始构建知识库

1. **准备文档**（1-2 小时）
   ```bash
   # 创建知识库目录结构
   mkdir -p knowledge_base/{products,store,activities,guides}
   
   # 编写文档内容
   # 参考 Java 项目的 brand-overview.md 和 products.md
   # 或使用已提供的示例文档
   ```

2. **创建 DashScope 知识库**（5 分钟）
   - 登录 DashScope 控制台
   - 创建新索引
   - 记录 Index ID

3. **上传文档**（10-30 分钟，取决于文档数量）
   ```bash
   # 方式 A：使用脚本批量上传
   python3 scripts/upload_knowledge_base.py
   
   # 方式 B：在控制台手动上传
   ```

4. **等待文档解析**（5-10 分钟）
   - DashScope 需要时间解析和索引文档
   - 在控制台查看解析状态

5. **配置环境变量**（1 分钟）
   ```bash
   # 编辑 .env 文件
   echo "DASHSCOPE_INDEX_ID=your_index_id" >> .env
   ```

6. **测试知识库**（5 分钟）
   ```bash
   # 启动服务
   python3 consult_mcp_server/run_consult_mcp_server.py
   
   # 在另一个终端测试
   python3 -c "
   from consult_mcp_server.consult_service import ConsultService
   service = ConsultService()
   result = service.search_knowledge('云边茉莉的特点是什么？')
   print(result)
   "
   ```

---

## 注意事项

### 1. 文档格式

- **推荐格式**：Markdown（`.md`）或纯文本（`.txt`）
- **编码**：必须使用 UTF-8
- **文件大小**：单个文件建议不超过 10MB
- **文件数量**：建议不超过 1000 个文件

### 2. 文档内容

- **清晰分段**：使用标题、列表等格式，便于理解
- **关键信息**：包含产品名称、价格、特点等关键信息
- **避免重复**：相同信息不要重复出现在多个文档中

### 3. 上传时机

- **上线前**：必须在应用上线前完成知识库构建
- **定期更新**：产品信息变化时，及时更新知识库
- **版本管理**：建议对知识库文档进行版本管理

### 4. 成本考虑

- DashScope 文档检索服务可能产生费用
- 建议查看 [DashScope 定价](https://help.aliyun.com/zh/dashscope/product-overview/billing-overview)
- 合理控制文档数量和大小

---

## 验证知识库

### 1. 检查文档是否上传成功

在 DashScope 控制台查看：
- 文档数量是否正确
- 文档解析状态（是否已完成）
- 是否有错误提示

### 2. 测试检索功能

```python
from consult_mcp_server.consult_service import ConsultService

service = ConsultService()

# 测试产品查询
result = service.search_knowledge("云边茉莉的特点")
print(result)

# 测试品牌查询
result = service.search_knowledge("云边奶茶铺的品牌理念")
print(result)

# 测试活动查询
result = service.search_knowledge("当前有什么活动")
print(result)
```

### 3. 检查检索质量

- 检索结果是否相关
- 是否包含关键信息
- 是否需要调整 rerank 参数

---

## 常见问题

### Q1: 文档上传后多久可以使用？

A: 通常需要 5-10 分钟，DashScope 需要时间解析和索引文档。可以在控制台查看解析状态。

### Q2: 可以更新已上传的文档吗？

A: 可以。在 DashScope 控制台删除旧文档，然后上传新文档。或者使用 API 更新。

### Q3: 知识库有大小限制吗？

A: 有。建议单个文件不超过 10MB，总文件数不超过 1000 个。具体限制请查看 DashScope 文档。

### Q4: 如何知道知识库是否正常工作？

A: 可以通过测试检索功能验证。如果返回相关结果，说明知识库正常工作。

---

## 总结

知识库构建的关键步骤：

1. ✅ **准备文档**：在项目中准备 Markdown/TXT 格式的知识库文档
2. ✅ **创建索引**：在 DashScope 控制台创建知识库索引
3. ✅ **上传文档**：上传准备好的文档到 DashScope
4. ✅ **配置环境**：将 Index ID 配置到环境变量
5. ✅ **测试验证**：测试知识库检索功能

**重要提示**：知识库必须在应用上线前构建完成，否则咨询功能将无法正常工作（会回退到数据库查询）。
