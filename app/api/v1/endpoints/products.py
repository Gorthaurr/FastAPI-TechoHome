"""
API endpoints для работы с товарами.

Содержит CRUD операции для товаров с поддержкой фильтрации,
сортировки, пагинации и управления изображениями.
"""

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, asc, case, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.database import get_db
from app.db.models import Product
from app.schemas.pagination import PageMeta
from app.services.storage_service import storage_service

router = APIRouter()

# Типы для сортировки
SortField = Literal["name", "-name", "price", "-price"]


@router.get("", response_model=dict)
def list_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
    brand: Optional[str] = Query(None, description="Фильтр по бренду"),
    heating_types: Optional[str] = Query(None, description="Фильтр по типам нагрева (через запятую)"),
    q: Optional[str] = Query(None, description="Поиск по названию (ILIKE)"),
    price_min: Optional[int] = Query(
        None, ge=0, description="Минимальная цена в центах"
    ),
    price_max: Optional[int] = Query(
        None, ge=0, description="Максимальная цена в центах"
    ),
    sort: Optional[SortField] = Query("name", description="Поле для сортировки"),
    include_images: bool = Query(False, description="Включить изображения"),
    include_attributes: bool = Query(False, description="Включить атрибуты"),
):
    """
    Получить список товаров с фильтрацией, сортировкой и пагинацией.

    Поддерживает:
    - Фильтрацию по категории, цене и поисковому запросу
    - Сортировку по названию и цене
    - Пагинацию результатов
    - Включение связанных данных (изображения, атрибуты)

    Args:
        db: Сессия базы данных
        page: Номер страницы (начиная с 1)
        page_size: Размер страницы (1-100)
        category_id: Фильтр по ID категории
        q: Поисковый запрос по названию (регистронезависимый)
        price_min: Минимальная цена в центах
        price_max: Максимальная цена в центах
        sort: Поле для сортировки (name, -name, price, -price)
        include_images: Включить изображения товаров
        include_attributes: Включить атрибуты товаров

    Returns:
        dict: Список товаров с метаданными пагинации

    Raises:
        HTTPException: При некорректных параметрах запроса
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
    
    # Фильтр по бренду через атрибуты
    brand_product_ids = None
    if brand:
        from app.db.models import ProductAttribute
        brand_stmt = select(ProductAttribute.product_id).where(
            and_(
                ProductAttribute.attr_key == 'Бренд',
                ProductAttribute.value == brand
            )
        )
        brand_product_ids = set(db.scalars(brand_stmt).all())
        if brand_product_ids:
            conditions.append(Product.id.in_(brand_product_ids))
        else:
            # Если бренд не найден, возвращаем пустой результат
            conditions.append(Product.id == None)
    
    # Фильтр по типам нагрева
    if heating_types:
        from app.db.models import ProductAttribute
        heating_list = [h.strip() for h in heating_types.split(',') if h.strip()]
        if heating_list:
            heating_stmt = select(ProductAttribute.product_id).where(
                and_(
                    ProductAttribute.attr_key == 'Тип панели',
                    func.lower(ProductAttribute.value).in_([h.lower() for h in heating_list])
                )
            )
            heating_product_ids = set(db.scalars(heating_stmt).all())
            if heating_product_ids:
                conditions.append(Product.id.in_(heating_product_ids))
            else:
                conditions.append(Product.id == None)
    
    where_clause = and_(*conditions) if conditions else None

    # Подсчет общего количества (отдельно, без ORDER/LIMIT)
    count_stmt = select(func.count()).select_from(Product)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = db.scalar(count_stmt) or 0

    # Основной запрос - ОПТИМИЗИРОВАННЫЙ с JOIN для изображений (только главное)
    from app.db.models import ProductImage
    
    # Всегда делаем JOIN с изображениями для сортировки по их наличию
    stmt = select(Product).outerjoin(
        ProductImage, 
        and_(
            Product.id == ProductImage.product_id,
            ProductImage.is_primary == True
        )
    )
    
    if where_clause is not None:
        stmt = stmt.where(where_clause)

    # Сортировка: сначала по наличию изображений, потом по выбранному полю
    # Создаем CASE для сортировки: товары с изображениями (1) перед товарами без (0)
    has_images_order = case(
        (ProductImage.id.isnot(None), 0),  # Товары С изображениями идут первыми (0 меньше 1)
        else_=1  # Товары БЕЗ изображений идут вторыми
    )
    
    # Основная сортировка по выбранному полю
    if sort in ("name", "-name"):
        main_order = asc(Product.name) if sort == "name" else desc(Product.name)
    else:
        price_col = Product.price_cents
        main_order = (
            asc(price_col).nulls_last()
            if sort == "price"
            else desc(price_col).nulls_last()
        )
    
    # Применяем сортировку: сначала по наличию изображений, потом по основному полю
    stmt = stmt.order_by(has_images_order, main_order)

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

        # Добавление изображений - ТОЛЬКО ГЛАВНОЕ для производительности
        if include_images:
            # Ищем главное изображение из JOIN'а
            primary_image = None
            for attr_name in dir(product):
                if 'image' in attr_name.lower() and hasattr(getattr(product, attr_name), 'is_primary'):
                    img = getattr(product, attr_name)
                    if img and img.is_primary:
                        primary_image = img
                        break
            
            # Если не нашли в JOIN, делаем быстрый запрос только для главного изображения
            if not primary_image:
                from app.db.models import ProductImage
                img_stmt = select(ProductImage).where(
                    and_(
                        ProductImage.product_id == product.id,
                        ProductImage.is_primary == True
                    )
                ).limit(1)
                primary_image = db.scalar(img_stmt)
            
            item["images"] = []
            if primary_image:
                presigned_url = storage_service.get_file_url(primary_image.path)
                image_data = {
                    "id": primary_image.id,
                    "path": primary_image.path,
                    "filename": primary_image.filename,
                    "sort_order": primary_image.sort_order,
                    "is_primary": primary_image.is_primary,
                    "status": primary_image.status,
                    "url": presigned_url,
                    "urls": {"original": presigned_url},
                    "file_size": primary_image.file_size,
                    "mime_type": primary_image.mime_type,
                    "width": primary_image.width,
                    "height": primary_image.height,
                    "alt_text": primary_image.alt_text,
                }
                item["images"].append(image_data)
        else:
            item["images"] = []

        # Добавление атрибутов - ТОЛЬКО ОСНОВНЫЕ для производительности
        if include_attributes:
            # Загружаем только ключевые атрибуты для списка товаров
            from app.db.models import ProductAttribute
            attr_stmt = select(ProductAttribute).where(
                ProductAttribute.product_id == product.id
            ).limit(10)  # Берем все основные атрибуты
            attributes = db.scalars(attr_stmt).all()
            item["attributes"] = [
                {"id": attr.id, "key": attr.attr_key, "value": attr.value}
                for attr in attributes
            ]
        else:
            item["attributes"] = []

        items.append(item)

    # Формирование метаданных пагинации
    meta_data = PageMeta.create(
        page=page, page_size=page_size, total=total
    ).model_dump()

    return {
        "items": items,
        "meta": meta_data,
    }


@router.get("/brands", response_model=list)
def get_brands(
    db: Session = Depends(get_db),
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
):
    """
    Получить список уникальных брендов.
    
    Возвращает список уникальных брендов из атрибутов товаров.
    Опционально можно фильтровать по категории.
    """
    from app.db.models import ProductAttribute
    
    # Запрос для получения уникальных брендов
    stmt = select(ProductAttribute.value).distinct().where(
        ProductAttribute.attr_key == 'Бренд'
    )
    
    # Фильтр по категории если указан
    if category_id is not None:
        from app.db.models import Product
        stmt = stmt.join(Product).where(Product.category_id == category_id)
    
    brands = db.scalars(stmt).all()
    
    # Фильтруем и сортируем
    filtered_brands = [b for b in brands if b and b.strip()]
    filtered_brands.sort()
    
    return filtered_brands


@router.get("/{product_id}", response_model=dict)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    include_images: bool = Query(False, description="Включить изображения"),
    include_attributes: bool = Query(False, description="Включить атрибуты"),
):
    """
    Получить товар по ID.

    Возвращает полную информацию о товаре с возможностью
    включения связанных данных (изображения, атрибуты).

    Args:
        product_id: ID товара
        db: Сессия базы данных
        include_images: Включить изображения товара
        include_attributes: Включить атрибуты товара

    Returns:
        dict: Данные товара с включенными связями

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
        raise HTTPException(404, detail="Product not found")

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
            product.images, key=lambda x: (not x.is_primary, x.sort_order, x.id)
        )
        item["images"] = []
        for img in images:
            # Используем storage_service для генерации presigned URL
            presigned_url = storage_service.get_file_url(img.path)
            image_data = {
                "id": img.id,
                "path": img.path,
                "filename": img.filename,
                "sort_order": img.sort_order,
                "is_primary": img.is_primary,
                "status": img.status,
                "url": presigned_url,
                "urls": {"original": presigned_url},
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
