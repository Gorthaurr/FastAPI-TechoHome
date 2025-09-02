"""
API эндпоинты для административной панели.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.core.auth import (
    auth_service,
    get_current_active_user,
    require_admin,
    require_super_admin,
)
from app.db.database import get_db
from app.db.models.category import Category
from app.db.models.order import Order, OrderItem
from app.db.models.product import Product
from app.db.models.product_image import ProductImage
from app.db.models.user import User
from app.schemas.admin import (
    AdminSearchParams,
    BulkActionRequest,
    ChangePasswordRequest,
    DashboardStats,
    LoginRequest,
    LoginResponse,
    OrderStats,
    ProductStats,
    SettingsUpdate,
    SystemSettings,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter()


# ==================== ТЕСТОВЫЙ ЭНДПОИНТ ====================


@router.get("/test")
async def test_endpoint():
    """Тестовый эндпоинт для проверки работы роутера"""
    return {"message": "Admin router is working", "status": "ok"}


# ==================== АУТЕНТИФИКАЦИЯ ====================


@router.post("/auth/login", response_model=LoginResponse)
async def admin_login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Вход в административную панель.

    Args:
        login_data: Данные для входа (username, password)
        db: Сессия базы данных

    Returns:
        JWT токен и информация о пользователе

    Raises:
        HTTPException: При неверных учетных данных
    """
    print(f"Login attempt for username: {login_data.username}")

    # Ищем пользователя по username или email
    user = (
        db.query(User)
        .filter(
            or_(User.username == login_data.username, User.email == login_data.username)
        )
        .first()
    )

    print(f"User found: {user is not None}")
    if user:
        print(
            f"User ID: {user.id}, Username: {user.username}, is_admin: {user.is_admin}, is_super_admin: {user.is_super_admin}"
        )

    if not user or not auth_service.verify_password(
        login_data.password, user.hashed_password
    ):
        print("Password verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    print("Password verified successfully")

    if not user.is_active:
        print("User account is disabled")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User account is disabled"
        )

    if not user.is_admin and not user.is_super_admin:
        print("User doesn't have admin privileges")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required.",
        )

    print("User has admin privileges")

    # Обновляем время последнего входа
    user.last_login = datetime.utcnow()
    db.commit()

    # Создаем JWT токен
    print("Creating JWT token...")
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    print(f"JWT token created: {access_token[:20]}...")

    # Создаем UserOut объект
    print("Creating UserOut object...")
    user_out = UserOut.from_orm(user)
    print(f"UserOut created: {user_out}")

    # Создаем ответ
    response = LoginResponse(
        access_token=access_token, expires_in=480 * 60, user=user_out  # 8 часов
    )
    print(f"LoginResponse created: {response}")

    return response


