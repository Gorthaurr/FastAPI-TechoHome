#!/usr/bin/env python3
"""
Тестовый скрипт для проверки аутентификации.
"""

from app.core.auth import AuthService
from app.db.database import SessionLocal
from app.db.models.user import User

def test_auth():
    """Тестируем аутентификацию"""
    auth_service = AuthService()
    
    # Тестируем хеширование пароля
    test_password = "admin123"
    hashed = auth_service.get_password_hash(test_password)
    print(f"Тестовый пароль: {test_password}")
    print(f"Хеш: {hashed}")
    
    # Тестируем проверку пароля
    is_valid = auth_service.verify_password(test_password, hashed)
    print(f"Проверка пароля: {is_valid}")
    
    # Проверяем пользователя в базе
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if user:
            print(f"\nПользователь найден:")
            print(f"  ID: {user.id}")
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Хеш в БД: {user.hashed_password}")
            print(f"  is_admin: {user.is_admin}")
            print(f"  is_super_admin: {user.is_super_admin}")
            
            # Тестируем проверку пароля из БД
            db_password_valid = auth_service.verify_password(test_password, user.hashed_password)
            print(f"  Проверка пароля из БД: {db_password_valid}")
        else:
            print("Пользователь admin не найден!")
    finally:
        db.close()

if __name__ == "__main__":
    test_auth()
