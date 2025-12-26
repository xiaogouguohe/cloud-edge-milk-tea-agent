# 数据库表结构说明

本文档描述了云边奶茶铺多智能体系统的完整数据库表结构。

---

## 一、用户表 (users)

### 表结构

```sql
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    phone VARCHAR(20),
    email VARCHAR(100),
    nickname VARCHAR(50),
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 字段说明

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `id` | BIGINT | 用户ID | PRIMARY KEY |
| `username` | VARCHAR(50) | 用户名 | NOT NULL, UNIQUE |
| `phone` | VARCHAR(20) | 手机号 | 可选 |
| `email` | VARCHAR(100) | 邮箱 | 可选 |
| `nickname` | VARCHAR(50) | 昵称 | 可选 |
| `status` | TINYINT | 状态（1-正常，0-禁用） | DEFAULT 1 |
| `created_at` | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | 更新时间 | DEFAULT CURRENT_TIMESTAMP |

---

## 二、产品表 (products)

### 表结构

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INT DEFAULT 0,
    shelf_time INT DEFAULT 30,
    preparation_time INT DEFAULT 5,
    is_seasonal TINYINT DEFAULT 0,
    season_start DATE,
    season_end DATE,
    is_regional TINYINT DEFAULT 0,
    available_regions TEXT,
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- MySQL
CREATE TABLE IF NOT EXISTS products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INT DEFAULT 0,
    shelf_time INT DEFAULT 30,
    preparation_time INT DEFAULT 5,
    is_seasonal TINYINT DEFAULT 0,
    season_start DATE,
    season_end DATE,
    is_regional TINYINT DEFAULT 0,
    available_regions JSON,
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 字段说明

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `id` | BIGINT/INTEGER | 产品ID | PRIMARY KEY, AUTO_INCREMENT |
| `name` | VARCHAR(100) | 产品名称 | NOT NULL, UNIQUE |
| `description` | TEXT | 产品描述 | 可选 |
| `price` | DECIMAL(10,2) | 价格 | NOT NULL |
| `stock` | INT | 库存 | DEFAULT 0 |
| `shelf_time` | INT | 保质期（天） | DEFAULT 30 |
| `preparation_time` | INT | 制作时间（分钟） | DEFAULT 5 |
| `is_seasonal` | TINYINT | 是否季节性产品 | DEFAULT 0 |
| `season_start` | DATE | 季节开始日期 | 可选 |
| `season_end` | DATE | 季节结束日期 | 可选 |
| `is_regional` | TINYINT | 是否区域限定 | DEFAULT 0 |
| `available_regions` | TEXT/JSON | 可用区域 | 可选 |
| `status` | TINYINT | 状态（1-上架，0-下架） | DEFAULT 1 |
| `created_at` | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | 更新时间 | DEFAULT CURRENT_TIMESTAMP |

---

## 三、订单表 (orders) - 主表

### 表结构

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(50) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) DEFAULT 'UNPAID',
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- MySQL
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) DEFAULT 'UNPAID',
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 字段说明

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `id` | BIGINT/INTEGER | 订单主键ID | PRIMARY KEY, AUTO_INCREMENT |
| `order_id` | VARCHAR(50) | 订单ID（业务ID，格式：ORDER_xxx） | NOT NULL, UNIQUE |
| `user_id` | BIGINT | 用户ID | NOT NULL, FOREIGN KEY → users(id) |
| `total_price` | DECIMAL(10,2) | 订单总价（所有订单项之和） | NOT NULL, DEFAULT 0 |
| `status` | VARCHAR(20) | 订单状态 | DEFAULT 'UNPAID' |
| `remark` | TEXT | 订单备注 | 可选 |
| `created_at` | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | 更新时间 | DEFAULT CURRENT_TIMESTAMP |

### 订单状态说明

- `UNPAID` - 未支付
- `PAID` - 已支付
- `SHIPPED` - 已发货
- `COMPLETED` - 已完成
- `CANCELLED` - 已取消
- `REFUNDED` - 已退款

**注意**：此表只存储订单基本信息，不包含产品信息。产品信息存储在 `order_items` 表中。

---

## 四、订单项表 (order_items) - 从表

### 表结构

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(50) NOT NULL,
    product_id BIGINT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    sweetness TINYINT NOT NULL,
    ice_level TINYINT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    item_price DECIMAL(10,2) NOT NULL,
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- MySQL
CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    product_id BIGINT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    sweetness TINYINT NOT NULL,
    ice_level TINYINT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    item_price DECIMAL(10,2) NOT NULL,
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
);
```

