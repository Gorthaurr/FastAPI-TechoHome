"""
Модели базы данных.

Импортирует все модели для корректной работы SQLAlchemy.
"""

from .base import Base
from .category import Category
from .product import Product
from .product_image import ProductImage
from .product_attribute import ProductAttribute
from .order import Order, OrderItem

__all__ = [
    "Base",
    "Category", 
    "Product",
    "ProductImage",
    "ProductAttribute",
    "Order",
    "OrderItem"
]
