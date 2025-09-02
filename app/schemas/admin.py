"""
Pydantic схемы для административной панели.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ==================== БАЗОВЫЕ СХЕМЫ ====================


class UserBase(BaseModel):
    """Базовая схема пользователя."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    is_super_admin: bool = False


class UserCreate(UserBase):
    """Схема для создания пользователя."""

    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """Схема для обновления пользователя."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_super_admin: Optional[bool] = None


class UserOut(UserBase):
    """Схема для вывода пользователя."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== АУТЕНТИФИКАЦИЯ ====================


class LoginRequest(BaseModel):
    """Схема для входа в систему."""

    username: str = Field(..., description="Username или email")
    password: str = Field(..., description="Пароль")


class LoginResponse(BaseModel):
    """Схема ответа при входе в систему."""

    access_token: str
    expires_in: int
    user: UserOut


class ChangePasswordRequest(BaseModel):
    """Схема для смены пароля."""

    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., min_length=6, description="Новый пароль")


# ==================== СТАТИСТИКА ====================


class ProductStats(BaseModel):
    """Статистика по продуктам."""

    total_products: int
    active_products: int
    products_with_images: int
    products_without_images: int


class OrderStats(BaseModel):
    """Статистика по заказам."""

    total_orders: int
    pending_orders: int
    completed_orders: int
    cancelled_orders: int
    total_revenue: float


class DashboardStats(BaseModel):
    """Общая статистика дашборда."""

    total_users: int
    active_users: int
    admin_users: int
    super_admin_users: int
    product_stats: ProductStats
    order_stats: OrderStats


# ==================== ПОИСК И ФИЛЬТРАЦИЯ ====================


class AdminSearchParams(BaseModel):
    """Параметры поиска для админки."""

    q: Optional[str] = Field(None, description="Поисковый запрос")
    page: int = Field(1, ge=1, description="Номер страницы")
    page_size: int = Field(20, ge=1, le=100, description="Размер страницы")
    sort_by: str = Field("created_at", description="Поле для сортировки")
    sort_order: str = Field(
        "desc", pattern="^(asc|desc)$", description="Порядок сортировки"
    )


# ==================== МАССОВЫЕ ОПЕРАЦИИ ====================


class BulkActionRequest(BaseModel):
    """Схема для массовых операций."""

    action: str = Field(
        ...,
        pattern="^(delete|activate|deactivate|move_category)$",
        description="Тип действия",
    )
    ids: List[UUID] = Field(..., min_items=1, description="Список ID для обработки")
    category_id: Optional[UUID] = Field(
        None, description="ID категории (для move_category)"
    )


# ==================== СИСТЕМНЫЕ НАСТРОЙКИ ====================


class SystemSettings(BaseModel):
    """Системные настройки."""

    site_name: str = "TechHome"
    site_description: str = "Интернет-магазин техники"
    maintenance_mode: bool = False
    registration_enabled: bool = True
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = ["jpg", "jpeg", "png", "webp", "gif"]


class SettingsUpdate(BaseModel):
    """Схема для обновления настроек."""

    site_name: Optional[str] = None
    site_description: Optional[str] = None
    maintenance_mode: Optional[bool] = None
    registration_enabled: Optional[bool] = None
    max_upload_size: Optional[int] = None
    allowed_file_types: Optional[List[str]] = None


# ==================== ЛОГИ ====================


class AdminLogEntry(BaseModel):
    """Запись в логе администратора."""

    id: UUID
    user_id: UUID
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
