# Руководство по стилю кода FastAPI

## Общие принципы

### 1. Единообразие
- Все файлы должны следовать единому стилю именования и форматирования
- Используйте консистентные отступы и пробелы
- Соблюдайте принятые в проекте соглашения

### 2. Читаемость
- Код должен быть самодокументируемым
- Используйте понятные имена переменных и функций
- Добавляйте комментарии для сложной логики

### 3. Поддерживаемость
- Разделяйте код на логические блоки
- Избегайте дублирования кода
- Следуйте принципу единственной ответственности

## Python/FastAPI (Backend)

### Именование

#### Файлы и папки
```
app/
├── api/
│   └── v1/
│       ├── endpoints/
│       │   ├── products.py
│       │   └── orders.py
│       └── routers.py
├── db/
│   ├── models/
│   │   ├── product.py
│   │   └── order.py
│   └── database.py
├── services/
│   ├── image_service.py
│   └── storage_service.py
└── core/
    └── config.py
```

#### Переменные и функции
```python
# ✅ Правильно
product_name = "Техника"
is_product_available = True
def get_product_by_id(product_id: int):
    pass

# ❌ Неправильно
pn = "Техника"
available = True
def get_prod(id):
    pass
```

#### Классы
```python
# ✅ Правильно
class ProductService:
    def __init__(self):
        pass
    
    def create_product(self, product_data: dict):
        pass

# ❌ Неправильно
class productService:
    def __init__(self):
        pass
    
    def createProd(self, data):
        pass
```

### Документация

#### Docstrings
```python
"""
Сервис для работы с товарами.

Обеспечивает CRUD операции для товаров,
включая валидацию и обработку изображений.
"""

class ProductService:
    """
    Сервис для работы с товарами.
    
    Attributes:
        db_session: Сессия базы данных
        image_service: Сервис для работы с изображениями
    """
    
    def create_product(self, product_data: dict) -> Product:
        """
        Создает новый товар.
        
        Args:
            product_data: Данные товара для создания
            
        Returns:
            Product: Созданный товар
            
        Raises:
            ValidationError: При неверных данных
            DatabaseError: При ошибке БД
        """
        pass
```

### Структура файлов

#### Импорты (в порядке приоритета)
```python
# 1. Стандартная библиотека Python
import os
import sys
from typing import List, Dict, Optional
from datetime import datetime

# 2. Внешние библиотеки
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from pydantic import BaseModel

# 3. Внутренние модули
from app.db.database import get_db
from app.db.models import Product
from app.services.image_service import image_service
from app.core.config import settings
```

#### Организация кода
```python
"""
Модуль для работы с товарами.

Содержит API endpoints, схемы данных и бизнес-логику
для управления товарами в системе.
"""

# 1. Импорты
from fastapi import APIRouter, Depends
from app.db.models import Product

# 2. Константы
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# 3. Типы
SortField = Literal["name", "-name", "price", "-price"]

# 4. Схемы данных
class ProductCreate(BaseModel):
    name: str
    price: int

# 5. Роутер
router = APIRouter()

# 6. Endpoints
@router.get("", response_model=dict)
def list_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """
    Получить список товаров с пагинацией.
    
    Args:
        db: Сессия базы данных
        page: Номер страницы
        page_size: Размер страницы
        
    Returns:
        dict: Список товаров с метаданными
    """
    pass
```

## API Endpoints

### Структура endpoint'ов

#### GET endpoints
```python
@router.get("", response_model=dict)
def list_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
):
    """
    Получить список товаров с фильтрацией и пагинацией.
    
    Поддерживает:
    - Пагинацию результатов
    - Фильтрацию по категории
    - Сортировку по различным полям
    
    Args:
        db: Сессия базы данных
        page: Номер страницы (начиная с 1)
        page_size: Размер страницы (1-100)
        category_id: Фильтр по ID категории
        
    Returns:
        dict: Список товаров с метаданными пагинации
        
    Raises:
        HTTPException: При некорректных параметрах запроса
    """
    # Логика endpoint'а
    pass
```

#### POST endpoints
```python
@router.post("", response_model=dict, status_code=201)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db)
):
    """
    Создать новый товар.
    
    Создает товар с указанными данными и возвращает
    полную информацию о созданном товаре.
    
    Args:
        product_data: Данные товара для создания
        db: Сессия базы данных
        
    Returns:
        dict: Созданный товар
        
    Raises:
        HTTPException: При некорректных данных или ошибке БД
    """
    # Логика создания товара
    pass
```

### Обработка ошибок

#### HTTPException
```python
# ✅ Правильно
if not product:
    raise HTTPException(404, detail="Product not found")

if not is_valid_data:
    raise HTTPException(400, detail="Invalid request data")

# ❌ Неправильно
if not product:
    raise HTTPException(404, detail="product not found")

if not is_valid_data:
    raise HTTPException(400, detail="invalid data")
```

#### Валидация данных
```python
# ✅ Правильно
if not isinstance(payload, dict):
    raise HTTPException(400, detail="Invalid request body")

if not items:
    raise HTTPException(400, detail="Order must contain at least one item")

# ❌ Неправильно
if not isinstance(payload, dict):
    raise HTTPException(400, detail="invalid body")

if not items:
    raise HTTPException(400, detail="empty items")
```

## База данных

