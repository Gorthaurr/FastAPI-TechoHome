#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""

import sys
from pathlib import Path

# Добавляем путь к модулю app
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import engine
from app.db.models import Base

def init_database():
    """Создает все таблицы в базе данных."""
    print("🗄️ Инициализация базы данных...")
    
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        print("✅ Все таблицы созданы успешно!")
        
        # Показываем созданные таблицы
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"📋 Создано таблиц: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания таблиц: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)
