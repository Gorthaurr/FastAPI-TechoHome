"""
Конфигурация приложения.

Содержит настройки для подключения к БД, CDN и режима отладки.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения.

    Attributes:
        DATABASE_URL: URL подключения к PostgreSQL
        CDN_BASE_URL: Базовый URL CDN для изображений
        DEBUG: Режим отладки
    """

    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:password@localhost:5433/fastapi_shop",
        description="URL подключения к PostgreSQL",
    )
    CDN_BASE_URL: str = Field(default="", description="Базовый URL CDN для изображений")
    DEBUG: bool = Field(default=False, description="Режим отладки")

    # Настройки хранилища изображений
    STORAGE_TYPE: str = Field(default="local", description="Тип хранилища: local/s3")
    STORAGE_PATH: str = Field(
        default="./demo_images", description="Путь для локального хранения файлов (демо)"
    )
    MAX_IMAGE_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Максимальный размер изображения в байтах",
    )
    ALLOWED_IMAGE_TYPES: str = Field(
        default="jpg,jpeg,png,webp,gif",
        description="Разрешенные типы изображений (через запятую)",
    )

    # Настройки S3 (опционально)
    S3_BUCKET_NAME: str = Field(
        default="product-images", description="Имя S3 bucket для хранения файлов"
    )
    AWS_REGION: str = Field(default="us-east-1", description="AWS регион для S3")
    S3_ENDPOINT_URL: str = Field(
        default="http://localhost:9002",
        description="Кастомный endpoint URL для S3 (для MinIO и т.д.)",
    )
    AWS_ACCESS_KEY_ID: str = Field(
        default="minioadmin", description="AWS Access Key ID"
    )
    AWS_SECRET_ACCESS_KEY: str = Field(
        default="minioadmin", description="AWS Secret Access Key"
    )

    class Config:
        env_file = ".env"
        extra = "ignore"


# Глобальный экземпляр настроек
settings = Settings()
