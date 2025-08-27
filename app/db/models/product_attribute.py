"""
Модель атрибута товара.
"""

from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, String, Integer, ForeignKey, UniqueConstraint, Index
from .base import Base


class ProductAttribute(Base):
    """
    Модель атрибута товара (key-value пары).
    
    Attributes:
        id: Уникальный идентификатор атрибута
        product_id: ID товара
        attr_key: Ключ атрибута
        value: Значение атрибута
        product: Связь с товаром
    """
    
    __tablename__ = "product_attributes"
    
    __table_args__ = (
        UniqueConstraint("product_id", "attr_key", name="uq_product_attribute_key"),
        Index("ix_product_attributes_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("products.id", ondelete="CASCADE")
    )
    attr_key: Mapped[str] = mapped_column(Text)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связь с товаром
    product: Mapped["Product"] = relationship(back_populates="attributes")
