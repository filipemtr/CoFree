from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    environment: str = 'development'
    database_url: str = 'sqlite:///./cofree-dev.db'
    redis_url: str = 'redis://redis:6379/0'
    app_secret: str = 'development-only-change-this-secret-before-production'
    frontend_url: str = 'http://localhost:5173'
    cookie_secure: bool = False
    smtp_host: str = ''
    smtp_port: int = 1025
    smtp_username: str = ''
    smtp_password: str = ''
    smtp_sender: str = 'CoFree <no-reply@cofree.local>'
    smtp_starttls: bool = False
    smtp_ssl: bool = False
    check_interval_hours: int = 24


@lru_cache

def get_settings() -> Settings:
    return Settings()
