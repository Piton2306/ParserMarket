import logging
import sqlite3
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Импортируем настройки из config.py
from config import HEADERS, categories, DELAY_BETWEEN_REQUESTS, DATABASE_PATH, LOG_FILE_PATH

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding="utf-8"),  # Логи в файл
        logging.StreamHandler()  # Логи в консоль
    ]
)


def create_database():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
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
        conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при создании базы данных: {e}")
    finally:
        conn.close()


def get_last_price(cursor, name):
    try:
        cursor.execute("SELECT price FROM products WHERE name = ? ORDER BY timestamp DESC LIMIT 1", (name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logging.error(f"Ошибка при получении последней цены: {e}")
        return None


def save_to_db(category, products):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        for product in products:
            name, new_price, stock_status = product

            # Очистка цены от пробелов и символов валюты
            clean_new_price = (
                new_price
                .replace("\u00A0", "")  # Удаляем неразрывные пробелы
                .replace(" ", "")  # Удаляем обычные пробелы
                .replace("руб.", "")  # Удаляем символ валюты
                .replace(",", ".")  # Заменяем запятую на точку (если есть)
            )

            # Получаем последнюю цену из базы данных
            old_price = get_last_price(cursor, name)

            # Если товар уже есть в базе и цена не изменилась — пропускаем
            if old_price:
                clean_old_price = (
                    old_price
                    .replace("\u00A0", "")
                    .replace(" ", "")
                    .replace("руб.", "")
                    .replace(",", ".")
                )
                if clean_new_price == clean_old_price:
                    logging.info(f"🔹 Цена не изменилась для {name}, пропускаем")
                    continue

            # Вычисляем разницу в цене
            if old_price:
                try:
                    price_difference = float(clean_new_price) - float(clean_old_price)
                except ValueError as e:
                    logging.error(f"Ошибка при вычислении разницы цен для {name}: {e}")
                    price_difference = "Ошибка вычисления"
            else:
                price_difference = "Новая запись"  # Для первого добавления товара

            # Добавляем запись в базу
            cursor.execute("""
                INSERT INTO products (category, name, price, stock_status, timestamp, price_difference)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                category, name, new_price, stock_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(price_difference)
            ))

            logging.info(f"✅ Добавлен новый товар: {name} | Цена: {new_price} | Разница: {price_difference}")

        conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при сохранении в базу данных: {e}")
    finally:
        conn.close()


def get_pagination_links(base_url):
    try:
        response = requests.get(base_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        pagination = soup.find("div", class_="catalog-pagination__nums")

        if not pagination:
            logging.info(f"Пагинация не найдена для {base_url}. Парсим только первую страницу.")
            return [base_url]

        links = pagination.find_all("a", href=True)
        page_numbers = [int(link["href"].split("PAGEN_2=")[-1]) for link in links if "PAGEN_2=" in link["href"]]
        max_page = max(page_numbers) if page_numbers else 1
        return [f"{base_url}?PAGEN_2={page}" for page in range(1, max_page + 1)]
    except Exception as e:
        logging.error(f"Ошибка при получении ссылок пагинации: {e}")
        return [base_url]


def parse_wishmaster(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        names = soup.find_all("div", class_="catalog-rounded-item__name")
        prices = soup.find_all("span", class_="catalog-rounded-item__price")
        stock_statuses = soup.find_all("div", class_="catalog-rounded-item__quantity-text")

        if not names or not prices or not stock_statuses:
            logging.warning(f"Данные не найдены на странице: {url}")
            return []

        products = [
            (name.text.strip(), price.text.strip(), stock.text.strip())
            for name, price, stock in zip(names, prices, stock_statuses)
        ]

        logging.info(f"Найдено товаров: {len(products)} на {url}")
        return products
    except Exception as e:
        logging.error(f"Ошибка при парсинге страницы {url}: {e}")
        return []


def parse_category(category_url, category_name):
    logging.info(f"Начинаем парсинг категории: {category_name} ({category_url})")
    pages = get_pagination_links(category_url)
    logging.info(f"Найдено страниц: {len(pages)}")

    all_products = []
    for index, url in enumerate(pages, start=1):
        logging.info(f"Парсинг страницы {index} → {url}")
        products = parse_wishmaster(url)
        all_products.extend(products)
        time.sleep(DELAY_BETWEEN_REQUESTS)  # Используем задержку из конфига

    save_to_db(category_name, all_products)


if __name__ == "__main__":
    create_database()
    for url, category in categories.items():
        parse_category(url, category)

    logging.info("Все данные успешно сохранены в базе!")
