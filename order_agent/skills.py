"""
订单智能体的 Skills 定义
支持角色权限分级：customer, staff, admin
"""

# --- 基础通用技能 (所有角色共享) ---
BASE_SKILLS = [
    {
        "type": "function",
        "function": {
            "name": "order_get_menu",
            "description": "获取奶茶店当前的菜单列表和价格。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# --- 顾客技能 (Customer) ---
CUSTOMER_SKILLS = BASE_SKILLS + [
    {
        "type": "function",
        "function": {
            "name": "order_create_order",
            "description": "创建奶茶订单。当用户想要下单、点单或购买时使用此工具。",
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
    },
    {
        "type": "function",
        "function": {
            "name": "order_get_orders_by_user",
            "description": "查询指定用户的所有历史订单。",
            "parameters": {
                "type": "object",
                "properties": {
                    "userId": {"type": "integer", "description": "用户ID"}
                },
                "required": ["userId"]
            }
        }
    }
]

# --- 店员技能 (Staff) ---
STAFF_SKILLS = CUSTOMER_SKILLS + [
    {
        "type": "function",
        "function": {
            "name": "order_update_order_status",
            "description": "更新订单状态（如：制作中、待取餐、已完成）。仅限店员操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "orderId": {"type": "string", "description": "订单ID"},
                    "status": {"type": "string", "enum": ["making", "ready", "completed"], "description": "新状态"}
                },
                "required": ["orderId", "status"]
            }
        }
    }
]

# --- 管理员技能 (Admin) ---
ADMIN_SKILLS = STAFF_SKILLS + [
    {
        "type": "function",
        "function": {
            "name": "order_delete_order",
            "description": "删除或取消指定的订单。仅限管理员操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "userId": {"type": "integer", "description": "用户ID"},
                    "orderId": {"type": "string", "description": "订单ID"}
                },
                "required": ["userId", "orderId"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "order_process_refund",
            "description": "处理订单退款。仅限管理员执行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "orderId": {"type": "string", "description": "订单ID"},
                    "reason": {"type": "string", "description": "退款原因"}
                },
                "required": ["orderId", "reason"]
            }
        }
    }
]

# 统一导出
SKILLS_BY_ROLE = {
    "customer": CUSTOMER_SKILLS,
    "staff": STAFF_SKILLS,
    "admin": ADMIN_SKILLS
}
