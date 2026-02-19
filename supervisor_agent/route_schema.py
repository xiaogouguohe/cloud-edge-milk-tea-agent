"""
监督者智能体 - 路由意图识别的结构化输出定义
使用 Pydantic + Function Calling 实现 AgentScope 式的结构化输出
"""
from typing import Literal
from pydantic import BaseModel, Field


class RouteResult(BaseModel):
    """路由结果 - 意图识别后的目标智能体"""
    target_agent: Literal["order_agent", "consult_agent", "feedback_agent"] = Field(
        description="路由目标智能体：order_agent(菜单/库存/订单)、consult_agent(产品咨询/闲聊)、feedback_agent(反馈/投诉)"
    )


def _remove_title_from_schema(schema: dict) -> None:
    """移除 schema 中的 title 字段，确保与 Function Calling 格式兼容"""
    if "title" in schema:
        del schema["title"]
    for key in ("properties", "items", "definitions"):
        if key in schema and isinstance(schema[key], dict):
            for v in schema[key].values():
                if isinstance(v, dict):
                    _remove_title_from_schema(v)


def get_route_tool_definition() -> dict:
    """获取路由用的 Function Calling 工具定义"""
    schema = RouteResult.model_json_schema()
    _remove_title_from_schema(schema)
    return {
        "type": "function",
        "function": {
            "name": "generate_structured_output",
            "description": "根据用户请求和对话上下文，选择应路由到的子智能体。",
            "parameters": schema,
        },
    }


# 预构建的工具定义，供 _route_by_llm 使用
ROUTE_TOOL = get_route_tool_definition()
