# 本地环境设置指南（不使用 Docker）

## 1. MySQL 安装和配置

### macOS
```bash
# 使用 Homebrew 安装
brew install mysql
brew services start mysql

# 设置 root 密码
mysql_secure_installation

# 创建数据库和用户
mysql -u root -p
```

```sql
CREATE DATABASE multi_agent_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'milk_tea_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON multi_agent_demo.* TO 'milk_tea_user'@'localhost';
FLUSH PRIVILEGES;
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql

# 设置 root 密码
sudo mysql_secure_installation
```

### Windows
1. 下载 MySQL Installer: https://dev.mysql.com/downloads/installer/
2. 运行安装程序，按提示安装
3. 使用 MySQL Workbench 或命令行创建数据库

### Python 连接
```python
import pymysql

conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='milk_tea_user',
    password='your_password',
    database='multi_agent_demo',
    charset='utf8mb4'
)
```

## 2. Redis 安装和配置

### macOS
```bash
brew install redis
brew services start redis

# 测试连接
redis-cli ping
```

### Linux (Ubuntu/Debian)
```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# 测试连接
redis-cli ping
```

### Windows
1. 下载 Redis for Windows: https://github.com/microsoftarchive/redis/releases
2. 解压并运行 `redis-server.exe`

### Python 连接
```python
import redis

r = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

# 测试
r.ping()
```

## 3. 服务发现方案

### 方案 A: 配置文件（最简单，推荐开发）

创建 `services.json`:
```json
{
  "order_agent": {
    "host": "localhost",
    "port": 10006,
    "url": "http://localhost:10006"
  },
  "consult_agent": {
    "host": "localhost",
    "port": 10005,
    "url": "http://localhost:10005"
  }
}
```

使用：
```python
from service_discovery import ServiceDiscovery

sd = ServiceDiscovery(method="config")
service = sd.discover("order_agent")
# {'host': 'localhost', 'port': 10006, 'url': 'http://localhost:10006'}
```

### 方案 B: Redis 作为服务注册表

```python
from service_discovery import ServiceDiscovery

# 初始化（使用 Redis）
sd = ServiceDiscovery(
    method="redis",
    redis_host="localhost",
    redis_port=6379
)

# 注册服务
sd.register("order_agent", host="localhost", port=10006)

# 发现服务
service = sd.discover("order_agent")
```

### 方案 C: Consul（生产环境推荐）

#### 安装 Consul
```bash
# macOS
brew install consul

# Linux
wget https://releases.hashicorp.com/consul/1.17.0/consul_1.17.0_linux_amd64.zip
unzip consul_1.17.0_linux_amd64.zip
sudo mv consul /usr/local/bin/

# 启动 Consul（开发模式）
consul agent -dev
```

#### Python 使用
```bash
pip install python-consul
```

```python
import consul

c = consul.Consul()

# 注册服务
c.agent.service.register(
    'order_agent',
    service_id='order_agent_1',
    address='localhost',
    port=10006
)

# 发现服务
services = c.agent.services()
order_agent = services.get('order_agent_1')
```

## 4. 环境变量配置

创建 `.env` 文件：
```env
# 数据库配置
DB_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=milk_tea_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=multi_agent_demo

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# 服务发现配置
SERVICE_DISCOVERY_METHOD=config  # config, redis, consul
```

## 5. 快速启动脚本

创建 `start_local.sh`:
```bash
#!/bin/bash

# 检查 MySQL
if ! mysqladmin ping -h localhost -u root --silent; then
    echo "MySQL 未运行，请先启动 MySQL"
    exit 1
fi

# 检查 Redis
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Redis 未运行，请先启动 Redis"
    exit 1
fi

# 启动应用
python chat.py
```

## 6. 对比 Docker vs 直接安装

| 方式 | 优点 | 缺点 |
|------|------|------|
| Docker | 环境隔离、易于管理、一键启动 | 需要 Docker、占用资源 |
| 直接安装 | 性能好、资源占用少、原生体验 | 需要手动配置、可能污染系统 |

## 推荐方案

- **开发环境**: 直接安装 MySQL 和 Redis，使用配置文件服务发现
- **生产环境**: Docker 或云服务，使用 Consul 或 Redis 服务发现
