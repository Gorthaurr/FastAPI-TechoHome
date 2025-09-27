"""
Сервис для работы с хранилищами файлов.

Поддерживает локальное хранилище и Amazon S3.
Обеспечивает единый интерфейс для работы с файлами
независимо от типа хранилища.
"""

import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional

import boto3
from botocore.config import Config
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
            print(f"❌ LOCAL STORAGE: Saving file to {file_path}")
            full_path = self.base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "wb") as f:
                shutil.copyfileobj(file_data, f)

            print(f"❌ LOCAL STORAGE: File saved to {full_path}")
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


class MinIOStorageProvider(StorageProvider):
    """
    MinIO хранилище через mc команды.
    
    Использует mc (MinIO Client) для работы с MinIO,
    обходя проблемы с boto3 API.
    """

    def __init__(self, bucket_name: str, endpoint_url: str = None):
        """
        Инициализация MinIO хранилища.

        Args:
            bucket_name: Имя bucket
            endpoint_url: URL MinIO сервера
        """
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL or "http://localhost:9000"
        self.access_key = settings.AWS_ACCESS_KEY_ID
        self.secret_key = settings.AWS_SECRET_ACCESS_KEY
        
        # Настраиваем mc alias
        self._setup_mc_alias()

    def _setup_mc_alias(self):
        """Настройка mc alias для подключения к MinIO."""
        try:
            cmd = [
                "docker", "exec", "scripts-minio-1", "mc", "alias", "set", 
                "local", self.endpoint_url, self.access_key, self.secret_key
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ MinIO mc alias настроен: {self.endpoint_url}")
            else:
                print(f"⚠️ MinIO mc alias setup warning: {result.stderr}")
        except Exception as e:
            print(f"❌ MinIO mc alias setup error: {e}")

    def save_file(
        self, file_path: str, file_data: BinaryIO, content_type: str = None
    ) -> bool:
        """
        Сохранить файл в MinIO через mc.

        Args:
            file_path: Путь к файлу в хранилище
            file_data: Данные файла
            content_type: MIME тип файла

        Returns:
            bool: True если файл успешно сохранен
        """
        try:
            print(f"✅ MinIO STORAGE: Saving file to {file_path}")
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                shutil.copyfileobj(file_data, temp_file)
                temp_file_path = temp_file.name
            
            try:
                # Копируем файл в контейнер
                copy_cmd = [
                    "docker", "cp", temp_file_path, 
                    f"scripts-minio-1:/tmp/{Path(file_path).name}"
                ]
                subprocess.run(copy_cmd, check=True, timeout=10)
                
                # Загружаем файл в MinIO через mc
                mc_cmd = [
                    "docker", "exec", "scripts-minio-1", "mc", "cp",
                    f"/tmp/{Path(file_path).name}",
                    f"local/{self.bucket_name}/{file_path}"
                ]
                result = subprocess.run(mc_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"✅ MinIO STORAGE: File uploaded successfully")
                    return True
                else:
                    print(f"❌ MinIO STORAGE: Upload failed: {result.stderr}")
                    return False
                    
            finally:
                # Удаляем временный файл
                Path(temp_file_path).unlink(missing_ok=True)
                
        except Exception as e:
            print(f"❌ MinIO STORAGE: Error saving file: {e}")
            return False

    def get_file_url(self, file_path: str) -> Optional[str]:
        """
        Получить URL файла в MinIO.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            Optional[str]: URL файла для доступа
        """
        # Для MinIO генерируем presigned URL через mc
        try:
            cmd = [
                "docker", "exec", "scripts-minio-1", "mc", "share", "download",
                f"local/{self.bucket_name}/{file_path}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Извлекаем URL из вывода mc
                output = result.stdout.strip()
                if "http" in output:
                    return output.split()[-1]  # Последнее слово должно быть URL
            return None
        except Exception as e:
            print(f"❌ MinIO STORAGE: Error generating URL: {e}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Удалить файл из MinIO.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            bool: True если файл успешно удален
        """
        try:
            cmd = [
                "docker", "exec", "scripts-minio-1", "mc", "rm",
                f"local/{self.bucket_name}/{file_path}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ MinIO STORAGE: File deleted successfully")
                return True
            else:
                print(f"❌ MinIO STORAGE: Delete failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ MinIO STORAGE: Error deleting file: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """
        Проверить существование файла в MinIO.

        Args:
            file_path: Путь к файлу в хранилище

        Returns:
            bool: True если файл существует
        """
        try:
            cmd = [
                "docker", "exec", "scripts-minio-1", "mc", "ls",
                f"local/{self.bucket_name}/{file_path}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False


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

        # Конфигурация для MinIO с retry и таймаутами
        config = Config(
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            connect_timeout=10,
            read_timeout=30,
            s3={
                'addressing_style': 'path'  # path-style для MinIO
            }
        )

        # Инициализация клиента S3 с правильными настройками для MinIO
        self.s3_client = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=config,
            use_ssl=False if endpoint_url and 'localhost' in endpoint_url else True
        )
        
        # Устанавливаем signature_version для MinIO
        self.s3_client._client_config.signature_version = 's3v4'

    def test_connection(self) -> bool:
        """
        Проверить подключение к S3/MinIO.
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            print(f"🔍 S3 STORAGE: Testing connection to {self.s3_client.meta.endpoint_url}")
            print(f"🔍 S3 STORAGE: Using credentials: {settings.AWS_ACCESS_KEY_ID}")
            
            # Пытаемся получить список bucket'ов
            response = self.s3_client.list_buckets()
            print(f"✅ S3 STORAGE: Connection successful, found {len(response.get('Buckets', []))} buckets")
            
            # Проверяем конкретный bucket
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print(f"✅ S3 STORAGE: Bucket '{self.bucket_name}' exists and accessible")
            except Exception as bucket_error:
                print(f"⚠️ S3 STORAGE: Bucket '{self.bucket_name}' check failed: {bucket_error}")
                
            return True
        except Exception as e:
            print(f"❌ S3 STORAGE: Connection failed: {e}")
            if hasattr(e, 'response'):
                print(f"❌ S3 STORAGE: Response details: {e.response}")
            return False

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
            print(f"✅ S3 STORAGE: Saving file to {file_path}")
            print(f"✅ S3 STORAGE: Bucket: {self.bucket_name}, Endpoint: {self.s3_client.meta.endpoint_url}")

            # Проверяем, что bucket существует
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print(f"✅ S3 STORAGE: Bucket {self.bucket_name} exists")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    print(f"❌ S3 STORAGE: Bucket {self.bucket_name} not found")
                    return False
                elif error_code == '403':
                    print(f"❌ S3 STORAGE: Access denied to bucket {self.bucket_name}")
                    return False
                else:
                    print(f"⚠️ S3 STORAGE: Bucket check error: {e}")
                    # Продолжаем попытку загрузки

            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            print(f"✅ S3 STORAGE: Uploading file to S3...")
            
            # Читаем все данные файла для получения размера
            file_data.seek(0)
            file_content = file_data.read()
            file_data.seek(0)
            
            # Добавляем ContentLength для MinIO
            extra_args["ContentLength"] = len(file_content)
            
            # Используем put_object вместо upload_fileobj для лучшей совместимости с MinIO
            from io import BytesIO
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=BytesIO(file_content),
                **extra_args
            )
            print(f"✅ S3 STORAGE: File uploaded successfully to S3")
            return True
        except (ClientError, NoCredentialsError) as e:
            print(f"❌ S3 STORAGE: Error saving file to S3: {e}")
            if hasattr(e, 'response'):
                print(f"❌ S3 STORAGE: Response: {e.response}")
            return False
        except Exception as e:
            print(f"❌ S3 STORAGE: Unexpected error: {e}")
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
            print(f"Generating presigned URL for path: {file_path}")
            # Генерируем presigned URL для доступа к файлу
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=3600,  # URL действителен 1 час
            )
            print(f"Generated URL: {url}")
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
            print(f"Deleting file from S3: {file_path}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            print(f"File deleted successfully from S3")
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
print("=" * 50)
print("STORAGE SERVICE INITIALIZATION")
print("=" * 50)
print(f"STORAGE_TYPE: {settings.STORAGE_TYPE}")
print(f"S3_BUCKET_NAME: {settings.S3_BUCKET_NAME}")
print(f"S3_ENDPOINT_URL: {settings.S3_ENDPOINT_URL}")

if settings.STORAGE_TYPE == "s3":
    print("Creating MinIOStorageProvider (using mc commands)...")
    storage_service = MinIOStorageProvider(
        bucket_name=settings.S3_BUCKET_NAME,
        endpoint_url=settings.S3_ENDPOINT_URL,
    )
    print("✅ MinIOStorageProvider created successfully")
    
    # Тестируем загрузку файла
    try:
        from io import BytesIO
        test_data = BytesIO(b"test minio connection")
        if storage_service.save_file("test_connection.txt", test_data):
            print("✅ MinIO connection test passed")
            storage_service.delete_file("test_connection.txt")
        else:
            print("❌ MinIO connection test failed")
    except Exception as e:
        print(f"❌ MinIO connection test error: {e}")
else:
    print("Creating LocalStorageProvider...")
    storage_service = LocalStorageProvider()
    print("✅ LocalStorageProvider created successfully")

print(f"Final storage service: {type(storage_service)}")
print("=" * 50)
