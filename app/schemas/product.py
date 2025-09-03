from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ImageOut(BaseModel):
    """Схема для вывода изображения с метаданными."""

    id: int
    path: str
    filename: Optional[str] = None
    sort_order: int
    is_primary: bool
    status: str = Field(description="uploading/processing/ready/error")

    # Метаданные файла
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    # SEO и доступность
    alt_text: Optional[str] = None

    # URL для разных размеров
    url: Optional[str] = None
    urls: Optional[Dict[str, str]] = None

    # Временные метки
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    # Обработка ошибок
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ImageCreate(BaseModel):
    """Схема для создания изображения."""

    filename: str = Field(..., description="Оригинальное имя файла")
    alt_text: Optional[str] = Field(None, description="Альтернативный текст для SEO")
    sort_order: int = Field(0, description="Порядок сортировки")
    is_primary: bool = Field(False, description="Главное изображение")


class ImageUpdate(BaseModel):
    """Схема для обновления изображения."""

    alt_text: Optional[str] = None
    sort_order: Optional[int] = None
    is_primary: Optional[bool] = None


class AttributeOut(BaseModel):
    id: int
    key: str
    value: Optional[str]

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: str
    category_id: int
    name: str

    price_raw: Optional[str]
    price_cents: Optional[int]
    description: Optional[str]
    images: Optional[List[ImageOut]] = None
    attributes: Optional[List[AttributeOut]] = None

    class Config:
        from_attributes = True
