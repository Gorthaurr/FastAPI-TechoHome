#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}"
echo "============================================================"
echo "🚀 FastAPI Image Management System"
echo "============================================================"
echo -e "${NC}"
echo -e "${YELLOW}Запуск системы управления изображениями...${NC}"
echo

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не найден. Установите Python 3.8+${NC}"
    exit 1
fi

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker не найден. Система будет работать без Docker сервисов.${NC}"
    echo
fi

# Делаем скрипт исполняемым
chmod +x run_system.py

# Запускаем систему
echo -e "${BLUE}Запуск системы...${NC}"
python3 run_system.py

echo
echo -e "${GREEN}Система остановлена.${NC}"
