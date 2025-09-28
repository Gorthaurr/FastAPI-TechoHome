#!/bin/bash

# Скрипт деплоя API на сервер
# Используется GitHub Actions для автоматического обновления

set -e

echo "🚀 Начинаем деплой API..."

# Переходим в директорию проекта
cd /opt/deploy

# Останавливаем старый контейнер
echo "⏹️ Останавливаем старый контейнер..."
docker-compose stop api || true

# Удаляем старый образ
echo "🗑️ Удаляем старый образ..."
docker image rm ghcr.io/demon/technofame-api:latest || true

# Подтягиваем новый образ
echo "📥 Подтягиваем новый образ..."
docker pull ghcr.io/demon/technofame-api:latest

# Запускаем новый контейнер
echo "▶️ Запускаем новый контейнер..."
docker-compose up -d api

# Проверяем статус
echo "✅ Проверяем статус контейнера..."
sleep 5
docker-compose ps api

echo "🎉 Деплой API завершен!"
