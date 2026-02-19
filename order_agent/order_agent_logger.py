"""
Order Agent 日志 - 访问日志 + 回源日志 + LLM 交互日志
每条日志一行，字段通过 \\t 分隔
- 访问日志: logs/order_agent_access.log
- 回源日志: logs/order_agent_backend.log
- LLM 交互: logs/order_agent_llm.log
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOGS_DIR.mkdir(exist_ok=True)
_ACCESS_FILE = open(_LOGS_DIR / "order_agent_access.log", "a", encoding="utf-8")
_BACKEND_FILE = open(_LOGS_DIR / "order_agent_backend.log", "a", encoding="utf-8")
_LLM_FILE = open(_LOGS_DIR / "order_agent_llm.log", "a", encoding="utf-8")


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _safe(s: Optional[str]) -> str:
    """字段值中的 tab 和换行替换为空格，避免破坏格式"""
    if s is None:
        return ""
    return str(s).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _field(s: Optional[str]) -> str:
    """空值用 '-' 占位"""
    v = _safe(s) if s is not None else ""
    return "-" if not v else v


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
    访问日志：记录入站请求（A2A），写入 logs/order_agent_access.log
    字段：req_id	timestamp	method	path	status	user_id	chat_id	duration_ms
    """
    parts = [_field(req_id), _ts(), _field(method), _field(path), _field(status), _field(user_id), _field(chat_id)]
    parts.append(_field(str(duration_ms)) if duration_ms is not None else "-")
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
    回源日志：记录调用 MCP 等下游服务，写入 logs/order_agent_backend.log
    字段：req_id	timestamp	target	operation	status	duration_ms	error
    """
    parts = [_field(req_id), _ts(), _field(target), _field(operation), _field(status)]
    parts.append(_field(str(duration_ms)) if duration_ms is not None else "-")
    parts.append(_field(error))
    _BACKEND_FILE.write("\t".join(parts) + "\n")
    _BACKEND_FILE.flush()


def _truncate(s: str, max_len: int = 2000) -> str:
    """截断并安全化，用于 input/output 字段；空值返回 '-'"""
    s = _safe(s)
    if not s:
        return "-"
    return s[:max_len] + ("..." if len(s) > max_len else "")


def log_llm(
    req_id: str,
    operation: str,
    model: str,
    status: str,
    duration_ms: Optional[int] = None,
    error: str = "",
    input_content: Any = "",
    output_content: Any = "",
) -> None:
    """
    LLM 交互日志：记录与 DashScope 等 LLM 的调用，写入 logs/order_agent_llm.log
    字段：req_id	timestamp	operation	model	status	duration_ms	error	input	output
    """
    parts = [_field(req_id), _ts(), _field(operation), _field(model), _field(status)]
    parts.append(_field(str(duration_ms)) if duration_ms is not None else "-")
    parts.append(_field(error))
    inp = input_content if isinstance(input_content, str) else json.dumps(input_content, ensure_ascii=False)
    out = output_content if isinstance(output_content, str) else json.dumps(output_content, ensure_ascii=False)
    parts.append(_truncate(inp))
    parts.append(_truncate(out))
    _LLM_FILE.write("\t".join(parts) + "\n")
    _LLM_FILE.flush()
