#!/usr/bin/env python3
"""
System Health Checker
Универсальный скрипт для быстрой проверки состояния всей системы

Usage:
    python test/check_system.py [component]
    
Examples:
    python test/check_system.py                    # Проверить всю систему
    python test/check_system.py postgres           # Проверить только PostgreSQL
    python test/check_system.py minio              # Проверить только MinIO
    python test/check_system.py fastapi            # Проверить только FastAPI
"""

import os
import sys
import argparse
import requests
import subprocess
from datetime import datetime
from sqlalchemy import create_engine, text
from minio import Minio
from minio.error import S3Error

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings


class SystemChecker:
    def __init__(self):
        self.results = {}
        
    def check_postgres(self):
        """Проверить PostgreSQL"""
        print(f"\n{'='*50}")
        print(f"🐘 ПРОВЕРКА POSTGRESQL")
        print(f"{'='*50}")
        
        try:
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                # Проверка подключения
                version_result = conn.execute(text("SELECT version()"))
                version = version_result.scalar()
                print(f"✅ Подключение: Успешно")
                print(f"📊 Версия: {version.split(',')[0]}")
                
                # Проверка таблиц
                tables_result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in tables_result]
                print(f"📋 Таблиц найдено: {len(tables)}")
                
                # Проверка основных таблиц
                main_tables = ['products', 'categories', 'product_images']
                for table in main_tables:
                    if table in tables:
                        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = count_result.scalar()
                        print(f"  {table}: {count:,} записей")
                    else:
                        print(f"  ❌ {table}: НЕ НАЙДЕНА")
                
                self.results['postgres'] = {
                    'status': 'OK',
                    'tables': len(tables),
                    'version': version.split(',')[0]
                }
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            self.results['postgres'] = {'status': 'ERROR', 'error': str(e)}
    
    def check_minio(self):
        """Проверить MinIO"""
        print(f"\n{'='*50}")
        print(f"📦 ПРОВЕРКА MINIO")
        print(f"{'='*50}")
        
        try:
            client = Minio(
                "localhost:9002",
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False
            )
            
            # Проверка подключения
            buckets = list(client.list_buckets())
            print(f"✅ Подключение: Успешно")
            print(f"📊 Buckets найдено: {len(buckets)}")
            
            # Проверка product-images bucket
            product_images_bucket = None
            for bucket in buckets:
                if bucket.name == 'product-images':
                    product_images_bucket = bucket
                    break
            
            if product_images_bucket:
                print(f"✅ Bucket 'product-images': Найден")
                
                # Подсчет объектов
                objects = list(client.list_objects('product-images', recursive=True))
                print(f"📊 Объектов в product-images: {len(objects):,}")
                
                # Подсчет размера
                total_size = sum(obj.size for obj in objects)
                size_mb = total_size / (1024 * 1024)
                print(f"💾 Общий размер: {size_mb:.1f} MB")
                
                self.results['minio'] = {
                    'status': 'OK',
                    'buckets': len(buckets),
                    'product_images_objects': len(objects),
                    'total_size_mb': size_mb
                }
            else:
                print(f"❌ Bucket 'product-images': НЕ НАЙДЕН")
                self.results['minio'] = {'status': 'WARNING', 'error': 'product-images bucket not found'}
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            self.results['minio'] = {'status': 'ERROR', 'error': str(e)}
    
    def check_fastapi(self):
        """Проверить FastAPI приложение"""
        print(f"\n{'='*50}")
        print(f"🚀 ПРОВЕРКА FASTAPI")
        print(f"{'='*50}")
        
        try:
            # Проверка доступности API
            response = requests.get("http://localhost:8000/docs", timeout=5)
            if response.status_code == 200:
                print(f"✅ API доступен: http://localhost:8000")
                print(f"📊 Статус: {response.status_code}")
                
                # Проверка основных эндпоинтов
                endpoints = [
                    ("/api/v1/products", "Продукты"),
                    ("/api/v1/categories", "Категории"),
                    ("/api/v1/products/images", "Изображения")
                ]
                
                for endpoint, name in endpoints:
                    try:
                        resp = requests.get(f"http://localhost:8000{endpoint}", timeout=3)
                        if resp.status_code in [200, 404]:  # 404 тоже нормально, если нет данных
                            print(f"  ✅ {name}: {resp.status_code}")
                        else:
                            print(f"  ⚠️  {name}: {resp.status_code}")
                    except:
                        print(f"  ❌ {name}: Недоступен")
                
                self.results['fastapi'] = {'status': 'OK', 'port': 8000}
                
            else:
                print(f"❌ API недоступен: {response.status_code}")
                self.results['fastapi'] = {'status': 'ERROR', 'error': f'HTTP {response.status_code}'}
                
        except requests.exceptions.ConnectionError:
            print(f"❌ API недоступен: Соединение отклонено")
            self.results['fastapi'] = {'status': 'ERROR', 'error': 'Connection refused'}
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            self.results['fastapi'] = {'status': 'ERROR', 'error': str(e)}
    
    def check_docker(self):
        """Проверить Docker контейнеры"""
        print(f"\n{'='*50}")
        print(f"🐳 ПРОВЕРКА DOCKER")
        print(f"{'='*50}")
        
        try:
            # Проверка запущенных контейнеров
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Есть заголовок
                    containers = lines[1:]
                    print(f"✅ Docker доступен")
                    print(f"📊 Контейнеров запущено: {len(containers)}")
                    
                    # Проверка нужных контейнеров
                    required_containers = ['postgres', 'minio', 'redis']
                    for container in containers:
                        if container.strip():
                            parts = container.split('\t')
                            if len(parts) >= 2:
                                name = parts[0]
                                status = parts[1]
                                ports = parts[2] if len(parts) > 2 else ""
                                
                                if any(req in name.lower() for req in required_containers):
                                    print(f"  ✅ {name}: {status}")
                                    if ports:
                                        print(f"    Порт: {ports}")
                                else:
                                    print(f"  ℹ️  {name}: {status}")
                    
                    self.results['docker'] = {'status': 'OK', 'containers': len(containers)}
                else:
                    print(f"ℹ️  Запущенных контейнеров нет")
                    self.results['docker'] = {'status': 'WARNING', 'containers': 0}
            else:
                print(f"❌ Docker недоступен")
                self.results['docker'] = {'status': 'ERROR', 'error': 'Docker not available'}
                
        except subprocess.TimeoutExpired:
            print(f"❌ Таймаут при проверке Docker")
            self.results['docker'] = {'status': 'ERROR', 'error': 'Timeout'}
        except FileNotFoundError:
            print(f"❌ Docker не установлен")
            self.results['docker'] = {'status': 'ERROR', 'error': 'Docker not installed'}
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            self.results['docker'] = {'status': 'ERROR', 'error': str(e)}
    
    def generate_summary(self):
        """Сгенерировать итоговый отчет"""
        print(f"\n{'='*60}")
        print(f"📋 ИТОГОВЫЙ ОТЧЕТ")
        print(f"{'='*60}")
        
        total_components = len(self.results)
        ok_components = sum(1 for r in self.results.values() if r['status'] == 'OK')
        error_components = sum(1 for r in self.results.values() if r['status'] == 'ERROR')
        warning_components = sum(1 for r in self.results.values() if r['status'] == 'WARNING')
        
        print(f"📊 Статистика:")
        print(f"  Всего компонентов: {total_components}")
        print(f"  ✅ Работают: {ok_components}")
        print(f"  ⚠️  Предупреждения: {warning_components}")
        print(f"  ❌ Ошибки: {error_components}")
        
        # Детальный статус
        print(f"\n🔍 Детальный статус:")
        for component, result in self.results.items():
            status_icon = "✅" if result['status'] == 'OK' else "⚠️" if result['status'] == 'WARNING' else "❌"
            print(f"  {status_icon} {component.upper()}: {result['status']}")
            if 'error' in result:
                print(f"    Ошибка: {result['error']}")
        
        # Рекомендации
        print(f"\n💡 Рекомендации:")
        if error_components > 0:
            print(f"  - Проверьте логи компонентов с ошибками")
            print(f"  - Убедитесь, что все сервисы запущены")
        
        if 'postgres' in self.results and self.results['postgres']['status'] == 'OK':
            print(f"  - Для детальной проверки БД: python test/check_postgres.py")
        
        if 'minio' in self.results and self.results['minio']['status'] == 'OK':
            print(f"  - Для детальной проверки MinIO: python test/check_minio.py")
        
        # Общий статус системы
        if error_components == 0 and warning_components == 0:
            print(f"\n🎉 СИСТЕМА РАБОТАЕТ ОТЛИЧНО!")
        elif error_components == 0:
            print(f"\n⚠️  СИСТЕМА РАБОТАЕТ С ПРЕДУПРЕЖДЕНИЯМИ")
        else:
            print(f"\n❌ СИСТЕМА ИМЕЕТ ПРОБЛЕМЫ")
    
    def run(self, component=None):
        """Запустить проверку"""
        print(f"🔍 System Health Checker")
        print(f"⏰ Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if component is None or component == 'postgres':
            self.check_postgres()
        
        if component is None or component == 'minio':
            self.check_minio()
        
        if component is None or component == 'fastapi':
            self.check_fastapi()
        
        if component is None or component == 'docker':
            self.check_docker()
        
        if component is None:
            self.generate_summary()


def main():
    parser = argparse.ArgumentParser(description='System Health Checker')
    parser.add_argument('component', nargs='?', choices=['postgres', 'minio', 'fastapi', 'docker'], 
                       help='Компонент для проверки (если не указан, проверяются все)')
    args = parser.parse_args()
    
    try:
        checker = SystemChecker()
        checker.run(args.component)
    except KeyboardInterrupt:
        print(f"\n⏹️  Проверка прервана пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
