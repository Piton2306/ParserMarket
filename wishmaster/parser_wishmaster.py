import logging
import os
import re
import sqlite3
import time
import urllib.parse
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from config import DATABASE_PATH, DELAY_BETWEEN_REQUESTS, HEADERS, LOG_DIR, categories

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = datetime.now().strftime("wishmaster_%Y-%m-%d_%H-%M-%S.log")
log_file_path = os.path.join(LOG_DIR, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

session = requests.Session()
session.headers.update(HEADERS)

if "User-Agent" not in session.headers:
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )


def calculate_jhash(b: int) -> int:
    x = 123456789
    k = 0
    for i in range(1677696):
        x = ((x + b) ^ (x + (x % 3) + (x % 17) + b) ^ i) % 16776960
        if x % 117 == 0:
            k = (k + 1) % 1111
    return k


def solve_antibot_challenge(url: str, response: requests.Response) -> bool:
    logging.info("🛡️ Обнаружен антибот DDoS-Guard. Вычисляем ключ проверки...")

    js_p = session.cookies.get("__js_p_")
    if not js_p:
        set_cookie = response.headers.get("Set-Cookie", "")
        match = re.search(r"__js_p_=([^;]+)", set_cookie)
        if match:
            js_p = match.group(1)

    if not js_p:
        logging.error("❌ Не удалось найти куку __js_p_ для расчета ключа")
        return False

    try:
        parts = js_p.split(",")
        code = int(parts[0])
    except (ValueError, IndexError) as e:
        logging.error(f"❌ Ошибка разбора __js_p_ ({js_p}): {e}")
        return False

    calc_start = time.time()
    jhash_val = calculate_jhash(code)
    logging.info(f"🔑 Хеш вычислен за {time.time() - calc_start:.2f} сек. Результат: {jhash_val}")

    ua = session.headers["User-Agent"]
    jua_val = urllib.parse.quote(ua, safe="~")

    domain = urlparse(url).hostname
    session.cookies.set("__jhash_", str(jhash_val), domain=domain, path="/")
    session.cookies.set("__jua_", jua_val, domain=domain, path="/")

    time.sleep(1.2)
    return True


def get_page(url: str, max_retries: int = 2) -> BeautifulSoup | None:
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()

            if "gorizontal-vertikal" in response.text or "get_jhash" in response.text:
                if attempt < max_retries - 1:
                    if solve_antibot_challenge(url, response):
                        continue
                logging.error(f"Не удалось пройти проверку антибота для {url}")
                return None

            return BeautifulSoup(response.content, "html.parser")

        except Exception as e:
            logging.error(f"Ошибка запроса к {url} (попытка {attempt + 1}): {e}")
            time.sleep(1)

    return None


