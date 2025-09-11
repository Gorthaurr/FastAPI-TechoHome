#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Доработанный парсер для сайта texcomplect.ru
Парсит все категории товаров и добавляет их в базу данных products.
БЕЗ парсинга картинок.
"""

import os
import re
import time
import hashlib
from urllib.parse import urljoin, urlparse, urlunparse, urlencode, parse_qsl
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

# Импорт моделей базы данных
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.database import SessionLocal
from app.db.models.product import Product
from app.db.models.category import Category
from app.db.models.product_attribute import ProductAttribute

# ---------------- НАСТРОЙКИ ----------------
BASE_URL = "https://texcomplect.ru/"
DELAY_SEC = 0.5
MAX_WORKERS = 4
MAX_PAGES_PER_CATEGORY = 200

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
}

PRICE_RE = re.compile(r"\d[\d\s]*\s?₽")
PAIR_RE = re.compile(r"^\s*([^:–—]+?)\s*[:–—]\s*(.+?)\s*$")

# ---------------- УТИЛИТЫ ----------------
def _err_kind(e: Exception) -> str:
    return getattr(e, "__class__", type("E",(object,),{})).__name__

def soup_get(session: requests.Session, url: str) -> BeautifulSoup:
    """Безопасное получение HTML страницы"""
    for i in range(3):
        try:
            r = session.get(url, timeout=25, headers=HEADERS)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if i == 2:
                print(f"[ERR] soup_get failed :: {_err_kind(e)}")
                return BeautifulSoup("", "html.parser")
            time.sleep(0.5 + i)
    return BeautifulSoup("", "html.parser")

def page_with(url: str, page_num: int) -> str:
    """Добавляет параметр page к URL"""
    u = urlparse(url)
    q = dict(parse_qsl(u.query))
    q["page"] = str(page_num)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q, doseq=True), u.fragment))

def text_clean(s: str) -> str:
    """Очистка текста от лишних пробелов"""
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()

def md5_id(s: str) -> str:
    """Генерация ID на основе MD5"""
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]

def is_product_page(s: BeautifulSoup) -> bool:
    """Проверка, является ли страница страницей товара"""
    try:
        return bool(s.select_one("div.pd-image__big-photo-inner"))
    except Exception:
        return False

def parse_price_to_cents(price_str: str) -> Optional[int]:
    """Конвертация цены в центы"""
    try:
        if not price_str:
            return None
        # Извлекаем только цифры
        digits = re.sub(r"[^\d]", "", price_str)
        if digits:
            return int(digits)
        return None
    except Exception:
        return None

# ---------------- ПОЛУЧЕНИЕ КАТЕГОРИЙ ----------------
def get_all_categories(session: requests.Session) -> List[Dict[str, str]]:
    """Получение всех категорий - используем фиксированный список из сайта"""
    # Фиксированный список всех 13 категорий с сайта texcomplect.ru
    categories = [
        {"name": "Холодильники", "slug": "kholodilniki", "url": "https://texcomplect.ru/kholodilniki/"},
        {"name": "Варочные панели", "slug": "varochnye-paneli", "url": "https://texcomplect.ru/varochnye-paneli/"},
        {"name": "Духовые шкафы", "slug": "dukhovye-shkafy", "url": "https://texcomplect.ru/dukhovye-shkafy/"},
        {"name": "Стиральные машины", "slug": "stiralnye-mashiny", "url": "https://texcomplect.ru/stiralnye-mashiny/"},
        {"name": "Сушильные машины", "slug": "sushilnye-mashiny", "url": "https://texcomplect.ru/sushilnye-mashiny/"},
        {"name": "Посудомоечные машины", "slug": "posudomoechnye-mashiny", "url": "https://texcomplect.ru/posudomoechnye-mashiny/"},
        {"name": "Вытяжки", "slug": "vytyazhki", "url": "https://texcomplect.ru/vytyazhki/"},
        {"name": "Морозильные камеры", "slug": "morozilnye-kamery", "url": "https://texcomplect.ru/morozilnye-kamery/"},
        {"name": "Микроволновые печи", "slug": "mikrovolnovye-pechi", "url": "https://texcomplect.ru/mikrovolnovye-pechi/"},
        {"name": "Винные шкафы", "slug": "vinnye-shkafy", "url": "https://texcomplect.ru/vinnye-shkafy/"},
        {"name": "Встраиваемые кофемашины", "slug": "vstraivaemye-kofemashiny", "url": "https://texcomplect.ru/vstraivaemye-kofemashiny/"},
        {"name": "Климатическое оборудование", "slug": "klimaticheskoe-oborudovanie", "url": "https://texcomplect.ru/klimaticheskoe-oborudovanie/"},
        {"name": "Сантехника", "slug": "santekhnika", "url": "https://texcomplect.ru/santekhnika/"}
    ]
    
    print(f"Loaded {len(categories)} predefined categories")
    return categories

# ---------------- ПОЛУЧЕНИЕ ССЫЛОК НА ТОВАРЫ ----------------
def collect_product_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Сбор ссылок на товары со страницы каталога - используем селекторы из оригинального парсера"""
    try:
        out, seen = [], set()
        for sel in [
            ".products a.woocommerce-LoopProduct-link",
            ".catalog a[href]",
            ".product-card a[href]",
            "a[rel=bookmark]",
            "a[href]",
        ]:
            for a in soup.select(sel):
                href = (a.get("href") or "").strip()
                if not href or href.startswith("#"): 
                    continue
                u = urljoin(base_url, href)
                if urlparse(u).netloc != urlparse(base_url).netloc: 
                    continue
                if u in seen: 
                    continue
                # «похоже на товар» — хотя бы два сегмента пути
                if len([x for x in urlparse(u).path.split("/") if x]) >= 2:
                    seen.add(u)
                    out.append(u)
        return list(dict.fromkeys(out))
    except Exception as e:
        print(f"[ERR] collect_product_links failed :: {_err_kind(e)}")
        return []

