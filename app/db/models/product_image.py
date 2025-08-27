"""
Модель изображения товара.
"""

from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, String, Integer, Boolean, ForeignKey, UniqueConstraint, Index, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from .base import Base


class ProductImage(Base):
    """
    Модель изображения товара с расширенными метаданными.
    
    Attributes:
        id: Уникальный идентификатор изображения
        product_id: ID товара
        path: Путь к файлу изображения
        filename: Оригинальное имя файла
        sort_order: Порядок сортировки
        is_primary: Флаг главного изображения
        status: Статус изображения (uploading/processing/ready/error)
        file_size: Размер файла в байтах
        mime_type: MIME тип файла
        width: Ширина изображения в пикселях
        height: Высота изображения в пикселях
        alt_text: Альтернативный текст для SEO
        metadata: Дополнительные метаданные (JSON)
        uploaded_at: Дата загрузки
        processed_at: Дата обработки
        error_message: Сообщение об ошибке (если есть)
        product: Связь с товаром
    """
    
    __tablename__ = "product_images"
    
    __table_args__ = (
        UniqueConstraint("product_id", "path", name="uq_product_image_path"),
        Index("ix_product_images_product_id", "product_id"),
        Index("ix_product_images_status", "status"),
        Index("ix_product_images_uploaded_at", "uploaded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("products.id", ondelete="CASCADE")
    )
    path: Mapped[str] = mapped_column(Text)
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Статус и обработка
    status: Mapped[str] = mapped_column(
        String(32), 
        default="uploading",
        comment="uploading/processing/ready/error"
    )
    
    # Метаданные файла
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # SEO и доступность
    alt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Дополнительные метаданные
    image_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Временные метки
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Обработка ошибок
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связь с товаром
    product: Mapped["Product"] = relationship(back_populates="images")
