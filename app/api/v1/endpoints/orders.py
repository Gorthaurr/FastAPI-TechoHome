"""
API endpoints для работы с заказами.

Содержит CRUD операции для заказов с поддержкой создания,
просмотра и управления статусами заказов.
"""

import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.database import get_db
from app.db.models import Order, OrderItem, Product

router = APIRouter()


def _normalize_uuid(s: str) -> str:
    """
    Нормализация и валидация UUID.

    Убирает фигурные скобки у {uuid} и проверяет корректность формата.

    Args:
        s: Строка с UUID

    Returns:
        str: Нормализованный UUID в нижнем регистре

    Raises:
        HTTPException: Если UUID некорректный
    """
    s = (s or "").strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    try:
        val = UUID(s)
    except Exception:
        raise HTTPException(400, detail="Order ID must be a valid UUID")
    return str(val)


@router.get("", response_model=dict)
def list_orders(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    status: Optional[str] = Query(
        None, description="Фильтр по статусу: pending/paid/canceled/shipped/completed"
    ),
):
    """
    Получить список заказов с пагинацией и фильтрацией.

    Поддерживает:
    - Пагинацию результатов
    - Фильтрацию по статусу заказа
    - Подсчет количества позиций в заказе

    Args:
        db: Сессия базы данных
        page: Номер страницы (начиная с 1)
        page_size: Размер страницы (1-100)
        status: Фильтр по статусу заказа

    Returns:
        dict: Список заказов с метаданными пагинации

    Raises:
        HTTPException: При некорректных параметрах запроса
    """
    # Подсчет общего количества
    count_stmt = select(func.count()).select_from(Order)
    if status:
        count_stmt = count_stmt.where(Order.status == status)
    total = db.scalar(count_stmt) or 0

    # Запрос с подсчетом позиций
    stmt = select(
        Order,
        func.count(OrderItem.id).label("items_count"),
    ).outerjoin(OrderItem, OrderItem.order_id == Order.id)
    if status:
        stmt = stmt.where(Order.status == status)
    stmt = (
        stmt.group_by(Order.id)
        .order_by(desc(Order.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows = db.execute(stmt).all()
    items: List[Dict[str, Any]] = []

    for order, items_count in rows:
        items.append(
            {
                "id": order.id,
                "status": order.status,
                "currency": order.currency,
                "subtotal_cents": order.subtotal_cents,
                "shipping_cents": order.shipping_cents,
                "total_cents": order.total_cents,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "created_at": (
                    str(order.created_at) if order.created_at is not None else None
                ),
                "items_count": int(items_count or 0),
            }
        )

    return {
        "items": items,
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.post("", response_model=dict, status_code=201)
def create_order(payload: dict, db: Session = Depends(get_db)):
    """
    Создать новый заказ.

    Создает заказ с указанными товарами и информацией о клиенте.
    Автоматически рассчитывает суммы и создает позиции заказа.

    Ожидает JSON:
    {
      "customer": {
        "name": "...",
        "email": "...",
        "phone": "...",
        "address": "...",
        "city": "...",
        "postal_code": "..."
      },
      "items": [{"product_id": "ABC123", "qty": 2}, ...],
      "comment": "...",
      "shipping_cents": 500,
      "currency": "EUR"
    }

    Args:
        payload: Данные заказа
        db: Сессия базы данных

    Returns:
        dict: Созданный заказ с позициями

    Raises:
        HTTPException: При некорректных данных или отсутствующих товарах
    """
    if not isinstance(payload, dict):
        raise HTTPException(400, detail="Invalid request body")

    customer = payload.get("customer") or {}
    items = payload.get("items") or []
    if not items:
        raise HTTPException(400, detail="Order must contain at least one item")

    currency = payload.get("currency") or "EUR"
    shipping_cents = int(payload.get("shipping_cents") or 0)
    comment = payload.get("comment")

    # Проверка товаров и создание снимка цен/названий
    product_ids = [
        str(item.get("product_id")) for item in items if item.get("product_id")
    ]
    rows = db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
    product_map = {p.id: p for p in rows}
    missing = [pid for pid in product_ids if pid not in product_map]
    if missing:
        raise HTTPException(400, detail=f"Unknown product ID(s): {', '.join(missing)}")

    # Создание заказа
    order_id = str(uuid.uuid4())
    order = Order(
        id=order_id,
        status="pending",
        currency=currency,
        customer_name=str(customer.get("name") or ""),
        customer_email=customer.get("email"),
        customer_phone=customer.get("phone"),
        shipping_address=customer.get("address"),
        shipping_city=customer.get("city"),
        shipping_postal_code=customer.get("postal_code"),
        shipping_cents=shipping_cents,
        comment=comment,
    )
    db.add(order)
    db.flush()

    # Создание позиций заказа
    subtotal = 0
    for item in items:
        product_id = str(item.get("product_id"))
        qty = int(item.get("qty") or 0)
        if qty <= 0:
            raise HTTPException(
                400, detail=f"Quantity must be > 0 for product {product_id}"
            )

        product = product_map[product_id]
        price = int(product.price_cents or 0)
        subtotal += price * qty

        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                qty=qty,
                item_name=product.name,
                item_price_cents=price,
            )
        )

    # Обновление сумм заказа
    order.subtotal_cents = subtotal
    order.total_cents = subtotal + shipping_cents

    db.add(order)
    db.commit()

    # Перечитываем заказ с предзагрузкой позиций
    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )

    return {
        "id": order.id,
        "status": order.status,
        "currency": order.currency,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
        "shipping_address": order.shipping_address,
        "shipping_city": order.shipping_city,
        "shipping_postal_code": order.shipping_postal_code,
        "subtotal_cents": order.subtotal_cents,
        "shipping_cents": order.shipping_cents,
        "total_cents": order.total_cents,
        "comment": order.comment,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "qty": item.qty,
                "item_name": item.item_name,
                "item_price_cents": item.item_price_cents,
            }
            for item in order.items
        ],
    }


@router.get("/{order_id}", response_model=dict)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """
    Получить заказ по ID.

    Возвращает полную информацию о заказе включая все позиции
    и данные о клиенте.

    Args:
        order_id: UUID заказа
        db: Сессия базы данных

    Returns:
        dict: Данные заказа с позициями

    Raises:
        HTTPException: Если заказ не найден или UUID некорректный
    """
    # Нормализуем и валидируем UUID
    order_id = _normalize_uuid(order_id)

    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if not order:
        raise HTTPException(404, detail="Order not found")

    return {
        "id": order.id,
        "status": order.status,
        "currency": order.currency,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
        "shipping_address": order.shipping_address,
        "shipping_city": order.shipping_city,
        "shipping_postal_code": order.shipping_postal_code,
        "subtotal_cents": order.subtotal_cents,
        "shipping_cents": order.shipping_cents,
        "total_cents": order.total_cents,
        "comment": order.comment,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "qty": item.qty,
                "item_name": item.item_name,
                "item_price_cents": item.item_price_cents,
            }
            for item in order.items
        ],
    }
