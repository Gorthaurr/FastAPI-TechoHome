"""
API endpoints для локального CDN.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.requests import Request
from fastapi.responses import Response

from app.core.config import settings
from app.services.local_cdn_service import local_cdn_service

router = APIRouter()


@router.get("/file/{file_path:path}")
async def serve_cdn_file(
    request: Request,
    file_path: str,
    size: Optional[str] = Query(
        None, description="Размер изображения (thumb, small, medium, large)"
    ),
):
    """
    Обслуживание файлов через CDN.

    Args:
        file_path: Путь к файлу
        size: Размер изображения

    Returns:
        Файл или ошибка 404
    """
    # Добавляем суффикс размера если указан
    if size:
        file_path = local_cdn_service._add_size_suffix(file_path, size)

    # Проверяем кэш
    cached_content = local_cdn_service.get_cached_file(file_path)
    if cached_content:
        return Response(
            content=cached_content,
            media_type=local_cdn_service._get_content_type(file_path),
            headers={"X-Cache": "HIT", "Cache-Control": "public, max-age=3600"},
        )

    # Ищем файл в хранилище
    storage_path = Path(settings.STORAGE_PATH) / file_path

    if not storage_path.exists():
        raise HTTPException(404, detail="File not found")

    try:
        # Читаем файл
        with open(storage_path, "rb") as f:
            content = f.read()

        # Кэшируем файл
        local_cdn_service.cache_file(file_path, content)

        # Определяем MIME тип
        content_type = local_cdn_service._get_content_type(file_path)

        return Response(
            content=content,
            media_type=content_type,
            headers={"X-Cache": "MISS", "Cache-Control": "public, max-age=3600"},
        )

    except Exception as e:
        raise HTTPException(500, detail=f"Error reading file: {str(e)}")


@router.get("/stats/cache")
async def get_cache_stats():
    """
    Получить статистику кэша CDN.

    Returns:
        Статистика кэша
    """
    return local_cdn_service.get_cache_stats()


@router.post("/cache/clear")
async def clear_cache():
    """
    Очистить кэш CDN.

    Returns:
        Результат очистки
    """
    local_cdn_service.clear_cache()
    return {"message": "Cache cleared successfully"}


@router.get("/health")
async def cdn_health():
    """
    Проверка здоровья CDN.

    Returns:
        Статус CDN
    """
    stats = local_cdn_service.get_cache_stats()
    return {
        "status": "healthy",
        "cache_stats": stats,
        "storage_path": settings.STORAGE_PATH,
        "cdn_base_url": settings.CDN_BASE_URL or "local",
    }