### 字段说明

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `id` | BIGINT/INTEGER | 订单项主键ID | PRIMARY KEY, AUTO_INCREMENT |
| `order_id` | VARCHAR(50) | 订单ID | NOT NULL, FOREIGN KEY → orders(order_id) |
| `product_id` | BIGINT | 产品ID | NOT NULL, FOREIGN KEY → products(id) |
| `product_name` | VARCHAR(100) | 产品名称（冗余字段，便于查询） | NOT NULL |
| `sweetness` | TINYINT | 甜度（1-无糖，2-微糖，3-半糖，4-少糖，5-标准糖） | NOT NULL |
| `ice_level` | TINYINT | 冰量（1-热，2-温，3-去冰，4-少冰，5-正常冰） | NOT NULL |
| `quantity` | INT | 数量 | NOT NULL, DEFAULT 1 |
| `unit_price` | DECIMAL(10,2) | 单价 | NOT NULL |
| `item_price` | DECIMAL(10,2) | 该项总价（unit_price × quantity） | NOT NULL |
| `remark` | TEXT | 该项备注 | 可选 |
| `created_at` | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |

### 甜度和冰量映射

**甜度 (sweetness)**：
- 1 = 无糖
- 2 = 微糖
- 3 = 半糖
- 4 = 少糖
- 5 = 标准糖

**冰量 (ice_level)**：
- 1 = 热
- 2 = 温
- 3 = 去冰
- 4 = 少冰
- 5 = 正常冰

**设计说明**：
- 一个订单可以包含多个订单项（支持多产品订单）
- `product_name` 是冗余字段，便于查询，避免频繁 JOIN
- `item_price = unit_price × quantity`，便于计算订单总价

---

## 五、反馈表 (feedback)

### 表结构

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(50),
    user_id BIGINT NOT NULL,
    feedback_type TINYINT NOT NULL,
    rating TINYINT,
    content TEXT NOT NULL,
    solution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- MySQL
CREATE TABLE IF NOT EXISTS feedback (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50),
    user_id BIGINT NOT NULL,
    feedback_type TINYINT NOT NULL,
    rating TINYINT,
    content TEXT NOT NULL,
    solution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 字段说明

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `id` | BIGINT/INTEGER | 反馈ID | PRIMARY KEY, AUTO_INCREMENT |
| `order_id` | VARCHAR(50) | 关联订单ID | 可选 |
| `user_id` | BIGINT | 用户ID | NOT NULL |
| `feedback_type` | TINYINT | 反馈类型 | NOT NULL |
| `rating` | TINYINT | 评分（1-5星） | 可选 |
| `content` | TEXT | 反馈内容 | NOT NULL |
| `solution` | TEXT | 解决方案 | 可选 |
| `created_at` | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | 更新时间 | DEFAULT CURRENT_TIMESTAMP |

### 反馈类型说明

- 1 = 产品反馈
- 2 = 服务反馈
- 3 = 投诉
- 4 = 建议

---

## 六、表关系图

```
users (用户表)
  │
  ├─→ orders (订单表)
  │     │
  │     └─→ order_items (订单项表)
  │           │
  │           └─→ products (产品表)
  │
  └─→ feedback (反馈表)
        │
        └─→ orders (订单表) [可选关联]
```

### 关系说明

1. **users → orders**：一个用户可以有多个订单（1:N）
2. **orders → order_items**：一个订单可以包含多个订单项（1:N）
3. **order_items → products**：一个订单项对应一个产品（N:1）
4. **users → feedback**：一个用户可以有多个反馈（1:N）
5. **feedback → orders**：一个反馈可以关联一个订单（N:1，可选）

### 外键约束

- `orders.user_id` → `users.id`
- `order_items.order_id` → `orders.order_id` (ON DELETE CASCADE)
- `order_items.product_id` → `products.id`

**CASCADE 说明**：
- 删除订单时，自动删除该订单的所有订单项
- 删除用户时，自动删除该用户的所有订单（MySQL）

---

## 七、索引建议

### 推荐索引

```sql
-- orders 表索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- order_items 表索引
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_order_items_product_name ON order_items(product_name);

-- feedback 表索引
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_order_id ON feedback(order_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);
```

---

## 八、数据示例

### 示例1：单产品订单

