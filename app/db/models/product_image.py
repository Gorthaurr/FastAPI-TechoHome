"""
Модель изображения товара.
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, String, Integer, Boolean, ForeignKey, UniqueConstraint, Index
from .base import Base


class ProductImage(Base):
    """
    Модель изображения товара.
    
    Attributes:
        id: Уникальный идентификатор изображения
        product_id: ID товара
        path: Путь к файлу изображения
        sort_order: Порядок сортировки
        is_primary: Флаг главного изображения
        product: Связь с товаром
    """
    
    __tablename__ = "product_images"
    
    __table_args__ = (
        UniqueConstraint("product_id", "path", name="uq_product_image_path"),
        Index("ix_product_images_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("products.id", ondelete="CASCADE")
    )
    path: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean)

    # Связь с товаром
    product: Mapped["Product"] = relationship(back_populates="images")
