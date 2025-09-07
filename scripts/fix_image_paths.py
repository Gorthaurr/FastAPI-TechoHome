#!/usr/bin/env python3
"""
Скрипт для исправления путей изображений в базе данных.
Обновляет пути в таблице product_images для соответствия новой структуре.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.db.models.product_image import ProductImage
from sqlalchemy import select

def fix_image_paths():
    """Исправление путей изображений в БД."""
    print("🔧 ИСПРАВЛЕНИЕ ПУТЕЙ ИЗОБРАЖЕНИЙ В БАЗЕ ДАННЫХ")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Получаем все изображения
        images = db.execute(select(ProductImage)).scalars().all()
        
        print(f"📦 Найдено изображений: {len(images)}")
        
        updated_count = 0
        for img in images:
            old_path = img.path
            
            # Анализируем текущий путь
            parts = old_path.split('/')
            
            # Если путь уже правильный (products/12символов/filename)
            if len(parts) == 3 and parts[0] == 'products' and len(parts[1]) == 12:
                continue
            
            # Исправляем путь
            filename = parts[-1]  # Берем имя файла
            new_path = f"products/{img.product_id[:12]}/{filename}"
            
            if new_path != old_path:
                print(f"\n  Товар: {img.product_id[:8]}...")
                print(f"    Было: {old_path}")
                print(f"    Стало: {new_path}")
                img.path = new_path
                updated_count += 1
        
        if updated_count > 0:
            print(f"\n💾 Сохранение изменений...")
            db.commit()
            print(f"✅ Обновлено путей: {updated_count}")
        else:
            print("\n✅ Все пути уже правильные, обновление не требуется")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_image_paths()

