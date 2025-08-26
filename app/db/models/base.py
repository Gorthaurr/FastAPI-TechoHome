"""
Базовый класс для всех моделей SQLAlchemy.

Использует новый Declarative API SQLAlchemy 2.0.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей.
    
    Наследуется от DeclarativeBase для использования нового API SQLAlchemy 2.0.
    """
    pass
