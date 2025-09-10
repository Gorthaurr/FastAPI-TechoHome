#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Каталог -> карточки -> products.json + фото по папкам.
Большое фото из .pd-image__big-photo-inner + «клики» миниатюр.
Стабилизированное исполнение: любые сбои пропускаются.
ЛОГИ: НИГДЕ не печатаются URL. Только номера страниц, product_id, счётчики и типы ошибок.
Цена: строго из div.pd-price__reg-price.s-product-price (с безопасными фолбэками).
"""

import os, re, json, time, hashlib
from urllib.parse import urljoin, urlparse, urlunparse, urlencode, parse_qsl
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup, Tag

# ---------------- НАСТРОЙКИ ----------------
START_URL   = "https://texcomplect.ru/kholodilniki/"  # <- каталог или конкретная карточка
OUT_DIR     = "out"
DELAY_SEC   = 0.2
MAX_PAGES   = 999
MAX_WORKERS = 6

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
}

PRICE_RE  = re.compile(r"\d[\d\s]*\s?₽")
SRCSET_RE = re.compile(r"\s*(\S+)\s+(\d+)w\s*")
SIZE_SUFFIX_RE = re.compile(r"-\d{2,4}x\d{2,4}(?=\.[a-z]{3,4}$)", re.I)
PAIR_RE   = re.compile(r"^\s*([^:–—]+?)\s*[:–—]\s*(.+?)\s*$")

# ---------------- БЕЗОПАСНОЕ ЛОГИРОВАНИЕ ----------------
def _err_kind(e: Exception) -> str:
    return getattr(e, "__class__", type("E",(object,),{})).__name__

def _status_from_exc(e: Exception):
    try:
        resp = getattr(e, "response", None)
        return getattr(resp, "status_code", None)
    except Exception:
        return None

# ---------------- УТИЛИТЫ ----------------
def soup_get(session: requests.Session, url: str) -> BeautifulSoup:
    for i in range(3):
        try:
            r = session.get(url, timeout=25)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if i == 2:
                code = _status_from_exc(e)
                print(f"[ERR] soup_get failed :: { _err_kind(e) }"
                      f"{'' if code is None else f' status={code}'}")
                return BeautifulSoup("", "html.parser")
            time.sleep(0.5 + i)
    return BeautifulSoup("", "html.parser")

def page_with(url: str, page_num: int) -> str:
    u = urlparse(url)
    q = dict(parse_qsl(u.query)); q["page"] = str(page_num)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q, doseq=True), u.fragment))

def text_clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()

def md5_id(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]

def is_product_page(s: BeautifulSoup) -> bool:
    try:
        return bool(s.select_one("div.pd-image__big-photo-inner"))
    except Exception:
        return False

def parse_srcset(srcset: str) -> list[tuple[str,int]]:
    out = []
    for part in (srcset or "").split(","):
        m = SRCSET_RE.match(part.strip())
        if m:
            out.append((m.group(1), int(m.group(2))))
    return out

def upscale_thumb(url: str) -> str:
    pu = urlparse(url)
    path = SIZE_SUFFIX_RE.sub("", pu.path)
    return urlunparse((pu.scheme, pu.netloc, path, pu.params, pu.query, pu.fragment))

# ---------------- ЛИСТИНГ ----------------
def collect_listing_links(s: BeautifulSoup, base: str) -> list[str]:
    try:
        out, seen = [], set()
        for sel in [
            ".products a.woocommerce-LoopProduct-link",
            ".catalog a[href]",
            ".product-card a[href]",
            "a[rel=bookmark]",
            "a[href]",
        ]:
            for a in s.select(sel):
                href = (a.get("href") or "").strip()
                if not href or href.startswith("#"): continue
                u = urljoin(base, href)
                if urlparse(u).netloc != urlparse(base).netloc: continue
                if u in seen: continue
                # «похоже на товар» — хотя бы два сегмента пути
                if len([x for x in urlparse(u).path.split("/") if x]) >= 2:
                    seen.add(u); out.append(u)
        return list(dict.fromkeys(out))
    except Exception as e:
        print(f"[ERR] collect_listing_links failed :: { _err_kind(e) }")
        return []

# ---------------- БОЛЬШИЕ ФОТО (строго из big-photo) ----------------
def big_photo_img_url(s: BeautifulSoup, product_url: str) -> str | None:
    try:
        img = s.select_one("div.pd-image__big-photo-inner img")
        if not img:
            return None
        return best_from_img(img, product_url)
    except Exception:
        return None

def best_from_img(img: Tag, base_url: str) -> str | None:
    try:
        candidates: list[tuple[str,int]] = []
        for attr in ("data-large_image","data-large-image","data-zoom-image","data-full"):
            v = img.get(attr)
            if v:
                u = upscale_thumb(urljoin(base_url, v))
                candidates.append((u, 10**9))
        for attr in ("srcset","data-srcset"):
            ss = img.get(attr)
            if ss:
                for u,w in parse_srcset(ss):
                    u = upscale_thumb(urljoin(base_url, u))
                    candidates.append((u, w))
        for attr in ("data-src","src"):
            v = img.get(attr)
            if v:
                candidates.append((upscale_thumb(urljoin(base_url, v)), 1))
        if not candidates:
            return None
        candidates.sort(key=lambda t: t[1], reverse=True)
        return candidates[0][0]
    except Exception:
        return None

def big_photos_via_thumbs(s: BeautifulSoup, product_url: str) -> list[str]:
    try:
        urls = []
        thumbs = s.select("div.pd-image__thumbs-slider img, div.pd-image__thumbs-slider a")
        for t in thumbs:
            tag = t
            if t.name == "a" and t.find("img"):
                tag = t
            elif t.name != "img" and t.find("img"):
                tag = t.find("img")
            u = best_from_img(tag, product_url)
            if u:
                urls.append(u)
        uniq, seen = [], set()
        for u in urls:
            pu = urlparse(u)
            bare = urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
            if bare not in seen:
                seen.add(bare); uniq.append(bare)
        return uniq
    except Exception:
        return []

def collect_big_images_strict(s: BeautifulSoup, product_url: str) -> list[str]:
    try:
        urls = []
        first = big_photo_img_url(s, product_url)
        if first:
            urls.append(first)
        via_clicks = big_photos_via_thumbs(s, product_url)
        urls.extend(via_clicks)
        uniq, seen = [], set()
        for u in urls:
            pu = urlparse(u)
            bare = urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
            if bare not in seen:
                seen.add(bare); uniq.append(bare)
        return uniq
    except Exception:
        return []

# ---------------- ОПИСАНИЕ И ХАРАКТЕРИСТИКИ ----------------
def extract_description(s: BeautifulSoup) -> str:
    try:
        cont = s.select_one("div.item-tabs__content")
        if not cont:
            return ""
        parts = []
        for node in cont.find_all(["p","div","li"]):
            t = text_clean(node.get_text(" "))
            if t and not PAIR_RE.match(t):
                parts.append(t)
        out, seen = [], set()
        for t in parts:
            if t not in seen:
                seen.add(t); out.append(t)
        return "\n\n".join(out).strip()
    except Exception:
        return ""

def find_chars_panel(s: BeautifulSoup):
    try:
        menu = s.select_one("div.item-tabs__menu")
        target = None
        if menu:
            for el in menu.select("a, li, button, span"):
                ttl = text_clean(el.get_text(" ")).lower()
                if "характерист" in ttl:
                    if el.has_attr("href") and str(el["href"]).startswith("#"):
                        target = str(el["href"])[1:]
                    for k in ("data-target","aria-controls"):
                        if not target and el.has_attr(k):
                            target = str(el[k]).lstrip("#")
                    break
        if target:
            panel = s.find(id=target)
            if panel:
                tc = panel.select_one("div.tab-chars")
                if tc: return tc
        return s.select_one("div.tab-chars")
    except Exception:
        return None

def extract_characteristics(s: BeautifulSoup) -> dict:
    try:
        panel = find_chars_panel(s)
        res = {}
        if not panel:
            return res
        for tr in panel.find_all("tr"):
            cells = [text_clean(td.get_text(" ")) for td in tr.find_all(["td","th"])]
            if len(cells) == 2:
                k, v = cells
                if k and v: res[k] = v
            elif len(cells) > 2 and len(cells) % 2 == 0:
                for i in range(0, len(cells), 2):
                    k, v = cells[i], cells[i+1]
                    if k and v: res[k] = v
        return res
    except Exception:
        return {}

# ---------------- СКАЧИВАНИЕ ИЗОБРАЖЕНИЙ ----------------
def download_image(session: requests.Session, url: str, folder: str, idx: int, product_id: str) -> str | None:
    """
    Скачивает изображение. В случае ошибки печатаем ТОЛЬКО product_id (без URL и без текста исключения).
    """
    try:
        r = session.get(url, timeout=60, stream=True, headers={"Referer": url})
        r.raise_for_status()
        os.makedirs(folder, exist_ok=True)
        ext = os.path.splitext(urlparse(url).path)[1].lower() or ".jpg"
        fn = f"img_{idx:03d}{ext}"
        path = os.path.join(folder, fn)
        with open(path, "wb") as f:
            for chunk in r.iter_content(16384):
                f.write(chunk)
        return fn
    except Exception as e:
        print(f"[WARN] download_image failed: product_id={product_id} :: { _err_kind(e) }")
        return None

# ---------------- ПОЛЯ КАРТОЧКИ ----------------
def extract_name(s: BeautifulSoup) -> str:
    try:
        h = s.find(["h1","h2"], string=True)
        return text_clean(h.get_text()) if h else ""
    except Exception:
        return ""

def extract_price(s: BeautifulSoup) -> str:
    """
    Приоритет: div.pd-price__reg-price.s-product-price.
    Фолбэки — прежние селекторы. Если ₽ нет — нормализуем цифры и добавляем ₽.
    """
    try:
        el = s.select_one("div.pd-price__reg-price.s-product-price")
        if el:
            raw = text_clean(el.get_text(" "))
            m = PRICE_RE.search(raw)
            if m:
                return m.group(0)
            digits = re.sub(r"[^\d\s]", "", raw).strip()
            if digits:
                return f"{re.sub(r'\\s+', ' ', digits)} ₽"

        for sel in [".pd-main__price", ".summary .price", ".product .price", ".entry-summary .price", ".price"]:
            el2 = s.select_one(sel)
            if not el2:
                continue
            raw2 = text_clean(el2.get_text(" "))
            m2 = PRICE_RE.search(raw2)
            if m2:
                return m2.group(0)
            digits2 = re.sub(r"[^\d\s]", "", raw2).strip()
            if digits2:
                return f"{re.sub(r'\\s+', ' ', digits2)} ₽"

        raw_all = text_clean(s.get_text(" "))
        m3 = PRICE_RE.search(raw_all)
        if m3:
            return m3.group(0)
        digits3 = re.sub(r"[^\d\s]", "", raw_all).strip()
        if digits3:
            return f"{re.sub(r'\\s+', ' ', digits3)} ₽"

        return ""
    except Exception:
        return ""

# ---------------- КАРТОЧКА ----------------
def parse_product(session: requests.Session, url: str, category_slug: str):
    """
    Возвращает (item_dict_or_None, saved_images_count). Любые ошибки -> SKIP.
    """
    try:
        s = soup_get(session, url)
        if not is_product_page(s):
            print(f"  [SKIP] not a product")
            return None, 0

        name  = extract_name(s)
        price = extract_price(s)
        images = collect_big_images_strict(s, url)   # может быть пусто — это ок
        description = extract_description(s)
        attrs = extract_characteristics(s)

        product_id = md5_id(url)
        img_dir = os.path.join(OUT_DIR, "images", category_slug, product_id)

        saved = []
        try:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                futs = {ex.submit(download_image, session, img_url, img_dir, i, product_id): (i, img_url)
                        for i, img_url in enumerate(images, start=1)}
                for fut in as_completed(futs):
                    fn = fut.result()
                    if fn:
                        saved.append(fn)
            saved.sort()
        except Exception as e:
            print(f"  [WARN] images batch failed: product_id={product_id} :: { _err_kind(e) }")

        item = {
            "id": product_id,
            "category": category_slug,
            "product_url": url,  # это поле в JSON оставляем, но НЕ печатаем его в логах
            "name": name,
            "price": price,
            "description": description,
            "attributes": attrs,
            "images": [f"images/{category_slug}/{product_id}/{fn}" for fn in saved]
        }
        return item, len(saved)
    except Exception as e:
        print(f"  [ERR] parse_product failed :: { _err_kind(e) }")
        return None, 0

# ---------------- ЗАПУСК ----------------
def run():
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        session = requests.Session()
        session.headers.update(HEADERS)

        start = START_URL.strip()
        base  = f"{urlparse(start).scheme}://{urlparse(start).netloc}"
        cat_slug = [p for p in urlparse(start).path.split("/") if p][0] if [p for p in urlparse(start).path.split("/") if p] else "category"

        products: list[dict] = []

        def write_json_safely():
            try:
                out_json = os.path.join(OUT_DIR, "products.json")
                with open(out_json, "w", encoding="utf-8") as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[ERR] write_json failed :: { _err_kind(e) }")

        # Счётчики для общего итога
        total_photo_dirs = 0  # товаров с ≥1 фото
        total_products = 0    # записано в JSON

        s0 = soup_get(session, start)
        if is_product_page(s0):
            item, saved_cnt = parse_product(session, start, cat_slug)
            if item:
                products.append(item)
                total_products += 1
                if saved_cnt > 0:
                    total_photo_dirs += 1
                write_json_safely()
            print(f"[SINGLE] photo_dirs_created={1 if saved_cnt>0 else 0}, products_written=1")
        else:
            seen = set()
            for page in range(1, MAX_PAGES + 1):
                page_url = page_with(start, page)
                print(f"[PAGE {page}]")  # без URL

                try:
                    s = soup_get(session, page_url)
                except Exception as e:
                    print(f"[WARN] page soup failed :: { _err_kind(e) }")
                    continue

                links = collect_listing_links(s, base)
                if not links:
                    print("[STOP] нет ссылок на товары — выходим")
                    break

                # Счётчики по странице
                page_photo_dirs = 0
                page_products_written = 0

                for href in links:
                    if href in seen:
                        continue
                    seen.add(href)
                    time.sleep(DELAY_SEC)
                    try:
                        item, saved_cnt = parse_product(session, href, cat_slug)
                        if item:
                            products.append(item)
                            page_products_written += 1
                            total_products += 1
                            if saved_cnt > 0:
                                page_photo_dirs += 1
                                total_photo_dirs += 1
                            write_json_safely()
                    except Exception as e:
                        print(f"  [ERR] loop parse failed :: { _err_kind(e) }")
                        # просто пропускаем

                print(f"[PAGE {page} SUMMARY] photo_dirs_created={page_photo_dirs}, "
                      f"products_written_this_page={page_products_written}, total_products={total_products}")

                if page_products_written == 0:
                    break

        print(f"[DONE] items_total={len(products)}, photo_dirs_total={total_photo_dirs} "
              f"-> {os.path.join(OUT_DIR, 'products.json')}")
    except Exception as e:
        print(f"[FATAL] run failed :: { _err_kind(e) }")

if __name__ == "__main__":
    run()
