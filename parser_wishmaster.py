import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# Функция для поиска всех ссылок (href) в блоке пагинации
def get_pagination_links(base_url):
    response = requests.get(base_url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Ошибка при доступе к {base_url}: {response.status_code}")
        return [base_url]  # Если ошибка, парсим только первую страницу

    soup = BeautifulSoup(response.content, "html.parser")

    # Ищем блок пагинации
    pagination = soup.find("div", class_="catalog-pagination__nums")

    if not pagination:
        print("Пагинация не найдена. Будем парсить только первую страницу.")
        return [base_url]

    # Ищем все ссылки внутри блока пагинации
    links = pagination.find_all("a", href=True)

    # Собираем номера страниц
    page_numbers = []
    for link in links:
        href = link["href"]
        if "PAGEN_2=" in href:
            try:
                page_num = int(href.split("PAGEN_2=")[-1])  # Достаем номер страницы
                page_numbers.append(page_num)
            except ValueError:
                continue  # Если что-то пошло не так, пропускаем

    if not page_numbers:
        return [base_url]  # Если нет других страниц, только первая

    max_page = max(page_numbers)  # Определяем последнюю страницу

    # Формируем список ссылок от 1 до max_page
    all_pages = [base_url]  # Добавляем первую страницу
    for page in range(2, max_page + 1):
        all_pages.append(f"{base_url}?PAGEN_2={page}")

    return all_pages


# Функция для парсинга товаров (название, цена, наличие)
def parse_wishmaster(url):
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Ошибка при доступе к {url}: {response.status_code}")
        return []  # Если ошибка, пропускаем страницу

    soup = BeautifulSoup(response.content, "html.parser")

    # Ищем товары
    names = soup.find_all("div", class_="catalog-rounded-item__name")
    prices = soup.find_all("span", class_="catalog-rounded-item__price")
    stock_statuses = soup.find_all("div", class_="catalog-rounded-item__quantity-text")

    if not names or not prices or not stock_statuses:
        print(f"Данные не найдены на странице: {url}")
        return []  # Если на странице нет товаров

    products = []
    for name, price, stock in zip(names, prices, stock_statuses):
        product_name = name.text.strip()
        product_price = price.text.strip()
        stock_text = stock.text.strip()

        products.append((product_name, product_price, stock_text))

    print(f"Найдено товаров: {len(products)} на странице {url}")
    return products


# Функция для парсинга всех страниц
def parse_all_pages(base_url):
    pages = get_pagination_links(base_url)
    print(f"Найдено страниц: {len(pages)}")  # Вывод количества страниц

    all_products = []
    for index, url in enumerate(pages, start=1):
        print(f"Парсинг страницы {index}: {url}")

        products = parse_wishmaster(url)
        all_products.extend(products)

    return all_products


# Основной URL (первая страница)
base_url = "https://wishmaster.me/catalog/noutbuki/noutbuki_apple/"

# Запуск парсинга
products = parse_all_pages(base_url)

# Вывод результата
print("\nТовары и их цены на сайте Wishmaster:")
for product in products:
    print(f"Название: {product[0]}")
    print(f"Цена: {product[1]}")
    print(f"Наличие: {product[2]}")
    print("-" * 50)
