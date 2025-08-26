"""
API endpoints для работы с категориями товаров.
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
    
    Args:
        db: Сессия базы данных
        
    Returns:
        List[dict]: Список категорий с id и slug
    """
    rows = db.scalars(select(Category).order_by(Category.slug)).all()
    return [{"id": c.id, "slug": c.slug} for c in rows]


@router.get("/{category_id}", response_model=dict)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """
    Получить категорию по ID.
    
    Args:
        category_id: ID категории
        db: Сессия базы данных
        
    Returns:
        dict: Данные категории
        
    Raises:
        HTTPException: Если категория не найдена
    """
    c = db.get(Category, category_id)
    if not c:
        raise HTTPException(404, detail="category not found")
    return {"id": c.id, "slug": c.slug}