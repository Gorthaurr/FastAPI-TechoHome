#!/usr/bin/env python3
"""
MinIO Storage Checker
Универсальный скрипт для проверки содержимого MinIO хранилища

Usage:
    python test/check_minio.py [bucket_name] [prefix]
    
Examples:
    python test/check_minio.py                    # Показать общую статистику
    python test/check_minio.py product-images     # Проверить bucket product-images
    python test/check_minio.py product-images products/  # Проверить папку products/
"""

import os
import sys
import argparse
from minio import Minio
from minio.error import S3Error
from datetime import datetime
import json


class MinioChecker:
    def __init__(self):
        self.client = Minio(
            "localhost:9002",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        
    def get_connection_info(self):
        """Получить информацию о подключении к MinIO"""
        try:
            # Попробуем получить список buckets
            buckets = list(self.client.list_buckets())
            print(f"✅ Подключение к MinIO успешно")
            print(f"📊 Найдено buckets: {len(buckets)}")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к MinIO: {e}")
            return False
    
    def get_bucket_list(self):
        """Получить список всех buckets"""
        try:
            buckets = list(self.client.list_buckets())
            return [bucket.name for bucket in buckets]
        except Exception as e:
            print(f"❌ Ошибка получения списка buckets: {e}")
            return []
    
    def get_bucket_stats(self, bucket_name):
        """Получить статистику по bucket"""
        try:
            # Получить все объекты
            objects = list(self.client.list_objects(bucket_name, recursive=True))
            
            total_objects = len(objects)
            total_size = sum(obj.size for obj in objects)
            
            # Группировка по папкам
            folders = {}
            for obj in objects:
                path_parts = obj.object_name.split('/')
                if len(path_parts) > 1:
                    folder = path_parts[0]
                    if folder not in folders:
                        folders[folder] = {'count': 0, 'size': 0}
                    folders[folder]['count'] += 1
                    folders[folder]['size'] += obj.size
            
            return {
                'total_objects': total_objects,
                'total_size': total_size,
                'folders': folders
            }
        except Exception as e:
            print(f"❌ Ошибка получения статистики для bucket {bucket_name}: {e}")
            return None
    
    def get_sample_objects(self, bucket_name, prefix="", limit=10):
        """Получить примеры объектов"""
        try:
            objects = list(self.client.list_objects(bucket_name, prefix=prefix, recursive=True))
            
            sample_data = []
            for obj in objects[:limit]:
                sample_data.append({
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'etag': obj.etag
                })
            
            return sample_data
        except Exception as e:
            print(f"❌ Ошибка получения объектов из bucket {bucket_name}: {e}")
            return []
    
    def check_specific_bucket(self, bucket_name, prefix=""):
        """Проверить конкретный bucket"""
        print(f"\n{'='*60}")
        if prefix:
            print(f"📦 ПРОВЕРКА BUCKET: {bucket_name.upper()} (папка: {prefix})")
        else:
            print(f"📦 ПРОВЕРКА BUCKET: {bucket_name.upper()}")
        print(f"{'='*60}")
        
        # Получить статистику
        stats = self.get_bucket_stats(bucket_name)
        
        if stats is None:
            print(f"❌ Bucket '{bucket_name}' не найден или недоступен")
            return
        
        print(f"📊 Общая статистика:")
        print(f"  Объектов: {stats['total_objects']:,}")
        print(f"  Общий размер: {self.format_size(stats['total_size'])}")
        
        # Показать структуру папок
        if stats['folders']:
            print(f"\n📁 Структура папок:")
            for folder, folder_stats in sorted(stats['folders'].items()):
                print(f"  {folder}/: {folder_stats['count']:,} файлов, {self.format_size(folder_stats['size'])}")
        
        # Показать примеры объектов
        sample_objects = self.get_sample_objects(bucket_name, prefix, 5)
        if sample_objects:
            print(f"\n📝 Примеры объектов:")
            for i, obj in enumerate(sample_objects, 1):
                print(f"\n--- Объект {i} ---")
                print(f"  Имя: {obj['name']}")
                print(f"  Размер: {self.format_size(obj['size'])}")
                if obj['last_modified']:
                    print(f"  Изменен: {obj['last_modified']}")
        
        # Специальные проверки для product-images
        if bucket_name == "product-images":
            self.check_product_images_specific(bucket_name)
    
    def check_product_images_specific(self, bucket_name):
        """Специальные проверки для bucket product-images"""
        try:
            print(f"\n🖼️  Специальная проверка product-images:")
            
            # Проверка структуры products/
            products_objects = list(self.client.list_objects(bucket_name, prefix="products/", recursive=True))
            
            if products_objects:
                # Группировка по продуктам
                products = {}
                for obj in products_objects:
                    path_parts = obj.object_name.split('/')
                    if len(path_parts) >= 3:
                        product_id = path_parts[1]
                        if product_id not in products:
                            products[product_id] = {'count': 0, 'size': 0}
                        products[product_id]['count'] += 1
                        products[product_id]['size'] += obj.size
                
                print(f"  Продуктов с изображениями: {len(products):,}")
                
                # Статистика по продуктам
                total_images = sum(p['count'] for p in products.values())
                avg_images_per_product = total_images / len(products) if products else 0
                
                print(f"  Всего изображений: {total_images:,}")
                print(f"  Среднее изображений на продукт: {avg_images_per_product:.1f}")
                
                # Топ-5 продуктов по количеству изображений
                top_products = sorted(products.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
                print(f"\n  Топ-5 продуктов по количеству изображений:")
                for product_id, stats in top_products:
                    print(f"    Продукт {product_id}: {stats['count']} изображений, {self.format_size(stats['size'])}")
                
                # Проверка размеров изображений
                all_sizes = [obj.size for obj in products_objects]
                if all_sizes:
                    min_size = min(all_sizes)
                    max_size = max(all_sizes)
                    avg_size = sum(all_sizes) / len(all_sizes)
                    
                    print(f"\n  Статистика размеров:")
                    print(f"    Минимальный: {self.format_size(min_size)}")
                    print(f"    Максимальный: {self.format_size(max_size)}")
                    print(f"    Средний: {self.format_size(avg_size)}")
            else:
                print(f"  ❌ Папка products/ пуста или не найдена")
                
        except Exception as e:
            print(f"❌ Ошибка специальной проверки product-images: {e}")
    
    def format_size(self, size_bytes):
        """Форматировать размер в читаемый вид"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def show_general_stats(self):
        """Показать общую статистику по всем buckets"""
        print(f"\n{'='*60}")
        print(f"📊 ОБЩАЯ СТАТИСТИКА MINIO")
        print(f"{'='*60}")
        
        buckets = self.get_bucket_list()
        if not buckets:
            print("❌ Не удалось получить список buckets")
            return
        
        print(f"📦 Найдено buckets: {len(buckets)}")
        
        total_stats = {}
        for bucket in buckets:
            stats = self.get_bucket_stats(bucket)
            if stats:
                total_stats[bucket] = stats
                print(f"  {bucket}: {stats['total_objects']:,} объектов, {self.format_size(stats['total_size'])}")
        
        # Общая статистика
        total_objects = sum(stats['total_objects'] for stats in total_stats.values())
        total_size = sum(stats['total_size'] for stats in total_stats.values())
        
        print(f"\n📈 Общая статистика:")
        print(f"  Всего объектов: {total_objects:,}")
        print(f"  Общий размер: {self.format_size(total_size)}")
        
        # Рекомендации
        print(f"\n💡 Рекомендации:")
        if 'product-images' in total_stats:
            print(f"  - Для проверки изображений: python test/check_minio.py product-images")
            print(f"  - Для проверки структуры: python test/check_minio.py product-images products/")
        
        for bucket in buckets:
            if bucket != 'product-images':
                print(f"  - Для проверки {bucket}: python test/check_minio.py {bucket}")
    
    def run(self, bucket_name=None, prefix=""):
        """Запустить проверку"""
        print(f"🔍 MinIO Storage Checker")
        print(f"⏰ Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Проверить подключение
        if not self.get_connection_info():
            return
        
        if bucket_name:
            self.check_specific_bucket(bucket_name, prefix)
        else:
            self.show_general_stats()


def main():
    parser = argparse.ArgumentParser(description='MinIO Storage Checker')
    parser.add_argument('bucket', nargs='?', help='Имя bucket для детальной проверки')
    parser.add_argument('prefix', nargs='?', default='', help='Префикс (папка) для проверки')
    args = parser.parse_args()
    
    try:
        checker = MinioChecker()
        checker.run(args.bucket, args.prefix)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
