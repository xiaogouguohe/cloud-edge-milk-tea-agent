"""
AgentCard 定义 - A2A 协议中的 Agent 卡片信息
"""
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class AgentCard:
    """Agent 卡片信息 - 用于 A2A 协议的服务注册和发现"""
    
    name: str  # Agent 名称，如 "order_agent"
    description: str  # Agent 描述
    version: str = "1.0.0"  # 版本号
    url: Optional[str] = None  # Agent 服务地址
    provider: Optional[Dict] = None  # 提供者信息
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "url": self.url,
            "provider": self.provider or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentCard':
        """从字典创建"""
        return cls(
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            url=data.get("url"),
            provider=data.get("provider")
        )
