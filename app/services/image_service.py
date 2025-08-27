"""
Сервис для работы с изображениями товаров.

Обеспечивает валидацию, обработку, оптимизацию и генерацию URL изображений.
"""

import os
import mimetypes
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse
from PIL import Image
import hashlib
from datetime import datetime

from app.core.config import settings


class ImageService:
    """
    Сервис для работы с изображениями товаров.
    
    Обеспечивает:
    - Валидацию загружаемых файлов
    - Обработку и оптимизацию изображений
    - Генерацию URL для разных размеров
    - Управление метаданными
    """
    
    # Поддерживаемые форматы
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    SUPPORTED_MIME_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 
        'image/webp', 'image/gif'
    }
    
    # Максимальные размеры
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DIMENSIONS = (4000, 4000)  # 4000x4000 пикселей
    
    # Стандартные размеры для генерации
    THUMBNAIL_SIZES = {
        'thumb': (150, 150),
        'small': (300, 300),
        'medium': (600, 600),
        'large': (1200, 1200),
    }
    
    def __init__(self):
        self.cdn_base_url = settings.CDN_BASE_URL.rstrip('/') if settings.CDN_BASE_URL else None
    
    def validate_file(self, file_path: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Валидация загруженного файла.
        
        Args:
            file_path: Путь к файлу
            file_size: Размер файла в байтах
            
        Returns:
            Tuple[bool, Optional[str]]: (валиден, сообщение об ошибке)
        """
        # Проверка размера файла
        if file_size > self.MAX_FILE_SIZE:
            return False, f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE} bytes"
        
        # Проверка расширения файла
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            return False, f"Unsupported file format: {file_ext}. Supported: {', '.join(self.SUPPORTED_FORMATS)}"
        
        # Проверка MIME типа
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            return False, f"Unsupported MIME type: {mime_type}"
        
        return True, None
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Извлечение метаданных из изображения.
        
        Args:
            file_path: Путь к файлу изображения
            
        Returns:
            Dict[str, Any]: Метаданные изображения
        """
        try:
            with Image.open(file_path) as img:
                # Основные размеры
                width, height = img.size
                
                # Формат и режим
                format_name = img.format
                mode = img.mode
                
                # Дополнительные метаданные
                metadata = {
                    'format': format_name,
                    'mode': mode,
                    'dpi': img.info.get('dpi'),
                    'exif': img.info.get('exif'),
                }
                
                return {
                    'width': width,
                    'height': height,
                    'mime_type': f"image/{format_name.lower()}" if format_name else None,
                    'metadata': metadata
                }
        except Exception as e:
            return {
                'width': None,
                'height': None,
                'mime_type': None,
                'metadata': {'error': str(e)}
            }
    
    def generate_path(self, product_id: str, filename: str) -> str:
        """
        Генерация пути для сохранения изображения.
        
        Args:
            product_id: ID товара
            filename: Имя файла
            
        Returns:
            str: Путь для сохранения
        """
        # Создаем хеш от product_id для распределения по папкам
        hash_value = hashlib.md5(product_id.encode()).hexdigest()[:8]
        
        # Структура: products/{hash}/{product_id}/{filename}
        return f"products/{hash_value}/{product_id}/{filename}"
    
    def generate_urls(self, base_path: str, include_sizes: bool = True) -> Dict[str, str]:
        """
        Генерация URL для изображения и его размеров.
        
        Args:
            base_path: Базовый путь к изображению
            include_sizes: Включить ли URL для разных размеров
            
        Returns:
            Dict[str, str]: Словарь с URL для разных размеров
        """
        urls = {
            'original': self._build_url(base_path)
        }
        
        if include_sizes and self.cdn_base_url:
            # Генерируем URL для разных размеров
            for size_name in self.THUMBNAIL_SIZES.keys():
                size_path = self._add_size_suffix(base_path, size_name)
                urls[size_name] = self._build_url(size_path)
        
        return urls
    
    def _build_url(self, path: str) -> str:
        """
        Построение полного URL для изображения.
        
        Args:
            path: Относительный путь
            
        Returns:
            str: Полный URL
        """
        if not self.cdn_base_url:
            return path
        
        return urljoin(self.cdn_base_url + '/', path.lstrip('/'))
    
    def _add_size_suffix(self, path: str, size_name: str) -> str:
        """
        Добавление суффикса размера к пути изображения.
        
        Args:
            path: Базовый путь
            size_name: Название размера
            
        Returns:
            str: Путь с суффиксом размера
        """
        path_obj = Path(path)
        stem = path_obj.stem
        suffix = path_obj.suffix
        
        # Добавляем суффикс размера перед расширением
        new_stem = f"{stem}_{size_name}"
        return str(path_obj.with_name(new_stem + suffix))
    
    def optimize_image(self, source_path: str, target_path: str, 
                      max_size: Tuple[int, int] = None, 
                      quality: int = 85) -> bool:
        """
        Оптимизация изображения.
        
        Args:
            source_path: Путь к исходному файлу
            target_path: Путь для сохранения оптимизированного файла
            max_size: Максимальные размеры (width, height)
            quality: Качество JPEG (1-100)
            
        Returns:
            bool: Успешность операции
        """
        try:
            with Image.open(source_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Создаем белый фон для прозрачных изображений
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Изменяем размер если нужно
                if max_size:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Создаем директорию если не существует
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Сохраняем оптимизированное изображение
                img.save(target_path, 'JPEG', quality=quality, optimize=True)
                return True
                
        except Exception as e:
            print(f"Error optimizing image {source_path}: {e}")
            return False
    
    def generate_thumbnails(self, original_path: str, base_path: str) -> Dict[str, str]:
        """
        Генерация миниатюр разных размеров.
        
        Args:
            original_path: Путь к оригинальному файлу
            base_path: Базовый путь для сохранения
            
        Returns:
            Dict[str, str]: Словарь с путями к миниатюрам
        """
        generated_paths = {}
        
        for size_name, dimensions in self.THUMBNAIL_SIZES.items():
            thumbnail_path = self._add_size_suffix(base_path, size_name)
            
            if self.optimize_image(original_path, thumbnail_path, dimensions):
                generated_paths[size_name] = thumbnail_path
        
        return generated_paths
    
    def cleanup_failed_upload(self, file_path: str):
        """
        Очистка файла при неудачной загрузке.
        
        Args:
            file_path: Путь к файлу для удаления
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {e}")


# Глобальный экземпляр сервиса
image_service = ImageService()
