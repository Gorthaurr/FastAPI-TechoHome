# Руководство по использованию pgAdmin

## 🚀 Запуск pgAdmin

### 1. Запуск системы
```bash
# В папке scripts
docker-compose up -d
```

### 2. Доступ к pgAdmin
- **URL**: http://localhost:5050
- **Email**: admin@admin.com
- **Password**: admin

## 📋 Первоначальная настройка

### 1. Вход в систему
1. Откройте браузер и перейдите на http://localhost:5050
2. Введите данные для входа:
   - Email: `admin@admin.com`
   - Password: `admin`

### 2. Добавление сервера PostgreSQL
1. После входа нажмите правой кнопкой мыши на "Servers" в левой панели
2. Выберите "Register" → "Server..."
3. Заполните вкладку "General":
   - **Name**: `FastAPI Shop` (любое удобное имя)
4. Перейдите на вкладку "Connection":
   - **Host name/address**: `postgres` (имя сервиса в docker-compose)
   - **Port**: `5432` (внутренний порт PostgreSQL)
   - **Maintenance database**: `fastapi_shop`
   - **Username**: `postgres`
   - **Password**: `password`
5. Нажмите "Save"

## 🔍 Просмотр данных

### 1. Навигация по базе данных
После подключения вы увидите структуру:
```
FastAPI Shop
├── Databases
│   └── fastapi_shop
│       ├── Schemas
│       │   └── public
│       │       ├── Tables
│       │       │   ├── products
│       │       │   ├── product_images
│       │       │   └── categories
│       │       └── Views
│       └── Extensions
```

### 2. Просмотр таблиц
1. Разверните: `FastAPI Shop` → `Databases` → `fastapi_shop` → `Schemas` → `public` → `Tables`
2. Вы увидите все таблицы: `products`, `product_images`, `categories`

### 3. Просмотр данных таблицы
1. Правой кнопкой мыши на таблицу (например, `products`)
2. Выберите "View/Edit Data" → "All Rows"
3. Откроется таблица с данными

### 4. Структура таблицы
1. Правой кнопкой мыши на таблицу
2. Выберите "Properties"
3. Перейдите на вкладку "Columns" - увидите все колонки и их типы

## 🛠️ Выполнение SQL запросов

### 1. Открытие Query Tool
1. Нажмите на иконку SQL (🔍) в верхней панели
2. Или правой кнопкой на сервер → "Query Tool"

### 2. Полезные запросы для анализа данных

#### Общая статистика
```sql
-- Количество записей в таблицах
SELECT 'products' as table_name, COUNT(*) as record_count FROM products
UNION ALL
SELECT 'product_images' as table_name, COUNT(*) as record_count FROM product_images
UNION ALL
SELECT 'categories' as table_name, COUNT(*) as record_count FROM categories;
```

#### Статистика продуктов
```sql
-- Статистика цен
SELECT 
    COUNT(*) as total_products,
    MIN(price_cents) as min_price_cents,
    MAX(price_cents) as max_price_cents,
    AVG(price_cents) as avg_price_cents,
    MIN(price_cents)/100.0 as min_price_rub,
    MAX(price_cents)/100.0 as max_price_rub,
    AVG(price_cents)/100.0 as avg_price_rub
FROM products;
```

#### Топ-10 самых дорогих продуктов
```sql
SELECT 
    id,
    name,
    price_raw,
    price_cents,
    price_cents/100.0 as price_rub
FROM products 
ORDER BY price_cents DESC 
LIMIT 10;
```

#### Статистика изображений
```sql
-- Анализ путей изображений
SELECT 
    COUNT(*) as total_images,
    COUNT(CASE WHEN path LIKE 'products/%' THEN 1 END) as minio_images,
    COUNT(CASE WHEN path LIKE 'images/%' THEN 1 END) as local_images,
    COUNT(CASE WHEN path NOT LIKE 'products/%' AND path NOT LIKE 'images/%' THEN 1 END) as other_paths,
    COUNT(CASE WHEN status = 'ready' THEN 1 END) as ready_status,
    COUNT(CASE WHEN is_primary = true THEN 1 END) as primary_images
FROM product_images;
```

#### Продукты с количеством изображений
```sql
SELECT 
    p.id,
    p.name,
    p.price_raw,
    COUNT(pi.id) as image_count
FROM products p
LEFT JOIN product_images pi ON p.id = pi.product_id
GROUP BY p.id, p.name, p.price_raw
ORDER BY image_count DESC
LIMIT 10;
```

#### Категории с количеством продуктов
```sql
SELECT 
    c.id,
    c.slug,
    COUNT(p.id) as product_count
FROM categories c
LEFT JOIN products p ON c.id = p.category_id
GROUP BY c.id, c.slug;
```

## 📊 Экспорт данных

### 1. Экспорт результатов запроса
1. Выполните SQL запрос
2. В результатах нажмите правой кнопкой мыши
3. Выберите "Save results to file"
4. Выберите формат: CSV, JSON, HTML, XML

### 2. Экспорт всей таблицы
1. Правой кнопкой на таблицу
2. Выберите "Backup..."
3. Настройте параметры экспорта
4. Выберите формат файла

## 🎯 Полезные функции pgAdmin

### 1. Автодополнение SQL
- Начните печатать SQL команду
- pgAdmin предложит варианты автодополнения

### 2. Подсветка синтаксиса
- SQL код автоматически подсвечивается
- Ошибки выделяются красным

### 3. План выполнения запроса
- Добавьте `EXPLAIN` перед запросом
- Увидите план выполнения и производительность

### 4. Фильтрация данных
- В таблице данных можно использовать фильтры
- Нажмите на заголовок колонки для сортировки

### 5. Поиск по данным
- Используйте Ctrl+F для поиска в результатах
- Или фильтры в интерфейсе таблицы

## 🔧 Настройки и советы

### 1. Настройка отображения
- **Tools** → **Preferences** → **Query Tool** → **Results grid**
- Настройте количество строк на странице
- Настройте ширину колонок

### 2. Сохранение запросов
- Сохраняйте часто используемые запросы
- **File** → **Save** в Query Tool

### 3. Мониторинг производительности
- **Dashboard** показывает статистику сервера
- **Statistics** для анализа таблиц

### 4. Резервное копирование
- **Tools** → **Backup** для создания бэкапов
- **Tools** → **Restore** для восстановления

## 🚨 Решение проблем

### 1. Не удается подключиться
- Проверьте, что PostgreSQL запущен: `docker ps`
- Убедитесь, что порт 5050 свободен
- Проверьте логи: `docker-compose logs pgadmin`

### 2. Медленная работа
- Ограничьте количество строк в запросах: `LIMIT 1000`
- Используйте индексы для больших таблиц
- Оптимизируйте запросы

### 3. Проблемы с кодировкой
- Убедитесь, что база данных использует UTF-8
- Проверьте настройки локали в pgAdmin

## 💡 Полезные сочетания клавиш

- **Ctrl+Enter** - Выполнить запрос
- **Ctrl+Shift+Enter** - Выполнить запрос и показать план
- **Ctrl+S** - Сохранить запрос
- **Ctrl+O** - Открыть файл с запросом
- **Ctrl+F** - Поиск в результатах
- **F5** - Обновить данные

## 📱 Мобильная версия

pgAdmin также доступен на мобильных устройствах:
- Откройте http://localhost:5050 на телефоне
- Интерфейс автоматически адаптируется
- Основные функции доступны

---

**Теперь у вас есть полноценный веб-интерфейс для работы с PostgreSQL!** 🎉
