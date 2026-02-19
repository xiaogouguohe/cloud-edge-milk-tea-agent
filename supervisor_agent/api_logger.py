"""
Supervisor API 日志 - 访问日志 + 回源日志
每条日志一行，字段通过 \\t 分隔
访问日志写入 logs/supervisor_access.log，回源日志写入 logs/supervisor_backend.log
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOGS_DIR.mkdir(exist_ok=True)
_ACCESS_FILE = open(_LOGS_DIR / "supervisor_access.log", "a", encoding="utf-8")
_BACKEND_FILE = open(_LOGS_DIR / "supervisor_backend.log", "a", encoding="utf-8")


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _safe(s: Optional[str]) -> str:
    """字段值中的 tab 和换行替换为空格，避免破坏格式"""
    if s is None:
        return ""
    return str(s).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def log_access(
    req_id: str,
    method: str,
    path: str,
    status: str,
    user_id: str = "",
    chat_id: str = "",
    duration_ms: Optional[int] = None,
) -> None:
    """
    访问日志：记录入站请求，写入 logs/supervisor_access.log
    字段：type	req_id	timestamp	method	path	status	user_id	chat_id	duration_ms
    """
    parts = ["ACCESS", req_id, _ts(), method, path, status, _safe(user_id), _safe(chat_id)]
    if duration_ms is not None:
        parts.append(str(duration_ms))
    _ACCESS_FILE.write("\t".join(parts) + "\n")
    _ACCESS_FILE.flush()


def log_backend(
    req_id: str,
    target: str,
    operation: str,
    status: str,
    duration_ms: Optional[int] = None,
    error: str = "",
) -> None:
    """
    回源日志：记录调用下游服务，写入 logs/supervisor_backend.log
    字段：type	req_id	timestamp	target	operation	status	duration_ms	error
    """
    parts = ["BACKEND", req_id, _ts(), target, operation, status]
    if duration_ms is not None:
        parts.append(str(duration_ms))
    else:
        parts.append("")
    parts.append(_safe(error))
    _BACKEND_FILE.write("\t".join(parts) + "\n")
    _BACKEND_FILE.flush()
