#!/bin/bash

# Скрипт для запуска парсера изображений
# Использование: ./run_image_parser.sh [количество_товаров]

echo "🚀 Запуск парсера изображений для товаров"
echo "=========================================="

# Проверка количества аргументов
if [ $# -eq 0 ]; then
    PRODUCT_COUNT=10
else
    PRODUCT_COUNT=$1
fi

echo "📋 Будет обработано товаров: $PRODUCT_COUNT"
echo ""

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте .env файл на основе .env.example"
    echo "Инструкции: https://github.com/your-repo/docs/api-keys"
    echo ""
fi

# Проверка наличия виртуального окружения
if [ ! -d "venv" ]; then
    echo "⚠️  Виртуальное окружение не найдено"
    echo "Рекомендуется создать виртуальное окружение:"
    echo "python -m venv venv"
    echo "source venv/bin/activate  # Linux/Mac"
    echo "venv\\Scripts\\activate     # Windows"
    echo ""
fi

# Установка зависимостей (если нужно)
echo "📦 Проверка зависимостей..."
pip install -r requirements.txt --quiet

# Запуск тестового скрипта
echo ""
echo "🧪 Запуск тестового скрипта..."
python scripts/test_image_parser.py

# Запрос подтверждения для запуска основного парсера
echo ""
echo "❓ Запустить основной парсер? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    echo "🎯 Запуск основного парсера..."
    python scripts/image_parser.py
else
    echo "Отменено пользователем"
fi

echo ""
echo "🎉 Скрипт завершен!"