@router.post("/auth/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Смена пароля текущего пользователя.

    Args:
        password_data: Текущий и новый пароль
        current_user: Текущий пользователь
        db: Сессия базы данных

    Returns:
        Сообщение об успешной смене пароля
    """
    if not auth_service.verify_password(
        password_data.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = auth_service.get_password_hash(
        password_data.new_password
    )
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Password changed successfully"}


# ==================== ПОЛЬЗОВАТЕЛИ ====================


@router.get("/users/profile", response_model=UserOut)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """
    Получить профиль текущего пользователя.

    Args:
        current_user: Текущий пользователь

    Returns:
        Профиль текущего пользователя
    """
    return current_user


@router.get("/users", response_model=dict)
async def list_users(
    q: Optional[str] = Query(None, description="Поиск по username или email"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    role: Optional[str] = Query(None, description="Фильтр по роли"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Получить список пользователей с фильтрацией и пагинацией.

    Args:
        q: Поисковый запрос
        page: Номер страницы
        page_size: Размер страницы
        is_active: Фильтр по активности
        role: Фильтр по роли
        current_user: Текущий пользователь (должен быть админом)
        db: Сессия базы данных

    Returns:
        Список пользователей с метаданными пагинации
    """
    try:
        query = db.query(User)

        # Применяем фильтры
        if q:
            query = query.filter(
                or_(
                    User.username.ilike(f"%{q}%"),
                    User.email.ilike(f"%{q}%"),
                    User.full_name.ilike(f"%{q}%"),
                )
            )

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if role:
            if role == "admin":
                query = query.filter(User.is_admin == True)
            elif role == "super_admin":
                query = query.filter(User.is_super_admin == True)
            elif role == "user":
                query = query.filter(User.is_admin == False, User.is_super_admin == False)

        # Применяем пагинацию и сортировку
        total = query.count()
        users = (
            query.order_by(desc(User.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # Формируем ответ с правильным форматом
        items = []
        for user in users:
            items.append({
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "notes": user.notes,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "is_super_admin": user.is_super_admin,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "avatar_url": user.avatar_url,
            })

        return {
            "items": items,
            "meta": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    
    except Exception as e:
        print(f"Error fetching users: {e}")
        # Возвращаем пустой результат в случае ошибки
        return {
            "items": [],
            "meta": {
                "page": page,
                "page_size": page_size,
                "total": 0,
                "total_pages": 0,
            },
        }


@router.post("/users", response_model=UserOut)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Создать нового пользователя.

    Args:
        user_data: Данные для создания пользователя
        current_user: Текущий пользователь (должен быть супер-админом)
        db: Сессия базы данных

    Returns:
        Созданный пользователь
    """
    # Проверяем уникальность email и username
    existing_user = (
        db.query(User)
        .filter(or_(User.email == user_data.email, User.username == user_data.username))
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        )

    # Создаем нового пользователя
    hashed_password = auth_service.get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        notes=user_data.notes,
        is_active=user_data.is_active,
        is_admin=user_data.is_admin,
        is_super_admin=user_data.is_super_admin,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Получить информацию о пользователе.

    Args:
        user_id: ID пользователя
        current_user: Текущий пользователь (должен быть админом)
        db: Сессия базы данных

    Returns:
        Информация о пользователе
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Обновить информацию о пользователе.

    Args:
        user_id: ID пользователя
        user_data: Данные для обновления
        current_user: Текущий пользователь (должен быть админом)
        db: Сессия базы данных

    Returns:
        Обновленный пользователь
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Обновляем поля
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Удалить пользователя.

    Args:
        user_id: ID пользователя
        current_user: Текущий пользователь (должен быть супер-админом)
        db: Сессия базы данных

    Returns:
        Сообщение об успешном удалении
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


# ==================== ДАШБОРД ====================


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """
    Получить статистику для дашборда.

    Args:
        current_user: Текущий пользователь (должен быть админом)
        db: Сессия базы данных

    Returns:
        Статистика дашборда
    """
    # Статистика по пользователям (с обработкой ошибок)
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active.is_(True)).count()
        admin_users = db.query(User).filter(User.is_admin.is_(True)).count()
        super_admin_users = db.query(User).filter(User.is_super_admin.is_(True)).count()
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        total_users = active_users = admin_users = super_admin_users = 0

    # Статистика по продуктам
    total_products = db.query(Product).count()
    active_products = total_products  # Убираем is_active так как его нет в модели

    # Быстрый подсчет продуктов с изображениями
    from sqlalchemy import select
    products_with_images = db.scalar(
        select(func.count(func.distinct(ProductImage.product_id))).select_from(ProductImage)
    ) or 0
    products_without_images = total_products - products_with_images

    product_stats = ProductStats(
        total_products=total_products,
        active_products=active_products,
        products_with_images=products_with_images,
        products_without_images=products_without_images,
    )

    # Статистика по заказам
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == "pending").count()
    completed_orders = db.query(Order).filter(Order.status == "completed").count()
    cancelled_orders = db.query(Order).filter(Order.status == "cancelled").count()

    # Подсчет общей выручки в центах, переводим в рубли
    revenue_result = (
        db.query(func.sum(Order.total_cents))
        .filter(Order.status == "completed")
        .scalar()
    )
    total_revenue = float(revenue_result / 100) if revenue_result else 0.0

    order_stats = OrderStats(
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        total_revenue=total_revenue,
    )

    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        super_admin_users=super_admin_users,
        product_stats=product_stats,
        order_stats=order_stats,
    )


# ==================== МАССОВЫЕ ОПЕРАЦИИ ====================


@router.post("/bulk-actions")
async def bulk_actions(
    bulk_data: BulkActionRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Выполнить массовые операции.

    Args:
        bulk_data: Данные для массовых операций
        current_user: Текущий пользователь (должен быть админом)
        db: Сессия базы данных

    Returns:
        Результат выполнения операций
    """
    if bulk_data.action == "delete":
        # Удаление пользователей
        users_to_delete = db.query(User).filter(User.id.in_(bulk_data.ids)).all()
        for user in users_to_delete:
            if user.id != current_user.id:  # Нельзя удалить себя
                db.delete(user)

        db.commit()
        return {"message": f"Deleted {len(users_to_delete)} users"}

    elif bulk_data.action == "activate":
        # Активация пользователей
        result = (
            db.query(User)
            .filter(User.id.in_(bulk_data.ids))
            .update(
                {"is_active": True, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )
        )
        db.commit()
        return {"message": f"Activated {result} users"}

    elif bulk_data.action == "deactivate":
        # Деактивация пользователей
        result = (
            db.query(User)
            .filter(User.id.in_(bulk_data.ids))
            .update(
                {"is_active": False, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )
        )
        db.commit()
        return {"message": f"Deactivated {result} users"}

    elif bulk_data.action == "move_category":
        # Перемещение продуктов в категорию
        if not bulk_data.category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category ID required for move_category action",
            )

        result = (
            db.query(Product)
            .filter(Product.id.in_(bulk_data.ids))
            .update(
                {"category_id": bulk_data.category_id, "updated_at": datetime.utcnow()},
                synchronize_session=False,
            )
        )
        db.commit()
        return {"message": f"Moved {result} products to category"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action"
    )


# ==================== УПРАВЛЕНИЕ КАТЕГОРИЯМИ ====================


@router.get("/categories", response_model=List[dict])
async def admin_list_categories(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Получить список категорий для админки с быстрым подсчетом продуктов.
    """
    from app.db.models import Category, Product
    from sqlalchemy import select, func
    
    # Один оптимизированный запрос с LEFT JOIN для подсчета продуктов
    stmt = (
        select(
            Category.id,
            Category.slug,
            func.coalesce(func.count(Product.id), 0).label("products_count")
        )
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id, Category.slug)
        .order_by(Category.slug)
    )
    
    results = db.execute(stmt).all()
    
    return [
        {
            "id": row.id,
            "slug": row.slug,
            "products_count": row.products_count,
        }
        for row in results
    ]


@router.post("/categories", response_model=dict)
async def admin_create_category(
    category_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Создать новую категорию.
    """
    from app.db.models import Category
    
    # Проверяем уникальность slug
    existing = db.query(Category).filter(Category.slug == category_data.get("slug")).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this slug already exists"
        )
    
    new_category = Category(
        slug=category_data.get("slug"),
    )
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return {
        "id": new_category.id,
        "slug": new_category.slug,
        "products_count": 0,
    }


@router.put("/categories/{category_id}", response_model=dict)
async def admin_update_category(
    category_id: int,
    category_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Обновить категорию.
    """
    from app.db.models import Category
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    
    # Проверяем уникальность slug если он изменился
    new_slug = category_data.get("slug")
    if new_slug and new_slug != category.slug:
        existing = db.query(Category).filter(Category.slug == new_slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this slug already exists"
            )
        category.slug = new_slug
    
    db.commit()
    db.refresh(category)
    
    return {
        "id": category.id,
        "slug": category.slug,
    }


@router.delete("/categories/{category_id}")
async def admin_delete_category(
    category_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Удалить категорию.
    """
    from app.db.models import Category, Product
    from sqlalchemy import select, func
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    
    # Быстрая проверка количества продуктов
    products_count = db.scalar(
        select(func.count(Product.id)).where(Product.category_id == category_id)
    ) or 0
    
    if products_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category with {products_count} products"
        )
    
    db.delete(category)
    db.commit()
    
    return {"message": "Category deleted successfully"}


# ==================== УПРАВЛЕНИЕ ПРОДУКТАМИ ====================


@router.get("/products", response_model=dict)
async def admin_list_products(
    q: Optional[str] = Query(None, description="Поиск по названию"),
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Получить список продуктов для админки.
    """
    from app.db.models import Product, Category
    from sqlalchemy import select, func, and_
    from sqlalchemy.orm import selectinload
    
    # Формирование условий WHERE
    conditions = []
    if category_id is not None:
        conditions.append(Product.category_id == category_id)
    if q:
        conditions.append(Product.name.ilike(f"%{q}%"))
    where_clause = and_(*conditions) if conditions else None

    # Подсчет общего количества
    count_stmt = select(func.count()).select_from(Product)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = db.scalar(count_stmt) or 0

    # Основной запрос без лишних JOIN'ов
    stmt = select(Product)
    if where_clause is not None:
        stmt = stmt.where(where_clause)

    # Пагинация
    offset = (page - 1) * page_size
    products = db.scalars(stmt.offset(offset).limit(page_size)).all()

    # Формирование ответа
    items = []
    for product in products:
        # Быстрый подсчет изображений
        images_count = db.scalar(
            select(func.count()).select_from(ProductImage).where(ProductImage.product_id == product.id)
        ) or 0
        
        # Получаем название категории отдельным запросом только если нужно
        category_name = None
        if product.category_id:
            category = db.scalar(select(Category.slug).where(Category.id == product.category_id))
            category_name = category
        
        item = {
            "id": product.id,
            "name": product.name,
            "category_id": product.category_id,
            "category_name": category_name,
            "price_raw": product.price_raw,
            "price_cents": product.price_cents,
            "description": product.description,
            "product_url": product.product_url,
            "images_count": images_count,
            "has_images": images_count > 0,
        }
        items.append(item)

    return {
        "items": items,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("/products", response_model=dict)
async def admin_create_product(
    product_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Создать новый продукт.
    """
    from app.db.models import Product
    import uuid
    
    # Генерируем уникальный ID
    product_id = str(uuid.uuid4())
    
    new_product = Product(
        id=product_id,
        name=product_data.get("name"),
        category_id=product_data.get("category_id"),
        price_raw=product_data.get("price_raw"),
        price_cents=product_data.get("price_cents"),
        description=product_data.get("description"),
        product_url=product_data.get("product_url"),
    )
    
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return {
        "id": new_product.id,
        "name": new_product.name,
        "category_id": new_product.category_id,
        "price_raw": new_product.price_raw,
        "price_cents": new_product.price_cents,
        "description": new_product.description,
        "product_url": new_product.product_url,
    }


@router.get("/products/{product_id}", response_model=dict)
async def admin_get_product(
    product_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Получить детали продукта.
    """
    from app.db.models import Product, Category
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    product = db.scalar(
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.attributes))
        .where(Product.id == product_id)
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    
    # Получаем категорию
    category_name = None
    if product.category_id:
        category = db.scalar(select(Category.slug).where(Category.id == product.category_id))
        category_name = category
    
    # Формируем ответ
    images = []
    for img in product.images:
        images.append({
            "id": img.id,
            "path": img.path,
            "filename": img.filename,
            "is_primary": img.is_primary,
            "sort_order": img.sort_order,
            "status": img.status,
        })
    
    attributes = []
    for attr in product.attributes:
        attributes.append({
            "id": attr.id,
            "key": attr.attr_key,
            "value": attr.value,
        })
    
    return {
        "id": product.id,
        "name": product.name,
        "category_id": product.category_id,
        "category_name": category_name,
        "price_raw": product.price_raw,
        "price_cents": product.price_cents,
        "description": product.description,
        "product_url": product.product_url,
        "images": images,
        "attributes": attributes,
    }


@router.put("/products/{product_id}", response_model=dict)
async def admin_update_product(
    product_id: str,
    product_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Обновить продукт.
    """
    from app.db.models import Product
    from sqlalchemy import select
    
    product = db.scalar(select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    
    # Обновляем только переданные поля
    for field, value in product_data.items():
        if hasattr(product, field) and value is not None:
            setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    return {
        "id": product.id,
        "name": product.name,
        "category_id": product.category_id,
        "price_raw": product.price_raw,
        "price_cents": product.price_cents,
        "description": product.description,
        "product_url": product.product_url,
    }


@router.delete("/products/{product_id}")
async def admin_delete_product(
    product_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Удалить продукт.
    """
    from app.db.models import Product
    from sqlalchemy import select
    
    product = db.scalar(select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    
    db.delete(product)
    db.commit()
    
    return {"message": "Product deleted successfully"}


@router.put("/products/{product_id}/images/{image_id}/primary")
async def admin_set_primary_image(
    product_id: str,
    image_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Установить изображение как главное.
    """
    from app.db.models import ProductImage
    from sqlalchemy import select
    
    # Проверяем существование изображения
    image = db.scalar(
        select(ProductImage).where(
            ProductImage.id == image_id,
            ProductImage.product_id == product_id
        )
    )
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    
    # Снимаем флаг главного с других изображений этого продукта
    other_images = db.scalars(
        select(ProductImage).where(
            ProductImage.product_id == product_id,
            ProductImage.id != image_id,
            ProductImage.is_primary == True
        )
    ).all()
    
    for other_img in other_images:
        other_img.is_primary = False
    
    # Устанавливаем текущее как главное
    image.is_primary = True
    
    db.commit()
    
    return {"message": "Primary image updated successfully", "image_id": image_id}


@router.post("/fix-sequences")
async def fix_database_sequences(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Исправить рассинхронизированные sequences в PostgreSQL.
    """
    from sqlalchemy import text
    
    try:
        # Исправляем sequence для product_images
        db.execute(text("""
            SELECT setval('product_images_id_seq', 
                COALESCE((SELECT MAX(id) FROM product_images), 0) + 1, false);
        """))
        
        # Исправляем sequence для categories если нужно
        db.execute(text("""
            SELECT setval('categories_id_seq', 
                COALESCE((SELECT MAX(id) FROM categories), 0) + 1, false);
        """))
        
        db.commit()
        
        return {
            "message": "Database sequences fixed successfully",
            "fixed_sequences": ["product_images_id_seq", "categories_id_seq"]
        }
        
    except Exception as e:
        return {
            "error": f"Failed to fix sequences: {str(e)}",
            "message": "Try restarting the database or contact administrator"
        }


@router.post("/products/{product_id}/images/upload")
async def admin_upload_image(
    product_id: str,
    file: UploadFile = File(...),
    alt_text: str = Form(""),
    sort_order: int = Form(0),
    is_primary: bool = Form(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Загрузка изображения через админку.
    """
    import tempfile
    import os
    from app.services.image_service import image_service
    from app.services.storage_service import storage_service
    
    # Проверяем существование товара
    from sqlalchemy import select
    product = db.scalar(select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(404, detail="Product not found")

    # Валидируем файл
    is_valid, error_message = image_service.validate_file(file.filename, file.size)
    if not is_valid:
        raise HTTPException(400, detail=error_message)

    try:
        # Читаем содержимое файла
        content = await file.read()
        
        # Простое сохранение в uploads
        from pathlib import Path
        from app.core.config import settings
        
        # Создаем структуру папок
        upload_dir = Path(settings.STORAGE_PATH) / "products" / product_id[:8] / product_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем файл
        file_path = upload_dir / file.filename
        with open(file_path, 'wb') as f:
            f.write(content)

        # Относительный путь для БД
        relative_path = f"products/{product_id[:8]}/{product_id}/{file.filename}"
        
        # Создаем запись в БД (только обязательные поля)
        image = ProductImage()
        image.product_id = product_id
        image.path = relative_path
        image.filename = file.filename
        image.sort_order = sort_order
        image.is_primary = is_primary
        image.status = "ready"
        image.file_size = file.size
        image.alt_text = alt_text or f"Изображение для {product.name}"

        # Если это главное изображение, сначала снимаем флаг с других
        if is_primary:
            other_images = db.scalars(
                select(ProductImage).where(
                    ProductImage.product_id == product_id,
                    ProductImage.is_primary == True
                )
            ).all()

            for other_image in other_images:
                other_image.is_primary = False

        db.add(image)
        db.commit()
        db.refresh(image)  # Получаем ID после commit

        return {
            "id": image.id,
            "product_id": image.product_id,
            "filename": image.filename,
            "path": image.path,
            "status": image.status,
            "message": "Image uploaded successfully",
        }

    except Exception as e:
        # Очистка при ошибке - удаляем файл если он был создан
        try:
            if 'file_path' in locals() and file_path.exists():
                file_path.unlink()
        except:
            pass
        raise HTTPException(500, detail=f"Upload failed: {str(e)}")


# ==================== УПРАВЛЕНИЕ ЗАКАЗАМИ ====================


@router.get("/orders", response_model=dict)
async def admin_list_orders(
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Получить список заказов для админки.
    """
    from app.db.models import Order, OrderItem
    from sqlalchemy import select, func, desc
    
    # Формируем условия
    conditions = []
    if status_filter:
        conditions.append(Order.status == status_filter)
    where_clause = and_(*conditions) if conditions else None
    
    # Подсчет общего количества
    count_stmt = select(func.count()).select_from(Order)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = db.scalar(count_stmt) or 0
    
    # Основной запрос заказов
    stmt = select(Order).order_by(desc(Order.created_at))
    if where_clause is not None:
        stmt = stmt.where(where_clause)
    
    # Пагинация
    offset = (page - 1) * page_size
    orders = db.scalars(stmt.offset(offset).limit(page_size)).all()
    
    # Формируем ответ
    items = []
    for order in orders:
        # Быстрый подсчет позиций заказа
        items_count = db.scalar(
            select(func.count(OrderItem.id)).where(OrderItem.order_id == order.id)
        ) or 0
        
        items.append({
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
            "created_at": str(order.created_at),
            "updated_at": str(order.updated_at),
            "items_count": items_count,
        })
    
    return {
        "items": items,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/orders/{order_id}", response_model=dict)
async def admin_get_order(
    order_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Получить детали заказа.
    """
    from app.db.models import Order
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    
    items = []
    for item in order.items:
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "qty": item.qty,
            "item_name": item.item_name,
            "item_price_cents": item.item_price_cents,
        })
    
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
        "created_at": str(order.created_at),
        "updated_at": str(order.updated_at),
        "items": items,
    }


@router.put("/orders/{order_id}/status")
async def admin_update_order_status(
    order_id: str,
    status_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Обновить статус заказа.
    """
    from app.db.models import Order
    from sqlalchemy import select
    
    order = db.scalar(select(Order).where(Order.id == order_id))
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    
    new_status = status_data.get("status")
    if new_status not in ["pending", "paid", "canceled", "shipped", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status"
        )
    
    order.status = new_status
    order.updated_at = datetime.utcnow().isoformat()
    
    db.commit()
    db.refresh(order)
    
    return {
        "id": order.id,
        "status": order.status,
        "updated_at": order.updated_at,
    }


@router.put("/orders/{order_id}", response_model=dict)
async def admin_update_order(
    order_id: str,
    order_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Обновить заказ (данные клиента, адрес и т.д.).
    """
    from app.db.models import Order
    from sqlalchemy import select
    
    order = db.scalar(select(Order).where(Order.id == order_id))
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    
    # Обновляем только переданные поля
    allowed_fields = [
        "customer_name", "customer_email", "customer_phone",
        "shipping_address", "shipping_city", "shipping_postal_code",
        "comment", "shipping_cents"
    ]
    
    for field, value in order_data.items():
        if field in allowed_fields and hasattr(order, field):
            setattr(order, field, value)
    
    order.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(order)
    
    return {
        "id": order.id,
        "status": order.status,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "updated_at": order.updated_at,
    }


# ==================== СИСТЕМНЫЕ НАСТРОЙКИ ====================


@router.get("/settings", response_model=SystemSettings)
async def get_system_settings(
    current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)
):
    """
    Получить системные настройки.

    Args:
        current_user: Текущий пользователь (должен быть супер-админом)
        db: Сессия базы данных

    Returns:
        Системные настройки
    """
    # Здесь можно добавить логику получения настроек из БД
    return SystemSettings()


@router.put("/settings")
async def update_system_settings(
    settings_data: SettingsUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Обновить системные настройки.

    Args:
        settings_data: Новые настройки
        current_user: Текущий пользователь (должен быть супер-админом)
        db: Сессия базы данных

    Returns:
        Сообщение об успешном обновлении
    """
    # Здесь можно добавить логику сохранения настроек в БД
    return {"message": "Settings updated successfully"}
