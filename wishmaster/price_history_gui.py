import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import tkinter as tk
from tkinter import ttk


# Функция для построения графика
def plot_price_history():
    selected_product = product_var.get()

    if not selected_product:
        return

    # Подключение к базе данных
    conn = sqlite3.connect('wishmaster.db')
    query = f"""
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
    plt.title(f'История изменения цены для товара: {selected_product}')
    plt.xlabel('Дата')
    plt.ylabel('Цена (в числовом формате)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()

    # Сохранение и отображение графика
    filename = f'история_цены_товара_{selected_product}.png'
    plt.savefig(filename)
    plt.show()
    plt.close()


# Подключение к базе данных для получения списка товаров
conn = sqlite3.connect('wishmaster.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT name FROM products")
products = [row[0] for row in cursor.fetchall()]
conn.close()

# Создание окна tkinter
root = tk.Tk()
root.title("Выбор товара")

# Метка и выпадающий список
tk.Label(root, text="Выберите товар:").pack(pady=5)
product_var = tk.StringVar()
product_dropdown = ttk.Combobox(root, textvariable=product_var, values=products, width=100)
product_dropdown.pack(pady=5)

# Кнопка для построения графика
plot_button = tk.Button(root, text="Построить график", command=plot_price_history)
plot_button.pack(pady=10)

# Запуск главного цикла Tkinter
root.mainloop()
