from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
app = Flask(__name__)

# Функция для подключения к базе данных и получения товаров
def get_products(query=""):
    conn = sqlite3.connect('db/wishmaster.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT name FROM products WHERE name LIKE ?", ('%' + query + '%',))
    products = [row[0] for row in cursor.fetchall()]
    conn.close()
    return products

# Функция для построения графика для выбранного товара
def create_price_chart(product_name):
    try:
        print(f"Построение графика для товара: {product_name}")  # Отладочное сообщение
        conn = sqlite3.connect('wishmaster.db')
        query = """
        SELECT timestamp, price_int
        FROM products
        WHERE name = ?
        ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn, params=(product_name,))
        conn.close()

        print(f"Данные из базы данных: {df}")  # Отладочное сообщение

        if df.empty:
            print(f"Нет данных для товара: {product_name}")
            return None

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df['timestamp'], df['price_int'], marker='o', linestyle='-', label=product_name)

        for i, row in df.iterrows():
            ax.text(row['timestamp'], row['price_int'], str(row['price_int']), ha='right', va='bottom', fontsize=9)

        ax.set_title(f'Изменение цены товара: {product_name}')
        ax.set_xlabel('Дата')
        ax.set_ylabel('Цена')
        ax.grid(True)
        ax.legend()

        img_buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(img_buf, format='png')
        img_buf.seek(0)

        img_base64 = base64.b64encode(img_buf.getvalue()).decode('utf-8')
        img_buf.close()
        plt.close(fig)

        print("График успешно создан")  # Отладочное сообщение
        return img_base64

    except Exception as e:
        print(f"Ошибка при создании графика: {e}")  # Отладочное сообщение
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    products = get_products(query)
    return jsonify(products)

@app.route('/chart', methods=['GET'])
def chart():
    product_name = request.args.get('product_name', '')
    if product_name:
        try:
            conn = sqlite3.connect('wishmaster.db')
            query = """
            SELECT timestamp, price_int
            FROM products
            WHERE name = ?
            ORDER BY timestamp
            """
            df = pd.read_sql_query(query, conn, params=(product_name,))
            conn.close()

            if df.empty:
                return jsonify({'error': 'Данные для построения графика отсутствуют'})

            # Преобразуем данные в список словарей
            data = {
                'labels': df['timestamp'].tolist(),  # Даты
                'prices': df['price_int'].tolist()  # Цены
            }
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': f'Ошибка при получении данных: {e}'})
    return jsonify({'error': 'Товар не найден'})

if __name__ == '__main__':
    app.run(debug=True)
