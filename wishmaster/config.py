import os

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

# Получаем абсолютный путь к директории, где находится текущий скрипт
base_dir = os.path.dirname(os.path.abspath(__file__))

# Определяем абсолютные пути для базы данных и логов
DATABASE_PATH = os.path.abspath(os.path.join(base_dir, "..", "db", "wishmaster.db"))
LOG_DIR = os.path.abspath(os.path.join(base_dir, "..", "logs"))
