import re
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import tkinter as tk
from tkinter import ttk


# Функция для очистки имени файла от недопустимых символов
def sanitize_filename(name, max_length=100):
    name = re.sub(r'[<>:"/\\|?*]', '', name)  # Удаляем запрещённые символы
    return name[:max_length]  # Ограничиваем длину имени файла


# Функция для построения графика
def plot_price_history():
    selected_product = product_var.get().strip()

    if not selected_product or selected_product not in products:
        result_label.config(text="Ошибка: выберите товар из списка!", fg="red")
        return

    # Подключение к базе данных
    conn = sqlite3.connect('wishmaster.db')
    query = """
    SELECT id, name, price_int, timestamp
    FROM products
    WHERE name = ?
    ORDER BY id, timestamp
    """

    df = pd.read_sql_query(query, conn, params=(selected_product,))
    conn.close()

    # Преобразование столбца timestamp в формат datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Построение графика
    plt.figure(figsize=(10, 5))
    plt.plot(df['timestamp'], df['price_int'], marker='o', linestyle='-', label=selected_product)

    # Добавление подписей цен возле каждой точки
    for i, row in df.iterrows():
        plt.text(row['timestamp'], row['price_int'], f"{row['price_int']}", ha='right', va='bottom', fontsize=9,
                 color='black')

    plt.title(f'История изменения цены для товара: {selected_product}')
    plt.xlabel('Дата')
    plt.ylabel('Цена (в числовом формате)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()

    # Создаём безопасное имя файла
    safe_filename = sanitize_filename(f'история_цены_товара_{selected_product}.png')

    # Сохранение и отображение графика
    plt.savefig(safe_filename)
    plt.show()
    plt.close()

    result_label.config(text=f"График сохранен: {safe_filename}", fg="green")


# Функция обновления списка товаров при вводе (без сброса курсора)
def update_suggestions(event):
    input_text = product_var.get().strip().lower()

    # Фильтруем товары
    filtered_products = [p for p in products if input_text in p.lower()]

    # Обновляем список значений в Combobox
    product_dropdown["values"] = filtered_products

    # Принудительное раскрытие списка, если есть совпадения
    if filtered_products:
        product_dropdown.event_generate("<Down>")  # Открытие списка предложений

    # Убедимся, что фокус не теряется
    product_dropdown.focus_force()


# Подключение к базе данных для получения списка товаров
conn = sqlite3.connect('wishmaster.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT name FROM products")
products = [row[0] for row in cursor.fetchall()]
conn.close()

# Создание окна tkinter
root = tk.Tk()
root.title("Выбор товара")

# Метка и выпадающий список с автодополнением
tk.Label(root, text="Введите товар:").pack(pady=5)
product_var = tk.StringVar()
product_dropdown = ttk.Combobox(root, textvariable=product_var, values=products, width=100)
product_dropdown.pack(pady=5)
product_dropdown.bind("<KeyRelease>", update_suggestions)  # Запуск поиска при вводе

# Кнопка для построения графика
plot_button = tk.Button(root, text="Построить график", command=plot_price_history)
plot_button.pack(pady=10)

# Метка для вывода сообщений (ошибки, путь сохраненного файла)
result_label = tk.Label(root, text="", fg="black")
result_label.pack(pady=5)

# Запуск главного цикла Tkinter
root.mainloop()
