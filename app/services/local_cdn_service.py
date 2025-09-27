"""
Локальный CDN сервис для разработки.
Имитирует работу CloudFlare CDN для локального тестирования.
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings


class LocalCDNService:
    """Локальный CDN сервис для разработки."""

    def __init__(self):
        self.cdn_base_url = (
            settings.CDN_BASE_URL.rstrip("/") if settings.CDN_BASE_URL else None
        )
        self.cache_dir = Path("cdn_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_metadata_file = self.cache_dir / "metadata.json"
        self.cache_metadata = self._load_cache_metadata()

    def _load_cache_metadata(self) -> Dict[str, Any]:
        """Загрузить метаданные кэша."""
        if self.cache_metadata_file.exists():
            try:
                with open(self.cache_metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"files": {}, "stats": {"hits": 0, "misses": 0}}

    def _save_cache_metadata(self):
        """Сохранить метаданные кэша."""
        try:
            with open(self.cache_metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения метаданных кэша: {e}")

    def get_cdn_url(self, file_path: str, size: Optional[str] = None) -> str:
        """Получить CDN URL для файла."""
        if not self.cdn_base_url:
            # Локальный CDN
            base_url = f"{settings.CDN_BASE_URL or 'http://localhost:8000'}/cdn"
        else:
            base_url = self.cdn_base_url

        # Добавляем размер если указан
        if size:
            file_path = self._add_size_suffix(file_path, size)

        # Добавляем версию для кэширования
        version = self._get_file_version(file_path)
        return f"{base_url}/{file_path}?v={version}"

    def _add_size_suffix(self, file_path: str, size: str) -> str:
        """Добавить суффикс размера к пути файла."""
        path = Path(file_path)
        stem = path.stem
        suffix = path.suffix

        # Убираем существующие суффиксы размеров
        for size_name in ["_thumb", "_small", "_medium", "_large"]:
            if stem.endswith(size_name):
                stem = stem[: -len(size_name)]
                break

        return str(path.parent / f"{stem}_{size}{suffix}")

    def _get_file_version(self, file_path: str) -> str:
        """Получить версию файла для кэширования."""
        full_path = Path(settings.STORAGE_PATH) / file_path
        if full_path.exists():
            # Используем время модификации файла
            mtime = full_path.stat().st_mtime
            return hashlib.md5(f"{file_path}_{mtime}".encode()).hexdigest()[:8]
        return "00000000"

    def _get_content_type(self, file_path: str) -> str:
        """Определить MIME тип файла."""
        import mimetypes

        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    def cache_file(self, file_path: str, content: bytes, content_type: str = None):
        """Кэшировать файл в CDN."""
        cache_path = self.cache_dir / file_path
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(cache_path, "wb") as f:
                f.write(content)

            # Обновляем метаданные
            self.cache_metadata["files"][file_path] = {
                "cached_at": datetime.utcnow().isoformat(),
                "size": len(content),
                "content_type": content_type,
                "version": self._get_file_version(file_path),
            }
            self._save_cache_metadata()

        except Exception as e:
            print(f"Ошибка кэширования файла {file_path}: {e}")

    def get_cached_file(self, file_path: str) -> Optional[bytes]:
        """Получить файл из кэша."""
        cache_path = self.cache_dir / file_path

        if cache_path.exists():
            # Проверяем актуальность кэша
            if self._is_cache_valid(file_path):
                self.cache_metadata["stats"]["hits"] += 1
                self._save_cache_metadata()

                try:
                    with open(cache_path, "rb") as f:
                        return f.read()
                except Exception as e:
                    print(f"Ошибка чтения кэшированного файла {file_path}: {e}")
            else:
                # Кэш устарел, удаляем
                self._invalidate_cache(file_path)

        self.cache_metadata["stats"]["misses"] += 1
        self._save_cache_metadata()
        return None

    def _is_cache_valid(self, file_path: str) -> bool:
        """Проверить актуальность кэша."""
        if file_path not in self.cache_metadata["files"]:
            return False

        cached_at = datetime.fromisoformat(
            self.cache_metadata["files"][file_path]["cached_at"]
        )
        # Кэш действителен 1 час
        return datetime.utcnow() - cached_at < timedelta(hours=1)

    def _invalidate_cache(self, file_path: str):
        """Инвалидировать кэш файла."""
        cache_path = self.cache_dir / file_path
        if cache_path.exists():
            try:
                cache_path.unlink()
            except Exception:
                pass

        if file_path in self.cache_metadata["files"]:
            del self.cache_metadata["files"][file_path]
            self._save_cache_metadata()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша."""
        total_files = len(self.cache_metadata["files"])
        total_size = sum(
            file_info.get("size", 0)
            for file_info in self.cache_metadata["files"].values()
        )

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "hits": self.cache_metadata["stats"]["hits"],
            "misses": self.cache_metadata["stats"]["misses"],
            "hit_rate": round(
                self.cache_metadata["stats"]["hits"]
                / max(
                    1,
                    self.cache_metadata["stats"]["hits"]
                    + self.cache_metadata["stats"]["misses"],
                )
                * 100,
                2,
            ),
        }

    def clear_cache(self):
        """Очистить весь кэш."""
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            self.cache_metadata = {"files": {}, "stats": {"hits": 0, "misses": 0}}
            self._save_cache_metadata()
        except Exception as e:
            print(f"Ошибка очистки кэша: {e}")


# Глобальный экземпляр CDN сервиса
local_cdn_service = LocalCDNService()
