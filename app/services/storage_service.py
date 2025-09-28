"""
Сервис для работы с хранилищами файлов.

Поддерживает локальное хранилище и Amazon S3.
Обеспечивает единый интерфейс для работы с файлами
независимо от типа хранилища.
"""

import os
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.config import settings


# ======================= ВСПОМОГАТЕЛЬНОЕ: безопасный запуск процессов =======================

def _run_utf8(cmd: list[str], timeout: int = 30) -> Tuple[str, str, int]:
    """
    Безопасный запуск подпроцессов:
    - НЕ используем text=True (чтобы не словить cp1251 на Windows);
    - читаем байты и декодируем в UTF-8 с errors='replace';
    - прокидываем LANG/LC_ALL=C.UTF-8.
    """
    env = os.environ.copy()
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=False,          # <- критично: читаем байты, не строки
            timeout=timeout,
            env=env,
        )
        out = p.stdout.decode("utf-8", errors="replace")
        err = p.stderr.decode("utf-8", errors="replace")
        return out, err, p.returncode
    except subprocess.TimeoutExpired as e:
        return "", f"TimeoutExpired: {e}", 124
    except Exception as e:
        return "", f"SubprocessError: {e}", 1


class StorageProvider(ABC):
    """
    Абстрактный базовый класс для провайдеров хранилища.
    """

    @abstractmethod
    def save_file(
        self, file_path: str, file_data: BinaryIO, content_type: str = None
    ) -> bool:
        pass

    @abstractmethod
    def get_file_url(self, file_path: str) -> Optional[str]:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        pass


class LocalStorageProvider(StorageProvider):
    """
    Локальное хранилище файлов.
    """

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_file(
        self, file_path: str, file_data: BinaryIO, content_type: str = None
    ) -> bool:
        try:
            print(f"✅ LOCAL STORAGE: Saving file to {file_path}")
            full_path = self.base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "wb") as f:
                shutil.copyfileobj(file_data, f)

            print(f"✅ LOCAL STORAGE: File saved to {full_path}")
            return True
        except Exception as e:
            print(f"❌ LOCAL STORAGE: Error saving file: {e}")
            return False

    def get_file_url(self, file_path: str) -> Optional[str]:
        if settings.CDN_BASE_URL:
            return f"{settings.CDN_BASE_URL.rstrip('/')}/{file_path.lstrip('/')}"
        return f"/static/{file_path}"

    def delete_file(self, file_path: str) -> bool:
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"❌ LOCAL STORAGE: Error deleting file: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        full_path = self.base_path / file_path
        return full_path.exists()


