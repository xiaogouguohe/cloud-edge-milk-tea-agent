"""
MCP Server 日志 - 访问日志 + 回源日志，通过 request_id 串联
工业实践：访问日志记录请求/响应，回源日志记录 DB 等后端操作
"""
import sys
import json
from typing import Any, Dict

# 延迟导入避免循环依赖
def _get_request_id() -> str:
    try:
        from mcp.request_context import get_request_id
        return get_request_id()
    except ImportError:
        return ""


def _log(prefix: str, **kwargs) -> None:
    """输出结构化日志到 stderr"""
    rid = _get_request_id()
    parts = [f"[{prefix}]", f"request_id={rid}"]
    for k, v in kwargs.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        parts.append(f"{k}={v}")
    msg = " ".join(parts)
    print(msg, file=sys.stderr, flush=True)


def log_access(tool_name: str, params: Dict, status: str, result: Any = None, error: str = None) -> None:
    """访问日志：记录 MCP 工具调用请求与响应"""
    extra = {"tool": tool_name, "params": params, "status": status}
    if error:
        extra["error"] = error
    if result is not None:
        s = str(result)
        extra["result_preview"] = s[:200] + "..." if len(s) > 200 else s
    _log("ACCESS", **extra)


def log_backend(op: str, **details) -> None:
    """回源日志：记录数据库读写等后端操作"""
    import json
    rid = _get_request_id()
    parts = [f"[BACKEND] request_id={rid} op={op}"]
    for k, v in details.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        parts.append(f"{k}={v}")
    print(" ".join(parts), file=sys.stderr, flush=True)
