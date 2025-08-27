# Тестовые скрипты

Эта папка содержит скрипты для проверки и диагностики системы FastAPI e-commerce.

## 🚀 Быстрый старт

### Проверка всей системы
```bash
python test/check_system.py
```

### Проверка отдельных компонентов
```bash
python test/check_postgres.py          # Проверка PostgreSQL
python test/check_minio.py             # Проверка MinIO
python test/check_system.py postgres   # Проверка только PostgreSQL
python test/check_system.py minio      # Проверка только MinIO
```

## 📋 Описание скриптов

### 1. `check_system.py` - Универсальная проверка системы
**Назначение**: Быстрая проверка состояния всех компонентов системы

**Что проверяет**:
- ✅ PostgreSQL (подключение, таблицы, данные)
- ✅ MinIO (подключение, buckets, объекты)
- ✅ FastAPI (доступность API, эндпоинты)
- ✅ Docker (контейнеры, статус)

**Использование**:
```bash
# Проверить всю систему
python test/check_system.py

# Проверить конкретный компонент
python test/check_system.py postgres
python test/check_system.py minio
python test/check_system.py fastapi
python test/check_system.py docker
```

**Пример вывода**:
```
🔍 System Health Checker
⏰ Время проверки: 2025-08-27 14:30:00

==================================================
🐘 ПРОВЕРКА POSTGRESQL
==================================================
✅ Подключение: Успешно
📊 Версия: PostgreSQL 15.4
📋 Таблиц найдено: 3
  products: 5,821 записей
  categories: 1 записей
  product_images: 5,669 записей

==================================================
📦 ПРОВЕРКА MINIO
==================================================
✅ Подключение: Успешно
📊 Buckets найдено: 1
✅ Bucket 'product-images': Найден
📊 Объектов в product-images: 5,669
💾 Общий размер: 1,234.5 MB

📋 ИТОГОВЫЙ ОТЧЕТ
============================================================
📊 Статистика:
  Всего компонентов: 4
  ✅ Работают: 4
  ⚠️  Предупреждения: 0
  ❌ Ошибки: 0

🎉 СИСТЕМА РАБОТАЕТ ОТЛИЧНО!
```

### 2. `check_postgres.py` - Детальная проверка PostgreSQL
**Назначение**: Подробная проверка базы данных PostgreSQL

**Что проверяет**:
- Подключение к базе данных
- Список всех таблиц
- Структуру таблиц
- Количество записей
- Примеры данных
- Специальные проверки для продуктов, изображений, категорий

**Использование**:
```bash
# Общая статистика
python test/check_postgres.py

# Детальная проверка конкретной таблицы
python test/check_postgres.py products
python test/check_postgres.py product_images
python test/check_postgres.py categories
```

**Пример вывода**:
```
🔍 PostgreSQL Database Checker
⏰ Время проверки: 2025-08-27 14:30:00
✅ Подключение к PostgreSQL успешно
📊 Версия: PostgreSQL 15.4 on x86_64-pc-linux-gnu

============================================================
📊 ОБЩАЯ СТАТИСТИКА БАЗЫ ДАННЫХ
============================================================
📋 Найдено таблиц: 3
  products: 5,821 записей
  categories: 1 записей
  product_images: 5,669 записей

📈 Общее количество записей: 11,491

💡 Рекомендации:
  - Для детальной проверки продуктов: python test/check_postgres.py products
  - Для проверки изображений: python test/check_postgres.py product_images
  - Для проверки категорий: python test/check_postgres.py categories
```

### 3. `check_minio.py` - Детальная проверка MinIO
**Назначение**: Подробная проверка MinIO хранилища

**Что проверяет**:
- Подключение к MinIO
- Список всех buckets
- Количество объектов
- Размеры файлов
- Структуру папок
- Специальные проверки для product-images

**Использование**:
```bash
# Общая статистика
python test/check_minio.py

# Проверка конкретного bucket
python test/check_minio.py product-images

# Проверка конкретной папки
python test/check_minio.py product-images products/
```

