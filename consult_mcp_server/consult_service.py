"""
咨询服务层 - 业务逻辑处理
参考原项目的 ConsultService
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    db_manager = None
    print(f"[ConsultService] 警告: 无法初始化数据库: {str(e)}", file=sys.stderr, flush=True)


class ConsultService:
    """咨询服务 - 处理产品咨询相关的业务逻辑"""
    
    def __init__(self):
        """初始化咨询服务"""
        self.db = db_manager
        
        # 初始化本地 RAG 服务（使用 DashScope Embeddings，不依赖 LangChain）
        try:
            from rag.rag_service import RAGService
            self.rag_service = RAGService()
            # 加载知识库
            self.rag_service.load_knowledge_base()
            self.rag_available = True
            print("[ConsultService] 本地 RAG 服务已启用", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[ConsultService] 本地 RAG 服务初始化失败: {str(e)}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            self.rag_service = None
            self.rag_available = False
    
    def search_knowledge(self, query: str) -> str:
        """
        根据查询内容检索知识库
        优先级：DashScope RAG > 数据库查询
        
        Args:
            query: 查询内容
            
        Returns:
            检索结果
        """
        # 优先级 1: 使用 DashScope RAG（如果可用）
        if self.rag_available and self.rag_service:
            try:
                result = self.rag_service.search(query)
                # 如果 RAG 返回有效结果（不是错误信息），直接返回
                if result and "未找到相关资料" not in result and "失败" not in result and "异常" not in result:
                    return result
                # 如果 RAG 未找到结果，回退到数据库查询
                print(f"[ConsultService] RAG 未找到结果，回退到数据库查询", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[ConsultService] RAG 检索失败，回退到数据库查询: {str(e)}", file=sys.stderr, flush=True)
        
        # 优先级 2: 回退到数据库查询
        return self._search_from_database(query)
    
    def _search_from_database(self, query: str) -> str:
        """
        从数据库查询产品信息（回退方案）
        
        Args:
            query: 查询内容
            
        Returns:
            检索结果
        """
        if not self.db:
            return f"知识库检索失败: 数据库不可用，查询内容：{query}"
        
        try:
            # 从产品表中搜索匹配的产品
            # 支持按名称、描述搜索
            if self.db.db_type == "sqlite":
                sql = """
                    SELECT name, description, price, stock, shelf_time, preparation_time
                    FROM products
                    WHERE status = 1
                    AND (name LIKE ? OR description LIKE ?)
                    LIMIT 10
                """
                params = (f"%{query}%", f"%{query}%")
            else:
                sql = """
                    SELECT name, description, price, stock, shelf_time, preparation_time
                    FROM products
                    WHERE status = 1
                    AND (name LIKE %s OR description LIKE %s)
                    LIMIT 10
                """
                params = (f"%{query}%", f"%{query}%")
            
            results = self.db.fetch_all(sql, params)
            
            if not results:
                return f"未找到相关资料，查询内容：{query}"
            
            # 整合结果
            result_text = f"知识库检索结果（查询：{query}）:\n\n"
            for i, product in enumerate(results, 1):
                result_text += f"{i}. {product['name']}\n"
                result_text += f"   描述: {product['description']}\n"
                result_text += f"   价格: ¥{product['price']:.2f}\n"
                result_text += f"   库存: {product['stock']}件\n"
                result_text += f"   保质期: {product['shelf_time']}分钟\n"
                result_text += f"   制作时间: {product['preparation_time']}分钟\n\n"
            
            return result_text.strip()
        except Exception as e:
            error_msg = f"知识库检索失败: {str(e)}，查询内容：{query}"
            print(f"[ConsultService] {error_msg}", file=sys.stderr, flush=True)
            return error_msg
    
    def get_all_products(self) -> List[Dict]:
        """
        获取所有可用产品列表
        
        Returns:
            产品列表
        """
        if not self.db:
            return []
        
        try:
            if self.db.db_type == "sqlite":
                sql = "SELECT * FROM products WHERE status = 1 ORDER BY name"
            else:
                sql = "SELECT * FROM products WHERE status = 1 ORDER BY name"
            
            products = self.db.fetch_all(sql)
            return products
        except Exception as e:
            print(f"[ConsultService] 获取产品列表失败: {str(e)}", file=sys.stderr, flush=True)
            return []
    
    def get_product_by_name(self, product_name: str) -> Optional[Dict]:
        """
        根据产品名称获取产品详情
        
        Args:
            product_name: 产品名称
            
        Returns:
            产品信息
        """
        if not self.db:
            return None
        
        try:
            if self.db.db_type == "sqlite":
                sql = "SELECT * FROM products WHERE name = ? AND status = 1"
                params = (product_name,)
            else:
                sql = "SELECT * FROM products WHERE name = %s AND status = 1"
                params = (product_name,)
            
            product = self.db.fetch_one(sql, params)
            return product
        except Exception as e:
            print(f"[ConsultService] 获取产品详情失败: {str(e)}", file=sys.stderr, flush=True)
            return None
    
    def search_products_by_name(self, product_name: str) -> List[Dict]:
        """
        根据产品名称模糊搜索产品列表
        
        Args:
            product_name: 产品名称关键词
            
        Returns:
            产品列表
        """
        if not self.db:
            return []
        
        try:
            if self.db.db_type == "sqlite":
                sql = "SELECT * FROM products WHERE name LIKE ? AND status = 1 ORDER BY name"
                params = (f"%{product_name}%",)
            else:
                sql = "SELECT * FROM products WHERE name LIKE %s AND status = 1 ORDER BY name"
                params = (f"%{product_name}%",)
            
            products = self.db.fetch_all(sql, params)
            return products
        except Exception as e:
            print(f"[ConsultService] 搜索产品失败: {str(e)}", file=sys.stderr, flush=True)
            return []
    
    def format_product_response(self, product: Dict) -> str:
        """
        格式化产品信息为用户友好的字符串
        
        Args:
            product: 产品信息字典
            
        Returns:
            格式化的字符串
        """
        return f"""产品信息:
名称: {product.get('name', '')}
描述: {product.get('description', '')}
价格: ¥{product.get('price', 0):.2f}
库存: {product.get('stock', 0)}件
保质期: {product.get('shelf_time', 30)}分钟
制作时间: {product.get('preparation_time', 5)}分钟"""
