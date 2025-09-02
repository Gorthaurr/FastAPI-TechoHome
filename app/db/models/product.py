"""
Модель товара.
"""

from typing import List, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Product(Base):
    """
    Модель товара.

    Attributes:
        id: Уникальный идентификатор товара
        category_id: ID категории товара
        product_url: URL страницы товара
        name: Название товара
        price_raw: Сырая цена (строка)
        price_cents: Цена в центах
        description: Описание товара
        category: Связь с категорией
        images: Связь с изображениями товара
        attributes: Связь с атрибутами товара
    """

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    product_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(Text)
    price_raw: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    price_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связи с другими моделями
    category: Mapped["Category"] = relationship(back_populates="products")
    images: Mapped[List["ProductImage"]] = relationship(
        back_populates="product", cascade="all,delete", lazy="selectin"
    )
    attributes: Mapped[List["ProductAttribute"]] = relationship(
        back_populates="product", cascade="all,delete", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Product(id='{self.id}', name='{self.name}')>"
