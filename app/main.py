"""
Главный модуль FastAPI приложения TechHome Catalog API.

Содержит конфигурацию приложения, middleware и роутеры.
Обеспечивает интеграцию с хранилищем изображений и CDN.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.routers import api_router
from app.services.image_processor import start_image_processor, stop_image_processor

# Создание экземпляра FastAPI приложения
app = FastAPI(
    title="TechHome Catalog API",
    description="API для каталога товаров с системой заказов и управления изображениями",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Подключение статических файлов для локального хранилища
try:
    from app.core.config import settings
    import os

    if settings.STORAGE_TYPE == "local":
        # Получаем абсолютный путь к папке uploads
        # Путь к изображениям: /static/products/abf6b685/abf6b685f7b8/filename.jpeg
        
        # Вариант 1: Текущая рабочая директория + uploads
        current_dir = os.getcwd()
        uploads_path = os.path.join(current_dir, settings.STORAGE_PATH)
        uploads_path = os.path.abspath(uploads_path)
        
        # Вариант 2: Относительно файла main.py
        if not os.path.exists(uploads_path):
            print(f"Warning: Uploads directory does not exist: {uploads_path}")
            alt_path = os.path.join(os.path.dirname(__file__), "..", "..", settings.STORAGE_PATH)
            alt_path = os.path.abspath(alt_path)
            if os.path.exists(alt_path):
                uploads_path = alt_path
                print(f"Using alternative path: {uploads_path}")
            else:
                print(f"Alternative path also does not exist: {alt_path}")
                # Вариант 3: Абсолютный путь к папке FastAPI
                fastapi_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                uploads_path = os.path.join(fastapi_root, settings.STORAGE_PATH)
                if os.path.exists(uploads_path):
                    print(f"Using FastAPI root path: {uploads_path}")
                else:
                    print(f"FastAPI root path also does not exist: {uploads_path}")
                    print("Skipping static files mount")
                    uploads_path = None
        
        # Монтируем статические файлы только если путь найден
        if uploads_path and os.path.exists(uploads_path):
            app.mount(
                "/static", StaticFiles(directory=uploads_path), name="static"
            )
            print(f"Static files mounted at /static from directory: {uploads_path}")
            print(f"Current working directory: {current_dir}")
            print(f"Settings STORAGE_PATH: {settings.STORAGE_PATH}")
            
            # Проверяем содержимое папки
            try:
                files = os.listdir(uploads_path)
                print(f"Files in uploads directory: {files[:10]}...")  # Показываем первые 10 файлов
            except Exception as e:
                print(f"Error listing uploads directory: {e}")
        else:
            print("No valid uploads path found, static files not mounted")
except Exception as e:
    print(f"Warning: Could not mount static files: {e}")


# Настройка CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: сузить в продакшене до конкретных доменов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    """
    Health check endpoint для мониторинга состояния приложения.

    Returns:
        dict: Статус приложения и основные метрики
    """
    return {"status": "ok", "service": "TechHome Catalog API", "version": "1.0.0"}


# Подключение API роутеров
app.include_router(api_router, prefix="/api/v1")




@app.on_event("startup")
async def startup_event():
    """
    Событие запуска приложения.

    Инициализирует фоновые процессы и сервисы.
    """
    await start_image_processor()


@app.on_event("shutdown")
async def shutdown_event():
    """
    Событие завершения приложения.

    Корректно останавливает фоновые процессы и освобождает ресурсы.
    """
    await stop_image_processor()
