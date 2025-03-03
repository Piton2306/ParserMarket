# Заголовки для HTTP-запросов
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Категории для парсинга (URL: Название категории)

categories = {
    "https://wishmaster.me/catalog/smartfony/smartfony_apple/iphone_16_pro/": "Apple iPhone 16 Pro",
    "https://wishmaster.me/catalog/smartfony/smartfony_apple": "Смартфоны Apple iPhone (Эппл Айфон)",
    "https://wishmaster.me/catalog/smartfony/smartfony_google/": "Смартфоны Google (Гугл)",
    "https://wishmaster.me/catalog/noutbuki/noutbuki_apple/": "Ноутбуки Apple MacBook (Эппл Макбук)",
}

# Задержка между запросами (в секундах)
DELAY_BETWEEN_REQUESTS = 1

# Путь к файлу базы данных
DATABASE_PATH = "wishmaster.db"

# Путь к файлу логов
LOG_FILE_PATH = "wishmaster_parser.log"
