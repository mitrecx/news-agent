"""Agent configuration management"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # DeepSeek API
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Agent
    agent_temperature: float = 0.7
    agent_max_tokens: int = 2000
    agent_model: str = "deepseek-chat"

    # Weibo (后期扩展)
    weibo_scraper_enabled: bool = False
    weibo_scraper_interval: int = 3600
    weibo_use_selenium: bool = True  # 是否使用 Selenium 爬虫
    weibo_scraper_timeout: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
