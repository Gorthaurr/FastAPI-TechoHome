"""
Сервис для обработки изображений в фоновом режиме.

Обеспечивает асинхронную обработку, оптимизацию и создание миниатюр.
"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import ProductImage
from app.services.image_service import image_service
from app.services.storage_service import storage_service

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageProcessor:
    """Сервис для обработки изображений в фоновом режиме."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing_queue = asyncio.Queue()
        self.is_running = False
        self._background_task = None

    async def start(self):
        """Запустить обработчик изображений."""
        if self.is_running:
            return

        self.is_running = True
        self._background_task = asyncio.create_task(self._process_queue())
        logger.info("Image processor started")

    async def stop(self):
        """Остановить обработчик изображений."""
        if not self.is_running:
            return

        self.is_running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        self.executor.shutdown(wait=True)
        logger.info("Image processor stopped")

    async def process_image(self, image_id: int, callback: Callable = None):
        """Добавить изображение в очередь обработки."""
        await self.processing_queue.put(
            {"image_id": image_id, "callback": callback, "timestamp": datetime.utcnow()}
        )
        logger.info(f"Image {image_id} added to processing queue")

    async def _process_queue(self):
        """Основной цикл обработки очереди."""
        while self.is_running:
            try:
                # Получаем задачу из очереди с таймаутом
                task = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)

                # Обрабатываем изображение в отдельном потоке
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor, self._process_single_image, task
                )

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in processing queue: {e}")

    def _process_single_image(self, task: Dict[str, Any]):
        """Обработать одно изображение."""
        image_id = task["image_id"]
        callback = task.get("callback")

        try:
            # Получаем изображение из БД
            db = SessionLocal()
            image = db.query(ProductImage).filter(ProductImage.id == image_id).first()

            if not image:
                logger.error(f"Image {image_id} not found")
                return

            # Обновляем статус на "processing"
            image.status = "processing"
            db.commit()

            # Проверяем существование исходного файла
            if not storage_service.file_exists(image.path):
                raise FileNotFoundError(f"Source file not found: {image.path}")

            # Создаем временный файл для обработки
            temp_path = self._create_temp_file(image.path)

            try:
                # Извлекаем метаданные
                metadata = image_service.extract_metadata(temp_path)

                # Обновляем метаданные в БД
                image.width = metadata.get("width")
                image.height = metadata.get("height")
                image.mime_type = metadata.get("mime_type")
                image.image_metadata = metadata.get("metadata", {})

                # Генерируем миниатюры
                thumbnails = self._generate_thumbnails(temp_path, image.path)

                # Сохраняем миниатюры в хранилище
                self._save_thumbnails(thumbnails)

                # Обновляем метаданные с путями к миниатюрам
                if thumbnails:
                    image.image_metadata = {
                        **(image.image_metadata or {}),
                        "thumbnails": thumbnails,
                    }

                # Обновляем статус на "ready"
                image.status = "ready"
                image.processed_at = datetime.utcnow()

                db.commit()
                logger.info(f"Image {image_id} processed successfully")

                # Вызываем callback если есть
                if callback:
                    try:
                        callback(image_id, True, None)
                    except Exception as e:
                        logger.error(f"Error in callback for image {image_id}: {e}")

            finally:
                # Очищаем временный файл
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error processing image {image_id}: {e}")

            # Обновляем статус на "error"
            try:
                db = SessionLocal()
                image = (
                    db.query(ProductImage).filter(ProductImage.id == image_id).first()
                )
                if image:
                    image.status = "error"
                    image.error_message = str(e)
                    db.commit()
            except Exception as db_error:
                logger.error(f"Error updating image status: {db_error}")

            # Вызываем callback с ошибкой
            if callback:
                try:
                    callback(image_id, False, str(e))
                except Exception as callback_error:
                    logger.error(
                        f"Error in error callback for image {image_id}: {callback_error}"
                    )

    def _create_temp_file(self, source_path: str) -> str:
        """Создать временный файл из исходного изображения."""
        import tempfile

        # Получаем файл из хранилища
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        temp_path = temp_file.name
        temp_file.close()

        # Копируем файл во временную директорию
        with open(temp_path, "wb") as f:
            # Здесь нужно реализовать получение файла из хранилища
            # Для локального хранилища:
            local_path = Path(settings.STORAGE_PATH) / source_path
            if local_path.exists():
                with open(local_path, "rb") as src:
                    f.write(src.read())

        return temp_path

    def _generate_thumbnails(self, source_path: str, base_path: str) -> Dict[str, str]:
        """Генерировать миниатюры изображения."""
        return image_service.generate_thumbnails(source_path, base_path)

    def _save_thumbnails(self, thumbnails: Dict[str, str]):
        """Сохранить миниатюры в хранилище."""
        for size_name, thumbnail_path in thumbnails.items():
            if os.path.exists(thumbnail_path):
                # Сохраняем миниатюру в хранилище
                with open(thumbnail_path, "rb") as f:
                    storage_service.save_file(thumbnail_path, f, "image/jpeg")

                # Удаляем временный файл
                os.unlink(thumbnail_path)

    async def get_queue_status(self) -> Dict[str, Any]:
        """Получить статус очереди обработки."""
        return {
            "queue_size": self.processing_queue.qsize(),
            "is_running": self.is_running,
            "max_workers": self.max_workers,
        }

    async def reprocess_failed_images(self):
        """Переобработать изображения со статусом 'error'."""
        db = SessionLocal()
        try:
            failed_images = (
                db.query(ProductImage).filter(ProductImage.status == "error").all()
            )

            for image in failed_images:
                await self.process_image(image.id)

            logger.info(
                f"Added {len(failed_images)} failed images to reprocessing queue"
            )

        finally:
            db.close()


# Глобальный экземпляр обработчика изображений
image_processor = ImageProcessor()


# Функции для интеграции с FastAPI
async def start_image_processor():
    """Запустить обработчик изображений при старте приложения."""
    await image_processor.start()


async def stop_image_processor():
    """Остановить обработчик изображений при завершении приложения."""
    await image_processor.stop()


def process_image_async(image_id: int, callback: Callable = None):
    """Асинхронно обработать изображение."""
    asyncio.create_task(image_processor.process_image(image_id, callback))
