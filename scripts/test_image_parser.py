#!/usr/bin/env python3
"""
Тестовый скрипт для парсера изображений.

Тестирует функциональность парсера без API ключей,
используя только DuckDuckGo как источник изображений.
"""

import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_parser import ImageParser


def test_image_search():
    """Тестирование поиска изображений."""
    print("🧪 Тестирование поиска изображений")
    print("=" * 40)

    parser = ImageParser()

    # Тестовые запросы
    test_queries = [
        "iPhone 14 Pro Max",
        "Samsung Galaxy S23",
        "MacBook Pro M3",
        "Sony WH-1000XM5",
        "Nintendo Switch OLED"
    ]

    for query in test_queries:
        print(f"\n🔍 Тестирую запрос: '{query}'")
        images = parser.search_images(query, 3)

        if images:
            print(f"✅ Найдено изображений: {len(images)}")
            for i, url in enumerate(images, 1):
                print(f"  {i}. {url}")
        else:
            print("❌ Изображения не найдены")

        print("-" * 40)


def test_image_download():
    """Тестирование загрузки изображений."""
    print("\n📥 Тестирование загрузки изображений")
    print("=" * 40)

    parser = ImageParser()

    # Тестовые URL (надежные источники для тестирования)
    test_urls = [
        "https://httpbin.org/image/jpeg",  # HTTPBin - тестовое изображение
        "https://httpbin.org/image/png",   # HTTPBin - тестовое изображение
        "https://httpbin.org/image/webp",  # HTTPBin - тестовое изображение
    ]

    for url in test_urls:
        print(f"\n🔗 Тестирую загрузку: {url}")

        image_data = parser.download_image(url)
        if image_data:
            print("✅ Изображение загружено успешно")

            # Тестируем оптимизацию
            optimized = parser.optimize_image(image_data)
            if optimized:
                print("✅ Изображение оптимизировано")
            else:
                print("❌ Ошибка оптимизации")
        else:
            print("❌ Ошибка загрузки")

        print("-" * 40)


def main():
    """Основная функция теста."""
    print("🚀 Запуск тестового скрипта парсера изображений")
    print("=" * 50)

    try:
        # Тестируем поиск
        test_image_search()

        # Тестируем загрузку
        test_image_download()

        print("\n" + "=" * 50)
        print("🎉 Тестирование завершено!")
        print("=" * 50)

    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