**Пример вывода**:
```
🔍 MinIO Storage Checker
⏰ Время проверки: 2025-08-27 14:30:00
✅ Подключение к MinIO успешно
📊 Найдено buckets: 1

============================================================
📊 ОБЩАЯ СТАТИСТИКА MINIO
============================================================
📦 Найдено buckets: 1
  product-images: 5,669 объектов, 1,234.5 MB

📈 Общая статистика:
  Всего объектов: 5,669
  Общий размер: 1,234.5 MB

💡 Рекомендации:
  - Для проверки изображений: python test/check_minio.py product-images
  - Для проверки структуры: python test/check_minio.py product-images products/
```

## 🛠️ pgAdmin - Веб-интерфейс для PostgreSQL

### Запуск pgAdmin
```bash
# В папке scripts
docker-compose up -d
```

### Доступ к pgAdmin
- **URL**: http://localhost:5050
- **Email**: admin@admin.com
- **Password**: admin

### Основные возможности pgAdmin:
- 🔍 Визуальный просмотр таблиц и данных
- 🛠️ Выполнение SQL запросов с автодополнением
- 📊 Экспорт данных в CSV, JSON, Excel
- 📈 Анализ производительности запросов
- 🔧 Управление структурой базы данных
- 💾 Резервное копирование и восстановление

### Подробная инструкция
См. файл: `test/pgadmin_guide.md`

## 🎯 Специальные возможности

### Проверка продуктов
```bash
python test/check_postgres.py products
```
Показывает:
- Статистику цен (мин/макс/средняя)
- Распределение по категориям
- Примеры данных

### Проверка изображений
```bash
python test/check_postgres.py product_images
```
Показывает:
- Статистику путей (MinIO vs локальные)
- Размеры файлов
- Распределение по продуктам

### Проверка MinIO изображений
```bash
python test/check_minio.py product-images
```
Показывает:
- Количество продуктов с изображениями
- Среднее количество изображений на продукт
- Топ-5 продуктов по количеству изображений
- Статистику размеров

## 🔧 Требования

### Python библиотеки:
```bash
pip install sqlalchemy psycopg2-binary minio requests
```

### Переменные окружения:
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5433/fastapi_shop
```

### Запущенные сервисы:
- PostgreSQL (порт 5433)
- MinIO (порт 9002)
- pgAdmin (порт 5050)
- FastAPI (порт 8000) - опционально
- Docker - опционально

## 🚨 Диагностика проблем

### Если PostgreSQL недоступен:
1. Проверьте, что PostgreSQL запущен
2. Проверьте настройки подключения в `DATABASE_URL`
3. Убедитесь, что порт 5433 свободен

### Если MinIO недоступен:
1. Проверьте, что MinIO запущен на порту 9002
2. Убедитесь, что credentials правильные (minioadmin/minioadmin)
3. Проверьте Docker контейнер: `docker ps | grep minio`

### Если pgAdmin недоступен:
1. Проверьте, что pgAdmin запущен на порту 5050
2. Убедитесь, что порт 5050 свободен
3. Проверьте логи: `docker-compose logs pgadmin`

### Если FastAPI недоступен:
1. Запустите FastAPI: `python -m app.main`
2. Проверьте, что порт 8000 свободен
3. Убедитесь, что все зависимости установлены

## 📊 Мониторинг

### Регулярные проверки:
```bash
# Ежедневная проверка системы
python test/check_system.py

# Проверка после миграций
python test/check_postgres.py product_images
python test/check_minio.py product-images
```

### Автоматизация:
Можно добавить в cron для автоматических проверок:
```bash
# Каждый час проверять систему
0 * * * * cd /path/to/project && python scripts/test/check_system.py
```

## 💡 Советы

1. **Начните с общей проверки**: `python test/check_system.py`
2. **При проблемах используйте детальные проверки**: `python test/check_postgres.py products`
3. **Для визуального анализа используйте pgAdmin**: http://localhost:5050
4. **Проверяйте после изменений**: После миграций, обновлений, изменений конфигурации
5. **Сохраняйте логи**: Все скрипты выводят подробную информацию для диагностики

## 📁 Структура файлов

```
scripts/test/
├── check_system.py          # Универсальная проверка системы
├── check_postgres.py        # Проверка PostgreSQL
├── check_minio.py           # Проверка MinIO
├── pgadmin_guide.md         # Руководство по pgAdmin
└── README.md                # Этот файл
```
