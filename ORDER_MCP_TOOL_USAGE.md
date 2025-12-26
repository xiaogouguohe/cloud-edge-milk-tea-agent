# OrderMCPServer 用户行为与 MCP Tool 映射

本文档列出了用户的各种行为表达方式，以及对应的 OrderMCPServer MCP Tool 调用。

---

## 1. `order-create-order-with-user` - 创建订单

### 用户行为示例

**场景1：直接下单**
```
用户: "我要下单，一杯云边茉莉，少糖，正常冰"
  ↓
调用: order-create-order-with-user
参数: {
  userId: 789012,
  productName: "云边茉莉",
  sweetness: "少糖",
  iceLevel: "正常冰",
  quantity: 1
}
```

**场景2：指定数量**
```
用户: "帮我点两杯桂花云露，半糖，去冰"
  ↓
调用: order-create-order-with-user
参数: {
  userId: 789012,
  productName: "桂花云露",
  sweetness: "半糖",
  iceLevel: "去冰",
  quantity: 2
}
```

**场景3：带备注的下单**
```
用户: "我要一杯云雾观音，标准糖，热饮，备注：不要珍珠"
  ↓
调用: order-create-order-with-user
参数: {
  userId: 789012,
  productName: "云雾观音",
  sweetness: "标准糖",
  iceLevel: "热",
  quantity: 1,
  remark: "不要珍珠"
}
```

**场景4：询问后下单**
```
用户: "我想买奶茶"
AI: "好的，请问您想要什么产品？"
用户: "云边茉莉，微糖，少冰，一杯"
  ↓
调用: order-create-order-with-user
参数: {
  userId: 789012,
  productName: "云边茉莉",
  sweetness: "微糖",
  iceLevel: "少冰",
  quantity: 1
}
```

**场景5：修改订单后重新下单**
```
用户: "刚才的订单不要了，重新下一杯云边茉莉，无糖，温的"
  ↓
调用: order-delete-order (先删除旧订单)
  ↓
调用: order-create-order-with-user (创建新订单)
参数: {
  userId: 789012,
  productName: "云边茉莉",
  sweetness: "无糖",
  iceLevel: "温",
  quantity: 1
}
```

---

## 2. `order-get-order` - 根据订单ID查询订单

### 用户行为示例

**场景1：查询订单详情**
```
用户: "查询订单 ORDER_1693654321000 的详情"
  ↓
调用: order-get-order
参数: {
  orderId: "ORDER_1693654321000"
}
```

**场景2：查看订单状态**
```
用户: "我的订单 ORDER_1693654321000 现在是什么状态？"
  ↓
调用: order-get-order
参数: {
  orderId: "ORDER_1693654321000"
}
```

**场景3：确认订单信息**
```
用户: "帮我看看订单 ORDER_1693654321000 里都有什么"
  ↓
调用: order-get-order
参数: {
  orderId: "ORDER_1693654321000"
}
```

**场景4：通过订单号查询**
```
用户: "ORDER_1693654321000 这个订单的信息"
  ↓
调用: order-get-order
参数: {
  orderId: "ORDER_1693654321000"
}
```

**场景5：客服查询订单**
```
用户: "我想查一下这个订单：ORDER_1693654321000"
  ↓
调用: order-get-order
参数: {
  orderId: "ORDER_1693654321000"
}
```

---

## 3. `order-get-order-by-user` - 根据用户ID和订单ID查询订单（带安全验证）

### 用户行为示例

**场景1：用户查询自己的订单（带用户ID验证）**
```
用户: "我是用户789012，想查询订单 ORDER_1693654321000"
  ↓
调用: order-get-order-by-user
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
```

**场景2：安全验证场景**
```
用户: "查询我的订单 ORDER_1693654321000"
AI: "为了安全，请提供您的用户ID"
用户: "我的用户ID是789012"
  ↓
调用: order-get-order-by-user
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
```

**场景3：多用户场景下的精确查询**
```
用户: "用户ID 789012，订单号 ORDER_1693654321000，帮我查一下"
  ↓
调用: order-get-order-by-user
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
```

**说明**：这个方法比 `order-get-order` 更安全，因为需要同时提供用户ID和订单ID，确保用户只能查询自己的订单。