**orders 表**：
```
id: 1
order_id: ORDER_1693654321000
user_id: 789012
total_price: 18.00
status: UNPAID
remark: 不要珍珠
created_at: 2025-01-15 10:30:00
```

**order_items 表**：
```
id: 1
order_id: ORDER_1693654321000
product_id: 1
product_name: 云边茉莉
sweetness: 4 (少糖)
ice_level: 5 (正常冰)
quantity: 1
unit_price: 18.00
item_price: 18.00
remark: 不要珍珠
created_at: 2025-01-15 10:30:00
```

### 示例2：多产品订单

**orders 表**：
```
id: 2
order_id: ORDER_1693654322000
user_id: 789012
total_price: 58.00
status: UNPAID
remark: 一起配送
created_at: 2025-01-15 11:00:00
```

**order_items 表**：
```
id: 2
order_id: ORDER_1693654322000
product_id: 1
product_name: 云边茉莉
sweetness: 4 (少糖)
ice_level: 5 (正常冰)
quantity: 1
unit_price: 18.00
item_price: 18.00
remark: 
created_at: 2025-01-15 11:00:00

id: 3
order_id: ORDER_1693654322000
product_id: 2
product_name: 桂花云露
sweetness: 3 (半糖)
ice_level: 3 (去冰)
quantity: 2
unit_price: 20.00
item_price: 40.00
remark: 
created_at: 2025-01-15 11:00:00
```

---

## 九、查询示例

### 查询订单及其所有订单项

```sql
SELECT 
    o.order_id,
    o.user_id,
    o.total_price,
    o.status,
    oi.product_name,
    oi.quantity,
    oi.item_price
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.user_id = 789012
ORDER BY o.created_at DESC;
```

### 查询订单总价（验证计算）

```sql
SELECT 
    o.order_id,
    o.total_price AS order_total,
    SUM(oi.item_price) AS calculated_total
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id
HAVING o.total_price != SUM(oi.item_price);
```

### 查询用户的所有订单（包含订单项数量）

```sql
SELECT 
    o.order_id,
    o.user_id,
    o.total_price,
    o.status,
    COUNT(oi.id) AS item_count
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.user_id = 789012
GROUP BY o.order_id
ORDER BY o.created_at DESC;
```

---

## 十、SQLite vs MySQL 差异

| 特性 | SQLite | MySQL |
|------|--------|-------|
| **AUTO_INCREMENT** | INTEGER PRIMARY KEY AUTOINCREMENT | BIGINT AUTO_INCREMENT PRIMARY KEY |
| **JSON 类型** | TEXT | JSON |
| **ON UPDATE** | 不支持 | 支持 ON UPDATE CURRENT_TIMESTAMP |
| **外键约束** | 需要启用 | 默认支持 |
| **CASCADE** | 支持 | 支持 |
| **数据类型** | 较宽松 | 严格 |

---

## 十一、设计特点

### 1. 订单与订单项分离

- ✅ **支持多产品订单**：一个订单可以包含多个不同产品
- ✅ **灵活扩展**：每个订单项可以有独立的规格和备注
- ✅ **数据一致性**：订单总价 = 所有订单项总价之和

### 2. 数据冗余

- ✅ **product_name 冗余**：在 `order_items` 表中冗余存储产品名称
- ✅ **优势**：避免频繁 JOIN，提升查询性能
- ✅ **劣势**：如果产品名称变更，历史订单不会更新（这是合理的，历史订单应该保持原样）

### 3. 外键约束

- ✅ **数据完整性**：确保订单项必须关联到有效订单
- ✅ **级联删除**：删除订单时自动删除订单项
- ✅ **级联限制**：删除产品时，如果有关联订单项，不允许删除（MySQL）

---

## 十二、总结

### 核心表结构

1. **users** - 用户表
2. **products** - 产品表
3. **orders** - 订单表（主表，只存储订单基本信息）
4. **order_items** - 订单项表（从表，存储订单中的每个产品）
5. **feedback** - 反馈表

### 关键设计

- ✅ **订单与订单项分离**：支持一个订单包含多个产品
- ✅ **数据冗余**：`order_items.product_name` 冗余存储，便于查询
- ✅ **外键约束**：保证数据一致性
- ✅ **级联删除**：删除订单时自动删除订单项

### 使用场景

- **单产品订单**：创建一个订单，包含1个订单项
- **多产品订单**：创建一个订单，包含多个订单项
- **订单查询**：查询订单时，自动加载所有订单项
- **订单统计**：可以按产品、用户、时间等维度统计

