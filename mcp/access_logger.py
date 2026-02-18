"""
MCP 访问日志 - 记录工具调用请求与响应
"""
import sys
import json
from typing import Any, Dict


def _get_request_id() -> str:
    try:
        from mcp.request_context import get_request_id
        return get_request_id()
    except ImportError:
        return ""


def log_access(tool_name: str, params: Dict, status: str, result: Any = None, error: str = None) -> None:
    """访问日志：记录 MCP 工具调用请求与响应"""
    rid = _get_request_id()
    payload = {"request_id": rid, "tool": tool_name, "params": params, "status": status}
    if error:
        payload["error"] = error
    if result is not None:
        s = str(result)
        payload["result_preview"] = s[:200] + "..." if len(s) > 200 else s
    print(f"[ACCESS] {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr, flush=True)
