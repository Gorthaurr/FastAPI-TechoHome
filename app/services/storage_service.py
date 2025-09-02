"""
Сервис для работы с хранилищами файлов.

Поддерживает локальное хранилище и Amazon S3.
Обеспечивает единый интерфейс для работы с файлами
независимо от типа хранилища.
"""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.config import settings


class StorageProvider(ABC):
    """
    Абстрактный базовый класс для провайдеров хранилища.

    Определяет интерфейс для работы с файлами в различных
    типах хранилищ (локальное, S3, и т.д.).
    """

    @abstractmethod
    def save_file(
        self, file_path: str, file_data: BinaryIO, content_type: str = None
    ) -> bool:
        """
        Сохранить файл в хранилище.

        Args:
            file_path: Путь к файлу в хранилище
            file_data: Данные файла
            content_type: MIME тип файла

        Returns:
            bool: True если файл успешно сохранен
        """
        pass

    @abstractmethod
    def get_file_url(self, file_path: str) -> Optional[str]:
        """
        Получить URL файла.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            Optional[str]: URL файла или None если недоступен
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Удалить файл из хранилища.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            bool: True если файл успешно удален
        """
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """
        Проверить существование файла.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            bool: True если файл существует
        """
        pass


class LocalStorageProvider(StorageProvider):
    """
    Локальное хранилище файлов.

    Сохраняет файлы в локальной файловой системе
    с поддержкой CDN URL для доступа.
    """

    def __init__(self, base_path: str = None):
        """
        Инициализация локального хранилища.

        Args:
            base_path: Базовый путь для хранения файлов
        """
        self.base_path = Path(base_path or settings.STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_file(
        self, file_path: str, file_data: BinaryIO, content_type: str = None
    ) -> bool:
        """
        Сохранить файл в локальное хранилище.

        Args:
            file_path: Путь к файлу в хранилище
            file_data: Данные файла
            content_type: MIME тип файла (не используется в локальном хранилище)

        Returns:
            bool: True если файл успешно сохранен
        """
        try:
            full_path = self.base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "wb") as f:
                shutil.copyfileobj(file_data, f)

            return True
        except Exception as e:
            print(f"Error saving file to local storage: {e}")
            return False

    def get_file_url(self, file_path: str) -> Optional[str]:
        """
        Получить локальный URL файла.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            Optional[str]: URL файла для доступа
        """
        if settings.CDN_BASE_URL:
            return f"{settings.CDN_BASE_URL.rstrip('/')}/{file_path.lstrip('/')}"
        return f"/static/{file_path}"

    def delete_file(self, file_path: str) -> bool:
        """
        Удалить файл из локального хранилища.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            bool: True если файл успешно удален
        """
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
        """
        Проверить существование файла в локальном хранилище.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            bool: True если файл существует
        """
        full_path = self.base_path / file_path
        return full_path.exists()


class S3StorageProvider(StorageProvider):
    """
    Amazon S3 хранилище.

    Сохраняет файлы в Amazon S3 или совместимых сервисах
    (MinIO, DigitalOcean Spaces и т.д.).
    """

    def __init__(self, bucket_name: str, region: str = None, endpoint_url: str = None):
        """
        Инициализация S3 хранилища.

        Args:
            bucket_name: Имя S3 bucket
            region: AWS регион
            endpoint_url: Кастомный endpoint URL (для MinIO и т.д.)
        """
        self.bucket_name = bucket_name
        self.region = region or "us-east-1"

        # Инициализация клиента S3
        self.s3_client = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def save_file(
        self, file_path: str, file_data: BinaryIO, content_type: str = None
    ) -> bool:
        """
        Сохранить файл в S3.

        Args:
            file_path: Путь к файлу в хранилище
            file_data: Данные файла
            content_type: MIME тип файла

        Returns:
            bool: True если файл успешно сохранен
        """
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            self.s3_client.upload_fileobj(
                file_data, self.bucket_name, file_path, ExtraArgs=extra_args
            )
            return True
        except (ClientError, NoCredentialsError) as e:
            print(f"Error saving file to S3: {e}")
            return False

    def get_file_url(self, file_path: str) -> Optional[str]:
        """
        Получить URL файла в S3.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            Optional[str]: URL файла для доступа
        """
        try:
            # Генерируем presigned URL для доступа к файлу
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=3600,  # URL действителен 1 час
            )
            return url
        except (ClientError, NoCredentialsError) as e:
            print(f"Error generating S3 URL: {e}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Удалить файл из S3.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            bool: True если файл успешно удален
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except (ClientError, NoCredentialsError) as e:
            print(f"Error deleting file from S3: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """
        Проверить существование файла в S3.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            bool: True если файл существует
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError:
            return False


# Создание экземпляра хранилища в зависимости от настроек
if settings.STORAGE_TYPE == "s3":
    storage_service = S3StorageProvider(
        bucket_name=settings.S3_BUCKET_NAME,
        region=settings.AWS_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL,
    )
else:
    storage_service = LocalStorageProvider()
