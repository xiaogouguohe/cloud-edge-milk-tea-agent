"""
数据库模块
"""
try:
    from .db_manager import DatabaseManager
    __all__ = ['DatabaseManager']
except ImportError:
    __all__ = []
