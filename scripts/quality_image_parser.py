#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер изображений товаров (DrissionPage)
Логика на КАЖДУЮ картинку:
1) По названию из БД открываем выдачу Яндекс.Картинок
2) Кликаем плитку -> открывается модалка
3) В модалке кликаем «Открыть»
4) Скачиваем файл ЛОКАЛЬНО (с корректным Referer), проверяем минимальный размер
5) Загружаем этот локальный файл в MinIO (механизм из «рабочей» версии), создаём запись в Postgres
6) Удаляем локальный файл
По 3 изображения на товар. Без ретраев.
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
from DrissionPage.common import Settings


# ========================= ВСПОМОГАТЕЛЬНОЕ =========================

def _safe_filename(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


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
        if 'jpeg' in ct:
            return '.jpg'
        if 'png' in ct:
            return '.png'
        if 'webp' in ct:
            return '.webp'
        if 'gif' in ct:
            return '.gif'
        if 'bmp' in ct:
            return '.bmp'
        if 'tiff' in ct:
            return '.tiff'
    return '.jpg'


def _origin(url: str) -> str:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return ''
    return f'{p.scheme}://{p.netloc}/'


# ========================= ОСНОВНОЙ КЛАСС =========================

class QualityImageParser:
    def __init__(self, min_side: int = 300):
        """Инициализация браузера, HTTP-сессии, MinIO+Postgres (запись включена)."""
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
        self.download_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloaded_images')
        _ensure_dir(self.download_root)

    # -------------------- Браузер --------------------

    def init_page(self) -> bool:
        if self.page is None:
            try:
                print("🌐 Инициализация DrissionPage...")
                self.page = ChromiumPage()
                self.page.set.user_agent(self.session.headers['User-Agent'])
                self.page.set.timeouts(base=10)
                print("✅ DrissionPage инициализирован")
                return True
            except Exception as e:
                print(f"❌ Ошибка инициализации DrissionPage: {e}")
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
        try:
            dump_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'html_dumps')
            _ensure_dir(dump_dir)
            path = os.path.join(dump_dir, f"{_safe_filename(product_name)}_{suffix}_{int(time.time())}.html")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"💾 HTML сохранен в {path}")
        except Exception as e:
            print(f"⚠️  Ошибка сохранения HTML: {e}")

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
        """Ожидание признаков модалки (кнопка «Открыть», viewer-параметры, крупный IMG)."""
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
        """Возвращает IMG из модалки, если находит, иначе None."""
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
        """Возвращает максимально крупный URL из модалки (srcset > src)."""
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
        """Ищем элемент «Открыть» максимально жёстко по тексту."""
        try:
            e = self.page.ele('xpath://a[normalize-space()="Открыть"]', timeout=0.3)
            if e:
                return e
        except Exception:
            pass
        try:
            e = self.page.ele('xpath://button[normalize-space()="Открыть"]', timeout=0.3)
            if e:
                return e
        except Exception:
            pass
        try:
            e = self.page.ele('text:Открыть', timeout=0.3)
            if e:
                return e
        except Exception:
            pass
        try:
            els = self.page.eles('css:a[aria-label*="Открыть"],a[title*="Открыть"]') or []
            if els:
                return els[0]
        except Exception:
            pass
        return None

    def _click_open_button_and_get_href(self) -> Optional[str]:
        """Находит «Открыть», скроллит, кликает (обычно + JS), возвращает абсолютный href (если есть)."""
        btn = self._find_open_button_element()
        if not btn:
            print("⚠️  Не нашли «Открыть» — будем вытаскивать картинку из модалки")
            return None

        href = btn.attr('href') or ''
        if href:
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = urljoin('https://yandex.ru', href)

        try:
            try:
                btn.scroll.to_see()
            except Exception:
                pass
            try:
                btn.click()
            except Exception:
                btn.click(by_js=True)
            print("✅ Клик по «Открыть» выполнен")
        except Exception as e:
            print(f"⚠️  Ошибка клика по «Открыть»: {e}")

        return href or None

    def _open_modal_by_tile_index(self, tile_index: int) -> bool:
        """Кликает по плитке с указанным индексом (обновляя список каждый раз)."""
        selectors = [
            'css:a.ImagesContentImage-Cover',
            'css:.ImagesContent-Item a[href]',
            'css:.serp-item a[href]',
            'css:img'
        ]
        for sel in selectors:
            try:
                tiles = self.page.eles(sel) or []
                if tile_index >= len(tiles):
                    continue
                t = tiles[tile_index]
                try:
                    t.scroll.to_see()
                except Exception:
                    pass
                try:
                    t.click()
                except Exception:
                    t.click(by_js=True)

                if self._wait_modal_opened(timeout=4.0):
                    print(f"✅ Модалка открыта по плитке #{tile_index+1} ({sel})")
                    return True

                print(f"ℹ️  Модалка не распознана после клика по плитке #{tile_index+1} ({sel})")
                try:
                    self.page.key.press('Escape')
                except Exception:
                    pass
                time.sleep(0.2)

            except Exception as e:
                print(f"⚠️  Ошибка при попытке клика по селектору {sel}: {e}")
                continue

        return False

    # -------------------- Шаг 4: скачать ЛОКАЛЬНО --------------------

    def _download_to_local(self, url: str, referer: Optional[str], product_name: str, seq: int) -> Optional[str]:
        """
        Скачивает бинарь локально в ./downloaded_images/<товар>/img_XXX.<ext>
        Валидирует минимальную сторону. Без ретраев. Возвращает путь на диске или None.
        """
        headers = self.session.headers.copy()
        if referer:
            headers['Referer'] = referer
        else:
            origin = _origin(url)
            if origin:
                headers['Referer'] = origin

        print(f"📥 Скачиваем локально: {url}")
        try:
            resp = self.session.get(url, headers=headers, timeout=25, verify=False, stream=True, allow_redirects=True)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ HTTP ошибка: {e}")
            return None

        content_type = resp.headers.get('content-type', '')
        ext = _guess_ext(url, content_type)

        # Проверим изображение и минимальный размер
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

        # Путь сохранения
        folder = os.path.join(self.download_root, _safe_filename(product_name))
        _ensure_dir(folder)
        filename = f"img_{seq:03d}{ext}"
        local_path = os.path.join(folder, filename)

        try:
            with open(local_path, 'wb') as f:
                f.write(resp.content)
            print(f"✅ Сохранено локально: {local_path}")
            return local_path
        except Exception as e:
            print(f"❌ Не удалось сохранить файл: {e}")
            return None

    # -------------------- МЕХАНИЗМ ИЗ «РАБОЧЕЙ» ВЕРСИИ: MinIO + БД --------------------

    def optimize_and_save_image(self, image_data: BytesIO, product_id: str, filename: str) -> Optional[str]:
        """
        Оптимизировать и сохранить изображение в MinIO (как в «рабочей» версии):
        - конвертация в JPEG
        - thumbnail до 800x600
        - storage_service.save_file(..., 'image/jpeg')
        Возвращает storage_path или None.
        """
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
        """Создание записи изображения в БД (как в «рабочей» версии)."""
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

    def _upload_local_to_minio_and_record(self, local_path: str, product, seq: int) -> bool:
        """
        Читает локальный файл -> через optimize_and_save_image(...) сохраняет в MinIO как JPEG ->
        создаёт запись в БД -> удаляет локальный файл.
        """
        filename = f"img_{seq:03d}.jpg"  # мы всегда конвертируем в JPEG
        try:
            with open(local_path, 'rb') as f:
                data = BytesIO(f.read())
        except Exception as e:
            print(f"❌ Ошибка чтения локального файла: {e}")
            return False

        storage_path = self.optimize_and_save_image(data, str(product.id), filename)
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
        if not ok:
            return False

        # Удаляем локальный файл после успешной записи
        try:
            os.remove(local_path)
            print(f"🧹 Удалён локальный файл: {local_path}")
        except Exception as e:
            print(f"⚠️  Не удалось удалить локальный файл: {e}")

        return True

    # -------------------- Поиск лучшей ссылки для скачивания --------------------

    def _largest_img_src_on_page(self) -> Optional[str]:
        """
        Если открылась страница не с raw-файлом, найдём КРУПНОЕ изображение.
        Выбираем по srcset (max width), иначе по src.
        """
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
                        url = t[0]
                        w = 0
                        if len(t) > 1 and t[1].endswith('w'):
                            try:
                                w = int(t[1][:-1])
                            except Exception:
                                w = 0
                        if url.startswith('http') and w > best_w:
                            best_w, best_url = w, url
                    continue
                src = img.attr('src')
                if src and src.startswith('http') and best_w < 0:
                    best_url = src
                    best_w = 0
            except Exception:
                continue
        return best_url

    # -------------------- Основной цикл: 3 файла на товар --------------------

    def process_product(self, product: Product, images_per_product: int = 3) -> int:
        """
        Скачивает до images_per_product картинок для одного товара:
        поиск → модалка → «Открыть» → локально → MinIO → БД → удалить локальный.
        """
        print(f"\n🎯 Обрабатываем товар: '{product.name}' (ID: {product.id})")
        print("-" * 60)

        if not self.init_page():
            print("❌ Не удалось инициализировать браузер")
            return 0

        # 1) Открыть выдачу и зафиксировать URL выдачи
        results_url = self.open_search_by_name(product.name)

        saved = 0
        tried = 0
        tile_index = 0
        downloaded_urls: Set[str] = set()
        max_tile_attempts = images_per_product * 12  # запас по плиткам

        while saved < images_per_product and tried < max_tile_attempts:
            # Если ушли с выдачи — вернёмся
            if not (self.page.url or "").startswith("https://yandex.ru/images"):
                self.page.get(results_url)
                time.sleep(0.6)

            # 2) Клик по плитке по индексу -> ожидание модалки
            opened = self._open_modal_by_tile_index(tile_index)
            tried += 1
            tile_index += 1

            if not opened:
                print("⚠️  Плитка не открыла модалку — следующая")
                continue

            # Сохраняем лучший URL из модалки НА СЛУЧАЙ если «Открыть» не даст прямой файл
            modal_best_url = self._best_modal_img_url()

            # 3) «Открыть» — строго клик, получаем href
            open_href = self._click_open_button_and_get_href()

            # 4) Получаем конечный URL для скачивания и корректный Referer
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
                    # Это страница — найдём самый крупный IMG
                    largest = self._largest_img_src_on_page()
                    if largest:
                        download_url = largest
                        referer_for_download = self.page.url

            # Если ничего не вышло — fallback на картинку из модалки
            if not download_url and modal_best_url:
                download_url = modal_best_url
                referer_for_download = _origin(modal_best_url) or 'https://yandex.ru/'

            if not download_url:
                self._dump_html(self.page.html or "", product.name, f"no_image_to_download_{saved+1}")
                print("❌ Не удалось получить ссылку на картинку — следующая плитка")
                # Вернёмся на выдачу
                self.page.get(results_url)
                time.sleep(0.6)
                continue

            if download_url in downloaded_urls:
                print("ℹ️  Дубликат URL — пропуск")
                self.page.get(results_url)
                time.sleep(0.6)
                continue

            print(f"🔗 Будем скачивать (локально): {download_url}")

            # Локально качаем файл
            local_path = self._download_to_local(download_url, referer_for_download, product.name, seq=saved + 1)

            # Возврат на выдачу для следующей плитки
            self.page.get(results_url)
            time.sleep(0.6)

            if not local_path:
                print("⚠️  Не удалось скачать локально — следующая плитка")
                continue

            # Заливка в MinIO (механизм из рабочей версии) + запись в БД + удаление локального
            if self._upload_local_to_minio_and_record(local_path, product, seq=saved + 1):
                saved += 1
                downloaded_urls.add(download_url)
                print(f"📈 Прогресс по товару: {saved}/{images_per_product}")
            else:
                print("⚠️  Не удалось загрузить в MinIO/записать в БД — следующая плитка")

        print(f"\n✅ Сохранено изображений для товара: {saved}/{images_per_product}")
        return saved

    # -------------------- Получение товаров из БД --------------------

    def get_products_from_db(self) -> List[Product]:
        """Берём товары из БД (без жадных связей)."""
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
    print("🚀 ПАРСЕР ИЗОБРАЖЕНИЙ — локально → MinIO (рабочий механизм) → запись в Postgres → удаление локального")
    print("=" * 94)
    print("Шаги: поиск → модалка → «Открыть» → локально → MinIO → БД → удалить локальный (3 изображения на товар)\n")

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
