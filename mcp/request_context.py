"""
请求上下文 - 用于在一次 MCP 工具调用中传递 request_id，串联访问日志与回源日志
"""
import contextvars
import uuid

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "mcp_request_id", default=""
)


def set_request_id(rid: str = None) -> str:
    """设置当前请求的 request_id，返回实际使用的 id"""
    rid = rid or str(uuid.uuid4())[:12]
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """获取当前请求的 request_id"""
    try:
        return _request_id_var.get() or ""
    except LookupError:
        return ""
