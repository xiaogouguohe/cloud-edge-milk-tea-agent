# 数据库进程说明

## 问题：SQL 和 Milvus 是否需要启动单独的进程？

## 答案：取决于数据库类型

---

## 一、关系数据库（订单数据）

### SQLite（开发环境，默认）

**是否需要单独进程**: ❌ **不需要**

**原因**:
- SQLite 是**嵌入式数据库**（Embedded Database）
- 作为 Python 标准库 `sqlite3` 直接使用
- 数据存储在本地文件中（`./data/milk_tea.db`）
- 通过文件 I/O 直接访问，无需网络通信

**使用方式**:
```python
import sqlite3
conn = sqlite3.connect('./data/milk_tea.db')  # 直接连接文件
```

**特点**:
- ✅ 无需安装和配置
- ✅ 无需单独进程
- ✅ 零配置，开箱即用
- ✅ 适合开发和小规模应用

---

### MySQL（生产环境，可选）

**是否需要单独进程**: ✅ **需要**

**原因**:
- MySQL 是**独立数据库服务器**（Standalone Database Server）
- 需要运行 `mysqld` 服务进程
- 通过 TCP/IP 网络协议访问
- 这是**外部服务**，不是项目代码的一部分

**使用方式**:
```python
import pymysql
conn = pymysql.connect(
    host='localhost',  # 连接到 MySQL 服务器
    port=3306,
    user='root',
    password='password',
    database='multi_agent_demo'
)
```

**启动方式**:
```bash
# 方式1: 系统服务（systemd）
sudo systemctl start mysql

# 方式2: Docker
docker run -d --name mysql -p 3306:3306 mysql:8.0

# 方式3: 本地安装
mysqld --datadir=/var/lib/mysql
```

**特点**:
- ✅ 支持高并发
- ✅ 支持多用户访问
- ✅ 适合生产环境
- ⚠️ 需要单独安装和配置

---

## 二、向量数据库（知识库）

### Milvus Lite（当前实现）

**是否需要单独进程**: ❌ **不需要**

**原因**:
- Milvus Lite 是**嵌入式向量数据库**（Embedded Vector Database）
- 作为 Python 库 `pymilvus` 的一部分直接使用
- 数据存储在本地文件中（`./data/milvus_lite.db`）
- 通过 `MilvusClient` 直接访问本地文件，无需网络通信

**使用方式**:
```python
from pymilvus import MilvusClient

# 直接连接本地文件，无需单独服务
client = MilvusClient(uri='./data/milvus_lite.db')
```

**特点**:
- ✅ 无需 Docker
- ✅ 无需单独进程
- ✅ 零配置，开箱即用
- ✅ 适合开发和小规模应用
- ✅ 数据持久化到本地文件

**代码示例**:
```python
# rag/milvus_lite_vector_store.py
self.client = MilvusClient(uri=db_path)  # 直接连接文件
```

---

### Milvus Standalone（生产环境，可选）

**是否需要单独进程**: ✅ **需要**

**原因**:
- Milvus Standalone 是**独立向量数据库服务器**
- 需要运行 Milvus 服务进程（通常通过 Docker）
- 通过 gRPC 网络协议访问
- 这是**外部服务**，不是项目代码的一部分

**使用方式**:
```python
from pymilvus import connections

# 连接到远程 Milvus 服务器
connections.connect(
    alias="default",
    host="localhost",  # Milvus 服务器地址
    port="19530"       # Milvus 服务端口
)
```

**启动方式**:
```bash
# Docker Compose
docker-compose up -d milvus

# 或直接运行 Docker
docker run -d --name milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest
```

**特点**:
- ✅ 支持高并发
- ✅ 支持分布式部署
- ✅ 适合生产环境
- ⚠️ 需要 Docker 或单独安装

---

## 三、总结对比

