#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==== ГЛОБАЛЬНЫЙ UTF-8 РЕЖИМ (фикс UnicodeDecodeError на Windows консоли/подпроцессах) ====
import os as _os
_os.environ.setdefault("PYTHONUTF8", "1")
_os.environ.setdefault("PYTHONIOENCODING", "UTF-8")

"""
Парсер изображений товаров без модалки (DrissionPage)

Главные изменения:
- НИКАКОГО viewer/modal. Берём кандидаты прямо с выдачи (anchors с ?img_url=).
- Собираем N*K кандидатов через скролл, вынимаем оригинальные URL из img_url,
  отбрасываем дубликаты, валидируем заголовки и сигнатуры, скачиваем.
- Подбираем корректный Referer под домены (mvideo/ozon/yandex/wb/leroy и т.д.).
- Батч-запрос товаров с недостающими фото, timezone-aware даты.
- HTTP pooling + retries, tuple-таймауты, разгрузка DOM.

"""

import sys
import re
import gc
import time
import warnings
from io import BytesIO
from datetime import datetime, timezone
from typing import List, Optional, Set, Dict, Tuple
from urllib.parse import quote, urljoin, urlparse, parse_qs, unquote

import requests
import urllib3
from PIL import Image

Image.MAX_IMAGE_PIXELS = 120_000_000  # ~120 МП

# ---------- Отключение SSL-предупреждений ----------
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# ---------- Пути/окружение проекта ----------
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('STORAGE_TYPE', 's3')
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://postgres:password@localhost:5433/fastapi_shop')

# ---------- Проектные импорты ----------
from app.db.database import SessionLocal
from app.db.models.product import Product
from app.db.models.product_image import ProductImage
from app.services.storage_service import storage_service
from app.core.config import settings

# ---------- DrissionPage ----------
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Settings

# ---------- HTTP pooling/retry ----------
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ========================= УТИЛИТЫ =========================

def _is_direct_image_url(url: str) -> bool:
    return bool(re.search(r'\.(jpg|jpeg|png|webp|gif|bmp|tif|tiff)(\?|$)', url, flags=re.I))


def _guess_ext(url: str, content_type: str) -> str:
    u = (url or '').lower()
    if u.endswith(('.jpg', '.jpeg')): return '.jpg'
    if u.endswith('.png'):  return '.png'
    if u.endswith('.webp'): return '.webp'
    if u.endswith('.gif'):  return '.gif'
    if u.endswith('.bmp'):  return '.bmp'
    if u.endswith(('.tif', '.tiff')): return '.tiff'
    if content_type:
        ct = (content_type or '').lower()
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


def _domain_referer(url: str, fallback: Optional[str] = None) -> Optional[str]:
    """Подбираем корректный Referer для капризных CDN."""
    host = (urlparse(url).netloc or '').lower()
    if host.endswith('mvideo.ru'):
        return 'https://www.mvideo.ru/'
    if host.endswith('ozone.ru'):
        return 'https://www.ozon.ru/'
    if host.endswith('yandex.net') or host.endswith('yandex.ru'):
        return 'https://yandex.ru/images/'
    if host.endswith('wildberries.ru'):
        return 'https://www.wildberries.ru/'
    if host.endswith('leroymerlin.ru'):
        return 'https://leroymerlin.ru/'
    return fallback


