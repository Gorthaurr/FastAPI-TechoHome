"""
API endpoints для работы с категориями товаров.

Содержит операции для получения списка категорий и
информации о конкретных категориях.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Category


router = APIRouter()


@router.get("", response_model=List[dict])
def list_categories(db: Session = Depends(get_db)):
    """
    Получить список всех категорий.
    
    Возвращает отсортированный по slug список всех доступных
    категорий товаров в системе.
    
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
    rows = db.scalars(select(Category).order_by(Category.slug)).all()
    return [{"id": c.id, "slug": c.slug} for c in rows]


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