| 数据库类型 | 是否需要单独进程 | 访问方式 | 适用场景 |
|-----------|----------------|---------|---------|
| **SQLite** | ❌ 不需要 | 文件 I/O | 开发环境、小规模应用 |
| **MySQL** | ✅ 需要 | TCP/IP 网络 | 生产环境、高并发 |
| **Milvus Lite** | ❌ 不需要 | 文件 I/O | 开发环境、小规模应用 |
| **Milvus Standalone** | ✅ 需要 | gRPC 网络 | 生产环境、高并发 |

---

## 四、当前项目的部署架构

### 开发环境（默认）

```
进程1: SupervisorAgent
进程2: OrderMCPServer
  └─ 直接访问 SQLite 文件 (./data/milk_tea.db) ← 无需单独进程
进程3: OrderAgent
进程4: ConsultAgent
进程5: ConsultMCPServer
  └─ 直接访问 Milvus Lite 文件 (./data/milvus_lite.db) ← 无需单独进程
```

**特点**:
- ✅ 所有服务都在应用进程中
- ✅ 无需额外的数据库服务进程
- ✅ 零配置，开箱即用

### 生产环境（可选）

```
进程1: SupervisorAgent
进程2: OrderMCPServer
  └─ 通过网络访问 MySQL 服务 ← 需要单独进程（外部服务）
进程3: OrderAgent
进程4: ConsultAgent
进程5: ConsultMCPServer
  └─ 通过网络访问 Milvus Standalone ← 需要单独进程（外部服务）

外部服务:
- MySQL 服务 (mysqld)
- Milvus Standalone 服务
```

**特点**:
- ✅ 数据库服务独立部署
- ✅ 支持高并发和分布式
- ⚠️ 需要额外的服务进程（但这是外部服务，不是项目代码的一部分）

---

## 五、关键理解

### 1. 嵌入式 vs 独立服务

- **嵌入式数据库**（SQLite、Milvus Lite）:
  - 作为库直接集成到应用中
  - 无需单独进程
  - 数据存储在本地文件

- **独立数据库服务**（MySQL、Milvus Standalone）:
  - 作为独立服务运行
  - 需要单独进程
  - 通过网络协议访问

### 2. 项目代码 vs 外部服务

- **项目代码中的服务**:
  - SupervisorAgent
  - OrderAgent
  - ConsultAgent
  - OrderMCPServer
  - ConsultMCPServer
  - 这些都需要单独进程

- **外部服务**（不是项目代码的一部分）:
  - MySQL（如果使用）
  - Milvus Standalone（如果使用）
  - 这些也需要单独进程，但是外部服务

### 3. 当前项目的设计

**默认使用嵌入式数据库**:
- SQLite（关系数据库）
- Milvus Lite（向量数据库）

**优势**:
- 简化部署，无需额外服务
- 适合开发和演示
- 零配置，开箱即用

**可扩展**:
- 生产环境可以切换到 MySQL 和 Milvus Standalone
- 只需修改配置，代码无需大改

---

## 六、面试时的回答

**问题**: SQL 和 Milvus 是否需要启动单独的进程来维护？

**回答**:

1. **SQLite（默认）**: 不需要单独进程
   - SQLite 是嵌入式数据库，作为 Python 库直接使用
   - 数据存储在本地文件中，通过文件 I/O 访问
   - 无需网络通信，无需单独服务进程

2. **MySQL（可选）**: 需要单独进程
   - MySQL 是独立数据库服务器，需要运行 mysqld 服务
   - 但这是外部服务，不是项目代码的一部分
   - 通常通过 systemd 或 Docker 管理

3. **Milvus Lite（默认）**: 不需要单独进程
   - Milvus Lite 是嵌入式向量数据库，作为 Python 库直接使用
   - 数据存储在本地文件中，通过文件 I/O 访问
   - 无需 Docker，无需单独服务进程

4. **Milvus Standalone（可选）**: 需要单独进程
   - Milvus Standalone 是独立向量数据库服务器
   - 但这是外部服务，不是项目代码的一部分
   - 通常通过 Docker 部署

**总结**: 
- 当前项目默认使用嵌入式数据库（SQLite + Milvus Lite），**无需单独进程**
- 生产环境可以切换到独立服务（MySQL + Milvus Standalone），**需要单独进程**，但这是外部服务

