# 🚀 FastAPI Image Management System

Полноценная система управления изображениями с поддержкой S3, CDN и асинхронной обработки.

## ⚡ Быстрый запуск

### Один файл - вся система!
```bash
# Windows
start.bat

# Linux/Mac
start.sh

# Или напрямую
python scripts/system_launcher.py
```

**Запускает автоматически:**
- ✅ FastAPI приложение (порт 8000)
- ✅ PostgreSQL (порт 5432)
- ✅ MinIO S3 (порт 9000)
- ✅ Redis (порт 6379)
- ✅ Создание директорий
- ✅ Настройка .env

## 🌟 Возможности

### 📸 Управление изображениями
- Загрузка изображений через API
- Автоматическая обработка (resize, optimize)
- Множественные размеры (thumb, small, medium, large)
- Валидация файлов
- Метаданные изображений

### 💾 Гибкое хранилище
- **Локальное хранилище** - для разработки
- **S3/MinIO** - для продакшна
- Автоматическое переключение

### 🌐 CDN интеграция
- **Локальный CDN** - для разработки
- **CloudFlare** - готовые инструкции
- **AWS CloudFront** - конфигурация
- Кэширование и статистика

### 🔄 Асинхронная обработка
- Фоновая обработка изображений
- Очередь задач
- Мониторинг статуса

## 📁 Структура проекта

```
FastAPI/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── images.py          # API изображений
│   │   ├── cdn.py             # CDN endpoints
│   │   ├── products.py        # Товары
│   │   ├── orders.py          # Заказы
│   │   └── categories.py      # Категории
│   ├── services/
│   │   ├── image_service.py   # Обработка изображений
│   │   ├── storage_service.py # S3/локальное хранилище
│   │   ├── image_processor.py # Фоновая обработка
│   │   └── local_cdn_service.py # Локальный CDN
│   ├── db/
│   │   ├── models/            # SQLAlchemy модели
│   │   └── sql/               # Миграции БД
│   └── schemas/               # Pydantic схемы
├── uploads/                   # Локальное хранилище
├── cdn_cache/                 # Кэш CDN
├── scripts/                   # 📁 Системные скрипты
│   ├── system_launcher.py     # 🚀 Единый запуск системы
│   ├── start_system.bat       # Windows запуск
│   ├── start_system.sh        # Linux/Mac запуск
│   ├── image_migration.py     # 📦 Миграция изображений
│   └── setup_s3.sh           # 🔧 Настройка S3
├── start.bat                  # 🚀 Быстрый запуск (Windows)
├── start.sh                   # 🚀 Быстрый запуск (Linux/Mac)
├── docker-compose.yml         # Docker сервисы
├── requirements.txt           # Зависимости
└── README.md                  # Документация
```

## 🚀 Запуск

### Требования
- Python 3.8+
- Docker (опционально)
- Docker Compose (опционально)

### Быстрый старт
```bash
# 1. Клонировать репозиторий
git clone <repository>
cd FastAPI

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Запустить систему
python scripts/system_launcher.py
```
```

### Доступные сервисы
- 🌐 **FastAPI**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs
- 🔍 **Health**: http://localhost:8000/healthz
- 💾 **MinIO**: http://localhost:9001 (minioadmin/minioadmin)
- 📊 **CDN Health**: http://localhost:8000/api/v1/cdn/health

## 📚 API Endpoints

### Изображения
```bash
# Загрузка изображения
POST /api/v1/images/upload/{product_id}

# Получение изображения
GET /api/v1/images/{image_id}

# Обновление изображения
PUT /api/v1/images/{image_id}

# Удаление изображения
DELETE /api/v1/images/{image_id}
```

### CDN
```bash
# Получение файла через CDN
GET /api/v1/cdn/file/{file_path}?size=thumb

# Статистика кэша
GET /api/v1/cdn/stats/cache

# Очистка кэша
POST /api/v1/cdn/cache/clear

# Проверка здоровья
GET /api/v1/cdn/health
```

### Товары
```bash
# Список товаров
GET /api/v1/products

# Получение товара
GET /api/v1/products/{product_id}

# Создание товара
POST /api/v1/products

# Обновление товара
PUT /api/v1/products/{product_id}

# Удаление товара
DELETE /api/v1/products/{product_id}
```

## 🔧 Конфигурация

### .env файл
```env
# База данных
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/fastapi_shop

# Хранилище
STORAGE_TYPE=local  # local или s3
STORAGE_PATH=uploads
MAX_IMAGE_SIZE=10485760
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,webp,gif

# S3 (для продакшна)
S3_BUCKET_NAME=my-product-images-bucket
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# CDN
CDN_BASE_URL=https://cdn.yourdomain.com

# Отладка
DEBUG=true
```

## 🌐 Продакшн настройка

### AWS S3 + CloudFlare
1. Создайте S3 bucket
2. Настройте CloudFlare CDN
3. Обновите .env файл
4. Запустите систему

Подробные инструкции: [S3_CDN_SETUP.md](S3_CDN_SETUP.md)

## 🧪 Тестирование

### Проверка здоровья
```bash
curl http://localhost:8000/healthz
```

### Загрузка изображения
```bash
curl -X POST "http://localhost:8000/api/v1/images/upload/test-product" \
  -F "file=@image.jpg" \
  -F "alt_text=Тестовое изображение" \
  -F "is_primary=true"
```

### CDN статистика
```bash
curl http://localhost:8000/api/v1/cdn/stats/cache
```

## 📊 Мониторинг

### Статистика CDN
- Количество файлов в кэше
- Размер кэша
- Hit/Miss ratio
- Время жизни кэша

### Обработка изображений
- Статус обработки
- Размеры изображений
- Метаданные
- Ошибки обработки

## 🔒 Безопасность

- Валидация файлов
- Ограничение размеров
- Проверка MIME типов
- Безопасные пути файлов
- CORS настройки

## 🚀 Развертывание

### Docker
```bash
docker-compose up -d
```

### Heroku
```bash
heroku create
git push heroku main
```

### AWS
```bash
# Настройте EC2 + RDS + S3 + CloudFront
# Используйте docker-compose.yml
```

## 📝 TODO

- [ ] Аутентификация/авторизация
- [ ] Alembic миграции
- [ ] Логирование
- [ ] Тесты
- [ ] Docker образ
- [ ] Кэширование
- [ ] Валидация email/телефона
- [ ] Уведомления о заказах

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Commit изменения
4. Push в branch
5. Создайте Pull Request

## 📄 Лицензия

MIT License

## 🆘 Поддержка

- 📧 Email: support@example.com
- 📖 Документация: [docs/](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/example/fastapi-images/issues)

---

**Сделано с ❤️ для эффективного управления изображениями**
