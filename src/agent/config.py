"""Agent configuration management"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from dotenv import dotenv_values


class Settings(BaseSettings):
    """Application settings"""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Weibo (后期扩展)
    weibo_scraper_enabled: bool = False
    weibo_scraper_interval: int = 3600
    weibo_use_selenium: bool = True  # 是否使用 Selenium 爬虫
    weibo_scraper_timeout: int = 10
    weibo_cookie: str = ""  # 微博 Cookie，用于绕过 Sina Visitor System 验证

    # 微博热搜描述抓取方案选择
    # True: 使用 Selenium 爬虫（旧方案，需要 Chrome 浏览器）
    # False: 使用 HTTP 爬虫（新方案，更轻量）
    # 注意：两种方案都需要成功获取微博内容，失败则不生成描述
    use_selenium_for_descriptions: bool = False

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "josie"
    db_password: str = "bills_password_2024"
    db_name: str = "news_agent"

    # JWT
    jwt_secret: str = "your-secret-key-change-this-in-production"

    # Conversation
    title_generation_strategy: str = "truncate"  # Options: "ai", "truncate"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file (like deployment config)


@lru_cache()
def _cached_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def get_settings() -> Settings:
    settings = _cached_settings()
    # Cookie 可通过页面修改；后台进程也需在下一次任务读取新值。
    env_file = Path(".env")
    cookie = dotenv_values(env_file).get("WEIBO_COOKIE") if env_file.is_file() else None
    if cookie is not None and cookie != settings.weibo_cookie:
        return settings.model_copy(update={"weibo_cookie": cookie})
    return settings
