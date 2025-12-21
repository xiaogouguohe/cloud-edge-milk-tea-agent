"""
数据库配置
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库类型：sqlite 或 mysql
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# SQLite 配置
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", None)  # None 表示使用默认路径

# MySQL 配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "multi_agent_demo")
