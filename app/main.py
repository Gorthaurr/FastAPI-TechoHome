"""
Главный модуль FastAPI приложения TechHome Catalog API.

Содержит конфигурацию приложения, middleware и роутеры.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routers import api_router


# Создание экземпляра FastAPI приложения
app = FastAPI(
    title="TechHome Catalog API",
    description="API для каталога товаров с системой заказов",
    version="1.0.0"
)


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
        dict: Статус приложения
    """
    return {"status": "ok"}


# Подключение API роутеров
app.include_router(api_router, prefix="/api/v1")