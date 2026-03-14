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

    # Database
    # SECURITY: These should be set via environment variables, not hardcoded!
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = ""
    db_password: str = ""
    db_name: str = "news_agent"

    # JWT
    # SECURITY WARNING: Always set a strong random secret in production!
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate critical security settings
        if not self.jwt_secret or self.jwt_secret == "your-secret-key-change-this-in-production":
            import warnings
            warnings.warn(
                "JWT_SECRET is not set or is using default value! "
                "This is a security risk in production.",
                RuntimeWarning,
                stacklevel=2
            )
        if not self.db_user or not self.db_password:
            import warnings
            warnings.warn(
                "Database credentials not configured properly. "
                "Please set DB_USER and DB_PASSWORD environment variables.",
                RuntimeWarning,
                stacklevel=2
            )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
