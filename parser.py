import requests
from bs4 import BeautifulSoup


# Функция для поиска всех ссылок (href) в блоке пагинации
def get_pagination_links(base_url):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Ищем блок пагинации
    pagination = soup.find("div", class_="catalog-pagination__nums")

    if not pagination:
        print("Пагинация не найдена. Будем парсить только первую страницу.")
        return [base_url]  # Если пагинации нет, возвращаем только первую страницу

    # Ищем все ссылки (a) внутри блока пагинации
    links = pagination.find_all("a", href=True)

    # Извлекаем href и формируем полный URL
    hrefs = [base_url + link["href"] for link in links if "PAGEN_2=" in link["href"]]

    # Добавляем первую страницу в список
    hrefs.insert(0, base_url)

    return list(set(hrefs))  # Убираем возможные дубликаты


# Функция для парсинга товаров (название и цена)
def parse_wishmaster(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Ищем товары
    names = soup.find_all("div", class_="catalog-rounded-item__name")
    prices = soup.find_all("span", class_="catalog-rounded-item__price")

    products = []
    for name, price in zip(names, prices):
        product_name = name.text.strip()
        product_price = price.text.strip()
        products.append((product_name, product_price))

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
base_url = "https://wishmaster.me/catalog/smartfony/smartfony_apple/iphone_16_pro/"

# Запуск парсинга
products = parse_all_pages(base_url)

# Вывод результата
print("\nТовары и их цены на сайте Wishmaster:")
for product in products:
    print(f"Название: {product[0]}")
    print(f"Цена: {product[1]}")
    print("-" * 50)
