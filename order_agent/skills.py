"""
订单智能体的 Skills 定义
支持角色权限分级：customer, staff, admin
"""

# --- 基础通用技能 (所有角色共享，包括未登录) ---
BASE_SKILLS = [
    {
        "type": "function",
        "function": {
            "name": "order_get_menu",
            "description": "获取奶茶店当前的完整菜单列表、价格及库存状态。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "order_get_product_info",
            "description": "获取某个特定奶茶产品的详细信息，包括价格和是否有货。",
            "parameters": {
                "type": "object",
                "properties": {
                    "productName": {"type": "string", "description": "奶茶名称"}
                },
                "required": ["productName"]
            }
        }
    }
]

# --- 顾客技能 (Customer) ---
CUSTOMER_SKILLS = BASE_SKILLS + [
    {
        "type": "function",
        "function": {
            "name": "order_get_orders_by_user",
            "description": "查询用户的历史订单列表。当用户询问「我的订单」「订单记录」「历史订单」「查订单」时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {"userId": {"type": "integer", "description": "用户ID"}},
                "required": ["userId"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "order_create_order",
            "description": "创建奶茶订单。当用户想要下单、点单或购买时使用此工具。同一产品若糖度或冰量不同，需拆成多条 items（每条对应一种规格）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "userId": {"type": "integer", "description": "用户ID"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "productName": {"type": "string", "description": "奶茶名称"},
                                "sweetness": {"type": "string", "enum": ["无糖", "微糖", "半糖", "少糖", "标准糖"]},
                                "iceLevel": {"type": "string", "enum": ["去冰", "少冰", "正常冰", "温", "热"]},
                                "quantity": {"type": "integer", "default": 1}
                            },
                            "required": ["productName", "sweetness", "iceLevel"]
                        }
                    }
                },
                "required": ["userId", "items"]
            }
        }
    }
]

# --- 店员技能 (Staff) ---
STAFF_SKILLS = CUSTOMER_SKILLS + [
    {
        "type": "function",
        "function": {
            "name": "order_propose_product_update",
            "description": "提议修改产品的单价或库存。不执行修改，仅返回当前值与拟修改值，供前端弹出确认框。当店员要求修改产品价格或库存时，必须先调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "productName": {"type": "string", "description": "产品名称"},
                    "price": {"type": "number", "description": "拟修改的单价（不修改则不传）"},
                    "stock": {"type": "integer", "description": "拟修改的库存（不修改则不传）"},
                },
                "required": ["productName"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "order_update_product",
            "description": "执行产品修改，更新数据库中的单价或库存。应在用户在前端确认后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "productName": {"type": "string", "description": "产品名称"},
                    "price": {"type": "number", "description": "新单价（不修改则不传）"},
                    "stock": {"type": "integer", "description": "新库存（不修改则不传）"},
                },
                "required": ["productName"]
            }
        }
    }
]

# 统一导出
SKILLS_BY_ROLE = {
    "base": BASE_SKILLS,      # 未登录/基础权限
    "customer": CUSTOMER_SKILLS,
    "staff": STAFF_SKILLS
}
