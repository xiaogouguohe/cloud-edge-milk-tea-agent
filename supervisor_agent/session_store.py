"""
短期记忆持久化 - 会话历史存储

业界常见方案：Redis（高并发）、SQLite（轻量/单机）、PostgreSQL（大规模）。
本实现使用 SQLite，与项目现有 data/ 目录一致，无需额外服务，进程退出后可恢复。
"""
import json

# 持久化时保留最近 N 条消息，避免无限增长（system 消息始终保留）
MAX_HISTORY_MESSAGES = 50
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# 默认存储路径：项目 data 目录
DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "chat_sessions.db"


def _get_conn():
    """获取数据库连接"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_table(conn: sqlite3.Connection):
    """初始化表结构。session_id 格式为 {user_id}_{chat_id}，可解析出 user_id/chat_id"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            role TEXT,
            history_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated 
        ON chat_sessions(updated_at)
    """)
    conn.commit()


def save_session(
    session_id: str,
    user_id: str,
    chat_id: str,
    role: Optional[str],
    history: List[Dict[str, str]],
) -> None:
    """持久化会话（短期记忆），超出部分截断保留最近 N 条。user_id/chat_id 仅用于 API 兼容，不落库。"""
    conn = _get_conn()
    try:
        _init_table(conn)
        # 保留 system 消息 + 最近 N-1 条
        if len(history) > MAX_HISTORY_MESSAGES:
            system_msgs = [h for h in history if h.get("role") == "system"]
            rest = [h for h in history if h.get("role") != "system"][-(MAX_HISTORY_MESSAGES - len(system_msgs)):]
            history = system_msgs + rest
        history_json = json.dumps(history, ensure_ascii=False)
        conn.execute(
            """
            INSERT INTO chat_sessions (session_id, role, history_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                role = excluded.role,
                history_json = excluded.history_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session_id, role, history_json),
        )
        conn.commit()
    finally:
        conn.close()


def _parse_session_id(session_id: str) -> Tuple[str, str]:
    """从 session_id 解析出 user_id, chat_id。格式为 {user_id}_{chat_id}"""
    if "_" in session_id:
        parts = session_id.split("_", 1)
        return parts[0], parts[1]
    return session_id, "default"


def load_session(session_id: str) -> Optional[Tuple[str, str, Optional[str], List[Dict[str, str]]]]:
    """
    从持久化加载会话。
    Returns: (user_id, chat_id, role, history) 或 None
    """
    conn = _get_conn()
    try:
        _init_table(conn)
        row = conn.execute(
            "SELECT role, history_json FROM chat_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        history = json.loads(row["history_json"]) if row["history_json"] else []
        user_id, chat_id = _parse_session_id(session_id)
        return (user_id, chat_id, row["role"], history)
    except (json.JSONDecodeError, sqlite3.Error):
        return None
    finally:
        conn.close()


def delete_session(session_id: str) -> bool:
    """删除会话持久化数据"""
    conn = _get_conn()
    try:
        _init_table(conn)
        cursor = conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
