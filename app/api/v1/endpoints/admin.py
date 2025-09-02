"""
API эндпоинты для административной панели.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_
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
        access_token=access_token, expires_in=30 * 60, user=user_out  # 30 минут
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


@router.get("/users", response_model=List[UserOut])
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
        Список пользователей
    """
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

    return users


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
    # Статистика по пользователям
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    admin_users = db.query(User).filter(User.is_admin.is_(True)).count()
    super_admin_users = db.query(User).filter(User.is_super_admin.is_(True)).count()

    # Статистика по продуктам
    total_products = db.query(Product).count()
    active_products = db.query(Product).filter(Product.is_active.is_(True)).count()

    # Подсчет продуктов с изображениями
    products_with_images = db.query(Product).join(ProductImage).distinct().count()
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

    # Подсчет общей выручки
    revenue_result = (
        db.query(func.sum(Order.total_amount))
        .filter(Order.status == "completed")
        .scalar()
    )
    total_revenue = float(revenue_result) if revenue_result else 0.0

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
