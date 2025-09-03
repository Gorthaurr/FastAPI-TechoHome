"""
Debug endpoints для диагностики и отладки.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db

router = APIRouter()

# Список таблиц для проверки
TABLES_TO_CHECK = [
    "categories",
    "products",
    "product_images",
    "product_attributes",
    "orders",
    "order_items",
]


@router.get("/db-ping")
def db_ping(db: Session = Depends(get_db)):
    """
    Проверка подключения к базе данных.

    Args:
        db: Сессия базы данных

    Returns:
        dict: Статус подключения и информация о БД
    """
    try:
        # Проверка подключения
        ping_ok = db.execute(text("SELECT 1")).scalar() == 1

        # Получение информации о БД
        row = db.execute(
            text("SELECT version(), current_database(), current_user")
        ).first()
        version = row[0] if row else None
        dbname = row[1] if row else None
        dbuser = row[2] if row else None

        # Проверка наличия таблиц
        present, missing = [], []
        for table in TABLES_TO_CHECK:
            exists = db.execute(
                text("SELECT to_regclass(:q)::text IS NOT NULL"),
                {"q": f"public.{table}"},
            ).scalar()
            (present if exists else missing).append(table)

        return {
            "ok": ping_ok,
            "version": version,
            "database": dbname,
            "user": dbuser,
            "tables_present": present,
            "tables_missing": missing,
        }
    except Exception as e:
        import traceback

        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


@router.get("/products-raw")
def products_raw(
    db: Session = Depends(get_db),
    limit: int = Query(5, ge=1, le=100, description="Количество записей"),
):
    """
    Получить сырые данные товаров для отладки.

    Args:
        db: Сессия базы данных
        limit: Количество записей для выборки

    Returns:
        dict: Сырые данные товаров
    """
    try:
        rows = (
            db.execute(
                text(
                    """
            SELECT id, category_id, name, price_raw, price_cents, description
            FROM public.products
            ORDER BY name ASC NULLS LAST
            LIMIT :lim
        """
                ),
                {"lim": limit},
            )
            .mappings()
            .all()
        )
        return {"ok": True, "sample": rows}
    except Exception as e:
        import traceback

        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


@router.get("/orders-raw")
def orders_raw(
    db: Session = Depends(get_db),
    limit: int = Query(5, ge=1, le=100, description="Количество записей"),
):
    """
    Получить сырые данные заказов для отладки.

    Args:
        db: Сессия базы данных
        limit: Количество записей для выборки

    Returns:
        dict: Сырые данные заказов
    """
    try:
        rows = (
            db.execute(
                text(
                    """
            SELECT o.id, o.status, o.currency, o.subtotal_cents, o.shipping_cents, o.total_cents,
                   o.customer_name, o.customer_email, o.created_at,
                   count(oi.id) AS items_count
            FROM public.orders o
            LEFT JOIN public.order_items oi ON oi.order_id = o.id
            GROUP BY o.id
            ORDER BY o.created_at DESC
            LIMIT :lim
        """
                ),
                {"lim": limit},
            )
            .mappings()
            .all()
        )
        return {"ok": True, "sample": rows}
    except Exception as e:
        import traceback

        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}