---

## 4. `order-get-orders-by-user` - 根据用户ID获取订单列表

### 用户行为示例

**场景1：查看历史订单**
```
用户: "我想查看我的历史订单"
  ↓
调用: order-get-orders-by-user
参数: {
  userId: 789012
}
```

**场景2：查看所有订单**
```
用户: "帮我列出我所有的订单"
  ↓
调用: order-get-orders-by-user
参数: {
  userId: 789012
}
```

**场景3：查看订单记录**
```
用户: "我之前都下过哪些订单？"
  ↓
调用: order-get-orders-by-user
参数: {
  userId: 789012
}
```

**场景4：订单历史查询**
```
用户: "我想看看我的订单历史"
  ↓
调用: order-get-orders-by-user
参数: {
  userId: 789012
}
```

**场景5：统计订单**
```
用户: "我一共下过多少单？"
  ↓
调用: order-get-orders-by-user
参数: {
  userId: 789012
}
返回结果中包含订单数量统计
```

**场景6：查看最近的订单**
```
用户: "我最近都买了什么？"
  ↓
调用: order-get-orders-by-user
参数: {
  userId: 789012
}
返回结果按时间倒序排列
```

---

## 5. `order-delete-order` - 删除订单

### 用户行为示例

**场景1：取消订单**
```
用户: "我要取消订单 ORDER_1693654321000"
  ↓
调用: order-delete-order
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
```

**场景2：删除错误订单**
```
用户: "刚才下的订单不要了，帮我删除 ORDER_1693654321000"
  ↓
调用: order-delete-order
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
```

**场景3：撤销订单**
```
用户: "撤销订单 ORDER_1693654321000"
  ↓
调用: order-delete-order
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
```

**场景4：取消并重新下单**
```
用户: "订单 ORDER_1693654321000 取消，我重新下一单"
  ↓
调用: order-delete-order (删除旧订单)
  ↓
调用: order-create-order-with-user (创建新订单)
```

**场景5：误下单后删除**
```
用户: "我点错了，帮我删除订单 ORDER_1693654321000"
  ↓
调用: order-delete-order
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
```

**场景6：带用户ID的删除（安全验证）**
```
用户: "我是用户789012，想删除订单 ORDER_1693654321000"
  ↓
调用: order-delete-order
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
```

---

## 6. `order-update-remark` - 更新订单备注

### 用户行为示例

**场景1：添加备注**
```
用户: "订单 ORDER_1693654321000 的备注改为：不要珍珠"
  ↓
调用: order-update-remark
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000",
  remark: "不要珍珠"
}
```

**场景2：修改备注**
```
用户: "修改订单 ORDER_1693654321000 的备注为：加急配送"
  ↓
调用: order-update-remark
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000",
  remark: "加急配送"
}
```

**场景3：更新特殊要求**
```
用户: "订单 ORDER_1693654321000，备注更新为：送到后门"
  ↓
调用: order-update-remark
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000",
  remark: "送到后门"
}
```

**场景4：补充备注信息**
```
用户: "给订单 ORDER_1693654321000 添加备注：如果不在家，放门口"
  ↓
调用: order-update-remark
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000",
  remark: "如果不在家，放门口"
}
```

**场景5：修改配送要求**
```
用户: "订单 ORDER_1693654321000 的备注改成：下午3点后配送"
  ↓
调用: order-update-remark
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000",
  remark: "下午3点后配送"
}
```

---

## 特殊场景：换产品

### 场景描述

用户之前点了一份奶茶A（例如：云边茉莉），现在想换成奶茶B（例如：桂花云露）。

### 用户行为示例

**方式1：明确说明换产品**
```
用户: "我想把订单 ORDER_1693654321000 换成桂花云露"
  ↓
调用: order-delete-order (删除旧订单)
参数: {
  userId: 789012,
  orderId: "ORDER_1693654321000"
}
  ↓
调用: order-create-order-with-user (创建新订单)
参数: {
  userId: 789012,
  productName: "桂花云露",
  sweetness: "少糖",  // 从旧订单继承或使用默认值
  iceLevel: "正常冰", // 从旧订单继承或使用默认值
  quantity: 1
}
```

