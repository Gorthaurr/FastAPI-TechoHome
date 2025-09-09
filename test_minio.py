#!/usr/bin/env python3
"""
Тест подключения к MinIO
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Настройки
endpoint_url = "http://localhost:9000"
bucket_name = "product-images"
access_key = "minioadmin"
secret_key = "minioadmin"

print("🔍 Тестирование подключения к MinIO...")
print(f"Endpoint: {endpoint_url}")
print(f"Bucket: {bucket_name}")

# Конфигурация для MinIO
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

try:
    # Создаем клиент
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=config,
        use_ssl=False
    )
    
    # Устанавливаем signature_version для MinIO
    s3_client._client_config.signature_version = 's3v4'
    
    print("✅ S3 клиент создан")
    
    # Тест 1: Список bucket'ов
    print("\n🔍 Тест 1: Получение списка bucket'ов...")
    try:
        response = s3_client.list_buckets()
        print(f"✅ Найдено bucket'ов: {len(response.get('Buckets', []))}")
        for bucket in response.get('Buckets', []):
            print(f"  - {bucket['Name']}")
    except Exception as e:
        print(f"❌ Ошибка получения списка bucket'ов: {e}")
    
    # Тест 2: Проверка bucket
    print(f"\n🔍 Тест 2: Проверка bucket '{bucket_name}'...")
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' существует и доступен")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ Ошибка проверки bucket: {error_code} - {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
    
    # Тест 3: Загрузка тестового файла
    print(f"\n🔍 Тест 3: Загрузка тестового файла...")
    try:
        test_content = b"Hello MinIO!"
        s3_client.put_object(
            Bucket=bucket_name,
            Key="test.txt",
            Body=test_content,
            ContentType="text/plain"
        )
        print("✅ Тестовый файл загружен успешно")
        
        # Удаляем тестовый файл
        s3_client.delete_object(Bucket=bucket_name, Key="test.txt")
        print("✅ Тестовый файл удален")
        
    except Exception as e:
        print(f"❌ Ошибка загрузки файла: {e}")
    
    print("\n✅ Все тесты завершены")
    
except Exception as e:
    print(f"❌ Критическая ошибка: {e}")
