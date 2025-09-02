"""
Модель пользователя для системы аутентификации.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    """Модель пользователя."""

    __tablename__ = "users"

    # Основные поля
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Права доступа
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Дополнительная информация
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    @property
    def permissions(self) -> list[str]:
        """Получить список разрешений пользователя."""
        if self.is_super_admin:
            return ["*"]  # Все разрешения

        if self.is_admin:
            return [
                "read_own_profile",
                "update_own_profile",
                "manage_products",
                "manage_categories",
                "view_orders",
                "manage_users",
            ]

        return ["read_own_profile"]

    def has_permission(self, permission: str) -> bool:
        """Проверить, есть ли у пользователя определенное разрешение."""
        if self.is_super_admin:
            return True

        return permission in self.permissions
