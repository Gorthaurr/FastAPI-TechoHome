#!/usr/bin/env python3
"""
Единый файл для запуска всей системы FastAPI с хранилищем и CDN.
Запускает: PostgreSQL, MinIO, Redis, FastAPI приложение
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional


# Цвета для вывода
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


class SystemRunner:
    """Класс для управления всей системой."""

    def __init__(self):
        self.processes = []
        self.running = False
        self.project_root = Path(__file__).parent

        # Настройки (обновлены в соответствии с docker-compose.yml)
        self.fastapi_port = 8000
        self.postgres_port = 5433
        self.minio_api_port = 9002  # Изменено с 9000 на 9002
        self.minio_console_port = 9001
        self.redis_port = 6379
        self.pgadmin_port = 5050  # Добавлен pgAdmin

        # Пути к файлам
        self.docker_compose_file = self.project_root / "docker-compose.yml"
        self.env_file = self.project_root.parent / ".env"  # .env в родительской папке
        self.uploads_dir = (
            self.project_root.parent / "uploads"
        )  # uploads в родительской папке
        self.cdn_cache_dir = (
            self.project_root.parent / "cdn_cache"
        )  # cdn_cache в родительской папке

    def print_status(self, message: str, color: str = Colors.GREEN):
        """Вывести статусное сообщение."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {message}{Colors.END}")

    def print_header(self):
        """Вывести заголовок."""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("=" * 60)
        print("🚀 FastAPI Image Management System")
        print("=" * 60)
        print(f"{Colors.END}")
        print(f"{Colors.YELLOW}Запуск системы управления изображениями...{Colors.END}")
        print()

    def check_dependencies(self) -> bool:
        """Проверить зависимости."""
        self.print_status("Проверка зависимостей...", Colors.BLUE)

        # Проверяем Python
        if sys.version_info < (3, 8):
            self.print_status("❌ Требуется Python 3.8+", Colors.RED)
            return False

        # Проверяем Docker
        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.print_status("✅ Docker найден", Colors.GREEN)
            else:
                self.print_status("❌ Docker не найден", Colors.RED)
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.print_status("❌ Docker не найден", Colors.RED)
            return False

        # Проверяем docker-compose
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.print_status("✅ Docker Compose найден", Colors.GREEN)
            else:
                self.print_status("❌ Docker Compose не найден", Colors.RED)
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.print_status("❌ Docker Compose не найден", Colors.RED)
            return False

        return True

    def start_docker_desktop(self) -> bool:
        """Запустить Docker Desktop."""
        self.print_status("Запуск Docker Desktop...", Colors.BLUE)

        # Проверяем, не запущен ли уже Docker
        try:
            result = subprocess.run(
                ["docker", "ps"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.print_status("✅ Docker Desktop уже запущен", Colors.GREEN)
                return True
        except:
            pass

        # Пытаемся запустить Docker Desktop
        docker_paths = [
            r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
            r"C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe",
            "Docker Desktop.exe",
        ]

        for docker_path in docker_paths:
            try:
                if os.path.exists(docker_path):
                    self.print_status(
                        f"Запуск Docker Desktop: {docker_path}", Colors.YELLOW
                    )
                    subprocess.Popen(
                        [docker_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    break
            except Exception as e:
                continue
        else:
            self.print_status("❌ Docker Desktop не найден", Colors.RED)
            return False

        # Ждем запуска Docker
        self.print_status("Ожидание запуска Docker Desktop...", Colors.YELLOW)
        for attempt in range(30):  # Ждем до 1 минуты
            try:
                result = subprocess.run(
                    ["docker", "ps"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    self.print_status("✅ Docker Desktop запущен", Colors.GREEN)
                    return True
            except:
                pass

            time.sleep(2)
            if attempt % 5 == 0:  # Каждые 10 секунд показываем прогресс
                self.print_status(f"Ожидание... ({attempt + 1}/30)", Colors.YELLOW)

        self.print_status("❌ Таймаут запуска Docker Desktop", Colors.RED)
        return False

    def setup_directories(self):
        """Создать необходимые директории."""
        self.print_status("Создание директорий...", Colors.BLUE)

        directories = [self.uploads_dir, self.cdn_cache_dir]
        for directory in directories:
            directory.mkdir(exist_ok=True)
            self.print_status(f"✅ Создана директория: {directory.name}", Colors.GREEN)

    def setup_env_file(self):
        """Настроить .env файл."""
        self.print_status("Настройка .env файла...", Colors.BLUE)

        if not self.env_file.exists():
            # Создаем .env из примера
            env_example = self.project_root.parent / "env.example"
            if env_example.exists():
                import shutil

                shutil.copy(env_example, self.env_file)
                self.print_status("✅ .env файл создан из env.example", Colors.GREEN)
            else:
                # Создаем базовый .env с обновленными настройками
                env_content = """# База данных
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5433/fastapi_shop

# Хранилище (автоматически переключается на S3 если Docker доступен)
STORAGE_TYPE=local
STORAGE_PATH=uploads
MAX_IMAGE_SIZE=10485760
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,webp,gif

# S3 настройки (для MinIO)
S3_BUCKET_NAME=product-images
AWS_REGION=us-east-1
S3_ENDPOINT_URL=http://localhost:9002
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin

# CDN (локальный)
CDN_BASE_URL=

# Режим отладки
DEBUG=true
"""
                self.env_file.write_text(env_content, encoding="utf-8")
                self.print_status(
                    "✅ .env файл создан с базовыми настройками", Colors.GREEN
                )
        else:
            self.print_status("✅ .env файл уже существует", Colors.GREEN)

    def start_docker_services(self) -> bool:
        """Запустить Docker сервисы."""
        self.print_status("Запуск Docker сервисов...", Colors.BLUE)

        if not self.docker_compose_file.exists():
            self.print_status("❌ docker-compose.yml не найден", Colors.RED)
            return False

        try:
            # Останавливаем существующие контейнеры
            subprocess.run(
                ["docker-compose", "down"], cwd=self.project_root, capture_output=True
            )

            # Запускаем сервисы
            process = subprocess.Popen(
                ["docker-compose", "up", "-d"],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Ждем завершения
            stdout, stderr = process.communicate(timeout=60)

            if process.returncode == 0:
                self.print_status("✅ Docker сервисы запущены", Colors.GREEN)
                return True
            else:
                self.print_status(f"❌ Ошибка запуска Docker: {stderr}", Colors.RED)
                return False

        except subprocess.TimeoutExpired:
            process.kill()
            self.print_status("❌ Таймаут запуска Docker сервисов", Colors.RED)
            return False
        except Exception as e:
            self.print_status(f"❌ Ошибка: {e}", Colors.RED)
            return False

    def setup_minio_bucket(self):
        """Настроить MinIO bucket."""
        self.print_status("Настройка MinIO bucket...", Colors.BLUE)

        bucket_name = "product-images"

        try:
            # Ждем готовности MinIO
            import socket

            for attempt in range(30):  # 1 минута
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(("localhost", self.minio_api_port))
                    sock.close()
                    if result == 0:
                        break
                except:
                    pass
                time.sleep(2)
            else:
                self.print_status("❌ MinIO не готов", Colors.RED)
                return False

            # Получаем имя контейнера MinIO
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        "ancestor=minio/minio",
                        "--format",
                        "{{.Names}}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0 and result.stdout.strip():
                    container_name = result.stdout.strip()
                    self.print_status(
                        f"Найден контейнер MinIO: {container_name}", Colors.GREEN
                    )
                else:
                    self.print_status(
                        "⚠️  Контейнер MinIO не найден, пропускаем настройку bucket",
                        Colors.YELLOW,
                    )
                    return True

                # Создаем bucket через MinIO client
                try:
                    # Пытаемся создать bucket
                    result = subprocess.run(
                        [
                            "docker",
                            "exec",
                            container_name,
                            "mc",
                            "mb",
                            f"local/{bucket_name}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if result.returncode == 0:
                        self.print_status("✅ MinIO bucket создан", Colors.GREEN)
                    elif "already exists" in result.stderr:
                        self.print_status(
                            "✅ MinIO bucket уже существует", Colors.GREEN
                        )
                    else:
                        self.print_status(
                            f"⚠️  Ошибка создания bucket: {result.stderr}", Colors.YELLOW
                        )

                    # Устанавливаем политику public read
                    subprocess.run(
                        [
                            "docker",
                            "exec",
                            container_name,
                            "mc",
                            "policy",
                            "set",
                            "download",
                            f"local/{bucket_name}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    self.print_status("✅ MinIO bucket настроен", Colors.GREEN)
                    return True

                except Exception as e:
                    self.print_status(f"⚠️  Ошибка настройки bucket: {e}", Colors.YELLOW)
                    return False

            except Exception as e:
                self.print_status(
                    f"⚠️  Ошибка поиска контейнера MinIO: {e}", Colors.YELLOW
                )
                return False

        except Exception as e:
            self.print_status(f"❌ Ошибка настройки MinIO: {e}", Colors.RED)
            return False

    def switch_to_s3_storage(self):
        """Переключить настройки на S3 хранилище."""
        self.print_status("Переключение на S3 хранилище...", Colors.BLUE)

        try:
            # Читаем текущий .env
            env_content = self.env_file.read_text(encoding="utf-8")

            # Заменяем STORAGE_TYPE на s3
            env_content = env_content.replace("STORAGE_TYPE=local", "STORAGE_TYPE=s3")

            # Записываем обратно
            self.env_file.write_text(env_content, encoding="utf-8")

            self.print_status("✅ Переключено на S3 хранилище", Colors.GREEN)

        except Exception as e:
            self.print_status(f"⚠️  Ошибка переключения на S3: {e}", Colors.YELLOW)

    def wait_for_services(self):
        """Ожидать готовности сервисов."""
        self.print_status("Ожидание готовности сервисов...", Colors.BLUE)

        services = [
            ("PostgreSQL", "localhost", self.postgres_port),
            ("MinIO API", "localhost", self.minio_api_port),
            ("MinIO Console", "localhost", self.minio_console_port),
            ("Redis", "localhost", self.redis_port),
            ("pgAdmin", "localhost", self.pgadmin_port),
        ]

        import socket

        ready_services = []

        for service_name, host, port in services:
            self.print_status(f"Проверка {service_name}...", Colors.YELLOW)

            for attempt in range(30):  # 30 попыток по 2 секунды = 1 минута
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((host, port))
                    sock.close()

                    if result == 0:
                        self.print_status(f"✅ {service_name} готов", Colors.GREEN)
                        ready_services.append(service_name)
                        break
                except:
                    pass

                time.sleep(2)
                if (
                    attempt % 7 == 0 and attempt > 0
                ):  # Каждые 14 секунд показываем прогресс
                    self.print_status(
                        f"Ожидание {service_name}... ({attempt + 1}/30)", Colors.YELLOW
                    )
            else:
                self.print_status(f"❌ {service_name} не отвечает", Colors.RED)

        # Выводим итоговую статистику
        if ready_services:
            self.print_status(
                f"✅ Готово сервисов: {len(ready_services)}/{len(services)}",
                Colors.GREEN,
            )
            for service in ready_services:
                self.print_status(f"  ✅ {service}", Colors.GREEN)

        if len(ready_services) < len(services):
            missing = [s[0] for s in services if s[0] not in ready_services]
            self.print_status(f"⚠️  Не готовы: {', '.join(missing)}", Colors.YELLOW)
            self.print_status(
                "Система будет работать с ограниченной функциональностью", Colors.YELLOW
            )

    def start_fastapi(self):
        """Запустить FastAPI приложение."""
        self.print_status("Запуск FastAPI приложения...", Colors.BLUE)

        # Проверяем, что порт свободен
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("localhost", self.fastapi_port))
            sock.close()
        except OSError:
            self.print_status(f"⚠️  Порт {self.fastapi_port} занят", Colors.YELLOW)
            return False

        # Запускаем FastAPI
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--reload",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(self.fastapi_port),
                ],
                cwd=self.project_root.parent,
            )  # Изменено: запускаем из родительской папки

            self.processes.append(process)
            self.print_status("✅ FastAPI запущен", Colors.GREEN)
            return True

        except Exception as e:
            self.print_status(f"❌ Ошибка запуска FastAPI: {e}", Colors.RED)
            return False

    def print_system_info(self):
        """Вывести информацию о системе."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}📊 Система запущена:{Colors.END}")
        print(
            f"{Colors.GREEN}🌐 FastAPI:     http://localhost:{self.fastapi_port}{Colors.END}"
        )
        print(
            f"{Colors.GREEN}📚 API Docs:    http://localhost:{self.fastapi_port}/docs{Colors.END}"
        )
        print(
            f"{Colors.GREEN}🔍 Health:      http://localhost:{self.fastapi_port}/healthz{Colors.END}"
        )
        print(
            f"{Colors.GREEN}💾 MinIO API:   http://localhost:{self.minio_api_port}{Colors.END}"
        )
        print(
            f"{Colors.GREEN}🖥️  MinIO Console: http://localhost:{self.minio_console_port}{Colors.END}"
        )
        print(
            f"{Colors.GREEN}🗄️  PostgreSQL:  localhost:{self.postgres_port}{Colors.END}"
        )
        print(f"{Colors.GREEN}🔴 Redis:       localhost:{self.redis_port}{Colors.END}")
        print(
            f"{Colors.GREEN}📊 pgAdmin:     http://localhost:{self.pgadmin_port}{Colors.END}"
        )

        print(f"\n{Colors.BOLD}{Colors.YELLOW}🔑 Доступы:{Colors.END}")
        print(
            f"{Colors.YELLOW}MinIO - Логин: minioadmin, Пароль: minioadmin{Colors.END}"
        )
        print(
            f"{Colors.YELLOW}pgAdmin - Email: admin@admin.com, Пароль: admin{Colors.END}"
        )

        print(f"\n{Colors.BOLD}{Colors.PURPLE}📝 Полезные команды:{Colors.END}")
        print(
            f"{Colors.PURPLE}curl http://localhost:{self.fastapi_port}/healthz{Colors.END}"
        )
        print(
            f"{Colors.PURPLE}curl http://localhost:{self.fastapi_port}/api/v1/cdn/stats/cache{Colors.END}"
        )
        print(f"{Colors.PURPLE}docker-compose logs -f{Colors.END}")

        print(
            f"\n{Colors.BOLD}{Colors.CYAN}⏹️  Для остановки нажмите Ctrl+C{Colors.END}"
        )
        print()

    def signal_handler(self, signum, frame):
        """Обработчик сигнала для корректного завершения."""
        self.print_status("Получен сигнал остановки...", Colors.YELLOW)
        self.stop()
        sys.exit(0)

    def stop(self):
        """Остановить все процессы."""
        self.print_status("Остановка системы...", Colors.YELLOW)

        # Останавливаем FastAPI
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()

        # Останавливаем Docker сервисы
        try:
            subprocess.run(
                ["docker-compose", "down"], cwd=self.project_root, capture_output=True
            )
            self.print_status("✅ Docker сервисы остановлены", Colors.GREEN)
        except:
            pass

        self.print_status("✅ Система остановлена", Colors.GREEN)

    def run(self):
        """Запустить всю систему."""
        try:
            self.print_header()

            # Проверяем зависимости
            if not self.check_dependencies():
                return False

            # Запускаем Docker Desktop
            if not self.start_docker_desktop():
                self.print_status("⚠️  Продолжаем без Docker сервисов", Colors.YELLOW)
                docker_available = False
            else:
                docker_available = True

            # Настраиваем систему
            self.setup_directories()
            self.setup_env_file()

            # Запускаем Docker сервисы только если Docker доступен
            if docker_available:
                if not self.start_docker_services():
                    self.print_status(
                        "⚠️  Ошибка запуска Docker сервисов", Colors.YELLOW
                    )
                    docker_available = False

            # Ждем готовности сервисов
            self.wait_for_services()

            # Настраиваем MinIO bucket если Docker доступен
            if docker_available:
                self.setup_minio_bucket()
                # Переключаем на S3 хранилище
                self.switch_to_s3_storage()

            # Запускаем FastAPI
            if not self.start_fastapi():
                return False

            # Выводим информацию
            self.print_system_info()

            # Устанавливаем обработчик сигналов
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            self.running = True

            # Ждем завершения
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            self.print_status("Получен сигнал остановки...", Colors.YELLOW)
        except Exception as e:
            self.print_status(f"❌ Ошибка: {e}", Colors.RED)
        finally:
            self.stop()

        return True


def main():
    """Главная функция."""
    runner = SystemRunner()
    success = runner.run()

    if success:
        print(f"{Colors.GREEN}✅ Система завершена успешно{Colors.END}")
    else:
        print(f"{Colors.RED}❌ Система завершена с ошибками{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()
