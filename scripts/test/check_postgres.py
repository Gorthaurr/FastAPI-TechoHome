#!/usr/bin/env python3
"""
PostgreSQL Database Checker
Универсальный скрипт для проверки содержимого базы данных PostgreSQL

Usage:
    python test/check_postgres.py [table_name]
    
Examples:
    python test/check_postgres.py                    # Показать общую статистику
    python test/check_postgres.py products           # Проверить таблицу products
    python test/check_postgres.py product_images     # Проверить таблицу product_images
    python test/check_postgres.py categories         # Проверить таблицу categories
"""

import os
import sys
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings


class PostgresChecker:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_connection_info(self):
        """Получить информацию о подключении к БД"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                print(f"✅ Подключение к PostgreSQL успешно")
                print(f"📊 Версия: {version}")
                return True
        except Exception as e:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            return False
    
    def get_table_list(self):
        """Получить список всех таблиц"""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
                result = conn.execute(query)
                tables = [row[0] for row in result]
                return tables
        except Exception as e:
            print(f"❌ Ошибка получения списка таблиц: {e}")
            return []
    
    def get_table_stats(self, table_name):
        """Получить статистику по таблице"""
        try:
            with self.engine.connect() as conn:
                # Количество записей
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                count_result = conn.execute(count_query)
                count = count_result.scalar()
                
                # Структура таблицы
                structure_query = text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    ORDER BY ordinal_position
                """)
                structure_result = conn.execute(structure_query, {"table_name": table_name})
                columns = [(row.column_name, row.data_type, row.is_nullable) for row in structure_result]
                
                return count, columns
        except Exception as e:
            print(f"❌ Ошибка получения статистики для таблицы {table_name}: {e}")
            return 0, []
    
    def get_sample_data(self, table_name, limit=5):
        """Получить примеры данных из таблицы"""
        try:
            with self.engine.connect() as conn:
                # Получить все колонки
                columns_query = text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    ORDER BY ordinal_position
                """)
                columns_result = conn.execute(columns_query, {"table_name": table_name})
                columns = [row.column_name for row in columns_result]
                
                if not columns:
                    return []
                
                # Получить данные
                data_query = text(f"SELECT * FROM {table_name} LIMIT {limit}")
                data_result = conn.execute(data_query)
                
                sample_data = []
                for row in data_result:
                    row_dict = {}
                    for i, column in enumerate(columns):
                        value = row[i]
                        # Обрезать длинные значения
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        row_dict[column] = value
                    sample_data.append(row_dict)
                
                return sample_data
        except Exception as e:
            print(f"❌ Ошибка получения данных из таблицы {table_name}: {e}")
            return []
    
    def check_specific_table(self, table_name):
        """Проверить конкретную таблицу"""
        print(f"\n{'='*60}")
        print(f"📋 ПРОВЕРКА ТАБЛИЦЫ: {table_name.upper()}")
        print(f"{'='*60}")
        
        # Получить статистику
        count, columns = self.get_table_stats(table_name)
        
        if count == 0 and not columns:
            print(f"❌ Таблица '{table_name}' не найдена или недоступна")
            return
        
        print(f"📊 Количество записей: {count:,}")
        
        # Показать структуру
        print(f"\n🏗️  Структура таблицы:")
        print(f"{'Колонка':<20} {'Тип':<15} {'NULL':<8}")
        print(f"{'-'*20} {'-'*15} {'-'*8}")
        for col_name, col_type, is_nullable in columns:
            nullable = "YES" if is_nullable == "YES" else "NO"
            print(f"{col_name:<20} {col_type:<15} {nullable:<8}")
        
        # Показать примеры данных
        if count > 0:
            sample_data = self.get_sample_data(table_name, 3)
            if sample_data:
                print(f"\n📝 Примеры данных (первые 3 записи):")
                for i, row in enumerate(sample_data, 1):
                    print(f"\n--- Запись {i} ---")
                    for key, value in row.items():
                        print(f"  {key}: {value}")
        
        # Специальные проверки для известных таблиц
        if table_name == "products":
            self.check_products_specific()
        elif table_name == "product_images":
            self.check_product_images_specific()
        elif table_name == "categories":
            self.check_categories_specific()
    
    def check_products_specific(self):
        """Специальные проверки для таблицы products"""
        try:
            with self.engine.connect() as conn:
                # Проверка цен
                price_query = text("""
                    SELECT 
                        MIN(price_cents) as min_price,
                        MAX(price_cents) as max_price,
                        AVG(price_cents) as avg_price,
                        COUNT(*) as total_products
                    FROM products
                """)
                price_result = conn.execute(price_query).fetchone()
                
                print(f"\n💰 Статистика цен:")
                print(f"  Минимальная цена: {price_result.min_price:,} копеек")
                print(f"  Максимальная цена: {price_result.max_price:,} копеек")
                print(f"  Средняя цена: {price_result.avg_price:,.0f} копеек")
                
                # Проверка категорий
                category_query = text("""
                    SELECT c.slug, COUNT(p.id) as product_count
                    FROM products p
                    JOIN categories c ON p.category_id = c.id
                    GROUP BY c.id, c.slug
                    ORDER BY product_count DESC
                """)
                category_result = conn.execute(category_query)
                
                print(f"\n📂 Продукты по категориям:")
                for row in category_result:
                    print(f"  {row.slug}: {row.product_count:,} продуктов")
                    
        except Exception as e:
            print(f"❌ Ошибка специальной проверки products: {e}")
    
    def check_product_images_specific(self):
        """Специальные проверки для таблицы product_images"""
        try:
            with self.engine.connect() as conn:
                # Проверка путей
                path_query = text("""
                    SELECT 
                        COUNT(*) as total_images,
                        COUNT(CASE WHEN path LIKE 'products/%' THEN 1 END) as minio_images,
                        COUNT(CASE WHEN path LIKE 'images/%' THEN 1 END) as local_images,
                        COUNT(CASE WHEN path NOT LIKE 'products/%' AND path NOT LIKE 'images/%' THEN 1 END) as other_paths
                    FROM product_images
                """)
                path_result = conn.execute(path_query).fetchone()
                
                print(f"\n🖼️  Статистика изображений:")
                print(f"  Всего изображений: {path_result.total_images:,}")
                print(f"  В MinIO (products/): {path_result.minio_images:,}")
                print(f"  Локальные (images/): {path_result.local_images:,}")
                print(f"  Другие пути: {path_result.other_paths:,}")
                
                # Проверка размеров файлов
                size_query = text("""
                    SELECT 
                        MIN(file_size) as min_size,
                        MAX(file_size) as max_size,
                        AVG(file_size) as avg_size
                    FROM product_images
                    WHERE file_size IS NOT NULL
                """)
                size_result = conn.execute(size_query).fetchone()
                
                if size_result.min_size:
                    print(f"\n📏 Размеры файлов:")
                    print(f"  Минимальный: {size_result.min_size:,} байт")
                    print(f"  Максимальный: {size_result.max_size:,} байт")
                    print(f"  Средний: {size_result.avg_size:,.0f} байт")
                    
        except Exception as e:
            print(f"❌ Ошибка специальной проверки product_images: {e}")
    
    def check_categories_specific(self):
        """Специальные проверки для таблицы categories"""
        try:
            with self.engine.connect() as conn:
                # Получить все категории с количеством продуктов
                query = text("""
                    SELECT c.id, c.slug, COUNT(p.id) as product_count
                    FROM categories c
                    LEFT JOIN products p ON c.id = p.category_id
                    GROUP BY c.id, c.slug
                    ORDER BY product_count DESC
                """)
                result = conn.execute(query)
                
                print(f"\n📂 Детальная информация по категориям:")
                for row in result:
                    print(f"  ID: {row.id}, Slug: {row.slug}, Продуктов: {row.product_count:,}")
                    
        except Exception as e:
            print(f"❌ Ошибка специальной проверки categories: {e}")
    
    def show_general_stats(self):
        """Показать общую статистику по всем таблицам"""
        print(f"\n{'='*60}")
        print(f"📊 ОБЩАЯ СТАТИСТИКА БАЗЫ ДАННЫХ")
        print(f"{'='*60}")
        
        tables = self.get_table_list()
        if not tables:
            print("❌ Не удалось получить список таблиц")
            return
        
        print(f"📋 Найдено таблиц: {len(tables)}")
        
        total_stats = {}
        for table in tables:
            count, _ = self.get_table_stats(table)
            total_stats[table] = count
            print(f"  {table}: {count:,} записей")
        
        # Общая статистика
        total_records = sum(total_stats.values())
        print(f"\n📈 Общее количество записей: {total_records:,}")
        
        # Рекомендации
        print(f"\n💡 Рекомендации:")
        if total_stats.get('products', 0) > 0:
            print(f"  - Для детальной проверки продуктов: python test/check_postgres.py products")
        if total_stats.get('product_images', 0) > 0:
            print(f"  - Для проверки изображений: python test/check_postgres.py product_images")
        if total_stats.get('categories', 0) > 0:
            print(f"  - Для проверки категорий: python test/check_postgres.py categories")
    
    def run(self, table_name=None):
        """Запустить проверку"""
        print(f"🔍 PostgreSQL Database Checker")
        print(f"⏰ Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Проверить подключение
        if not self.get_connection_info():
            return
        
        if table_name:
            self.check_specific_table(table_name)
        else:
            self.show_general_stats()


def main():
    parser = argparse.ArgumentParser(description='PostgreSQL Database Checker')
    parser.add_argument('table', nargs='?', help='Имя таблицы для детальной проверки')
    args = parser.parse_args()
    
    try:
        checker = PostgresChecker()
        checker.run(args.table)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