### Модели SQLAlchemy

#### Структура модели
```python
"""
Модель товара.
"""

from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey
from .base import Base


class Product(Base):
    """
    Модель товара.
    
    Attributes:
        id: Уникальный идентификатор товара
        category_id: ID категории товара
        name: Название товара
        price_cents: Цена в центах
        description: Описание товара
        category: Связь с категорией
        images: Связь с изображениями товара
        attributes: Связь с атрибутами товара
    """
    
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        index=True
    )
    name: Mapped[str] = mapped_column(Text)
    price_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Связи с другими моделями
    category: Mapped["Category"] = relationship(back_populates="products")
    images: Mapped[List["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all,delete",
        lazy="selectin"
    )
```

### Запросы к БД

#### Использование SQLAlchemy
```python
# ✅ Правильно
stmt = select(Product).where(Product.category_id == category_id)
products = db.scalars(stmt).all()

count_stmt = select(func.count()).select_from(Product)
total = db.scalar(count_stmt) or 0

# ❌ Неправильно
products = db.query(Product).filter(Product.category_id == category_id).all()
total = db.query(Product).count()
```

#### Предзагрузка связей
```python
# ✅ Правильно
stmt = (
    select(Product)
    .options(selectinload(Product.images))
    .options(selectinload(Product.attributes))
    .where(Product.id == product_id)
)
product = db.scalar(stmt)

# ❌ Неправильно
product = db.get(Product, product_id)
# Это приведет к N+1 проблеме при обращении к связям
```

## Сервисы

### Структура сервиса
```python
"""
Сервис для работы с изображениями товаров.

Обеспечивает валидацию, обработку, оптимизацию и генерацию URL изображений.
"""

import os
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from PIL import Image

from app.core.config import settings


class ImageService:
    """
    Сервис для работы с изображениями товаров.
    
    Обеспечивает:
    - Валидацию загружаемых файлов
    - Обработку и оптимизацию изображений
    - Генерацию URL для разных размеров
    - Управление метаданными
    """
    
    # Константы
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        """Инициализация сервиса."""
        self.cdn_base_url = settings.CDN_BASE_URL.rstrip('/') if settings.CDN_BASE_URL else None
    
    def validate_file(self, file_path: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Валидация загруженного файла.
        
        Args:
            file_path: Путь к файлу
            file_size: Размер файла в байтах
            
        Returns:
            Tuple[bool, Optional[str]]: (валиден, сообщение об ошибке)
        """
        # Логика валидации
        pass
```

## Конфигурация

### Настройки приложения
```python
"""
Конфигурация приложения.

Содержит настройки для подключения к БД, CDN и режима отладки.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения.
    
    Attributes:
        DATABASE_URL: URL подключения к PostgreSQL
        CDN_BASE_URL: Базовый URL CDN для изображений
        DEBUG: Режим отладки
    """
    
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://user:pass@localhost:5432/db",
        description="URL подключения к PostgreSQL"
    )
    CDN_BASE_URL: str = Field(
        default="",
        description="Базовый URL CDN для изображений"
    )
    DEBUG: bool = Field(
        default=False,
        description="Режим отладки"
    )

    class Config:
        env_file = ".env"
        extra = "ignore"


# Глобальный экземпляр настроек
settings = Settings()
```

## Комментарии

### Общие правила
- Используйте комментарии для объяснения "почему", а не "что"
- Обновляйте комментарии при изменении кода
- Избегайте избыточных комментариев

### TODO комментарии
```python
# TODO: Добавить кэширование для часто запрашиваемых товаров
# FIXME: Исправить race condition в обработке изображений
# NOTE: Временное решение, заменить на Redis
```

## Форматирование

### Python
- Используйте Black для автоматического форматирования
- Максимальная длина строки: 88 символов
- Отступы: 4 пробела
- Следуйте PEP 8

### Команды для форматирования
```bash
# Форматирование всех файлов
black app/

# Проверка стиля
flake8 app/

# Проверка типов
mypy app/
```

## Тестирование

### Python
```python
"""
Тесты для ProductService
"""
class TestProductService:
    """Тесты для сервиса товаров."""
    
    def test_create_product(self):
        """Тест создания товара."""
        # ...
    
    def test_get_product_by_id(self):
        """Тест получения товара по ID."""
        # ...
```

## Безопасность

### Общие принципы
- Валидируйте все входные данные
- Используйте параметризованные запросы
- Обрабатывайте ошибки безопасно
- Не раскрывайте чувствительную информацию в логах

### Python
```python
# ✅ Правильно
from sqlalchemy import text
result = db.execute(text("SELECT * FROM products WHERE id = :id"), {"id": product_id})

# ❌ Неправильно
result = db.execute(f"SELECT * FROM products WHERE id = {product_id}")
```

## Производительность

### Python
- Используйте async/await для I/O операций
- Применяйте кэширование для дорогих вычислений
- Оптимизируйте запросы к базе данных

## Логирование

### Python
```python
# ✅ Правильно
import logging

logger = logging.getLogger(__name__)

logger.info("Product created", extra={"product_id": product.id})
logger.error("Failed to create product", exc_info=True)

# ❌ Неправильно
print("Product created")
print(f"Error: {error}")
```

Это руководство должно соблюдаться всеми разработчиками проекта для обеспечения единообразия и качества кода.
