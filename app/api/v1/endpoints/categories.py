"""
API endpoints для работы с категориями товаров.

Содержит операции для получения списка категорий и
информации о конкретных категориях.
"""

from typing import List
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Category

router = APIRouter()

# Простое in-memory кэширование для категорий
_categories_cache = None
_cache_timestamp = 0
CACHE_TTL = 300  # 5 минут


@router.get("", response_model=List[dict])
def list_categories(db: Session = Depends(get_db)):
    """
    Получить список всех категорий с кэшированием.

    Возвращает отсортированный по slug список всех доступных
    категорий товаров в системе с кэшированием на 5 минут.

    Args:
        db: Сессия базы данных

    Returns:
        List[dict]: Список категорий с id и slug

    Example:
        [
            {"id": 1, "slug": "electronics"},
            {"id": 2, "slug": "home-appliances"}
        ]
    """
    global _categories_cache, _cache_timestamp
    
    # Проверяем кэш
    current_time = time.time()
    if _categories_cache and (current_time - _cache_timestamp) < CACHE_TTL:
        return _categories_cache
    
    # Загружаем из БД - ТОЛЬКО НУЖНЫЕ ПОЛЯ для скорости
    rows = db.execute(select(Category.id, Category.slug).order_by(Category.slug)).all()
    result = [{"id": row.id, "slug": row.slug} for row in rows]
    
    # Обновляем кэш
    _categories_cache = result
    _cache_timestamp = current_time
    
    return result


@router.get("/{category_id}", response_model=dict)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """
    Получить категорию по ID.

    Возвращает информацию о конкретной категории товаров.

    Args:
        category_id: ID категории
        db: Сессия базы данных

    Returns:
        dict: Данные категории с id и slug

    Raises:
        HTTPException: Если категория не найдена

    Example:
        {"id": 1, "slug": "electronics"}
    """
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(404, detail="Category not found")
    return {"id": category.id, "slug": category.slug}
