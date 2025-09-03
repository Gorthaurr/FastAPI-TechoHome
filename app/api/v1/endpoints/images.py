"""
API endpoints для работы с изображениями товаров.
"""

import os
import tempfile
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.database import get_db
from app.db.models import Product, ProductImage
from app.schemas.product import ImageCreate, ImageOut, ImageUpdate
from app.core.auth import require_admin
from app.db.models.user import User
from app.services.image_processor import process_image_async
from app.services.image_service import image_service
from app.services.storage_service import storage_service

router = APIRouter()


@router.post("/upload/{product_id}", response_model=Dict[str, Any])
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    alt_text: str = Form(None),
    sort_order: int = Form(0),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
):
    """
    Загрузка изображения для товара.

    Args:
        product_id: ID товара
        file: Загружаемый файл
        alt_text: Альтернативный текст
        sort_order: Порядок сортировки
        is_primary: Главное изображение
        db: Сессия базы данных

    Returns:
        dict: Информация о загруженном изображении
    """
    # Проверяем существование товара
    product = db.scalar(select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(404, detail="Product not found")

    # Валидируем файл
    is_valid, error_message = image_service.validate_file(file.filename, file.size)
    if not is_valid:
        raise HTTPException(400, detail=error_message)

    # Создаем временный файл для обработки
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(file.filename)[1]
    ) as temp_file:
        # Сохраняем загруженный файл
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        # Генерируем путь для сохранения
        storage_path = image_service.generate_path(product_id, file.filename)
        print(f"🖼️  IMAGES API: Saving image via images.py endpoint: {storage_path}")

        # Сохраняем файл в хранилище используя временный файл
        with open(temp_file_path, 'rb') as temp_file_handle:
            if not storage_service.save_file(storage_path, temp_file_handle, file.content_type):
                raise HTTPException(500, detail="Failed to save file to storage")

        # Создаем запись в БД
        image = ProductImage(
            product_id=product_id,
            path=storage_path,
            filename=file.filename,
            sort_order=sort_order,
            is_primary=is_primary,
            status="uploading",
            file_size=file.size,
            alt_text=alt_text,
        )

        db.add(image)
        db.flush()  # Получаем ID

        # Если это главное изображение, снимаем флаг с других
        if is_primary:
            other_images = db.scalars(
                select(ProductImage).where(
                    and_(
                        ProductImage.product_id == product_id,
                        ProductImage.id != image.id,
                        ProductImage.is_primary == True,
                    )
                )
            ).all()

            for other_image in other_images:
                other_image.is_primary = False

        db.commit()

        # Запускаем асинхронную обработку изображения
        process_image_async(image.id)

        # Формируем ответ
        urls = image_service.generate_urls(image.path)

        return {
            "id": image.id,
            "product_id": image.product_id,
            "filename": image.filename,
            "path": image.path,
            "status": image.status,
            "urls": urls,
            "message": "Image uploaded successfully. Processing started in background.",
        }

    except Exception as e:
        # Очищаем временный файл
        image_service.cleanup_failed_upload(temp_file_path)
        raise HTTPException(500, detail=f"Upload failed: {str(e)}")

    finally:
        # Удаляем временный файл
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.get("/{image_id}", response_model=ImageOut)
def get_image(
    image_id: int,
    db: Session = Depends(get_db),
    include_urls: bool = Query(True, description="Включить URL для разных размеров"),
):
    """
    Получить информацию об изображении.

    Args:
        image_id: ID изображения
        db: Сессия базы данных
        include_urls: Включить URL для разных размеров

    Returns:
        ImageOut: Информация об изображении
    """
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id))

    if not image:
        raise HTTPException(404, detail="Image not found")

    # Формируем URL
    urls = image_service.generate_urls(image.path, include_urls)

    return ImageOut(
        id=image.id,
        path=image.path,
        filename=image.filename,
        sort_order=image.sort_order,
        is_primary=image.is_primary,
        status=image.status,
        file_size=image.file_size,
        mime_type=image.mime_type,
        width=image.width,
        height=image.height,
        alt_text=image.alt_text,
        url=urls.get("original"),
        urls=urls if include_urls else None,
        uploaded_at=image.uploaded_at,
        processed_at=image.processed_at,
        error_message=image.error_message,
    )


