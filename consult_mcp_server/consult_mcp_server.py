"""
咨询 MCP Server - 提供咨询相关的工具
参考原项目的 ConsultTools
"""
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import MCPServer, Tool, ToolDefinition
from .consult_service import ConsultService

# 尝试导入数据库管理器
try:
    from database.db_manager import DatabaseManager
    from database.config import DB_TYPE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
    
    if DB_TYPE == "mysql":
        db_manager = DatabaseManager(
            db_type="mysql",
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
    else:
        db_manager = DatabaseManager(db_type="sqlite")
    
    # 确保数据库表已初始化
    if db_manager:
        db_manager.init_tables()
        db_manager.init_products()
        print(f"[ConsultMCPServer] 数据库初始化完成. 路径: {db_manager.db_path if db_manager.db_type == 'sqlite' else MYSQL_DATABASE}", file=sys.stderr, flush=True)
except Exception as e:
    print(f"[ConsultMCPServer] 警告: 无法初始化数据库，将使用内存存储: {str(e)}", file=sys.stderr, flush=True)
    db_manager = None


class ConsultMCPServer:
    """咨询 MCP Server - 提供咨询相关的工具"""
    
    def __init__(self, port: int = 10003):
        """
        初始化咨询 MCP Server
        
        Args:
            port: 服务端口
        """
        self.port = port
        
        # 初始化服务层
        self.consult_service = ConsultService()
        
        # 创建 MCP Server
        self.mcp_server = MCPServer(server_name="consult-mcp-server", port=port)
        
        # 注册工具
        self._register_tools()
    
    def _register_tools(self):
        """注册所有咨询相关的工具"""
        
        # 1. 知识库检索工具
        self.mcp_server.register_tool_func(
            name="consult-search-knowledge",
            description="根据用户查询内容检索云边奶茶铺知识库，包括产品信息、店铺介绍等。支持模糊匹配，可以查询产品名称、描述、分类、茶底等信息。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询内容，可以是产品名称、产品描述关键词、店铺信息关键词等，例如：云边茉莉、经典奶茶、品牌介绍等"
                    }
                },
                "required": ["query"]
            },
            handler=self._search_knowledge
        )
        
        # 2. 获取所有产品列表工具
        self.mcp_server.register_tool_func(
            name="consult-get-products",
            description="获取云边奶茶铺所有可用产品的完整列表，包括产品名称、详细描述、当前价格和库存数量。帮助用户了解可选择的奶茶产品。",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._get_products
        )
        
        # 3. 获取产品详细信息工具
        self.mcp_server.register_tool_func(
            name="consult-get-product-info",
            description="获取指定产品的详细信息，包括产品描述、价格和当前库存状态。帮助用户了解产品的具体信息。",
            parameters={
                "type": "object",
                "properties": {
                    "productName": {
                        "type": "string",
                        "description": "产品名称，必须是云边奶茶铺的现有产品，如：云边茉莉、桂花云露、云雾观音、红茶拿铁、抹茶相思"
                    }
                },
                "required": ["productName"]
            },
            handler=self._get_product_info
        )
        
        # 4. 根据产品名称模糊搜索产品工具
        self.mcp_server.register_tool_func(
            name="consult-search-products",
            description="根据产品名称进行模糊搜索，返回匹配的产品列表。支持部分名称搜索，例如搜索'云'可以找到所有包含'云'字的产品。",
            parameters={
                "type": "object",
                "properties": {
                    "productName": {
                        "type": "string",
                        "description": "产品名称关键词，支持模糊匹配，例如：云、茉莉、乌龙等"
                    }
                },
                "required": ["productName"]
            },
            handler=self._search_products
        )
    
    def _search_knowledge(self, query: str) -> str:
        """工具：知识库检索"""
        print(f"[ConsultMCPServer] 调用 _search_knowledge, query: {query}", file=sys.stderr, flush=True)
        try:
            result = self.consult_service.search_knowledge(query)
            return result
        except Exception as e:
            print(f"[ConsultMCPServer] _search_knowledge 失败: {str(e)}", file=sys.stderr, flush=True)
            return f"知识库检索失败: {str(e)}"
    
    def _get_products(self) -> str:
        """工具：获取所有产品列表"""
        print(f"[ConsultMCPServer] 调用 _get_products", file=sys.stderr, flush=True)
        try:
            products = self.consult_service.get_all_products()
            if not products:
                return "当前没有任何可用产品。"
            
            result = f"云边奶茶铺可用产品列表（共 {len(products)} 个产品）:\n\n"
            for product in products:
                result += f"- {product['name']}: {product['description']}, 价格: ¥{product['price']:.2f}, 库存: {product['stock']}件\n"
            
            return result.strip()
        except Exception as e:
            print(f"[ConsultMCPServer] _get_products 失败: {str(e)}", file=sys.stderr, flush=True)
            return f"获取产品列表失败: {str(e)}"
    
    def _get_product_info(self, productName: str) -> str:
        """工具：获取产品详细信息"""
        print(f"[ConsultMCPServer] 调用 _get_product_info, productName: {productName}", file=sys.stderr, flush=True)
        try:
            product = self.consult_service.get_product_by_name(productName)
            if not product:
                return f"产品不存在或已下架: {productName}"
            
            return self.consult_service.format_product_response(product)
        except Exception as e:
            print(f"[ConsultMCPServer] _get_product_info 失败: {str(e)}", file=sys.stderr, flush=True)
            return f"获取产品信息失败: {str(e)}"
    
    def _search_products(self, productName: str) -> str:
        """工具：根据产品名称模糊搜索产品"""
        print(f"[ConsultMCPServer] 调用 _search_products, productName: {productName}", file=sys.stderr, flush=True)
        try:
            products = self.consult_service.search_products_by_name(productName)
            if not products:
                return f"未找到匹配的产品: {productName}"
            
            result = f"搜索结果（共 {len(products)} 个产品）:\n\n"
            for product in products:
                result += f"- {product['name']}: {product['description']}, 价格: ¥{product['price']:.2f}, 库存: {product['stock']}件\n"
            
            return result.strip()
        except Exception as e:
            print(f"[ConsultMCPServer] _search_products 失败: {str(e)}", file=sys.stderr, flush=True)
            return f"搜索产品失败: {str(e)}"
    
    def run(self, host: str = '0.0.0.0', debug: bool = False):
        """
        启动 MCP 服务
        
        Args:
            host: 监听地址
            debug: 是否开启调试模式
        """
        print(f"ConsultMCPServer 启动在 http://{host}:{self.port}", file=sys.stderr, flush=True)
        self.mcp_server.run(host=host, port=self.port, debug=debug)