**方式2：取消后重新下单**
```
用户: "刚才的订单不要了，重新下一杯桂花云露"
  ↓
调用: order-delete-order (删除旧订单)
  ↓
调用: order-create-order-with-user (创建新订单)
```

**方式3：修改订单**
```
用户: "订单 ORDER_1693654321000 改成桂花云露"
  ↓
调用: order-delete-order (删除旧订单)
  ↓
调用: order-create-order-with-user (创建新订单)
```

**说明**：
- 由于 OrderMCPServer 没有直接修改订单产品的方法
- "换产品"需要两步操作：先删除旧订单，再创建新订单
- OrderAgent 的 LLM 会理解用户意图，自动执行这两个操作

---

## 完整对话流程示例

### 示例1：下单 → 查询 → 修改备注 → 删除

```
用户: "我要下单，一杯云边茉莉，少糖，正常冰"
  ↓ order-create-order-with-user
AI: "好的，订单已创建！订单ID: ORDER_1693654321000"

用户: "查询订单 ORDER_1693654321000"
  ↓ order-get-order
AI: "订单详情：云边茉莉，少糖，正常冰，¥18.00..."

用户: "订单 ORDER_1693654321000 的备注改为：不要珍珠"
  ↓ order-update-remark
AI: "备注已更新为：不要珍珠"

用户: "算了，取消这个订单"
  ↓ order-delete-order
AI: "订单已删除"
```

### 示例2：查看历史 → 查询详情 → 换产品

```
用户: "我想查看我的历史订单"
  ↓ order-get-orders-by-user
AI: "您共有3个订单：ORDER_xxx, ORDER_yyy, ORDER_zzz..."

用户: "查询订单 ORDER_xxx 的详情"
  ↓ order-get-order-by-user
AI: "订单详情：云边茉莉，少糖，正常冰..."

用户: "我想把订单 ORDER_xxx 换成桂花云露"
  ↓ order-delete-order (删除旧订单)
  ↓ order-create-order-with-user (创建新订单)
AI: "好的，已为您取消原订单，新订单已创建！订单ID: ORDER_new"
```

---

## MCP Tool 调用频率统计

根据实际使用场景，各方法的调用频率大致如下：

| MCP Tool | 调用频率 | 说明 |
|---------|---------|------|
| `order-create-order-with-user` | ⭐⭐⭐⭐⭐ | 最高频，用户下单的核心功能 |
| `order-get-orders-by-user` | ⭐⭐⭐⭐ | 高频，用户经常查看历史订单 |
| `order-get-order` | ⭐⭐⭐ | 中频，查询单个订单详情 |
| `order-get-order-by-user` | ⭐⭐⭐ | 中频，带安全验证的查询 |
| `order-update-remark` | ⭐⭐ | 低频，偶尔修改备注 |
| `order-delete-order` | ⭐ | 最低频，用户很少删除订单 |

---

## 安全考虑

### 需要用户ID验证的方法

以下方法需要同时提供 `userId` 和 `orderId`，确保用户只能操作自己的订单：

1. **`order-get-order-by-user`** - 查询订单（带用户验证）
2. **`order-delete-order`** - 删除订单（必须验证用户身份）
3. **`order-update-remark`** - 更新备注（必须验证用户身份）

### 不需要用户ID的方法

以下方法只需要订单ID，但系统内部会进行权限检查：

1. **`order-get-order`** - 查询订单（如果系统需要，可以从会话中获取用户ID）
2. **`order-get-orders-by-user`** - 查询订单列表（需要用户ID，但通常从会话获取）

---

## 总结

OrderMCPServer 提供了完整的订单生命周期管理：

1. **创建** - `order-create-order-with-user` - 用户下单
2. **查询** - `order-get-order` / `order-get-order-by-user` / `order-get-orders-by-user` - 查看订单
3. **修改** - `order-update-remark` - 更新备注（注意：不支持修改产品）
4. **删除** - `order-delete-order` - 取消订单
5. **换产品** - `order-delete-order` + `order-create-order-with-user` - 删除旧订单并创建新订单

所有方法都围绕用户的实际需求设计，支持完整的订单管理流程。

