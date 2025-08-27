#!/usr/bin/env python3
"""
Простой скрипт для проверки локальной БД.
"""

import psycopg2
import sys

def main():
    try:
        print("🔍 Проверка подключения к локальной БД...")
        
        # Пробуем разные варианты подключения
        connection_strings = [
            "postgresql://postgres:Anton533@localhost:5432/Shop",
            "host=localhost port=5432 dbname=Shop user=postgres password=Anton533",
            "postgresql://postgres:Anton533@127.0.0.1:5432/Shop"
        ]
        
        for i, conn_str in enumerate(connection_strings, 1):
            print(f"\nПопытка {i}: {conn_str}")
            try:
                conn = psycopg2.connect(conn_str)
                print("✅ Подключение успешно!")
                
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                
                tables = cursor.fetchall()
                print(f"📋 Найдено таблиц: {len(tables)}")
                for table in tables:
                    print(f"  - {table[0]}")
                
                cursor.close()
                conn.close()
                return True
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                continue
        
        print("\n❌ Не удалось подключиться ни одним способом")
        return False
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
