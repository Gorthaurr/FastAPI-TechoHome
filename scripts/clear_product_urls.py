#!/usr/bin/env python3
"""
Скрипт для очистки поля product_url во всех товарах в базе данных.

Использование:
    python scripts/clear_product_urls.py
"""

import sys
import os
from pathlib import Path

# Добавляем корневую папку проекта в путь для импорта
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def clear_product_urls():
    """Очищает поле product_url во всех товарах"""

    # Импортируем настройки базы данных
    from app.core.config import settings

    # Создаем подключение к базе данных
    engine = create_engine(settings.DATABASE_URL)

    # Создаем сессию
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Получаем количество товаров с заполненным product_url
        count_query = text("SELECT COUNT(*) FROM products WHERE product_url IS NOT NULL AND product_url != ''")
        result = db.execute(count_query)
        count = result.scalar()

        print(f"Найдено {count} товаров с заполненным product_url")

        if count == 0:
            print("Нечего очищать - все product_url уже пустые")
            return

        # Очищаем product_url
        update_query = text("UPDATE products SET product_url = NULL WHERE product_url IS NOT NULL AND product_url != ''")
        db.execute(update_query)
        db.commit()

        print(f"✅ Успешно очищено {count} полей product_url")

        # Проверяем результат
        verify_query = text("SELECT COUNT(*) FROM products WHERE product_url IS NOT NULL AND product_url != ''")
        result = db.execute(verify_query)
        remaining = result.scalar()

        if remaining == 0:
            print("✅ Все product_url успешно очищены")
        else:
            print(f"⚠️  Осталось {remaining} товаров с product_url")

    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Основная функция"""
    print("🧹 Начинаем очистку product_url...")

    try:
        clear_product_urls()
        print("✅ Очистка завершена успешно!")
    except Exception as e:
        print(f"❌ Ошибка выполнения: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
