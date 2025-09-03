#!/usr/bin/env python3
"""
Простая демонстрация парсера изображений.

Показывает как работает парсер изображений без API ключей,
используя только стандартные методы парсинга HTML.
Сохраняет изображения в локальную папку ./demo_images/
"""

import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_parser import ImageParser


def demo_search():
    """Демонстрация поиска изображений."""
    print("🔍 ДЕМОНСТРАЦИЯ ПОИСКА ИЗОБРАЖЕНИЙ")
    print("=" * 50)

    parser = ImageParser()

    # Тестовые товары
    test_products = [
        "iPhone 15 Pro Max",
        "MacBook Air M3",
        "Sony WH-1000XM5"
    ]

    for product in test_products:
        print(f"\n🎯 Ищем изображения для: '{product}'")
        print("-" * 40)

        # Ищем изображения
        images = parser.search_images(product, 2)

        if images:
            print(f"✅ Найдено {len(images)} изображений:")
            for i, url in enumerate(images, 1):
                print(f"   {i}. {url}")
        else:
            print("❌ Изображения не найдены")

        print()


def demo_download():
    """Демонстрация загрузки изображений товаров."""
    print("📥 ДЕМОНСТРАЦИЯ ПОИСКА И ЗАГРУЗКИ ИЗОБРАЖЕНИЙ ТОВАРОВ")
    print("=" * 60)
    print("📁 Изображения будут сохранены в папку: ./demo_images/")
    print("🎯 Парсер найдет реальные изображения товаров по их названиям")
    print()

    parser = ImageParser()

    # Тестируем поиск изображений для реальных товаров
    test_products = [
        "iPhone 15 Pro Max",
        "MacBook Air M3",
        "Sony WH-1000XM5"
    ]

    for product in test_products:
        print(f"\n🎯 Обрабатываем товар: '{product}'")
        print("-" * 40)

        # Ищем изображения товара
        images = parser.search_images(product, 2)

        if images:
            print(f"✅ Найдено {len(images)} изображений")

            # Пробуем загрузить первое изображение
            for i, image_url in enumerate(images[:1]):  # Загружаем только первое
                print(f"📥 Загружаю изображение: {image_url}")

                image_data = parser.download_image(image_url)
                if image_data:
                    print("✅ Изображение загружено успешно")

                    # Показываем размер данных
                    size = len(image_data.getvalue())
                    print(f"📏 Размер: {size} байт")

                    # Пробуем оптимизировать изображение
                    try:
                        optimized = parser.optimize_image(image_data)
                        file_to_save = optimized if optimized else image_data

                        if optimized:
                            optimized_size = len(optimized.getvalue())
                            compression_ratio = optimized_size / size
                            print(f"🖼️  Оптимизировано: {optimized_size} байт ({compression_ratio:.1f}x)")
                        else:
                            print("⚠️  Оптимизация не удалась, сохраняем оригинал")
                            file_to_save = image_data

                        # Сохраняем изображение (оптимизированное или оригинальное)
                        safe_name = "".join(c for c in product if c.isalnum() or c in (' ', '-')).rstrip()
                        safe_name = safe_name.replace(' ', '_')
                        filename = f"{safe_name}_demo.jpg"
                        filepath = f"./demo_images/{filename}"

                        # Сохраняем файл
                        with open(filepath, 'wb') as f:
                            f.write(file_to_save.getvalue())

                        print(f"💾 Сохранено: {filepath}")
                        print(f"   📂 Полный путь: {os.path.abspath(filepath)}")
                        print(f"   📏 Размер файла: {len(file_to_save.getvalue())} байт")

                    except Exception as e:
                        print(f"❌ Ошибка сохранения: {e}")
                        # Попробуем сохранить оригинальное изображение
                        try:
                            safe_name = "".join(c for c in product if c.isalnum() or c in (' ', '-')).rstrip()
                            safe_name = safe_name.replace(' ', '_')
                            filename = f"{safe_name}_original.jpg"
                            filepath = f"./demo_images/{filename}"

                            with open(filepath, 'wb') as f:
                                f.write(image_data.getvalue())

                            print(f"💾 Сохранен оригинал: {filepath}")
                            print(f"   📂 Полный путь: {os.path.abspath(filepath)}")

                        except Exception as e2:
                            print(f"❌ Критическая ошибка сохранения: {e2}")
                else:
                    print("❌ Ошибка загрузки изображения")

                print("-" * 30)
        else:
            print("❌ Изображения не найдены")
            print("-" * 30)


def main():
    """Основная демонстрация."""
    print("🚀 ДЕМОНСТРАЦИЯ ПАРСЕРА ИЗОБРАЖЕНИЙ")
    print("Только стандартные методы парсинга (без API)")
    print("=" * 60)

    try:
        # Демонстрация поиска
        demo_search()

        # Демонстрация загрузки
        demo_download()

        print("\n" + "=" * 60)
        print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
        print()

        # Показываем сохраненные файлы
        demo_dir = "./demo_images"
        if os.path.exists(demo_dir):
            files = os.listdir(demo_dir)
            if files:
                print("📂 СОХРАНЕННЫЕ ФАЙЛЫ:")
                for file in files:
                    filepath = os.path.join(demo_dir, file)
                    size = os.path.getsize(filepath)
                    print(f"   📄 {file} ({size} байт)")
                    print(f"      📍 Полный путь: {os.path.abspath(filepath)}")
                print()

        print("💡 ОСОБЕННОСТИ ПАРСЕРА:")
        print("   • Работает без API ключей")
        print("   • Использует только HTTP парсинг")
        print("   • Находит изображения через Bing")
        print("   • Оптимизирует размер и качество")
        print("   • Сохраняет локально в ./demo_images/")
        print()
        print("🚀 Для запуска полного парсера:")
        print("   python scripts/image_parser.py")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n⏹️  Демонстрация прервана")
    except Exception as e:
        print(f"\n❌ Ошибка в демонстрации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
