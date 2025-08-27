@echo off
chcp 65001 >nul
title FastAPI Image Management System

echo.
echo ============================================================
echo 🚀 FastAPI Image Management System
echo ============================================================
echo.

echo Запуск системы управления изображениями...
echo.

REM Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден. Установите Python 3.8+
    pause
    exit /b 1
)

REM Проверяем Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Docker не найден. Система будет работать без Docker сервисов.
    echo.
)

REM Запускаем систему
echo Запуск системы...
python run_system.py

echo.
echo Система остановлена.
pause