# ---------------- ПАРСИНГ ТОВАРА ----------------
def extract_product_name(soup: BeautifulSoup) -> str:
    """Извлечение названия товара"""
    try:
        # Различные селекторы для названия
        selectors = ["h1", "h2", ".product-title", ".pd-title", ".entry-title"]
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                return text_clean(el.get_text())
        return ""
    except Exception:
        return ""

def extract_product_price(soup: BeautifulSoup) -> str:
    """Извлечение цены товара"""
    try:
        # Приоритетный селектор для цены
        el = soup.select_one("div.pd-price__reg-price.s-product-price")
        if el:
            raw = text_clean(el.get_text(" "))
            m = PRICE_RE.search(raw)
            if m:
                return m.group(0)
            digits = re.sub(r"[^\d\s]", "", raw).strip()
            if digits:
                return f"{re.sub(r'\\s+', ' ', digits)} ₽"

        # Альтернативные селекторы
        for sel in [".pd-main__price", ".summary .price", ".product .price", ".entry-summary .price", ".price"]:
            el2 = soup.select_one(sel)
            if not el2:
                continue
            raw2 = text_clean(el2.get_text(" "))
            m2 = PRICE_RE.search(raw2)
            if m2:
                return m2.group(0)
            digits2 = re.sub(r"[^\d\s]", "", raw2).strip()
            if digits2:
                return f"{re.sub(r'\\s+', ' ', digits2)} ₽"

        return ""
    except Exception:
        return ""

def extract_product_description(soup: BeautifulSoup) -> str:
    """Извлечение описания товара"""
    try:
        cont = soup.select_one("div.item-tabs__content")
        if not cont:
            return ""
        
        parts = []
        for node in cont.find_all(["p", "div", "li"]):
            t = text_clean(node.get_text(" "))
            if t and not PAIR_RE.match(t):
                parts.append(t)
        
        out, seen = [], set()
        for t in parts:
            if t not in seen:
                seen.add(t)
                out.append(t)
        
        return "\n\n".join(out).strip()
    except Exception:
        return ""