class MinIOStorageProvider(StorageProvider):
    """
    MinIO хранилище через mc команды (docker exec mc ...).
    """

    def __init__(self, bucket_name: str, endpoint_url: str = None, container_name: str = "scripts-minio-1"):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL or "http://localhost:9000"
        self.access_key = settings.AWS_ACCESS_KEY_ID
        self.secret_key = settings.AWS_SECRET_ACCESS_KEY
        self.container_name = container_name

        # Настройка alias один раз
        self._setup_mc_alias()

    def _setup_mc_alias(self):
        """Настройка mc alias для подключения к MinIO."""
        try:
            cmd = [
                "docker", "exec", self.container_name, "mc", "alias", "set",
                "local", self.endpoint_url, self.access_key, self.secret_key
            ]
            out, err, rc = _run_utf8(cmd, timeout=15)
            if rc == 0:
                print(f"✅ MinIO mc alias настроен: {self.endpoint_url}")
            else:
                print(f"⚠️ MinIO mc alias setup warning (rc={rc}): {err.strip() or out.strip()}")
        except Exception as e:
            print(f"❌ MinIO mc alias setup error: {e}")

    def save_file(
        self, file_path: str, file_data: BinaryIO, content_type: str = None
    ) -> bool:
        """
        Сохранить файл в MinIO через mc:
        1) пишем во временный файл на хосте;
        2) docker cp -> /tmp внутри контейнера;
        3) docker exec mc cp -> local/bucket/path;
        4) удаляем временный файл в контейнере.
        """
        try:
            print(f"✅ MinIO STORAGE: Saving file to {file_path}")

            # 1) Временный файл на хосте
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                shutil.copyfileobj(file_data, temp_file)
                temp_file_path = temp_file.name

            filename_only = Path(file_path).name
            container_tmp = f"/tmp/{filename_only}"

            try:
                # 2) Копируем файл в контейнер (байтовый режим; лог по завершении)
                copy_cmd = [
                    "docker", "cp", temp_file_path,
                    f"{self.container_name}:{container_tmp}"
                ]
                out, err, rc = _run_utf8(copy_cmd, timeout=30)
                if rc != 0:
                    print(f"❌ MinIO STORAGE: docker cp failed (rc={rc}): {err.strip() or out.strip()}")
                    return False
                else:
                    size_kb = max(1, Path(temp_file_path).stat().st_size // 1024)
                    print(f"Successfully copied {size_kb:.1f}kB to {self.container_name}:{container_tmp}")

                # 3) Загружаем файл в MinIO через mc
                mc_cmd = [
                    "docker", "exec", self.container_name, "mc", "cp",
                    container_tmp,
                    f"local/{self.bucket_name}/{file_path}"
                ]
                out, err, rc = _run_utf8(mc_cmd, timeout=60)
                if rc == 0:
                    print("✅ MinIO STORAGE: File uploaded successfully")
                    return True
                else:
                    print(f"❌ MinIO STORAGE: Upload failed (rc={rc}): {err.strip() or out.strip()}")
                    return False

            finally:
                # 4) Чистим временные файлы (и на хосте, и в контейнере)
                Path(temp_file_path).unlink(missing_ok=True)
                rm_cmd = ["docker", "exec", self.container_name, "rm", "-f", container_tmp]
                _run_utf8(rm_cmd, timeout=10)

        except Exception as e:
            print(f"❌ MinIO STORAGE: Error saving file: {e}")
            return False

    def get_file_url(self, file_path: str) -> Optional[str]:
        """
        Получить presigned URL файла в MinIO через mc share download.
        """
        try:
            cmd = [
                "docker", "exec", self.container_name, "mc", "share", "download",
                f"local/{self.bucket_name}/{file_path}"
            ]
            out, err, rc = _run_utf8(cmd, timeout=20)
            if rc == 0:
                text = (out or "").strip()
                # Простейшая выборка URL — берём последнее "слово", содержащее http
                parts = text.split()
                for token in reversed(parts):
                    if token.startswith("http://") or token.startswith("https://"):
                        return token
            else:
                print(f"⚠️ MinIO STORAGE: URL generation failed (rc={rc}): {err.strip() or out.strip()}")
            return None
        except Exception as e:
            print(f"❌ MinIO STORAGE: Error generating URL: {e}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Удалить файл из MinIO.
        """
        try:
            cmd = [
                "docker", "exec", self.container_name, "mc", "rm",
                f"local/{self.bucket_name}/{file_path}"
            ]
            out, err, rc = _run_utf8(cmd, timeout=20)
            if rc == 0:
                print("✅ MinIO STORAGE: File deleted successfully")
                return True
            else:
                print(f"❌ MinIO STORAGE: Delete failed (rc={rc}): {err.strip() or out.strip()}")
                return False
        except Exception as e:
            print(f"❌ MinIO STORAGE: Error deleting file: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """
        Проверить существование файла в MinIO.
        """
        try:
            cmd = [
                "docker", "exec", self.container_name, "mc", "ls",
                f"local/{self.bucket_name}/{file_path}"
            ]
            out, err, rc = _run_utf8(cmd, timeout=15)
            return rc == 0
        except Exception:
            return False


class S3StorageProvider(StorageProvider):
    """
    Amazon S3 хранилище (или совместимые сервисы).
    """

    def __init__(self, bucket_name: str, region: str = None, endpoint_url: str = None):
        self.bucket_name = bucket_name
        self.region = region or "us-east-1"

        config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            connect_timeout=10,
            read_timeout=30,
            s3={'addressing_style': 'path'}
        )

        self.s3_client = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=config,
            use_ssl=False if endpoint_url and 'localhost' in endpoint_url else True
        )
        # Для MinIO
        self.s3_client._client_config.signature_version = 's3v4'

    def test_connection(self) -> bool:
        try:
            print(f"🔍 S3 STORAGE: Testing connection to {self.s3_client.meta.endpoint_url}")
            print(f"🔍 S3 STORAGE: Using credentials: {settings.AWS_ACCESS_KEY_ID}")
            response = self.s3_client.list_buckets()
            print(f"✅ S3 STORAGE: Connection successful, found {len(response.get('Buckets', []))} buckets")
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
        try:
            print(f"✅ S3 STORAGE: Saving file to {file_path}")
            print(f"✅ S3 STORAGE: Bucket: {self.bucket_name}, Endpoint: {self.s3_client.meta.endpoint_url}")

            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print(f"✅ S3 STORAGE: Bucket {self.bucket_name} exists")
            except ClientError as e:
                code = e.response['Error']['Code']
                if code == '404':
                    print(f"❌ S3 STORAGE: Bucket {self.bucket_name} not found")
                    return False
                elif code == '403':
                    print(f"❌ S3 STORAGE: Access denied to bucket {self.bucket_name}")
                    return False
                else:
                    print(f"⚠️ S3 STORAGE: Bucket check error: {e}")

            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            # Читаем содержимое, чтобы указать ContentLength (важно для MinIO)
            file_data.seek(0)
            file_content = file_data.read()
            file_data.seek(0)
            extra_args["ContentLength"] = len(file_content)

            from io import BytesIO
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=BytesIO(file_content),
                **extra_args
            )
            print("✅ S3 STORAGE: File uploaded successfully to S3")
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
        try:
            print(f"Generating presigned URL for path: {file_path}")
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=3600,
            )
            print(f"Generated URL: {url}")
            return url
        except (ClientError, NoCredentialsError) as e:
            print(f"Error generating S3 URL: {e}")
            return None

    def delete_file(self, file_path: str) -> bool:
        try:
            print(f"Deleting file from S3: {file_path}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            print("File deleted successfully from S3")
            return True
        except (ClientError, NoCredentialsError) as e:
            print(f"Error deleting file from S3: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError:
            return False


# ======================= Создание экземпляра провайдера =======================

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

    # Тест соединения и загрузки маленького файла (для ранней диагностики)
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
