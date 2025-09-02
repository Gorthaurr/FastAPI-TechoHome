#!/usr/bin/env python3
"""
Скрипт для создания администратора в базе данных.
"""

import os
import sys
from pathlib import Path

# Добавляем путь к модулю app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import sessionmaker

from app.core.auth import AuthService
from app.db.database import engine
from app.db.models.user import User


def create_admin():
    """Создает администратора в базе данных."""
    print("🔑 Создание администратора...")
    print("=" * 50)

    try:
        # Создаем сессию базы данных
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # Проверяем, существует ли уже администратор
        existing_admin = (
            db.query(User)
            .filter((User.username == "admin") | (User.email == "admin@techhome.com"))
            .first()
        )

        if existing_admin:
            print("✅ Администратор уже существует:")
            print(f"   Username: {existing_admin.username}")
            print(f"   Email: {existing_admin.email}")
            print(f"   ID: {existing_admin.id}")
            print(f"   Админ: {existing_admin.is_admin}")
            print(f"   Супер-админ: {existing_admin.is_super_admin}")

            # Обновляем пароль на admin123
            new_hash = AuthService.get_password_hash("admin123")
            existing_admin.hashed_password = new_hash
            db.commit()

            print("✅ Пароль обновлен на: admin123")
            print(f"   Новый хеш: {new_hash}")

        else:
            print("📝 Создаем нового администратора...")

            # Создаем хеш пароля
            password = "admin123"
            hashed_password = AuthService.get_password_hash(password)

            # Создаем пользователя
            admin_user = User(
                username="admin",
                email="admin@techhome.com",
                hashed_password=hashed_password,
                full_name="Системный администратор",
                is_active=True,
                is_admin=True,
                is_super_admin=True,
                notes="Супер-администратор по умолчанию. Смените пароль после первого входа!",
            )

            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

            print("✅ Администратор создан успешно!")
            print(f"   Username: {admin_user.username}")
            print(f"   Email: {admin_user.email}")
            print(f"   ID: {admin_user.id}")
            print(f"   Пароль: {password}")
            print(f"   Хеш: {hashed_password}")

        db.close()

        print("=" * 50)
        print("🎉 Администратор готов к использованию!")
        print("📝 Данные для входа:")
        print("   Логин: admin")
        print("   Пароль: admin123")
        print("   Email: admin@techhome.com")

        return True

    except Exception as e:
        print(f"❌ Ошибка при создании администратора: {e}")
        return False


if __name__ == "__main__":
    try:
        success = create_admin()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
