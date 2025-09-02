.PHONY: help install format lint type-check test clean

help:  ## Показать справку по командам
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Установить зависимости
	pip install -r requirements.txt

install-dev:  ## Установить dev-зависимости
	pip install -r requirements.txt

format:  ## Форматировать код с помощью black и isort
	@echo "Форматирование кода..."
	black app/ scripts/
	isort app/ scripts/

lint:  ## Проверить стиль кода с помощью flake8
	@echo "Проверка стиля кода..."
	flake8 app/ scripts/

type-check:  ## Проверить типы с помощью mypy
	@echo "Проверка типов..."
	mypy app/

check: format lint type-check  ## Выполнить все проверки

test:  ## Запустить тесты
	@echo "Запуск тестов..."
	pytest

clean:  ## Очистить кэш и временные файлы
	@echo "Очистка кэша..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

dev:  ## Запустить приложение в режиме разработки
	@echo "Запуск приложения в режиме разработки..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

