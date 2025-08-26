"""
Модель категории товаров.
"""

from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String
from .base import Base


class Category(Base):
    """
    Модель категории товаров.
    
    Attributes:
        id: Уникальный идентификатор категории
        slug: URL-friendly название категории
        products: Связь с товарами в этой категории
    """
    
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Связь с товарами (каскадное удаление)
    products: Mapped[List["Product"]] = relationship(
        back_populates="category",
        cascade="all,delete",
        lazy="selectin"
    )
