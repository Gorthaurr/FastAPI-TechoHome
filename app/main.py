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
    redoc_url="/redoc"
)

# Подключение статических файлов для локального хранилища
try:
    from app.core.config import settings
    if settings.STORAGE_TYPE == "local":
        app.mount("/static", StaticFiles(directory=settings.STORAGE_PATH), name="static")
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
    return {
        "status": "ok",
        "service": "TechHome Catalog API",
        "version": "1.0.0"
    }


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