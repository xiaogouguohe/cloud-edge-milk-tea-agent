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
        
        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                phone VARCHAR(20),
                email VARCHAR(100),
                nickname VARCHAR(50),
                status TINYINT DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建产品表
        if self.db_type == "sqlite":
            cursor.execute("""
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
                )
            """)
        else:  # MySQL
            cursor.execute("""
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
                )
            """)
        
        # 创建订单表（主表，只存储订单基本信息）
        if self.db_type == "sqlite":
            cursor.execute("""
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
                )
            """)
        else:  # MySQL
            cursor.execute("""
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
                )
            """)
        
        # 创建订单项表（从表，存储订单中的每个产品）
        if self.db_type == "sqlite":
            cursor.execute("""
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
                )
            """)
        else:  # MySQL
            cursor.execute("""
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
        # self._init_products()  # 注释掉，避免每次创建表都初始化产品
    
    def _init_products(self):
        """初始化产品数据"""
        cursor = self.connection.cursor()
        
        # 检查是否已有产品数据
        if self.db_type == "sqlite":
            cursor.execute("SELECT COUNT(*) as count FROM products")
        else:
            cursor.execute("SELECT COUNT(*) as count FROM products")
        
        result = cursor.fetchone()
        count = result[0] if isinstance(result, dict) else result['count'] if hasattr(result, '__getitem__') else 0
        
        if count > 0:
            return  # 已有数据，不重复插入
        
        # 插入默认产品
        products = [
            ("云边茉莉", "优质茉莉花茶，清香淡雅", 18.00, 100),
            ("桂花云露", "桂花乌龙茶，香气浓郁", 20.00, 80),
            ("云雾观音", "铁观音茶，回甘悠长", 22.00, 60),
            ("珍珠奶茶", "经典珍珠奶茶", 15.00, 120),
            ("红豆奶茶", "红豆奶茶，香甜可口", 16.00, 100),
        ]
        
        for name, desc, price, stock in products:
            try:
                if self.db_type == "sqlite":
                    cursor.execute("""
                        INSERT INTO products (name, description, price, stock, status)
                        VALUES (?, ?, ?, ?, 1)
                    """, (name, desc, price, stock))
                else:
                    cursor.execute("""
                        INSERT INTO products (name, description, price, stock, status)
                        VALUES (%s, %s, %s, %s, 1)
                    """, (name, desc, price, stock))
            except Exception:
                pass  # 如果已存在则跳过
        
        self.connection.commit()
    
    def execute(self, query: str, params: tuple = None) -> Any:
        """执行 SQL 查询"""
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.connection.commit()
        return cursor
    
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
