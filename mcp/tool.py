"""
MCP 工具定义
"""
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str  # 工具名称
    description: str  # 工具描述
    parameters: Dict[str, Any]  # 参数定义（JSON Schema 格式）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class Tool:
    """MCP 工具 - 包含定义和执行函数"""
    
    def __init__(self, definition: ToolDefinition, handler: Callable):
        """
        初始化工具
        
        Args:
            definition: 工具定义
            handler: 工具执行函数
        """
        self.definition = definition
        self.handler = handler
    
    def invoke(self, parameters: Dict[str, Any]) -> Any:
        """
        调用工具
        
        Args:
            parameters: 工具参数
            
        Returns:
            工具执行结果
        """
        return self.handler(**parameters)
