"""
Модели заказа и позиций заказа.
"""

from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, CheckConstraint, ForeignKey, BigInteger, text
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Order(Base):
    """
    Модель заказа.
    
    Attributes:
        id: UUID заказа
        status: Статус заказа (pending/paid/canceled/shipped/completed)
        currency: Валюта заказа
        customer_name: Имя клиента
        customer_email: Email клиента
        customer_phone: Телефон клиента
        shipping_address: Адрес доставки
        shipping_city: Город доставки
        shipping_postal_code: Почтовый индекс
        subtotal_cents: Сумма товаров в центах
        shipping_cents: Стоимость доставки в центах
        total_cents: Общая сумма в центах
        comment: Комментарий к заказу
        created_at: Дата создания
        updated_at: Дата обновления
        items: Позиции заказа
    """
    
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(32),
        server_default=text("'pending'")
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        server_default=text("'EUR'")
    )

    # Данные клиента
    customer_name: Mapped[str] = mapped_column(Text)
    customer_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shipping_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shipping_city: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shipping_postal_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Финансовые данные
    subtotal_cents: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    shipping_cents: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    total_cents: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Временные метки
    created_at: Mapped[str] = mapped_column(Text, server_default=text("NOW()"))
    updated_at: Mapped[str] = mapped_column(Text, server_default=text("NOW()"))

    # Связь с позициями заказа
    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all,delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('pending','paid','canceled','shipped','completed')",
            name="ck_orders_status"
        ),
    )


class OrderItem(Base):
    """
    Модель позиции заказа.
    
    Attributes:
        id: Уникальный идентификатор позиции
        order_id: ID заказа
        product_id: ID товара
        qty: Количество товара
        item_name: Название товара (снимок)
        item_price_cents: Цена товара в центах (снимок)
        order: Связь с заказом
    """
    
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("products.id", ondelete="RESTRICT")
    )

    qty: Mapped[int] = mapped_column(Integer)
    item_name: Mapped[str] = mapped_column(Text)
    item_price_cents: Mapped[int] = mapped_column(Integer)

    # Связь с заказом
    order: Mapped[Order] = relationship(back_populates="items")
