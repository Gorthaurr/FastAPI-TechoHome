"""
API endpoints для работы с товарами.
"""

from typing import Optional, List, Literal, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func, asc, desc
from sqlalchemy.orm import Session, selectinload

from app.db.database import get_db
from app.db.models import Product
from app.core.config import settings
from app.schemas.pagination import PageMeta
from app.services.image_service import image_service


router = APIRouter()

# Типы для сортировки
SortField = Literal["name", "-name", "price", "-price"]


@router.get("", response_model=dict)
def list_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
    q: Optional[str] = Query(None, description="Поиск по названию (ILIKE)"),
    price_min: Optional[int] = Query(None, ge=0, description="Минимальная цена в центах"),
    price_max: Optional[int] = Query(None, ge=0, description="Максимальная цена в центах"),
    sort: Optional[SortField] = Query("name", description="Поле для сортировки"),
    include_images: bool = Query(False, description="Включить изображения"),
    include_attributes: bool = Query(False, description="Включить атрибуты"),
):
    """
    Получить список товаров с фильтрацией, сортировкой и пагинацией.
    
    Args:
        db: Сессия базы данных
        page: Номер страницы
        page_size: Размер страницы
        category_id: Фильтр по ID категории
        q: Поисковый запрос по названию
        price_min: Минимальная цена
        price_max: Максимальная цена
        sort: Поле для сортировки
        include_images: Включить изображения товаров
        include_attributes: Включить атрибуты товаров
        
    Returns:
        dict: Список товаров с метаданными пагинации
    """
    # Формирование условий WHERE
    conditions = []
    if category_id is not None:
        conditions.append(Product.category_id == category_id)
    if q:
        conditions.append(Product.name.ilike(f"%{q}%"))
    if price_min is not None:
        conditions.append(Product.price_cents >= price_min)
    if price_max is not None:
        conditions.append(Product.price_cents <= price_max)
    where_clause = and_(*conditions) if conditions else None

    # Подсчет общего количества (отдельно, без ORDER/LIMIT)
    count_stmt = select(func.count()).select_from(Product)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = db.scalar(count_stmt) or 0

    # Основной запрос
    stmt = select(Product)
    if where_clause is not None:
        stmt = stmt.where(where_clause)

    # Предзагрузка связей (чтобы избежать ленивых обращений)
    if include_images:
        stmt = stmt.options(selectinload(Product.images))
    if include_attributes:
        stmt = stmt.options(selectinload(Product.attributes))

    # Сортировка
    if sort in ("name", "-name"):
        order = asc(Product.name) if sort == "name" else desc(Product.name)
    else:
        price_col = Product.price_cents
        order = asc(price_col).nulls_last() if sort == "price" else desc(price_col).nulls_last()
    stmt = stmt.order_by(order)

    # Пагинация
    offset = (page - 1) * page_size
    rows = db.scalars(stmt.offset(offset).limit(page_size)).all()

    # Формирование ответа
    items: List[Dict[str, Any]] = []
    
    for product in rows:
        item = {
            "id": product.id,
            "category_id": product.category_id,
            "name": product.name,
            "price_raw": product.price_raw,
            "price_cents": product.price_cents,
            "description": product.description,
        }
        
        # Добавление изображений
        if include_images:
            images = sorted(
                product.images,
                key=lambda x: (not x.is_primary, x.sort_order, x.id)
            )
            item["images"] = []
            for img in images:
                urls = image_service.generate_urls(img.path)
                image_data = {
                    "id": img.id,
                    "path": img.path,
                    "filename": img.filename,
                    "sort_order": img.sort_order,
                    "is_primary": img.is_primary,
                    "status": img.status,
                    "url": urls.get('original'),
                    "urls": urls,
                    "file_size": img.file_size,
                    "mime_type": img.mime_type,
                    "width": img.width,
                    "height": img.height,
                    "alt_text": img.alt_text,
                }
                item["images"].append(image_data)
            
        # Добавление атрибутов
        if include_attributes:
            item["attributes"] = [
                {"id": attr.id, "key": attr.attr_key, "value": attr.value}
                for attr in product.attributes
            ]
            
        items.append(item)

    meta_data = PageMeta.create(page=page, page_size=page_size, total=total).model_dump()
    print(f"🔍 Products API Meta: {meta_data}")
    
    return {
        "items": items,
        "meta": meta_data,
    }


@router.get("/{product_id}", response_model=dict)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    include_images: bool = Query(False, description="Включить изображения"),
    include_attributes: bool = Query(False, description="Включить атрибуты"),
):
    """
    Получить товар по ID.
    
    Args:
        product_id: ID товара
        db: Сессия базы данных
        include_images: Включить изображения товара
        include_attributes: Включить атрибуты товара
        
    Returns:
        dict: Данные товара
        
    Raises:
        HTTPException: Если товар не найден
    """
    stmt = select(Product).where(Product.id == product_id)
    if include_images:
        stmt = stmt.options(selectinload(Product.images))
    if include_attributes:
        stmt = stmt.options(selectinload(Product.attributes))
        
    product = db.scalar(stmt)
    if not product:
        raise HTTPException(404, detail="product not found")

    # Формирование ответа
    item: Dict[str, Any] = {
        "id": product.id,
        "category_id": product.category_id,
        "name": product.name,
        "price_raw": product.price_raw,
        "price_cents": product.price_cents,
        "description": product.description,
    }
    
    # Добавление изображений
    if include_images:
        images = sorted(
            product.images,
            key=lambda x: (not x.is_primary, x.sort_order, x.id)
        )
        item["images"] = []
        for img in images:
            urls = image_service.generate_urls(img.path)
            image_data = {
                "id": img.id,
                "path": img.path,
                "filename": img.filename,
                "sort_order": img.sort_order,
                "is_primary": img.is_primary,
                "status": img.status,
                "url": urls.get('original'),
                "urls": urls,
                "file_size": img.file_size,
                "mime_type": img.mime_type,
                "width": img.width,
                "height": img.height,
                "alt_text": img.alt_text,
            }
            item["images"].append(image_data)
        
    # Добавление атрибутов
    if include_attributes:
        item["attributes"] = [
            {"id": attr.id, "key": attr.attr_key, "value": attr.value}
            for attr in product.attributes
        ]

    return item
