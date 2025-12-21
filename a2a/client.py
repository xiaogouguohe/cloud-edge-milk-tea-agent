"""
A2A Client - 用于调用其他 Agent
"""
import requests
from typing import Dict, Optional
from service_discovery import ServiceDiscovery
from .agent_card import AgentCard


class A2AClient:
    """A2A 协议客户端 - 用于调用其他 Agent"""
    
    def __init__(self, service_discovery: Optional[ServiceDiscovery] = None):
        """
        初始化 A2A 客户端
        
        Args:
            service_discovery: 服务发现实例，如果为 None 则创建默认实例
        """
        self.sd = service_discovery or ServiceDiscovery(method="config")
    
    def get_agent_card(self, agent_name: str) -> Optional[AgentCard]:
        """
        获取 Agent 卡片信息
        
        Args:
            agent_name: Agent 名称
            
        Returns:
            AgentCard 对象，如果未找到则返回 None
        """
        service = self.sd.discover(agent_name)
        if not service:
            return None
        
        # 从服务信息构建 AgentCard
        return AgentCard(
            name=agent_name,
            description=service.get("description", ""),
            version=service.get("version", "1.0.0"),
            url=service.get("url"),
            provider=service.get("provider")
        )
    
    def call_agent(self, agent_name: str, input_data: Dict, timeout: int = 30) -> Dict:
        """
        调用其他 Agent（A2A 协议）
        
        Args:
            agent_name: Agent 名称
            input_data: 输入数据，包含 input, chat_id, user_id 等
            timeout: 超时时间（秒）
            
        Returns:
            Agent 的响应结果
        """
        # 1. 发现服务
        service = self.sd.discover(agent_name)
        if not service:
            raise ValueError(f"Agent {agent_name} not found")
        
        # 2. 构建 A2A 协议请求
        url = f"{service['url']}/a2a/invoke"
        
        # 3. 发送请求
        try:
            response = requests.post(
                url,
                json=input_data,
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to call agent {agent_name}: {str(e)}")
    
    def call_agent_stream(self, agent_name: str, input_data: Dict):
        """
        流式调用其他 Agent（SSE 方式，可选实现）
        
        Args:
            agent_name: Agent 名称
            input_data: 输入数据
            
        Yields:
            流式响应数据
        """
        service = self.sd.discover(agent_name)
        if not service:
            raise ValueError(f"Agent {agent_name} not found")
        
        url = f"{service['url']}/a2a/stream"
        
        # 使用 SSE 接收流式数据
        response = requests.post(url, json=input_data, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                yield line.decode('utf-8')
