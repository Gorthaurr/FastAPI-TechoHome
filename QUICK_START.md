# 🚀 Быстрый старт системы

## 📋 Требования

- **Python 3.8+**
- **Docker** (опционально, для MinIO/PostgreSQL)
- **Docker Compose** (опционально)

## ⚡ Быстрый запуск

### Windows
```bash
# Двойной клик на файл
start_system.bat

# Или через командную строку
start_system.bat
```

### Linux/Mac
```bash
# Сделать исполняемым и запустить
chmod +x start_system.sh
./start_system.sh

# Или напрямую Python
python3 run_system.py
```

### Ручной запуск
```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить систему
python run_system.py
```

## 🎯 Что запускается

### Автоматически:
- ✅ **FastAPI приложение** (порт 8000)
- ✅ **PostgreSQL** (порт 5432) - через Docker
- ✅ **MinIO S3** (порт 9000) - через Docker  
- ✅ **Redis** (порт 6379) - через Docker
- ✅ **Создание директорий** (uploads/, cdn_cache/)
- ✅ **Настройка .env файла**

### Доступные сервисы:
- 🌐 **FastAPI**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs
- 🔍 **Health Check**: http://localhost:8000/healthz
- 💾 **MinIO API**: http://localhost:9000
- 🖥️ **MinIO Console**: http://localhost:9001
- 📊 **CDN Health**: http://localhost:8000/api/v1/cdn/health

## 🔑 Доступы

### MinIO Console:
- **URL**: http://localhost:9001
- **Логин**: `minioadmin`
- **Пароль**: `minioadmin`

## 🧪 Тестирование

### Проверка здоровья:
```bash
curl http://localhost:8000/healthz
```

### Статистика CDN:
```bash
curl http://localhost:8000/api/v1/cdn/stats/cache
```

### Загрузка изображения:
```bash
curl -X POST "http://localhost:8000/api/v1/images/upload/test-product" \
  -F "file=@image.jpg" \
  -F "is_primary=true"
```

## ⏹️ Остановка

Нажмите **Ctrl+C** для корректной остановки всех сервисов.

## 🔧 Устранение проблем

### Docker не запущен:
- Система продолжит работу с локальным хранилищем
- MinIO и PostgreSQL будут недоступны

### Порт занят:
- Измените порт в `run_system.py`
- Или остановите процесс, использующий порт

### Ошибки зависимостей:
```bash
pip install -r requirements.txt
```

## 📁 Структура после запуска

```
FastAPI/
├── uploads/              # Загруженные файлы
├── cdn_cache/            # Кэш CDN
├── .env                  # Настройки (создается автоматически)
└── logs/                 # Логи (если включены)
```

## 🎉 Готово!

Система готова к использованию! Откройте http://localhost:8000/docs для просмотра API документации.