def create_database():
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    article TEXT,
                    name TEXT,
                    price_text TEXT,
                    price_int INTEGER,
                    price_difference REAL,
                    stock_status TEXT,
                    url TEXT,
                    timestamp TEXT
                )
            """)

            cursor.execute("PRAGMA table_info(products)")
            columns = [info[1] for info in cursor.fetchall()]
            if "article" not in columns:
                cursor.execute("ALTER TABLE products ADD COLUMN article TEXT")
            if "url" not in columns:
                cursor.execute("ALTER TABLE products ADD COLUMN url TEXT")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_name_id ON products (name, id DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_id ON products (article, id DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cat_name ON products (category, name)")
    except Exception as e:
        logging.error(f"Ошибка при создании БД: {e}")


def get_last_product_info(cursor, name: str, article: str = None) -> dict | None:
    try:
        if article:
            cursor.execute("""
                SELECT price_int, price_text, stock_status, article, url 
                FROM products 
                WHERE article = ? 
                ORDER BY id DESC LIMIT 1
            """, (article,))
            row = cursor.fetchone()
            if row:
                return {"price_int": row[0], "price_text": row[1], "stock_status": row[2], "article": row[3], "url": row[4]}

        cursor.execute("""
            SELECT price_int, price_text, stock_status, article, url 
            FROM products 
            WHERE name = ? 
            ORDER BY id DESC LIMIT 1
        """, (name,))
        row = cursor.fetchone()
        if row:
            return {"price_int": row[0], "price_text": row[1], "stock_status": row[2], "article": row[3], "url": row[4]}

        return None
    except Exception as e:
        logging.error(f"Ошибка получения данных для '{name}': {e}")
        return None


def clean_price(price_str: str) -> int | None:
    if not price_str:
        return None
    try:
        cleaned = re.sub(r"[\s\xa0\u202f]", "", price_str)
        numbers = [int(n) for n in re.findall(r"\d+", cleaned)]
        if not numbers:
            return None
        return max(numbers)
    except Exception as e:
        logging.error(f"Ошибка парсинга цены '{price_str}': {e}")
        return None


def save_to_db(category: str, products: list[dict]):
    if not products:
        return

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            for item in products:
                name = item["name"]
                article = item.get("article", "")
                price_text = item["price_text"]
                stock_status = item["stock_status"]
                product_url = item.get("url", "")

                clean_new_price = clean_price(price_text)
                last_info = get_last_product_info(cursor, name, article)

                if clean_new_price is None and last_info:
                    clean_new_price = last_info["price_int"]
                    price_text = last_info["price_text"]

                if clean_new_price is None:
                    continue

                if not product_url and last_info:
                    product_url = last_info.get("url", "")

                # Пропускаем, только если цена и статус не изменились
                if last_info:
                    same_price = (clean_new_price == last_info["price_int"])
                    same_stock = (stock_status.lower() == last_info["stock_status"].lower())
                    if same_price and same_stock:
                        continue

                price_diff = None
                if last_info and last_info["price_int"] is not None:
                    price_diff = clean_new_price - last_info["price_int"]

                cursor.execute("""
                    INSERT INTO products (category, article, name, price_text, price_int, price_difference, stock_status, url, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    category,
                    article,
                    name,
                    price_text,
                    clean_new_price,
                    price_diff,
                    stock_status,
                    product_url,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

                art_info = f" [Арт: {article}]" if article else ""
                diff_info = f"{price_diff:+d} руб." if (price_diff is not None and price_diff != 0) else "Без изм. цены"
                logging.info(f"✅ {name}{art_info} | {clean_new_price} руб. [{stock_status}] ({diff_info})")

    except Exception as e:
        logging.error(f"Ошибка сохранения в БД: {e}", exc_info=True)


def mark_missing_products_as_out_of_stock(category: str, seen_product_keys: set):
    if not seen_product_keys:
        return

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT name, article FROM products WHERE category = ?", (category,))
            db_products = cursor.fetchall()

            for name, article in db_products:
                if (article and article in seen_product_keys) or (name in seen_product_keys):
                    continue

                last_info = get_last_product_info(cursor, name, article)
                if not last_info:
                    continue

                current_status = last_info["stock_status"]
                if "ожидаем" in current_status.lower() or "нет" in current_status.lower():
                    continue

                new_status = "Ожидаем в ближайшее время"
                cursor.execute("""
                    INSERT INTO products (category, article, name, price_text, price_int, price_difference, stock_status, url, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    category,
                    article,
                    name,
                    last_info["price_text"],
                    last_info["price_int"],
                    0.0,
                    new_status,
                    last_info.get("url", ""),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                logging.warning(
                    f"⚠️ Товар исчез из каталога: {name} (Арт: {article or 'нет'}) | Статус: '[{new_status}]'"
                )

    except Exception as e:
        logging.error(f"Ошибка при обработке отсутствующих товаров: {e}", exc_info=True)


def extract_article(card) -> str:
    card_text = card.get_text()
    match = re.search(r"Артикул[:\s]+(\d+)", card_text, re.IGNORECASE)
    if match:
        return match.group(1)

    wish_btn = card.find(attrs={"data-offer": True})
    if wish_btn and wish_btn.get("data-offer"):
        return str(wish_btn["data-offer"]).strip()

    card_id = card.get("id", "")
    id_match = re.search(r"bx_\d+_(\d+)_", card_id)
    if id_match:
        return id_match.group(1)

    return ""


def extract_product_url(card) -> str:
    """Извлекает прямую ссылку на товар из карточки."""
    name_el = card.find(class_=re.compile(r"catalog-rounded-item__name"))
    link_el = name_el.find("a", href=True) if name_el else None

    if not link_el:
        link_el = card.find("a", class_=re.compile(r"name|title|image", re.I), href=True)

    if not link_el:
        link_el = card.find("a", href=True)

    if link_el and link_el.get("href"):
        href = link_el["href"].strip()
        if href.startswith("/"):
            return f"https://wishmaster.me{href}"
        elif href.startswith("http"):
            return href

    return ""


def build_page_url(base_url: str, page_number: int) -> str:
    parts = urlsplit(base_url)
    query_params = parse_qs(parts.query)
    query_params["PAGEN_2"] = [str(page_number)]
    new_query = urlencode(query_params, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def get_pagination_links(base_url: str) -> list[str]:
    soup = get_page(base_url)
    if not soup:
        return [base_url]

    try:
        pagination = soup.find("div", class_="catalog-pagination__nums")
        if not pagination:
            logging.info(f"Пагинация не найдена для {base_url}. Парсим 1 страницу.")
            return [base_url]

        page_numbers = []
        for link in pagination.find_all("a", href=True):
            if "PAGEN_2=" in link["href"]:
                try:
                    num = int(link["href"].split("PAGEN_2=")[-1].split("&")[0])
                    page_numbers.append(num)
                except ValueError:
                    continue

        max_page = max(page_numbers) if page_numbers else 1
        return [build_page_url(base_url, p) for p in range(1, max_page + 1)]

    except Exception as e:
        logging.error(f"Ошибка при сборе ссылок пагинации: {e}")
        return [base_url]


def parse_wishmaster(url: str) -> list[dict]:
    soup = get_page(url)
    if not soup:
        return []

    try:
        cards = soup.find_all("div", class_="catalog-rounded-item", attrs={"data-entity": "item"})
        if not cards:
            cards = [
                div for div in soup.find_all("div", class_="catalog-rounded-item")
                if "catalog-rounded-item__top" not in div.get("class", [])
            ]

        if not cards:
            return []

        products = []
        for card in cards:
            name_el = card.find(class_=re.compile(r"catalog-rounded-item__name"))
            if not name_el:
                continue

            name = name_el.get_text(strip=True)
            article = extract_article(card)
            product_url = extract_product_url(card)

            credit_block = card.find(class_=re.compile(r"credit|installment", re.I))
            if credit_block:
                credit_block.decompose()

            price_el = (
                card.find(class_=re.compile(r"price-current|price__current|price-val", re.I)) or
                card.find("span", class_=re.compile(r"catalog-rounded-item__price")) or
                card.find(class_=re.compile(r"catalog-rounded-item__price"))
            )

            stock_el = card.find(class_=re.compile(r"catalog-rounded-item__quantity-text|quantity|stock"))
            if stock_el and stock_el.get_text(strip=True):
                st_text = stock_el.get_text(strip=True).lower()
                if "наличии" in st_text or "мало" in st_text or "много" in st_text:
                    stock_status = "В наличии"
                elif "ожидаем" in st_text or "нет" in st_text:
                    stock_status = "Ожидаем в ближайшее время"
                else:
                    stock_status = stock_el.get_text(strip=True)
            else:
                stock_status = "В наличии"

            price_text = price_el.get_text(strip=True) if price_el else ""

            products.append({
                "article": article,
                "name": name,
                "price_text": price_text,
                "stock_status": stock_status,
                "url": product_url
            })

        logging.info(f"Найдено товаров: {len(products)} на {url}")
        return products

    except Exception as e:
        logging.error(f"Ошибка при парсинге {url}: {e}")
        return []


def parse_category(category_url: str, category_name: str):
    logging.info(f"--- Старт категории: {category_name} ---")
    pages = get_pagination_links(category_url)
    total_pages = len(pages)
    logging.info(f"Всего страниц: {total_pages}")

    seen_product_keys = set()
    completed_pages = 0

    try:
        for index, url in enumerate(pages, start=1):
            logging.info(f"Страница {index}/{total_pages} → {url}")
            products = parse_wishmaster(url)

            for p in products:
                if p["article"]:
                    seen_product_keys.add(p["article"])
                seen_product_keys.add(p["name"])

            save_to_db(category_name, products)
            completed_pages += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)

        if completed_pages == total_pages and total_pages > 0:
            mark_missing_products_as_out_of_stock(category_name, seen_product_keys)
        else:
            logging.warning("⚠️ Категория спарсена не полностью. Статусы 'Ожидаем' не проставлялись.")

    except Exception as e:
        logging.error(f"Сбой парсинга категории {category_name}: {e}")


if __name__ == "__main__":
    start_time = time.time()
    create_database()

    try:
        for url, category in categories.items():
            parse_category(url, category)
    finally:
        session.close()

    logging.info(f"🎉 Парсинг полностью завершен за: {time.time() - start_time:.2f} сек.")