@router.put("/{image_id}", response_model=ImageOut)
def update_image(
    image_id: int, 
    image_data: ImageUpdate, 
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Обновить метаданные изображения.

    Args:
        image_id: ID изображения
        image_data: Данные для обновления
        db: Сессия базы данных

    Returns:
        ImageOut: Обновленное изображение
    """
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id))

    if not image:
        raise HTTPException(404, detail="Image not found")

    # Обновляем поля
    if image_data.alt_text is not None:
        image.alt_text = image_data.alt_text
    if image_data.sort_order is not None:
        image.sort_order = image_data.sort_order
    if image_data.is_primary is not None:
        image.is_primary = image_data.is_primary

        # Если устанавливаем как главное, снимаем флаг с других
        if image_data.is_primary:
            db.execute(
                select(ProductImage).where(
                    and_(
                        ProductImage.product_id == image.product_id,
                        ProductImage.id != image.id,
                        ProductImage.is_primary.is_(True),
                    )
                )
            ).scalars().all()

            for other_image in (
                db.execute(
                    select(ProductImage).where(
                                            and_(
                        ProductImage.product_id == image.product_id,
                        ProductImage.id != image.id,
                        ProductImage.is_primary.is_(True),
                    )
                    )
                )
                .scalars()
                .all()
            ):
                other_image.is_primary = False

    db.commit()
    db.refresh(image)

    # Формируем URL
    urls = image_service.generate_urls(image.path)

    return ImageOut(
        id=image.id,
        path=image.path,
        filename=image.filename,
        sort_order=image.sort_order,
        is_primary=image.is_primary,
        status=image.status,
        file_size=image.file_size,
        mime_type=image.mime_type,
        width=image.width,
        height=image.height,
        alt_text=image.alt_text,
        url=urls.get("original"),
        urls=urls,
        uploaded_at=image.uploaded_at,
        processed_at=image.processed_at,
        error_message=image.error_message,
    )


@router.delete("/{image_id}")
def delete_image(
    image_id: int, 
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Удалить изображение.

    Args:
        image_id: ID изображения
        db: Сессия базы данных

    Returns:
        dict: Результат удаления
    """
    image = db.scalar(select(ProductImage).where(ProductImage.id == image_id))

    if not image:
        raise HTTPException(404, detail="Image not found")

    # Здесь должна быть логика удаления файлов из хранилища
    # Для примера просто удаляем запись из БД

    db.delete(image)
    db.commit()

    return {"message": "Image deleted successfully"}


@router.get("/product/{product_id}", response_model=List[ImageOut])
def get_product_images(
    product_id: str,
    db: Session = Depends(get_db),
    include_urls: bool = Query(True, description="Включить URL для разных размеров"),
):
    """
    Получить все изображения товара.

    Args:
        product_id: ID товара
        db: Сессия базы данных
        include_urls: Включить URL для разных размеров

    Returns:
        List[ImageOut]: Список изображений
    """
    images = db.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order, ProductImage.id)
    ).all()

    result = []
    for image in images:
        urls = image_service.generate_urls(image.path, include_urls)

        result.append(
            ImageOut(
                id=image.id,
                path=image.path,
                filename=image.filename,
                sort_order=image.sort_order,
                is_primary=image.is_primary,
                status=image.status,
                file_size=image.file_size,
                mime_type=image.mime_type,
                width=image.width,
                height=image.height,
                alt_text=image.alt_text,
                url=urls.get("original"),
                urls=urls if include_urls else None,
                uploaded_at=image.uploaded_at,
                processed_at=image.processed_at,
                error_message=image.error_message,
            )
        )

    return result


@router.get("/processor/status")
async def get_processor_status():
    """
    Получить статус обработчика изображений.

    Returns:
        dict: Статус обработчика
    """
    from app.services.image_processor import image_processor

    return await image_processor.get_queue_status()


@router.post("/processor/reprocess-failed")
async def reprocess_failed_images():
    """
    Переобработать изображения со статусом 'error'.

    Returns:
        dict: Результат операции
    """
    from app.services.image_processor import image_processor

    await image_processor.reprocess_failed_images()
    return {"message": "Failed images added to reprocessing queue"}


@router.get("/processor/queue")
async def get_processing_queue():
    """
    Получить информацию о очереди обработки.

    Returns:
        dict: Информация о очереди
    """
    from app.services.image_processor import image_processor

    status = await image_processor.get_queue_status()

    # Получаем статистику по статусам изображений
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        status_counts = db.execute(
            select(
                ProductImage.status, func.count(ProductImage.id).label("count")
            ).group_by(ProductImage.status)
        ).all()

        status_stats = {row.status: row.count for row in status_counts}

        return {**status, "status_stats": status_stats}
    finally:
        db.close()
