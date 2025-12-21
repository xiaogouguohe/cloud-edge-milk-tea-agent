"""
服务发现模块 - 支持多种方式
"""
import json
from typing import Dict, Optional
from pathlib import Path

# 尝试导入可选依赖
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class ServiceDiscovery:
    """服务发现 - 支持配置文件、Redis、数据库等多种方式"""
    
    def __init__(self, method: str = "config", **kwargs):
        """
        初始化服务发现
        
        Args:
            method: 服务发现方式 "config", "redis", "database"
            **kwargs: 配置参数
        """
        self.method = method
        
        if method == "config":
            self.config_file = kwargs.get("config_file", "services.json")
            self._load_from_config()
        elif method == "redis":
            if not REDIS_AVAILABLE:
                raise ImportError("请安装 redis: pip install redis")
            self.redis_client = redis.Redis(
                host=kwargs.get("redis_host", "localhost"),
                port=kwargs.get("redis_port", 6379),
                password=kwargs.get("redis_password"),
                decode_responses=True
            )
        elif method == "database":
            # TODO: 实现数据库方式
            pass
        else:
            raise ValueError(f"不支持的服务发现方式: {method}")
    
    def _load_from_config(self):
        """从配置文件加载服务信息"""
        config_path = Path(__file__).parent / self.config_file
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.services = json.load(f)
        else:
            # 默认配置
            self.services = {
                "order_agent": {
                    "host": "localhost",
                    "port": 10006,
                    "url": "http://localhost:10006"
                },
                "consult_agent": {
                    "host": "localhost",
                    "port": 10005,
                    "url": "http://localhost:10005"
                },
                "feedback_agent": {
                    "host": "localhost",
                    "port": 10007,
                    "url": "http://localhost:10007"
                }
            }
            # 保存默认配置
            self._save_config()
    
    def _save_config(self):
        """保存配置到文件"""
        config_path = Path(__file__).parent / self.config_file
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.services, f, indent=2, ensure_ascii=False)
    
    def discover(self, service_name: str) -> Optional[Dict]:
        """
        发现服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务信息字典，包含 host, port, url 等
        """
        if self.method == "config":
            return self.services.get(service_name)
        elif self.method == "redis":
            service_key = f"services:{service_name}"
            service_info = self.redis_client.hgetall(service_key)
            if service_info:
                return {
                    "host": service_info.get("host"),
                    "port": int(service_info.get("port", 0)),
                    "url": service_info.get("url", f"http://{service_info.get('host')}:{service_info.get('port')}")
                }
            return None
        return None
    
    def register(self, service_name: str, host: str, port: int, **kwargs):
        """
        注册服务
        
        Args:
            service_name: 服务名称
            host: 服务地址
            port: 服务端口
            **kwargs: 其他服务信息
        """
        service_info = {
            "host": host,
            "port": port,
            "url": kwargs.get("url", f"http://{host}:{port}"),
            **kwargs
        }
        
        if self.method == "config":
            self.services[service_name] = service_info
            self._save_config()
        elif self.method == "redis":
            service_key = f"services:{service_name}"
            self.redis_client.hset(service_key, mapping={
                "host": host,
                "port": str(port),
                "url": service_info["url"],
                "status": "active"
            })
            # 设置过期时间（可选，用于健康检查）
            self.redis_client.expire(service_key, 300)  # 5分钟
    
    def list_services(self) -> Dict[str, Dict]:
        """列出所有服务"""
        if self.method == "config":
            return self.services.copy()
        elif self.method == "redis":
            services = {}
            for key in self.redis_client.keys("services:*"):
                service_name = key.replace("services:", "")
                services[service_name] = self.discover(service_name)
            return services
        return {}


# 默认实例（使用配置文件方式）
default_discovery = ServiceDiscovery(method="config")
