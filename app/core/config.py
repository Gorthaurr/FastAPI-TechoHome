"""
Конфигурация приложения.

Содержит настройки для подключения к БД, CDN и режима отладки.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения.
    
    Attributes:
        DATABASE_URL: URL подключения к PostgreSQL
        CDN_BASE_URL: Базовый URL CDN для изображений
        DEBUG: Режим отладки
    """
    
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:Anton533@localhost:5432/Shop",
        description="URL подключения к PostgreSQL"
    )
    CDN_BASE_URL: str = Field(
        default="",
        description="Базовый URL CDN для изображений"
    )
    DEBUG: bool = Field(
        default=False,
        description="Режим отладки"
    )

    class Config:
        env_file = ".env"
        extra = "ignore"


# Глобальный экземпляр настроек
settings = Settings()