import sqlite3
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Категории для парсинга
categories = {
    "https://wishmaster.me/catalog/smartfony/smartfony_apple/iphone_16_pro/": "Apple iPhone 16 Pro",
    "https://wishmaster.me/catalog/smartfony/smartfony_apple/iphone_16_plus/": "Apple iPhone 16 Plus",
}


# Создание базы данных и таблицы (если не существует)
def create_database():
    conn = sqlite3.connect("wishmaster.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price TEXT,
            price_difference TEXT,
            stock_status TEXT,
            timestamp TEXT
        )
    """)

    # Добавляем индекс для ускорения поиска
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON products (name);")

    conn.commit()
    conn.close()


# Получаем последнюю цену товара
def get_last_price(cursor, name):
    cursor.execute("SELECT price FROM products WHERE name = ? ORDER BY timestamp DESC LIMIT 1", (name,))
    result = cursor.fetchone()
    return result[0] if result else None


# Функция для вставки данных в базу
def save_to_db(category, products):
    conn = sqlite3.connect("wishmaster.db")
    cursor = conn.cursor()

    for product in products:
        name, new_price, stock_status = product

        # Получаем предыдущую цену
        old_price = get_last_price(cursor, name)

        # Вычисляем разницу
        if old_price and old_price != new_price:
            try:
                price_diff = float(new_price.replace(" ", "").replace("₽", "")) - float(
                    old_price.replace(" ", "").replace("₽", ""))
                price_diff = f"{price_diff:+,.2f} ₽".replace(",", " ")  # Приводим к читаемому виду
            except ValueError:
                price_diff = "Ошибка вычисления"
        else:
            price_diff = "0 ₽" if old_price else "Новый товар"

        # Добавляем новую запись в БД (старая остается)
        cursor.execute("""
            INSERT INTO products (category, name, price, price_difference, stock_status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (category, name, new_price, price_diff, stock_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        print(f"✅ Добавлена запись: {name} | Цена: {new_price} | Разница: {price_diff}")

    conn.commit()
    conn.close()


# Получение всех страниц пагинации
def get_pagination_links(base_url):
    response = requests.get(base_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ Ошибка {response.status_code} при доступе к {base_url}")
        return [base_url]

    soup = BeautifulSoup(response.content, "html.parser")
    pagination = soup.find("div", class_="catalog-pagination__nums")

    if not pagination:
        print(f"ℹ️ Пагинация не найдена для {base_url}. Парсим только первую страницу.")
        return [base_url]

    links = pagination.find_all("a", href=True)
    page_numbers = []

    for link in links:
        href = link["href"]
        if "PAGEN_2=" in href:
            try:
                page_numbers.append(int(href.split("PAGEN_2=")[-1]))
            except ValueError:
                continue

    max_page = max(page_numbers) if page_numbers else 1
    return [f"{base_url}?PAGEN_2={page}" for page in range(1, max_page + 1)]


# Парсинг товаров с одной страницы
def parse_wishmaster(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ Ошибка {response.status_code} при доступе к {url}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    names = soup.find_all("div", class_="catalog-rounded-item__name")
    prices = soup.find_all("span", class_="catalog-rounded-item__price")
    stock_statuses = soup.find_all("div", class_="catalog-rounded-item__quantity-text")

    if not names or not prices or not stock_statuses:
        print(f"⚠️ Данные не найдены на странице: {url}")
        return []

    products = [
        (name.text.strip(), price.text.strip(), stock.text.strip())
        for name, price, stock in zip(names, prices, stock_statuses)
    ]

    print(f"🔎 Найдено товаров: {len(products)} на {url}")
    return products


# Парсинг всех страниц в категории
def parse_category(category_url, category_name):
    print(f"\n🔍 Начинаем парсинг категории: {category_name} ({category_url})")
    pages = get_pagination_links(category_url)
    print(f"📂 Найдено страниц: {len(pages)}")

    all_products = []
    for index, url in enumerate(pages, start=1):
        print(f"📄 Парсинг страницы {index} → {url}")
        products = parse_wishmaster(url)
        all_products.extend(products)

    save_to_db(category_name, all_products)


# Основной запуск
if __name__ == "__main__":
    create_database()
    for url, category in categories.items():
        parse_category(url, category)

    print("\n✅ Все данные успешно сохранены в базе!")
