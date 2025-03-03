import sqlite3
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Список категорий (можно добавлять новые)
categories = {
    "https://wishmaster.me/catalog/smartfony/smartfony_apple/iphone_16_pro/": "Apple iPhone 16 Pro",
    "https://wishmaster.me/catalog/smartfony/smartfony_apple/iphone_16_plus/": "Apple iPhone 16 Plus",
}


# Создание базы данных и таблицы
def create_database():
    conn = sqlite3.connect("wishmaster.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price TEXT,
            stock_status TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()


# Проверка, изменилась ли цена
def is_price_changed(cursor, name, new_price):
    cursor.execute("SELECT price FROM products WHERE name = ?", (name,))
    result = cursor.fetchone()
    if result:
        return result[0] != new_price  # True, если цена изменилась
    return True  # Если товара нет в базе, добавляем


# Функция для вставки данных в базу с проверкой цены
def save_to_db(category, products):
    conn = sqlite3.connect("wishmaster.db")
    cursor = conn.cursor()

    for product in products:
        name, price, stock_status = product

        # Проверяем, изменилась ли цена
        if is_price_changed(cursor, name, price):
            cursor.execute("""
                INSERT INTO products (category, name, price, stock_status, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (category, name, price, stock_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()


# Функция для поиска всех ссылок (href) в блоке пагинации
def get_pagination_links(base_url):
    response = requests.get(base_url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Ошибка при доступе к {base_url}: {response.status_code}")
        return [base_url]  # Если ошибка, парсим только первую страницу

    soup = BeautifulSoup(response.content, "html.parser")

    pagination = soup.find("div", class_="catalog-pagination__nums")

    if not pagination:
        print(f"Пагинация не найдена для {base_url}. Будем парсить только первую страницу.")
        return [base_url]

    links = pagination.find_all("a", href=True)

    page_numbers = []
    for link in links:
        href = link["href"]
        if "PAGEN_2=" in href:
            try:
                page_num = int(href.split("PAGEN_2=")[-1])
                page_numbers.append(page_num)
            except ValueError:
                continue

    if not page_numbers:
        return [base_url]

    max_page = max(page_numbers)

    all_pages = [base_url]
    for page in range(2, max_page + 1):
        all_pages.append(f"{base_url}?PAGEN_2={page}")

    return all_pages


# Функция для парсинга товаров
def parse_wishmaster(url):
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Ошибка при доступе к {url}: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    names = soup.find_all("div", class_="catalog-rounded-item__name")
    prices = soup.find_all("span", class_="catalog-rounded-item__price")
    stock_statuses = soup.find_all("div", class_="catalog-rounded-item__quantity-text")

    if not names or not prices or not stock_statuses:
        print(f"Данные не найдены на странице: {url}")
        return []

    products = []
    for name, price, stock in zip(names, prices, stock_statuses):
        product_name = name.text.strip()
        product_price = price.text.strip()
        stock_text = stock.text.strip()

        products.append((product_name, product_price, stock_text))

    print(f"Найдено товаров: {len(products)} на странице {url}")
    return products


# Функция для парсинга всех страниц категории
def parse_category(category_url, category_name):
    print(f"\n🔍 Начинаем парсинг категории: {category_name} ({category_url})")
    pages = get_pagination_links(category_url)
    print(f"Найдено страниц: {len(pages)}")

    all_products = []
    for index, url in enumerate(pages, start=1):
        print(f"📄 Парсинг страницы {index}: {url}")

        products = parse_wishmaster(url)
        all_products.extend(products)

    # Сохранение в базу
    save_to_db(category_name, all_products)
    return all_products


# Создание базы перед парсингом
create_database()

# Запуск парсинга всех категорий
for url, category_name in categories.items():
    parse_category(url, category_name)

print("\n✅ Все данные успешно сохранены в базу данных!")
