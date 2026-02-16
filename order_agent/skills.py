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
CUSTOMER_SKILLS = BASE_SKILLS + []

# --- 店员技能 (Staff) ---
STAFF_SKILLS = CUSTOMER_SKILLS + []

# 统一导出
SKILLS_BY_ROLE = {
    "base": BASE_SKILLS,      # 未登录/基础权限
    "customer": CUSTOMER_SKILLS,
    "staff": STAFF_SKILLS
}
