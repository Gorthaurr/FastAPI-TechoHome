#!/bin/bash

# Скрипт для быстрой настройки S3/MinIO

set -e

echo "🚀 Настройка S3/MinIO для FastAPI проекта"
echo "=========================================="

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose не установлен. Установите docker-compose и попробуйте снова."
    exit 1
fi

echo "✅ Docker и docker-compose найдены"

# Создаем .env файл если его нет
if [ ! -f .env ]; then
    echo "📄 Создаем .env файл из примера..."
    cp ../env.example .env
    echo "✅ .env файл создан"
    echo "⚠️  Не забудьте обновить настройки в .env файле!"
else
    echo "✅ .env файл уже существует"
fi

# Запускаем MinIO и PostgreSQL
echo "🐳 Запускаем MinIO и PostgreSQL..."
cd "$(dirname "$0")"
docker-compose up -d

# Ждем запуска сервисов
echo "⏳ Ждем запуска сервисов..."
sleep 10

# Проверяем статус сервисов
echo "🔍 Проверяем статус сервисов..."
docker-compose ps

# Создаем bucket в MinIO
echo "🪣 Создаем bucket в MinIO..."
BUCKET_NAME=$(grep S3_BUCKET_NAME .env | cut -d '=' -f2)

if [ -z "$BUCKET_NAME" ]; then
    BUCKET_NAME="my-product-images-bucket"
fi

# Используем MinIO Client для создания bucket
if command -v mc &> /dev/null; then
    echo "📦 Используем MinIO Client..."
    mc alias set myminio http://localhost:9000 minioadmin minioadmin
    mc mb myminio/$BUCKET_NAME
    mc policy set public myminio/$BUCKET_NAME
    echo "✅ Bucket '$BUCKET_NAME' создан и настроен как публичный"
else
    echo "⚠️  MinIO Client не установлен. Создайте bucket вручную:"
    echo "   1. Откройте http://localhost:9001"
    echo "   2. Войдите с minioadmin/minioadmin"
    echo "   3. Создайте bucket '$BUCKET_NAME'"
    echo "   4. Установите политику 'Public'"
fi

# Применяем CORS настройки
echo "🌐 Применяем CORS настройки..."
if command -v mc &> /dev/null; then
    echo "⚠️  CORS настройки нужно применить вручную через веб-консоль MinIO"
    echo "   1. Откройте http://localhost:9001"
    echo "   2. Войдите с minioadmin/minioadmin"
    echo "   3. Перейдите в Settings -> CORS"
    echo "   4. Добавьте правило для всех источников (*)"
else
    echo "⚠️  Примените CORS настройки вручную через веб-консоль MinIO"
fi

# Тестируем подключение
echo "🧪 Тестируем подключение..."
if command -v python3 &> /dev/null; then
    python3 test_s3_connection.py
else
    echo "⚠️  Python3 не найден. Запустите тест вручную:"
    echo "   python3 test_s3_connection.py"
fi

echo ""
echo "🎉 Настройка завершена!"
echo ""
echo "📋 Что дальше:"
echo "1. Обновите настройки в .env файле"
echo "2. Запустите FastAPI приложение: uvicorn app.main:app --reload"
echo "3. Протестируйте загрузку изображений через API"
echo ""
echo "🔗 Полезные ссылки:"
echo "- MinIO Console: http://localhost:9001"
echo "- FastAPI: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 Для остановки сервисов: cd scripts && docker-compose down"