def _magic_image_type(header16: bytes) -> Optional[str]:
    """Определяем тип по сигнатуре (первые 16 байт)."""
    if len(header16) < 8:
        return None
    b = header16
    # JPEG
    if b[:2] == b'\xFF\xD8':
        return 'jpeg'
    # PNG
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    # GIF87a/GIF89a
    if b[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    # WEBP: RIFF....WEBP
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
        return 'webp'
    # BMP
    if b[:2] == b'BM':
        return 'bmp'
    # TIFF
    if b[:4] in (b'II*\x00', b'MM\x00*'):
        return 'tiff'
    return None


# ========================= ОСНОВНОЙ КЛАСС =========================

class QualityImageParser:
    def __init__(
        self,
        min_side: int = 300,
        rotate_every_products: int = 20,          # каждые N товаров перезапускаем Chromium
        close_browser_each_product: bool = False  # закрывать Chromium после каждого товара
    ):
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

        # HTTP session + pooling/retry
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.2, status_forcelist=(429, 500, 502, 503, 504))
        adapter = HTTPAdapter(pool_connections=32, pool_maxsize=64, max_retries=retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
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
        self.rotate_every_products = int(rotate_every_products) if rotate_every_products else 0
        self.close_browser_each_product = bool(close_browser_each_product)

        # Временная папка
        self.download_dir = os.path.join(os.getcwd(), "downloaded_images")
        os.makedirs(self.download_dir, exist_ok=True)

    # -------------------- Браузер --------------------

    def init_page(self) -> bool:
        if self.page is None:
            try:
                print("🌐 Инициализация DrissionPage (headless)...")
                co = ChromiumOptions()

                # 1) Современный API headless
                enabled = False
                for m in ('set_headless', 'headless'):
                    if hasattr(co, m):
                        try:
                            getattr(co, m)(True)
                            enabled = True
                            break
                        except Exception:
                            pass

                # 2) Фолбэк флагами
                if not enabled:
                    for flag in ('--headless=new', '--headless'):
                        try:
                            if hasattr(co, 'set_argument'):
                                co.set_argument(flag)
                                enabled = True
                                break
                        except Exception:
                            continue

                # Флаги стабильности
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
                print("ℹ️ Укажите путь к Chromium при необходимости: co.set_browser_path('/usr/bin/chromium')")
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

    # -------------------- Поиск (без модалки) --------------------

    def open_search_by_name(self, product_name: str) -> str:
        q = quote(product_name)
        url = f"https://yandex.ru/images/search?text={q}"
        print(f"📡 Открываем выдачу Яндекс.Картинок: {url}")
        self.page.get(url)
        time.sleep(0.5)
        return url

    def _scroll_collect_candidate_hrefs(self, need: int, max_rounds: int = 12) -> List[str]:
        """Скроллим SERP вниз и собираем href с img_url из плиток."""
        seen: Set[str] = set()
        hrefs: List[str] = []

        rounds = 0
        last_count = 0

        while rounds < max_rounds and len(hrefs) < need:
            rounds += 1
            # собрать все a[href*="img_url="]
            try:
                anchors = self.page.eles('css:a[href*="img_url="]') or []
            except Exception:
                anchors = []

            for a in anchors:
                try:
                    href = a.attr('href') or ''
                    if not href:
                        continue
                    # нормализуем абсолютный
                    if href.startswith('//'): href = 'https:' + href
                    elif href.startswith('/'): href = urljoin('https://yandex.ru', href)
                    if 'img_url=' not in href:
                        continue
                    if href in seen:
                        continue
                    seen.add(href)
                    hrefs.append(href)
                except Exception:
                    continue

            # если прироста нет — пробуем пролистать ещё
            if len(hrefs) >= need:
                break

            if len(hrefs) == last_count:
                # доскроллить до низа + подождать
                try:
                    self.page.scroll.to_bottom()
                except Exception:
                    pass
                time.sleep(0.6)
            else:
                last_count = len(hrefs)
                try:
                    self.page.scroll.down(1200)
                except Exception:
                    pass
                time.sleep(0.3)

        return hrefs

    def _extract_img_urls_from_hrefs(self, hrefs: List[str], max_items: int) -> List[str]:
        """Достаём оригинальные картинки из параметра img_url."""
        out: List[str] = []
        seen_urls: Set[str] = set()
        for href in hrefs:
            try:
                q = parse_qs(urlparse(href).query)
                raw = q.get('img_url', [None])[0]
                if not raw:
                    continue
                url = unquote(raw)
                if not url.startswith('http'):
                    continue
                # нормализуем без query для дедупликации
                base = url.split('?', 1)[0]
                if base in seen_urls:
                    continue
                seen_urls.add(base)
                out.append(url)
                if len(out) >= max_items:
                    break
            except Exception:
                continue
        return out

    # -------------------- Скачивание с валидацией --------------------

    def _download_to_file(self, url: str, referer: Optional[str]) -> Optional[str]:
        headers = self.session.headers.copy()

        # Подбор безопасного Referer
        ref = _domain_referer(url, referer or _origin(url) or 'https://yandex.ru/images/')
        if ref:
            headers['Referer'] = ref

        try:
            os.makedirs(self.download_dir, exist_ok=True)
        except Exception:
            pass

        ts = int(time.time() * 1000)
        tmp_name = f"dl_{ts}_{os.getpid()}"

        # HEAD быстрая проверка
        try:
            head = self.session.head(url, headers=headers, timeout=(5, 10), verify=False, allow_redirects=True)
            ct_head = (head.headers.get("Content-Type", "") or "").lower()
            if ct_head and (not ct_head.startswith('image/')):
                print(f"⚠️  HEAD не image/* ({ct_head}) — пропуск")
                return None
        except Exception:
            ct_head = ""

        # GET с сигнатурой
        try:
            r = self.session.get(url, headers=headers, timeout=(5, 25), verify=False, stream=True, allow_redirects=True)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ HTTP ошибка: {e}")
            return None

        ct = (r.headers.get('Content-Type', '') or '').lower()
        if ct and (not ct.startswith('image/')):
            print(f"⚠️  GET не image/* ({ct}) — пропуск")
            try: r.close()
            except Exception: pass
            return None

        # первые байты
        try:
            first = next(r.iter_content(chunk_size=8192))
        except StopIteration:
            first = b''
        except Exception:
            try: r.close()
            except Exception: pass
            return None

        magic = _magic_image_type(first[:16])
        if not magic:
            print("⚠️  Не похоже на изображение по сигнатуре — пропуск")
            try: r.close()
            except Exception: pass
            return None

        ext = _guess_ext(url, ct or ct_head) or ".jpg"
        file_path = os.path.join(self.download_dir, f"{tmp_name}{ext}")

        print(f"📥 Скачиваем в файл: {url} -> {file_path}")
        try:
            with open(file_path, "wb") as f:
                if first:
                    f.write(first)
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            print(f"❌ Ошибка записи файла: {e}")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            return None
        finally:
            try: r.close()
            except Exception: pass

        # Быстрая проверка размеров (без полного декодирования)
        try:
            with Image.open(file_path) as im:
                w, h = im.size
                if min(w, h) < self.min_side:
                    print(f"⚠️  Слишком маленькое: {w}x{h} (<{self.min_side})")
                    os.remove(file_path)
                    return None
                if (w * h) > 40_000_000:
                    print(f"⚠️  Слишком большое изображение {w}x{h} (>40 МП) — пропуск")
                    os.remove(file_path)
                    return None
        except Exception as e:
            print(f"⚠️  PIL ошибка: {e}")
            try: os.remove(file_path)
            except Exception: pass
            return None

        return file_path

    # -------------------- MinIO + БД --------------------

    def optimize_and_save_image_from_file(self, file_path: str, product_id: str, filename: str) -> Optional[str]:
        """Оптимизация с диска: draft() для JPEG, конверт в RGB, thumbnail -> JPEG -> MinIO."""
        try:
            with Image.open(file_path) as img:
                try:
                    if (img.format or '').upper() == 'JPEG':
                        img.draft('RGB', (800, 600))
                except Exception:
                    pass

                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
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
                uploaded_at=datetime.now(timezone.utc),
                processed_at=datetime.now(timezone.utc)
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

    def _upload_file_to_minio_and_record(self, file_path: str, product, seq: int) -> bool:
        filename = f"img_{seq:03d}.jpg"
        try:
            storage_path = self.optimize_and_save_image_from_file(file_path, str(product.id), filename)
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
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    # -------------------- Вспомогательное (оставлено для совместимости) --------------------
    def _largest_img_src_on_page(self) -> Optional[str]:
        """Оставляю на случай, если понадобится открыть конкретную страницу (не используется в основном пути)."""
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

    # -------------------- Выбор товаров --------------------

    def get_products_needing_images(self, images_per_product: int = 3) -> Tuple[List[Product], Dict[str, int]]:
        """Один батч-запрос: берем только товары, где фото < images_per_product."""
        try:
            print(f"📦 Батч-запрос: ищем товары с фото < {images_per_product} ...")
            from sqlalchemy import func
            from sqlalchemy.orm import lazyload
            with SessionLocal() as db:
                q = (
                    db.query(
                        Product,
                        func.count(ProductImage.id).label('img_cnt')
                    )
                    .outerjoin(ProductImage, ProductImage.product_id == Product.id)
                    .group_by(Product.id)
                    .having(func.count(ProductImage.id) < images_per_product)
                )

                rows = (
                    q.options(
                        lazyload(Product.attributes),
                        lazyload(Product.images),
                        lazyload(Product.category)
                    )
                    .all()
                )

                products = [row[0] for row in rows]
                counts = {row[0].id: int(row[1]) for row in rows}
                print(f"📦 Товаров с недостающими фото: {len(products)}")
                return products, counts
        except Exception as e:
            print(f"❌ Ошибка батч-запроса: {e}")
            return [], {}

    # -------------------- Основной цикл по товару (без модалки) --------------------

    def process_product(self, product: Product, images_per_product: int = 3, **kwargs) -> int:
        """
        existing_count — опциональный аргумент (из батч-запроса).
        """
        print(f"\n🎯 Обрабатываем товар: '{product.name}' (ID: {product.id})")
        print("-" * 60)

        if not self.init_page():
            print("❌ Не удалось инициализировать браузер")
            return 0

        existing = kwargs.get('existing_count')
        if existing is None:
            try:
                with SessionLocal() as db:
                    existing = db.query(ProductImage).filter(ProductImage.product_id == product.id).count()
            except Exception:
                existing = 0

        if existing >= images_per_product:
            print(f"⏭️ Уже есть {existing} изображений (≥ {images_per_product}). Пропуск товара.")
            return 0

        need_to_save = images_per_product - existing
        print(f"ℹ️  В БД уже: {existing}. Нужно докачать: {need_to_save}.")

        # 1) Открываем выдачу
        self.open_search_by_name(product.name)

        # 2) Собираем кандидатов из плиток (без открытия модалки)
        raw_hrefs = self._scroll_collect_candidate_hrefs(need=need_to_save * 8, max_rounds=14)
        candidates = self._extract_img_urls_from_hrefs(raw_hrefs, max_items=need_to_save * 6)

        if not candidates:
            print("⚠️  Не нашли ни одного прямого кандидата по img_url — пропуск товара")
            return 0

        # 3) Грузим по кандидатам
        saved = 0
        tried = 0
        seen_hosts: Set[str] = set()
        downloaded_urls: Set[str] = set()

        for url in candidates:
            if saved >= need_to_save:
                break
            tried += 1

            # лёгкая диверсификация по доменам (чтобы не биться много раз о один и тот же блокирующий CDN)
            host = (urlparse(url).netloc or '').lower()
            if host in seen_hosts and tried < len(candidates):
                # попробуем сначала новые домены
                continue
            seen_hosts.add(host)

            ref = _domain_referer(url, 'https://yandex.ru/images/')
            if url in downloaded_urls:
                continue

            seq = existing + saved + 1
            print(f"🔗 Будем скачивать (в файл): {url} -> seq={seq}")
            file_path = self._download_to_file(url, referer=ref)
            if not file_path:
                print("⚠️  Не удалось скачать/валидировать — skip")
                continue

            if self._upload_file_to_minio_and_record(file_path, product, seq=seq):
                downloaded_urls.add(url)
                saved += 1
                print(f"📈 Прогресс по товару: {existing + saved}/{images_per_product}")
                if (existing + saved) % 10 == 0:
                    gc.collect()
            else:
                print("⚠️  Не удалось загрузить в MinIO/записать в БД — skip")

        print(f"\n✅ Сохранено изображений для товара: {saved}/{need_to_save} (итог в БД будет {existing + saved})")

        # Разгрузка тяжёлых страниц
        try:
            if self.page:
                self.page.get('about:blank')
                time.sleep(0.1)
        except Exception:
            pass

        return saved

    # -------------------- Получение всех товаров (на всякий) --------------------

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
    print("🚀 ПАРСЕР ИЗОБРАЖЕНИЙ — файл → MinIO → запись в Postgres (без модалки)")
    print("=" * 94)
    print("Шаги: поиск → кандидаты по img_url → файл → MinIO → БД (до 3 изображений на товар)\n")

    parser = QualityImageParser(min_side=300, rotate_every_products=20, close_browser_each_product=False)

    try:
        images_per_product = 3

        products, counts = parser.get_products_needing_images(images_per_product=images_per_product)
        if not products:
            print(f"✅ Все товары уже имеют ≥ {images_per_product} изображений")
            return

        saved_total = 0
        processed = 0

        for product in products:
            # Ротация Chromium каждые N товаров (опционально)
            if parser.rotate_every_products and processed > 0 and processed % parser.rotate_every_products == 0:
                parser.close_page()
                time.sleep(0.2)

            try:
                print(f"\n🔄 Товар {processed + 1}/{len(products)}")
                existing = counts.get(product.id, 0)
                saved = parser.process_product(
                    product,
                    images_per_product=images_per_product,
                    existing_count=existing
                )
                saved_total += saved
                processed += 1
                time.sleep(0.2)

                # Закрывать Chromium после каждого товара (радикально снижает RAM)
                if parser.close_browser_each_product:
                    parser.close_page()
                    time.sleep(0.1)

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
