# TechHome Catalog API

Минимальный модульный бэкенд каталога товаров с системой заказов на FastAPI + PostgreSQL.

## 🚀 Возможности

- **Каталог товаров**: полный CRUD с фильтрацией, сортировкой и пагинацией
- **Система заказов**: создание и управление заказами с позициями
- **Изображения товаров**: поддержка множественных изображений с CDN
- **Атрибуты товаров**: гибкая система key-value атрибутов
- **Категории**: иерархическая структура товаров
- **API документация**: автоматическая генерация Swagger/OpenAPI

## 📋 Требования

- Python 3.11+
- PostgreSQL 13+
- psycopg2-binary

## 🛠️ Установка и настройка

### 1. Клонирование и настройка окружения

```bash
git clone <repository-url>
cd FastAPI
```

### 2. Создание виртуального окружения

**Windows (PowerShell):**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
py -m venv .venv
.\.venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Установка зависимостей

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Настройка конфигурации

Создайте файл `.env` на основе `.env.example`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/database_name
CDN_BASE_URL=https://cdn.example.com
DEBUG=false
```

## 🗄️ Инициализация базы данных

### Вариант 1: Новая база данных

Выполните полную схему через **pgAdmin → Query Tool**:

```sql
-- Выполните содержимое файла:
app/db/sql/00_full_schema.sql
```

### Вариант 2: Существующая база с каталогом

Если у вас уже есть таблицы каталога, добавьте только заказы:

```sql
-- Выполните содержимое файла:
app/db/sql/02_orders.sql
```

## 🚀 Запуск приложения

```bash
uvicorn app.main:app --reload
```

Приложение будет доступно по адресу: `http://localhost:8000`

## 📚 API Endpoints

### Проверка состояния
- `GET /healthz` - Health check

### Товары
- `GET /api/v1/products` - Список товаров с фильтрацией
- `GET /api/v1/products/{id}` - Детальная информация о товаре

### Заказы
- `GET /api/v1/orders` - Список заказов
- `POST /api/v1/orders` - Создание нового заказа
- `GET /api/v1/orders/{order_id}` - Информация о заказе

### Категории
- `GET /api/v1/categories` - Список категорий
- `GET /api/v1/categories/{id}` - Информация о категории

### Отладка
- `GET /api/v1/_debug/db-ping` - Проверка подключения к БД
- `GET /api/v1/_debug/products-raw` - Сырые данные товаров
- `GET /api/v1/_debug/orders-raw` - Сырые данные заказов

## 📖 Примеры использования

### Получение списка товаров

```bash
curl "http://localhost:8000/api/v1/products?page=1&page_size=20&include_images=true"
```

### Создание заказа

```bash
curl -X POST "http://localhost:8000/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {
      "name": "Иван Иванов",
      "email": "ivan@example.com",
      "phone": "+7-999-123-45-67"
    },
    "items": [
      {"product_id": "ABC123", "qty": 2}
    ],
    "shipping_cents": 500,
    "comment": "Позвонить перед доставкой"
  }'
```

### Получение заказа

```bash
curl "http://localhost:8000/api/v1/orders/{order-uuid}"
```

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DATABASE_URL` | URL подключения к PostgreSQL | - |
| `CDN_BASE_URL` | Базовый URL CDN для изображений | "" |
| `DEBUG` | Режим отладки | false |

### Параметры API

#### Фильтрация товаров
- `category_id` - фильтр по категории
- `q` - поиск по названию (ILIKE)
- `price_min` / `price_max` - диапазон цен
- `sort` - сортировка (name, -name, price, -price)

#### Пагинация
- `page` - номер страницы (начиная с 1)
- `page_size` - размер страницы (1-100)

#### Дополнительные опции
- `include_images` - включить изображения товаров
- `include_attributes` - включить атрибуты товаров

## 🏗️ Архитектура

```
app/
├── main.py              # Точка входа приложения
├── core/
│   └── config.py        # Конфигурация
├── api/
│   └── v1/
│       ├── routers.py   # Основной роутер
│       └── endpoints/   # API endpoints
├── db/
│   ├── database.py      # Подключение к БД
│   ├── models/          # SQLAlchemy модели
│   └── sql/            # SQL скрипты
└── schemas/            # Pydantic схемы
```

## 🔍 Отладка

### Проверка подключения к БД

```bash
curl "http://localhost:8000/api/v1/_debug/db-ping"
```

### Просмотр сырых данных

```bash
curl "http://localhost:8000/api/v1/_debug/products-raw?limit=5"
curl "http://localhost:8000/api/v1/_debug/orders-raw?limit=5"
```

## 📝 Заметки

- `CDN_BASE_URL` автоматически добавляется как префикс к путям изображений
- Все цены хранятся в центах для избежания проблем с плавающей точкой
- Заказы используют UUID для уникальной идентификации
- При создании заказа делается снимок цен и названий товаров
- Поддерживается каскадное удаление связанных данных

## 🚧 TODO

- [ ] Добавить аутентификацию и авторизацию
- [ ] Реализовать миграции через Alembic
- [ ] Добавить логирование
- [ ] Написать тесты
- [ ] Добавить Docker конфигурацию
- [ ] Реализовать кэширование
- [ ] Добавить валидацию email и телефона
- [ ] Реализовать уведомления о заказах
