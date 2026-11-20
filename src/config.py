"""兼容旧导入路径，统一使用应用配置。模型由页面按用户管理。"""

from .agent.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
