"""
Основной роутер API v1.

Подключает все endpoint'ы приложения.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, address, categories, cdn, debug, images, orders, products

# Создание основного роутера API v1
api_router = APIRouter()

# Подключение роутеров для различных ресурсов
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(cdn.router, prefix="/cdn", tags=["cdn"])
api_router.include_router(address.router, prefix="/address", tags=["address"])
api_router.include_router(debug.router, prefix="/_debug", tags=["_debug"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
