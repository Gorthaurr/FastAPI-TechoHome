#!/usr/bin/env python3
"""
Тест MinIO через mc команды
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.storage_service import MinIOStorageProvider
from io import BytesIO

print("🔍 Тестирование MinIO через mc команды...")

# Создаем MinIO provider
minio_provider = MinIOStorageProvider(
    bucket_name="product-images",
    endpoint_url="http://localhost:9000"
)

print("✅ MinIO provider создан")

# Тест 1: Загрузка файла
print("\n🔍 Тест 1: Загрузка файла...")
try:
    test_content = b"Hello MinIO via mc!"
    test_data = BytesIO(test_content)
    
    if minio_provider.save_file("test_mc.txt", test_data):
        print("✅ Файл загружен успешно")
    else:
        print("❌ Ошибка загрузки файла")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Тест 2: Проверка существования файла
print("\n🔍 Тест 2: Проверка существования файла...")
try:
    if minio_provider.file_exists("test_mc.txt"):
        print("✅ Файл существует")
    else:
        print("❌ Файл не найден")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Тест 3: Получение URL
print("\n🔍 Тест 3: Получение URL...")
try:
    url = minio_provider.get_file_url("test_mc.txt")
    if url:
        print(f"✅ URL получен: {url}")
    else:
        print("❌ URL не получен")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Тест 4: Удаление файла
print("\n🔍 Тест 4: Удаление файла...")
try:
    if minio_provider.delete_file("test_mc.txt"):
        print("✅ Файл удален успешно")
    else:
        print("❌ Ошибка удаления файла")
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\n✅ Все тесты завершены")
