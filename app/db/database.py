"""
Конфигурация базы данных.

Содержит настройки подключения к PostgreSQL и фабрику сессий.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from app.core.config import settings


# Создание движка SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    future=True,  # Использование новых API SQLAlchemy 2.0
    echo=bool(settings.DEBUG),  # Логирование SQL запросов в режиме отладки
)


# Фабрика сессий базы данных
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True
)


def get_db() -> Generator:
    """
    Dependency для получения сессии базы данных.
    
    Yields:
        Session: Сессия SQLAlchemy
        
    Note:
        Автоматически закрывает сессию после использования
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
