#!/usr/bin/env python3
"""
Простой и эффективный поиск изображений товаров.
Использует Google Images через альтернативный метод.
"""

import sys
import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode
from io import BytesIO
from PIL import Image

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SimpleImageSearch:
    """Простой поиск изображений товаров."""

    def __init__(self):
        """Инициализация поисковика."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def search_google_images_alt(self, query: str, num_images: int = 5) -> list:
        """Альтернативный поиск через Google Images."""
        try:
            # Формируем URL для Google Images
            params = {
                'q': query,
                'tbm': 'isch',  # Image search
                'hl': 'en',
                'gl': 'us',
                'ijn': '0'
            }
            
            url = "https://www.google.com/search?" + urlencode(params)
            
            # Отправляем запрос
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Парсим HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            images = []
            
            # Ищем изображения в разных местах
            # Метод 1: data-src атрибуты
            for img in soup.find_all('img'):
                src = img.get('data-src') or img.get('src')
                if src and src.startswith('http'):
                    if not any(skip in src.lower() for skip in ['gstatic', 'google', 'googleapis']):
                        images.append(src)
                        if len(images) >= num_images:
                            break
            
            # Метод 2: Ищем в скриптах JSON данные
            if len(images) < num_images:
                for script in soup.find_all('script'):
                    if script.string and 'AF_initDataCallback' in script.string:
                        try:
                            # Извлекаем JSON из скрипта
                            start = script.string.find('[')
                            end = script.string.rfind(']') + 1
                            if start != -1 and end != 0:
                                json_text = script.string[start:end]
                                # Ищем URL изображений в JSON
                                import re
                                urls = re.findall(r'https?://[^"]+\.(?:jpg|jpeg|png|webp)', json_text)
                                for url in urls:
                                    if not any(skip in url.lower() for skip in ['gstatic', 'google', 'googleapis']):
                                        if url not in images:
                                            images.append(url)
                                            if len(images) >= num_images:
                                                break
                        except:
                            continue
            
            print(f"✅ Google Images (альтернативный): найдено {len(images)} изображений")
            return images[:num_images]
            
        except Exception as e:
            print(f"❌ Ошибка поиска в Google Images: {e}")
            return []

    def search_yandex_images(self, query: str, num_images: int = 5) -> list:
        """Поиск через Яндекс.Картинки."""
        try:
            # URL для Яндекс.Картинок
            params = {
                'text': query,
                'type': 'photo',
                'isize': 'large'
            }
            
            url = "https://yandex.ru/images/search?" + urlencode(params)
            
            # Отправляем запрос
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Парсим HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            images = []
            
            # Ищем изображения
            for item in soup.find_all('div', {'class': 'serp-item'}):
                try:
                    # Извлекаем данные из атрибутов
                    data_bem = item.get('data-bem')
                    if data_bem:
                        data = json.loads(data_bem)
                        if 'serp-item' in data:
                            img_data = data['serp-item']
                            if 'img_href' in img_data:
                                images.append(img_data['img_href'])
                            elif 'preview' in img_data:
                                for preview in img_data['preview']:
                                    if 'url' in preview:
                                        images.append(preview['url'])
                                        break
                            
                            if len(images) >= num_images:
                                break
                except:
                    continue
            
            print(f"✅ Яндекс.Картинки: найдено {len(images)} изображений")
            return images[:num_images]
            
        except Exception as e:
            print(f"❌ Ошибка поиска в Яндекс.Картинках: {e}")
            return []

    def search_duckduckgo_images_improved(self, query: str, num_images: int = 5) -> list:
        """Улучшенный поиск через DuckDuckGo."""
        try:
            # Используем DuckDuckGo API endpoint
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            # Сначала получаем токен
            token_url = f"https://duckduckgo.com/?q={quote(query)}&iar=images&iax=images&ia=images"
            token_response = self.session.get(token_url, headers=headers, timeout=10)
            
            # Извлекаем vqd токен
            import re
            vqd_match = re.search(r'vqd=([\d-]+)', token_response.text)
            if not vqd_match:
                vqd_match = re.search(r'"vqd":"([\d-]+)"', token_response.text)
            
            if vqd_match:
                vqd = vqd_match.group(1)
                
                # Теперь делаем запрос за изображениями
                api_url = f"https://duckduckgo.com/i.js"
                params = {
                    'l': 'us-en',
                    'o': 'json',
                    'q': query,
                    'vqd': vqd,
                    'f': ',,,',
                    'p': '1',
                    'v7exp': 'a',
                }
                
                response = self.session.get(api_url, params=params, headers=headers, timeout=10)
                data = response.json()
                
                images = []
                if 'results' in data:
                    for result in data['results'][:num_images]:
                        if 'image' in result:
                            images.append(result['image'])
                        elif 'thumbnail' in result:
                            images.append(result['thumbnail'])
                
                print(f"✅ DuckDuckGo (улучшенный): найдено {len(images)} изображений")
                return images
            
        except Exception as e:
            print(f"❌ Ошибка поиска в DuckDuckGo: {e}")
            
        return []

    def search_all_sources(self, query: str, num_images: int = 5) -> list:
        """Поиск по всем источникам."""
        print(f"\n🔍 Ищем изображения для: '{query}'")
        print("=" * 50)
        
        all_images = []
        
        # Пробуем Google Images (альтернативный)
        images = self.search_google_images_alt(query, num_images)
        all_images.extend(images)
        
        # Если мало, пробуем Яндекс
        if len(all_images) < num_images:
            images = self.search_yandex_images(query, num_images - len(all_images))
            all_images.extend(images)
        
        # Если все еще мало, пробуем DuckDuckGo
        if len(all_images) < num_images:
            images = self.search_duckduckgo_images_improved(query, num_images - len(all_images))
            all_images.extend(images)
        
        # Убираем дубликаты
        unique_images = []
        seen = set()
        for img in all_images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        
        print(f"\n✅ ИТОГО найдено уникальных изображений: {len(unique_images)}")
        return unique_images[:num_images]

    def download_and_save_image(self, url: str, filename: str) -> bool:
        """Загрузка и сохранение изображения."""
        try:
            print(f"📥 Загружаю: {url}")
            
            response = self.session.get(url, timeout=15, stream=True)
            response.raise_for_status()
            
            # Проверяем размер
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) < 1000:
                print(f"⚠️  Изображение слишком маленькое: {content_length} байт")
                return False
            
            # Загружаем изображение
            image_data = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                image_data.write(chunk)
            
            image_data.seek(0)
            
            # Проверяем что это изображение
            try:
                with Image.open(image_data) as img:
                    width, height = img.size
                    if width < 100 or height < 100:
                        print(f"⚠️  Изображение слишком маленькое: {width}x{height}")
                        return False
                    
                    # Сохраняем
                    image_data.seek(0)
                    filepath = f"./demo_images/{filename}"
                    
                    with open(filepath, 'wb') as f:
                        f.write(image_data.getvalue())
                    
                    print(f"✅ Сохранено: {filepath} ({width}x{height})")
                    return True
                    
            except Exception as e:
                print(f"❌ Ошибка обработки изображения: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            return False


def main():
    """Тестирование поиска изображений."""
    print("🚀 ТЕСТИРОВАНИЕ УЛУЧШЕННОГО ПОИСКА ИЗОБРАЖЕНИЙ")
    print("=" * 60)
    
    searcher = SimpleImageSearch()
    
    # Тестовые товары
    test_products = [
        "iPhone 15 Pro Max",
        "MacBook Air M3",
        "Sony WH-1000XM5"
    ]
    
    for product in test_products:
        # Поиск изображений
        images = searcher.search_all_sources(product, 3)
        
        if images:
            print(f"\n📸 Загружаем первое изображение для '{product}'...")
            
            # Пробуем загрузить первое найденное изображение
            for i, img_url in enumerate(images[:1]):
                safe_name = "".join(c for c in product if c.isalnum() or c in (' ', '-')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                filename = f"{safe_name}_test.jpg"
                
                if searcher.download_and_save_image(img_url, filename):
                    break
                else:
                    print(f"⚠️  Пробуем следующее изображение...")
                    if i < len(images) - 1:
                        if searcher.download_and_save_image(images[i+1], filename):
                            break
        else:
            print(f"❌ Изображения не найдены для '{product}'")
        
        print("-" * 60)
    
    print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    
    # Показываем сохраненные файлы
    import os
    demo_dir = "./demo_images"
    if os.path.exists(demo_dir):
        files = os.listdir(demo_dir)
        if files:
            print("\n📂 СОХРАНЕННЫЕ ФАЙЛЫ:")
            for file in files:
                if file.endswith('_test.jpg'):
                    filepath = os.path.join(demo_dir, file)
                    size = os.path.getsize(filepath)
                    print(f"   📄 {file} ({size:,} байт)")


if __name__ == "__main__":
    main()
