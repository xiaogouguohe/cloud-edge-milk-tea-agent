"""
数据库管理器 - 支持 SQLite 和 MySQL
"""
import os
import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path

# 尝试导入 MySQL 相关库（可选）
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


class DatabaseManager:
    """数据库管理器 - 支持 SQLite 和 MySQL"""
    
    def __init__(self, db_type: str = "sqlite", **kwargs):
        """
        初始化数据库管理器
        
        Args:
            db_type: 数据库类型，"sqlite" 或 "mysql"
            **kwargs: 数据库连接参数
                - SQLite: db_path (可选，默认: ./data/milk_tea.db)
                - MySQL: host, port, user, password, database
        """
        self.db_type = db_type.lower()
        self.connection = None
        
        if self.db_type == "sqlite":
            self._init_sqlite(**kwargs)
        elif self.db_type == "mysql":
            if not MYSQL_AVAILABLE:
                raise ImportError("请安装 pymysql: pip install pymysql")
            self._init_mysql(**kwargs)
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        
        # 初始化数据库表
        self._init_tables()
    
    def _init_sqlite(self, db_path: Optional[str] = None):
        """初始化 SQLite 连接"""
        if db_path is None:
            # 默认路径：项目根目录下的 data 文件夹
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "milk_tea.db")
        
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # 返回字典格式的结果
    
    def _init_mysql(self, host: str = "localhost", port: int = 3306, 
                    user: str = "root", password: str = "", 
                    database: str = "multi_agent_demo", **kwargs):
        """初始化 MySQL 连接"""
        self.connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            **kwargs
        )
    
    def _init_tables(self):
        """初始化数据库表结构"""
        cursor = self.connection.cursor()
        
        # 创建用户表（精简版：id, username，供 orders 外键引用）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE
            )
        """)
        
        # 创建产品表（精简版：id, name, description, price, stock）
        if self.db_type == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    price DECIMAL(10,2) NOT NULL,
                    stock INT DEFAULT 0
                )
            """)
        else:  # MySQL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    price DECIMAL(10,2) NOT NULL,
                    stock INT DEFAULT 0
                )
            """)
        
        # 创建订单表（主表，精简版：order_id, user_id, total_price, created_at）
        if self.db_type == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id VARCHAR(50) NOT NULL UNIQUE,
                    user_id BIGINT NOT NULL,
                    total_price DECIMAL(10,2) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        else:  # MySQL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    order_id VARCHAR(50) NOT NULL UNIQUE,
                    user_id BIGINT NOT NULL,
                    total_price DECIMAL(10,2) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
        
        # 创建订单项表（精简版：同一产品不同甜度/冰量分多条）
        if self.db_type == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id VARCHAR(50) NOT NULL,
                    product_id BIGINT NOT NULL,
                    sweetness TINYINT NOT NULL,
                    ice_level TINYINT NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    unit_price DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
        else:  # MySQL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    order_id VARCHAR(50) NOT NULL,
                    product_id BIGINT NOT NULL,
                    sweetness TINYINT NOT NULL,
                    ice_level TINYINT NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    unit_price DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
                )
            """)
        
        # 创建反馈表
        if self.db_type == "sqlite":
            cursor.execute("""
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
                )
            """)
        else:  # MySQL
            cursor.execute("""
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
                )
            """)
        
        self.connection.commit()
        # 不再初始化产品数据，由测试或业务自行写入
    
    def execute(self, query: str, params: tuple = None) -> Any:
        """执行 SQL 查询（自动提交）"""
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.connection.commit()
        return cursor

    def execute_no_commit(self, query: str, params: tuple = None) -> Any:
        """执行 SQL 查询（不提交，用于事务内）"""
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor

    def run_transaction(self, callback):
        """
        在事务中执行回调。成功则提交，异常则回滚。
        callback(db) 中应使用 db.execute_no_commit() 执行操作。
        """
        try:
            result = callback(self)
            self.connection.commit()
            return result
        except Exception:
            self.connection.rollback()
            raise
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """执行查询并返回一条记录"""
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        row = cursor.fetchone()
        if row:
            if self.db_type == "sqlite":
                return dict(row)
            else:
                return row
        return None
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询并返回所有记录"""
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        rows = cursor.fetchall()
        if self.db_type == "sqlite":
            return [dict(row) for row in rows]
        else:
            return rows
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
