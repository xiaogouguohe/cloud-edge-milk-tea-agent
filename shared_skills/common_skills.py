"""
公共技能定义 (Common Skills)
这些技能可以被多个 Agent 共享，如查询菜单、查询门店信息等。
"""

COMMON_SKILLS = [
    {
        "type": "function",
        "function": {
            "name": "common_get_menu",
            "description": "获取奶茶店当前的菜单列表和价格。",
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
            "name": "common_get_shop_info",
            "description": "获取奶茶店的营业时间、地址和联系电话。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
