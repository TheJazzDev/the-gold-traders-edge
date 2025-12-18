"""
Application configuration settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "Gold Trader's Edge API"
    VERSION: str = "1.0.0"

    # CORS - Can be comma-separated string or list
    CORS_ORIGINS: str | List[str] = "http://localhost:3000,http://localhost:8000,http://localhost:5173,http://localhost:8001"

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "postgresql://goldtrader:localdev123@localhost:5432/goldtrader"
    DATABASE_ECHO: bool = False  # Set to True for SQL query logging

    # Redis (for future implementation)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Strategy Configuration
    DEFAULT_TIMEFRAME: str = "4h"
    DEFAULT_RULES: str | List[int] = "1,2,5,6"

    @field_validator('DEFAULT_RULES', mode='before')
    @classmethod
    def parse_default_rules(cls, v):
        if isinstance(v, str):
            return [int(rule.strip()) for rule in v.split(',')]
        return v

    INITIAL_BALANCE: float = 10000.0
    RISK_PER_TRADE: float = 2.0

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields from .env
    )


settings = Settings()
