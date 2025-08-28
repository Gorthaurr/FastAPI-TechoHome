"""
Сервис для работы с хранилищами файлов.

Поддерживает локальное хранилище и Amazon S3.
"""

import os
import shutil
from typing import Optional, BinaryIO, Dict, Any
from pathlib import Path
from abc import ABC, abstractmethod
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile

from app.core.config import settings


class StorageProvider(ABC):
    """Абстрактный базовый класс для провайдеров хранилища."""
    
    @abstractmethod
    def save_file(self, file_path: str, file_data: BinaryIO, content_type: str = None) -> bool:
        """Сохранить файл в хранилище."""
        pass
    
    @abstractmethod
    def get_file_url(self, file_path: str) -> Optional[str]:
        """Получить URL файла."""
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Удалить файл из хранилища."""
        pass
    
    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Проверить существование файла."""
        pass


class LocalStorageProvider(StorageProvider):
    """Локальное хранилище файлов."""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_path: str, file_data: BinaryIO, content_type: str = None) -> bool:
        """Сохранить файл в локальное хранилище."""
        try:
            full_path = self.base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
            
            return True
        except Exception as e:
            print(f"Error saving file to local storage: {e}")
            return False
    
    def get_file_url(self, file_path: str) -> Optional[str]:
        """Получить локальный URL файла."""
        if settings.CDN_BASE_URL:
            return f"{settings.CDN_BASE_URL.rstrip('/')}/{file_path.lstrip('/')}"
        return f"/static/{file_path}"
    
    def delete_file(self, file_path: str) -> bool:
        """Удалить файл из локального хранилища."""
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file from local storage: {e}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """Проверить существование файла в локальном хранилище."""
        full_path = self.base_path / file_path
        return full_path.exists()


class S3StorageProvider(StorageProvider):
    """Amazon S3 хранилище."""
    
    def __init__(self, bucket_name: str, region: str = None, endpoint_url: str = None):
        self.bucket_name = bucket_name
        self.region = region or 'us-east-1'
        
        # Инициализация клиента S3
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
    
    def save_file(self, file_path: str, file_data: BinaryIO, content_type: str = None) -> bool:
        """Сохранить файл в S3."""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_fileobj(
                file_data,
                self.bucket_name,
                file_path,
                ExtraArgs=extra_args
            )
            return True
        except (ClientError, NoCredentialsError) as e:
            print(f"Error saving file to S3: {e}")
            return False
    
    def get_file_url(self, file_path: str) -> Optional[str]:
        """Получить URL файла из S3."""
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_path},
                ExpiresIn=3600  # 1 час
            )
        except Exception as e:
            print(f"Error generating S3 URL: {e}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """Удалить файл из S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
        except ClientError as e:
            print(f"Error deleting file from S3: {e}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """Проверить существование файла в S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError:
            return False


class StorageService:
    """Основной сервис для работы с хранилищами."""
    
    def __init__(self):
        self.provider = self._create_provider()
    
    def _create_provider(self) -> StorageProvider:
        """Создать провайдер хранилища на основе настроек."""
        storage_type = getattr(settings, 'STORAGE_TYPE', 's3')  # По умолчанию используем S3/MinIO
        
        if storage_type == 's3':
            bucket_name = settings.S3_BUCKET_NAME
            region = settings.AWS_REGION
            endpoint_url = settings.S3_ENDPOINT_URL
            return S3StorageProvider(bucket_name, region, endpoint_url)
        else:
            base_path = getattr(settings, 'STORAGE_PATH', 'uploads')
            return LocalStorageProvider(base_path)
    
    def save_file(self, file_path: str, file_data: BinaryIO, content_type: str = None) -> bool:
        """Сохранить файл."""
        return self.provider.save_file(file_path, file_data, content_type)
    
    def get_file_url(self, file_path: str) -> Optional[str]:
        """Получить URL файла."""
        return self.provider.get_file_url(file_path)
    
    def delete_file(self, file_path: str) -> bool:
        """Удалить файл."""
        return self.provider.delete_file(file_path)
    
    def file_exists(self, file_path: str) -> bool:
        """Проверить существование файла."""
        return self.provider.file_exists(file_path)
    
    def save_upload_file(self, file_path: str, upload_file: UploadFile) -> bool:
        """Сохранить загруженный файл."""
        try:
            upload_file.file.seek(0)  # Сброс позиции в начало файла
            return self.save_file(file_path, upload_file.file, upload_file.content_type)
        except Exception as e:
            print(f"Error saving upload file: {e}")
            return False


# Глобальный экземпляр сервиса хранилища
storage_service = StorageService()
