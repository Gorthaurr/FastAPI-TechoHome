#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер изображений товаров (DrissionPage)

Ключевые свойства:
- Браузер запускается скрыто (headless) с надёжными фоллбэками под разные версии DrissionPage/Chromium.
- Никаких очисток MinIO/БД/локальных артефактов при старте.
- Если у товара уже >= 3 изображений — пропуск.
- Докачиваем недостающее количество.
- Вся работа с изображениями идёт в памяти (BytesIO); НИКАКИХ локальных директорий 'downloaded_images' или 'html_dumps'.

Шаги на каждую картинку:
1) По названию из БД — выдача Яндекс.Картинок
2) Кликаем плитку -> модалка
3) В модалке жмём «Открыть»
4) Качаем файл В ПАМЯТЬ (с корректным Referer), валидируем размер
5) Оптимизируем и грузим в MinIO, создаём запись в Postgres
"""

import sys
import os
import re
import time
import warnings
from io import BytesIO
from datetime import datetime
from typing import List, Optional, Set
from urllib.parse import quote, urljoin, urlparse

import requests
import urllib3
from PIL import Image

# S3 / MinIO
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# ---------- Отключение SSL-предупреждений ----------
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# ---------- Пути/окружение проекта ----------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('STORAGE_TYPE', 's3')
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://postgres:password@localhost:5433/fastapi_shop')

# ---------- Импорты проекта ----------
from app.db.database import SessionLocal
from app.db.models.product import Product
from app.db.models.product_image import ProductImage
from app.services.storage_service import storage_service
from app.core.config import settings

# ---------- DrissionPage ----------
from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions
from DrissionPage.common import Settings


# ========================= ВСПОМОГАТЕЛЬНОЕ =========================

def _safe_filename(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')


def _is_direct_image_url(url: str) -> bool:
    return bool(re.search(r'\.(jpg|jpeg|png|webp|gif|bmp|tiff)(\?|$)', url, flags=re.I))


def _guess_ext(url: str, content_type: str) -> str:
    u = (url or '').lower()
    if u.endswith('.jpg') or u.endswith('.jpeg'):
        return '.jpg'
    if u.endswith('.png'):
        return '.png'
    if u.endswith('.webp'):
        return '.webp'
    if u.endswith('.gif'):
        return '.gif'
    if u.endswith('.bmp'):
        return '.bmp'
    if u.endswith('.tif') or u.endswith('.tiff'):
        return '.tiff'
    if content_type:
        ct = content_type.lower()
        if 'jpeg' in ct: return '.jpg'
        if 'png'  in ct: return '.png'
        if 'webp' in ct: return '.webp'
        if 'gif'  in ct: return '.gif'
        if 'bmp'  in ct: return '.bmp'
        if 'tiff' in ct: return '.tiff'
    return '.jpg'


def _origin(url: str) -> str:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return ''
    return f'{p.scheme}://{p.netloc}/'


# ========================= ОСНОВНОЙ КЛАСС =========================

class QualityImageParser:
    def __init__(self, min_side: int = 300):
        """Инициализация HTTP-сессии, MinIO+Postgres (запись включена), подготовка браузера."""
        print("==================================================")
        print("STORAGE SERVICE INITIALIZATION")
        print("==================================================")
        print(f"STORAGE_TYPE: {os.environ.get('STORAGE_TYPE', 'local')}")
        print(f"S3_BUCKET_NAME: {settings.S3_BUCKET_NAME}")
        print(f"S3_ENDPOINT_URL: {settings.S3_ENDPOINT_URL}")
        print(f"Final storage service: {type(storage_service)}")
        print("==================================================")

        Settings.raise_when_ele_not_found = False
        self.page: Optional[ChromiumPage] = None

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        self.min_side = min_side
        # ВАЖНО: никаких локальных директорий — вся работа с байтами в памяти.

    # -------------------- (НЕ ИСПОЛЬЗУЕТСЯ) Очистка при запуске --------------------

    def clear_minio_products(self, prefix: str = 'products/'):
        print("🗑️  Очистка MinIO (ручной вызов)...")
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                config=Config(s3={'addressing_style': 'path'}, signature_version='s3v4'),
            )
            paginator = s3.get_paginator('list_objects_v2')
            total_deleted = 0
            for page in paginator.paginate(Bucket=settings.S3_BUCKET_NAME, Prefix=prefix):
                if 'Contents' not in page:
                    continue
                objs = [{'Key': obj['Key']} for obj in page['Contents']]
                while objs:
                    batch = objs[:1000]
                    s3.delete_objects(Bucket=settings.S3_BUCKET_NAME, Delete={'Objects': batch, 'Quiet': True})
                    total_deleted += len(batch)
                    objs = objs[1000:]
            if total_deleted:
                print(f"✅ MinIO: удалено объектов: {total_deleted}")
            else:
                print("📭 MinIO: по префиксу ничего не найдено")
        except Exception as e:
            print(f"❌ Ошибка очистки MinIO: {e}")

    def clear_database_images(self):
        print("🗑️  Очистка записей в БД product_images (ручной вызов)...")
        try:
            with SessionLocal() as db:
                before = db.query(ProductImage).count()
                print(f"📊 В БД записей до очистки: {before}")
                if before == 0:
                    print("📭 Очистка БД: уже пусто")
                    return
                batch_size = 1000
                deleted_total = 0
                while True:
                    batch = db.query(ProductImage).limit(batch_size).all()
                    if not batch:
                        break
                    for rec in batch:
                        db.delete(rec)
                    db.commit()
                    deleted_total += len(batch)
                    print(f"🗑️  Удалено батчом: {len(batch)} (итого: {deleted_total}/{before})")
                after = db.query(ProductImage).count()
                print(f"✅ Очистка БД завершена. Осталось записей: {after}")
        except Exception as e:
            print(f"❌ Ошибка очистки БД: {e}")

    def clear_local_artifacts(self):
        """Заглушка: локальные артефакты больше не используются и не создаются."""
        print("ℹ️ Локальные артефакты не создаются — очищать нечего.")

    # -------------------- Браузер --------------------

    def init_page(self) -> bool:
        if self.page is None:
            try:
                print("🌐 Инициализация DrissionPage (headless)...")
                co = ChromiumOptions()

                # 1) Пытаемся включить headless через "современный" API
                enabled = False
                for m in ('set_headless', 'headless'):
                    if hasattr(co, m):
                        try:
                            getattr(co, m)(True)  # co.set_headless(True) или co.headless(True)
                            enabled = True
                            break
                        except Exception:
                            pass

                # 2) Если нет — фоллбэк на передачу аргументов
                if not enabled:
                    for flag in ('--headless=new', '--headless'):
                        try:
                            # У некоторых версий есть set_argument, у некоторых — только add_argument отсутствует.
                            if hasattr(co, 'set_argument'):
                                co.set_argument(flag)
                                enabled = True
                                break
                        except Exception:
                            continue

                # Доп. надёжные флаги для контейнеров/VPS
                for arg in ('--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage', '--window-size=1920,1080'):
                    try:
                        if hasattr(co, 'set_argument'):
                            co.set_argument(arg)
                    except Exception:
                        pass

                self.page = ChromiumPage(co)
                self.page.set.user_agent(self.session.headers['User-Agent'])
                self.page.set.timeouts(base=10)
                print("✅ DrissionPage инициализирован (скрыт)")
                return True
            except Exception as e:
                print(f"❌ Ошибка инициализации DrissionPage: {e}")
                print("ℹ️ Проверьте установку Chromium/Chrome. При необходимости задайте путь вручную, например:")
                print("   co = ChromiumOptions(); co.set_browser_path('/usr/bin/chromium')  # затем ChromiumPage(co)")
                return False
        return True

    def close_page(self):
        if self.page:
            try:
                self.page.quit()
                self.page = None
                print("✅ DrissionPage закрыт")
            except Exception:
                pass

    def _dump_html(self, html: str, product_name: str, suffix: str):
        """Заглушка: не сохраняем HTML на диск."""
        return

    # -------------------- Шаг 1: открыть поиск --------------------

    def open_search_by_name(self, product_name: str) -> str:
        q = quote(product_name)
        url = f"https://yandex.ru/images/search?text={q}"
        print(f"📡 Открываем выдачу Яндекс.Картинок: {url}")
        self.page.get(url)
        time.sleep(1.0)
        return url

    # -------------------- Шаг 2: клик по плитке -> модалка --------------------

    def _wait_modal_opened(self, timeout: float = 4.0) -> bool:
        end = time.time() + timeout
        last_url = None
        while time.time() < end:
            btn = self._find_open_button_element()
            if btn:
                return True

            url = (self.page.url or "").lower()
            if url != last_url:
                last_url = url
                if ('rpt=imageview' in url) or ('rpt=simage' in url) or ('img_url=' in url):
                    return True

            if self._modal_img_element() is not None:
                return True

            time.sleep(0.25)
        return False

    def _modal_img_element(self):
        for sel in [
            'css:.MMImage-Origin img',
            'css:.MMImage img',
            'css:.ImagePreview img',
            'css:.ModalImage img',
        ]:
            try:
                img = self.page.ele(sel, timeout=0.2)
                if img and img.attr('src'):
                    return img
            except Exception:
                continue
        return None

    def _best_modal_img_url(self) -> Optional[str]:
        for sel in [
            'css:.MMImage-Origin img',
            'css:.MMImage img',
            'css:.ImagePreview img',
            'css:.ModalImage img',
            'css:img'
        ]:
            try:
                img = self.page.ele(sel, timeout=0.6)
                if not img:
                    continue
                ss = img.attr('srcset')
                if ss:
                    best_url = None
                    best_w = -1
                    for part in ss.split(','):
                        t = part.strip().split()
                        if not t:
                            continue
                        url = t[0]
                        w = 0
                        if len(t) > 1 and t[1].endswith('w'):
                            try:
                                w = int(t[1][:-1])
                            except Exception:
                                w = 0
                        if url.startswith('http') and w > best_w:
                            best_w, best_url = w, url
                    if best_url:
                        return best_url
                src = img.attr('src')
                if src and src.startswith('http'):
                    return src
            except Exception:
                continue
        return None

    def _find_open_button_element(self):
        try:
            e = self.page.ele('xpath://a[normalize-space()="Открыть"]', timeout=0.3)
            if e: return e
        except Exception: pass
        try:
            e = self.page.ele('xpath://button[normalize-space()="Открыть"]', timeout=0.3)
            if e: return e
        except Exception: pass
        try:
            e = self.page.ele('text:Открыть', timeout=0.3)
            if e: return e
        except Exception: pass
        try:
            els = self.page.eles('css:a[aria-label*="Открыть"],a[title*="Открыть"]') or []
            if els: return els[0]
        except Exception: pass
        return None

    def _click_open_button_and_get_href(self) -> Optional[str]:
        btn = self._find_open_button_element()
        if not btn:
            print("⚠️  Не нашли «Открыть» — будем вытаскивать картинку из модалки")
            return None

        href = btn.attr('href') or ''
        if href:
            if href.startswith('//'): href = 'https:' + href
            elif href.startswith('/'): href = urljoin('https://yandex.ru', href)

        try:
            try: btn.scroll.to_see()
            except Exception: pass
            try: btn.click()
            except Exception: btn.click(by_js=True)
            print("✅ Клик по «Открыть» выполнен")
        except Exception as e:
            print(f"⚠️  Ошибка клика по «Открыть»: {e}")

        return href or None

    def _open_modal_by_tile_index(self, tile_index: int) -> bool:
        selectors = [
            'css:a.ImagesContentImage-Cover',
            'css:.ImagesContent-Item a[href]',
            'css:.serp-item a[href]',
            'css:img'
        ]
        for sel in selectors:
            try:
                tiles = self.page.eles(sel) or []
                if tile_index >= len(tiles): continue
                t = tiles[tile_index]
                try: t.scroll.to_see()
                except Exception: pass
                try: t.click()
                except Exception: t.click(by_js=True)

                if self._wait_modal_opened(timeout=4.0):
                    print(f"✅ Модалка открыта по плитке #{tile_index+1} ({sel})")
                    return True

                print(f"ℹ️  Модалка не распознана после клика по плитке #{tile_index+1} ({sel})")
                try: self.page.key.press('Escape')
                except Exception: pass
                time.sleep(0.2)

            except Exception as e:
                print(f"⚠️  Ошибка при попытке клика по селектору {sel}: {e}")
                continue
        return False

    # -------------------- Шаг 4: скачать В ПАМЯТЬ --------------------

    def _download_to_memory(self, url: str, referer: Optional[str]) -> Optional[BytesIO]:
        headers = self.session.headers.copy()
        if referer:
            headers['Referer'] = referer
        else:
            origin = _origin(url)
            if origin:
                headers['Referer'] = origin

        print(f"📥 Скачиваем в память: {url}")
        try:
            resp = self.session.get(url, headers=headers, timeout=25, verify=False, stream=True, allow_redirects=True)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ HTTP ошибка: {e}")
            return None

        data = BytesIO(resp.content)
        try:
            with Image.open(data) as im:
                im.load()
                w, h = im.size
                if min(w, h) < self.min_side:
                    print(f"⚠️  Слишком маленькое: {w}x{h} (<{self.min_side})")
                    return None
        except Exception as e:
            print(f"⚠️  PIL ошибка: {e}")
            return None

        data.seek(0)
        return data

    # -------------------- MinIO + БД --------------------

    def optimize_and_save_image(self, image_data: BytesIO, product_id: str, filename: str) -> Optional[str]:
        try:
            image_data.seek(0)
            with Image.open(image_data) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.thumbnail((800, 600), Image.Resampling.LANCZOS)

                output_buffer = BytesIO()
                img.save(output_buffer, format='JPEG', quality=85, optimize=True)

                storage_path = f"products/{product_id[:12]}/{filename}"
                output_buffer.seek(0)
                success = storage_service.save_file(
                    storage_path,
                    output_buffer,
                    "image/jpeg"
                )
                if not success:
                    print("❌ storage_service вернул False")
                    return None
                print(f"✅ Изображение сохранено в MinIO: {storage_path}")
                return storage_path
        except Exception as e:
            print(f"❌ Ошибка обработки/сохранения в MinIO: {e}")
            return None

    def create_image_record(self, db, product_id: str, storage_path: str,
                            is_primary: bool = False, alt_text: str = "") -> bool:
        try:
            if is_primary:
                existing_primary = db.query(ProductImage).filter(
                    ProductImage.product_id == product_id,
                    ProductImage.is_primary == True
                ).first()
                if existing_primary:
                    is_primary = False

            image_record = ProductImage(
                product_id=product_id,
                path=storage_path,
                filename=os.path.basename(storage_path),
                is_primary=is_primary,
                status="ready",
                alt_text=alt_text or "Изображение товара",
                sort_order=0,
                uploaded_at=datetime.utcnow(),
                processed_at=datetime.utcnow()
            )

            db.add(image_record)
            db.flush()
            db.commit()
            print(f"✅ Запись в БД создана: ID={image_record.id}, path={storage_path}, primary={is_primary}")
            return True

        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка создания записи в БД: {e}")
            return False

    def _upload_bytes_to_minio_and_record(self, image_data: BytesIO, product, seq: int) -> bool:
        filename = f"img_{seq:03d}.jpg"  # всегда JPEG
        storage_path = self.optimize_and_save_image(image_data, str(product.id), filename)
        if not storage_path:
            return False

        with SessionLocal() as db:
            ok = self.create_image_record(
                db=db,
                product_id=product.id,
                storage_path=storage_path,
                is_primary=(seq == 1),
                alt_text=f"Изображение товара {product.name}"
            )
        return ok

    # -------------------- Поиск лучшей ссылки --------------------

    def _largest_img_src_on_page(self) -> Optional[str]:
        try:
            imgs = self.page.eles('css:img') or []
        except Exception:
            imgs = []
        best_url, best_w = None, -1
        for img in imgs:
            try:
                ss = img.attr('srcset')
                if ss:
                    for part in ss.split(','):
                        t = part.strip().split()
                        if not t:
                            continue
                        u = t[0]
                        w = 0
                        if len(t) > 1 and t[1].endswith('w'):
                            try:
                                w = int(t[1][:-1])
                            except Exception:
                                w = 0
                        if u.startswith('http') and w > best_w:
                            best_w, best_url = w, u
                    continue
                src = img.attr('src')
                if src and src.startswith('http') and best_w < 0:
                    best_url = src
                    best_w = 0
            except Exception:
                continue
        return best_url

    # -------------------- Подсчёт уже загруженных изображений --------------------

    def _existing_images_count(self, product_id: str) -> int:
        try:
            with SessionLocal() as db:
                return db.query(ProductImage).filter(ProductImage.product_id == product_id).count()
        except Exception as e:
            print(f"⚠️ Не удалось получить число изображений для продукта {product_id}: {e}")
            return 0

    # -------------------- Основной цикл: докачать до 3 файлов на товар --------------------

    def process_product(self, product: Product, images_per_product: int = 3) -> int:
        print(f"\n🎯 Обрабатываем товар: '{product.name}' (ID: {product.id})")
        print("-" * 60)

        if not self.init_page():
            print("❌ Не удалось инициализировать браузер")
            return 0

        existing = self._existing_images_count(product.id)
        if existing >= images_per_product:
            print(f"⏭️ Уже есть {existing} изображений (≥ {images_per_product}). Пропуск товара.")
            return 0

        need_to_save = images_per_product - existing
        print(f"ℹ️  В БД уже: {existing}. Нужно докачать: {need_to_save}.")

        results_url = self.open_search_by_name(product.name)

        saved = 0
        tried = 0
        tile_index = 0
        downloaded_urls: Set[str] = set()
        max_tile_attempts = need_to_save * 12

        while saved < need_to_save and tried < max_tile_attempts:
            if not (self.page.url or "").startswith("https://yandex.ru/images"):
                self.page.get(results_url)
                time.sleep(0.6)

            opened = self._open_modal_by_tile_index(tile_index)
            tried += 1
            tile_index += 1

            if not opened:
                print("⚠️  Плитка не открыла модалку — следующая")
                continue

            modal_best_url = self._best_modal_img_url()
            open_href = self._click_open_button_and_get_href()

            download_url = None
            referer_for_download = None

            if open_href:
                print(f"➡️  Переходим по «Открыть»: {open_href}")
                self.page.get(open_href)
                time.sleep(1.0)
                final_url = self.page.url or ""

                if _is_direct_image_url(final_url):
                    download_url = final_url
                    referer_for_download = _origin(final_url)
                else:
                    largest = self._largest_img_src_on_page()
                    if largest:
                        download_url = largest
                        referer_for_download = self.page.url

            if not download_url and modal_best_url:
                download_url = modal_best_url
                referer_for_download = _origin(modal_best_url) or 'https://yandex.ru/'

            if not download_url:
                print("❌ Не удалось получить ссылку на картинку — следующая плитка")
                self.page.get(results_url)
                time.sleep(0.6)
                continue

            if download_url in downloaded_urls:
                print("ℹ️  Дубликат URL — пропуск")
                self.page.get(results_url)
                time.sleep(0.6)
                continue

            seq = existing + saved + 1
            print(f"🔗 Будем скачивать (в память): {download_url} -> seq={seq}")

            img_bytes = self._download_to_memory(download_url, referer_for_download)

            self.page.get(results_url)
            time.sleep(0.6)

            if not img_bytes:
                print("⚠️  Не удалось скачать в память — следующая плитка")
                continue

            if self._upload_bytes_to_minio_and_record(img_bytes, product, seq=seq):
                saved += 1
                downloaded_urls.add(download_url)
                print(f"📈 Прогресс по товару: {existing + saved}/{images_per_product}")
            else:
                print("⚠️  Не удалось загрузить в MinIO/записать в БД — следующая плитка")

        print(f"\n✅ Сохранено изображений для товара: {saved}/{need_to_save} (итог в БД будет {existing + saved})")
        return saved

    # -------------------- Получение товаров из БД --------------------

    def get_products_from_db(self) -> List[Product]:
        try:
            print("📦 Получаем товары из БД...")
            with SessionLocal() as db:
                from sqlalchemy.orm import lazyload
                products = db.query(Product).options(
                    lazyload(Product.attributes),
                    lazyload(Product.images),
                    lazyload(Product.category)
                ).all()
                print(f"📦 Получено товаров: {len(products)}")
                return products
        except Exception as e:
            print(f"❌ Ошибка получения товаров: {e}")
            return []


# ========================= main =========================

def main():
    print("🚀 ПАРСЕР ИЗОБРАЖЕНИЙ — в память → MinIO (рабочий механизм) → запись в Postgres")
    print("=" * 94)
    print("Шаги: поиск → модалка → «Открыть» → в память → MinIO → БД (до 3 изображений на товар)\n")

    parser = QualityImageParser(min_side=300)

    try:
        products = parser.get_products_from_db()
        if not products:
            print("❌ В БД нет товаров")
            return

        images_per_product = 3
        saved_total = 0
        processed = 0

        for product in products:
            try:
                print(f"\n🔄 Товар {processed + 1}/{len(products)}")
                saved = parser.process_product(product, images_per_product=images_per_product)
                saved_total += saved
                processed += 1
                time.sleep(0.4)
            except KeyboardInterrupt:
                print("\n⏹️  Прервано пользователем")
                break
            except Exception as e:
                print(f"❌ Ошибка обработки товара {product.name}: {e}")
                continue

        print("\n🎉 ГОТОВО")
        print("=" * 50)
        print(f"📊 Обработано товаров: {processed}")
        print(f"📸 Всего сохранено файлов: {saved_total}")

    finally:
        parser.close_page()
        print("✅ DrissionPage закрыт")


if __name__ == "__main__":
    main()