def extract_product_characteristics(soup: BeautifulSoup) -> Dict[str, str]:
    """Извлечение характеристик товара"""
    try:
        # Поиск панели характеристик
        panel = soup.select_one("div.tab-chars")
        if not panel:
            return {}
        
        res = {}
        for tr in panel.find_all("tr"):
            cells = [text_clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            if len(cells) == 2:
                k, v = cells
                if k and v:
                    res[k] = v
            elif len(cells) > 2 and len(cells) % 2 == 0:
                for i in range(0, len(cells), 2):
                    k, v = cells[i], cells[i+1]
                    if k and v:
                        res[k] = v
        return res
    except Exception:
        return {}

def parse_product(session: requests.Session, url: str, category_slug: str, db: Session) -> bool:
    """Парсинг одного товара и сохранение в БД"""
    try:
        soup = soup_get(session, url)
        if not is_product_page(soup):
            return False

        # Извлекаем данные товара
        name = extract_product_name(soup)
        price_raw = extract_product_price(soup)
        price_cents = parse_price_to_cents(price_raw)
        description = extract_product_description(soup)
        characteristics = extract_product_characteristics(soup)

        if not name:
            return False

        # Генерируем ID товара
        product_id = md5_id(url)

        # Проверяем, существует ли товар
        existing_product = db.query(Product).filter(Product.id == product_id).first()
        if existing_product:
            print(f"  [SKIP] Product already exists: {name}")
            return "skipped"  # Возвращаем специальное значение для пропущенных товаров

        # Получаем или создаем категорию
        category = db.query(Category).filter(Category.slug == category_slug).first()
        if not category:
            category = Category(slug=category_slug)
            db.add(category)
            db.flush()

        # Создаем товар
        product = Product(
            id=product_id,
            category_id=category.id,
            product_url=url,
            name=name,
            price_raw=price_raw,
            price_cents=price_cents,
            description=description
        )
        db.add(product)

        # Добавляем характеристики
        for key, value in characteristics.items():
            attr = ProductAttribute(
                product_id=product_id,
                attr_key=key,
                value=value
            )
            db.add(attr)

        db.commit()
        print(f"  [SAVED] {name} - {price_raw}")
        return True

    except Exception as e:
        db.rollback()
        print(f"  [ERR] parse_product failed :: {_err_kind(e)}")
        return False

# ---------------- ПАРСИНГ КАТЕГОРИИ ----------------
def parse_category(session: requests.Session, category_info: Dict[str, str], db: Session) -> int:
    """Парсинг всех товаров в категории"""
    category_url = category_info["url"]
    category_slug = category_info["slug"]
    category_name = category_info["name"]
    
    print(f"\n[CATEGORY] {category_name} ({category_slug})")
    
    total_products = 0
    
    try:
        for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
            page_url = page_with(category_url, page)
            print(f"  [PAGE {page}] {page_url}")
            
            soup = soup_get(session, page_url)
            product_links = collect_product_links(soup, category_url)
            
            print(f"  [DEBUG] Found {len(product_links)} product links on page {page}")
            if len(product_links) > 0:
                print(f"  [DEBUG] First few links: {product_links[:3]}")
            
            if not product_links:
                print(f"  [STOP] No products found on page {page}")
                break
            
            page_products = 0
            for link in product_links:
                time.sleep(DELAY_SEC)
                result = parse_product(session, link, category_slug, db)
                if result == True:  # Только для действительно сохраненных товаров
                    page_products += 1
                    total_products += 1
            
            print(f"  [PAGE {page} SUMMARY] Products saved: {page_products}")
            
            # Убираем прерывание парсинга при отсутствии новых товаров
            # Продолжаем парсинг до конца лимита страниц
                
    except Exception as e:
        print(f"[ERR] parse_category failed for {category_name} :: {_err_kind(e)}")
    
    print(f"[CATEGORY SUMMARY] {category_name}: {total_products} products")
    return total_products

# ---------------- ОСНОВНАЯ ФУНКЦИЯ ----------------
def run():
    """Основная функция парсера"""
    try:
        print("[START] Starting texcomplect.ru parser")
        
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Получаем все категории
        print("[STEP 1] Getting all categories...")
        categories = get_all_categories(session)
        print(f"Found {len(categories)} categories")
        
        if not categories:
            print("[ERROR] No categories found")
            return
        
        # Подключаемся к базе данных
        db = SessionLocal()
        
        try:
            total_all_products = 0
            
            # Парсим каждую категорию
            for i, category_info in enumerate(categories, 1):
                print(f"\n[PROGRESS] Category {i}/{len(categories)}")
                products_count = parse_category(session, category_info, db)
                total_all_products += products_count
                
                # Небольшая пауза между категориями
                time.sleep(1)
            
            print(f"\n[DONE] Total products saved: {total_all_products}")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"[FATAL] run failed :: {_err_kind(e)}")

if __name__ == "__main__":
    run()
