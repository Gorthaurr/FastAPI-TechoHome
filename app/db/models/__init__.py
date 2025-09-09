"""
Модели базы данных.

Импортирует все модели для корректной работы SQLAlchemy.
"""

from .base import Base
from .category import Category
from .order import Order, OrderItem
from .product import Product
from .product_attribute import ProductAttribute
from .product_image import ProductImage
from .user import User

__all__ = [
    "Base",
    "Category",
    "Product",
    "ProductImage",
    "ProductAttribute",
    "Order",
    "OrderItem",
    "User",
]
