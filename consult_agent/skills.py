"""
咨询智能体的 Skills 定义
无权限分级，所有用户使用相同技能集
"""

CONSULT_SKILLS = [
    {
        "type": "function",
        "function": {
            "name": "consult_search_knowledge",
            "description": "根据用户查询内容检索云边奶茶铺知识库，包括产品信息、店铺介绍等。支持模糊匹配，可以查询产品名称、描述、分类、茶底等信息。当用户询问产品介绍、口感、冲泡方法、活动信息、品牌介绍时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询内容，可以是产品名称、产品描述关键词、店铺信息关键词等，例如：云边茉莉、经典奶茶、品牌介绍等"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_get_product_info",
            "description": "获取指定产品的详细信息，包括产品描述、价格和当前库存状态。帮助用户了解产品的具体信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "productName": {
                        "type": "string",
                        "description": "产品名称，必须是云边奶茶铺的现有产品，如：云边茉莉、桂花云露、云雾观音、红茶拿铁、抹茶相思"
                    }
                },
                "required": ["productName"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_search_products",
            "description": "根据产品名称进行模糊搜索，返回匹配的产品列表。支持部分名称搜索，例如搜索'云'可以找到所有包含'云'字的产品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "productName": {
                        "type": "string",
                        "description": "产品名称关键词，支持模糊匹配，例如：云、茉莉、乌龙等"
                    }
                },
                "required": ["productName"]
            }
        }
    }
]
