import logging
import os
import platform
import re
import sqlite3
import subprocess
import tkinter as tk
import urllib.parse
import webbrowser
from datetime import datetime
from tkinter import ttk

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
from config import DATABASE_PATH, LOG_DIR
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

base_dir = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.abspath(os.path.join(base_dir, "..", "charts"))
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

gui_log_path = os.path.join(LOG_DIR, "gui_history.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler(gui_log_path, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logging.info("=" * 60)
logging.info("🚀 Запуск графического интерфейса Wishmaster Analytics")

current_selected_name = ""
current_selected_article = ""
current_selected_url = ""
current_selected_price = 0


def sanitize_filename(name, max_length=100):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return name[:max_length]


def format_rubles(value):
    try:
        return f"{int(value):,} ₽".replace(",", " ")
    except (ValueError, TypeError):
        return "— ₽"


def open_charts_folder():
    logging.info(f"📂 Открытие папки с графиками: {CHARTS_DIR}")
    if platform.system() == "Windows":
        os.startfile(CHARTS_DIR)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", CHARTS_DIR])
    else:
        subprocess.Popen(["xdg-open", CHARTS_DIR])


def open_on_website():
    if current_selected_url and current_selected_url.startswith("http"):
        logging.info(f"🌐 Переход по прямой ссылке: {current_selected_url}")
        webbrowser.open(current_selected_url)
        result_label.config(text="🌐 Открываем карточку товара...", fg="#00f0ff")
        return

    if current_selected_article:
        search_link = f"https://wishmaster.me/search/?q={current_selected_article}"
        logging.info(f"🌐 Переход по артикулу [{current_selected_article}]: {search_link}")
        webbrowser.open(search_link)
        result_label.config(text=f"🌐 Ищем по артикулу [{current_selected_article}]...", fg="#00f0ff")
    else:
        logging.warning("Попытка открыть сайт: у выбранного товара нет артикула")
        result_label.config(text="⚠️ У этого товара нет артикула", fg="#ffb703")


def copy_article():
    if current_selected_article:
        root.clipboard_clear()
        root.clipboard_append(current_selected_article)
        logging.info(f"📋 Артикул скопирован в буфер: {current_selected_article}")
        result_label.config(text=f"📋 Артикул [{current_selected_article}] скопирован!", fg="#00ff88")
    else:
        logging.info("Копирование артикула: артикул отсутствует")
        result_label.config(text="⚠️ У этого товара нет сохранённого артикула", fg="#ffb703")


def copy_name():
    if current_selected_name:
        root.clipboard_clear()
        root.clipboard_append(current_selected_name)
        logging.info(f"📋 Название товара скопировано в буфер: {current_selected_name}")
        result_label.config(text="📋 Название товара скопировано!", fg="#00ff88")


def plot_price_history():
    selected_name = current_selected_name

    if not selected_name:
        text = search_var.get().strip()
        if text in products_info:
            selected_name = text

    if not selected_name or selected_name not in products_info:
        logging.warning("Попытка построить график без выбора товара")
        result_label.config(text="⚠️ Выберите товар из списка кликом мыши!", fg="#ff4d4d")
        return

    logging.info(f"📊 Построение графика для товара: '{selected_name}'")

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        query = """
        SELECT id, name, price_int, stock_status, timestamp
        FROM products
        WHERE name = ?
        ORDER BY id ASC
        """
        df = pd.read_sql_query(query, conn, params=(selected_name,))
        conn.close()

        if df.empty:
            logging.warning(f"Данные по товару '{selected_name}' не найдены в БД")
            result_label.config(text="Нет данных по этому товару", fg="#ff4d4d")
            return

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        logging.info(f"Загружено записей истории: {len(df)}")

        bg_color = "#131b2e"
        neon_line = "#00f0ff"
        neon_green = "#00ff88"
        neon_red = "#ff2a5f"
        grid_color = "#243354"

        plt.close('all')
        fig, ax = plt.subplots(figsize=(10.5, 6.0), facecolor=bg_color)
        ax.set_facecolor(bg_color)

        min_idx = df['price_int'].idxmin()
        max_idx = df['price_int'].idxmax()
        min_row = df.loc[min_idx]
        max_row = df.loc[max_idx]

        current_price = df.iloc[-1]['price_int']
        first_price = df.iloc[0]['price_int']
        total_change = current_price - first_price
        pct_change = (total_change / first_price) * 100 if first_price else 0

        spread = max_row['price_int'] - min_row['price_int']
        pad = spread * 0.35 if spread > 0 else min_row['price_int'] * 0.1
        y_min = max(0, min_row['price_int'] - pad)
        y_max = max_row['price_int'] + pad
        ax.set_ylim(bottom=y_min, top=y_max)

        ax.plot(df['timestamp'], df['price_int'], color=neon_line, linewidth=3.2, zorder=3)
        ax.fill_between(df['timestamp'], df['price_int'], y2=y_min, color=neon_line, alpha=0.18, zorder=2)
        ax.scatter(df['timestamp'], df['price_int'], color="#ffffff", edgecolor=neon_line, linewidth=2, s=40, zorder=4)

        ax.annotate(
            f"Мин: {format_rubles(min_row['price_int'])}",
            xy=(min_row['timestamp'], min_row['price_int']),
            xytext=(0, -28),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            fontweight="bold",
            color="#0b0f19",
            bbox=dict(boxstyle="round,pad=0.45", facecolor=neon_green, edgecolor="none"),
            arrowprops=dict(arrowstyle="->", color=neon_green, lw=2.0)
        )

        if min_row['price_int'] != max_row['price_int']:
            ax.annotate(
                f"Макс: {format_rubles(max_row['price_int'])}",
                xy=(max_row['timestamp'], max_row['price_int']),
                xytext=(0, 24),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                fontweight="bold",
                color="#ffffff",
                bbox=dict(boxstyle="round,pad=0.45", facecolor=neon_red, edgecolor="none"),
                arrowprops=dict(arrowstyle="->", color=neon_red, lw=2.0)
            )

        change_sign = "+" if total_change > 0 else ""
        change_color = neon_red if total_change > 0 else (neon_green if total_change < 0 else "#94a3b8")
        
        art_header = f"[Арт: {current_selected_article}] " if current_selected_article else ""
        title_text = f"{art_header}{selected_name}"
        if len(title_text) > 75:
            title_text = title_text[:72] + "..."

        fig.text(0.5, 0.94, title_text, fontsize=11, fontweight="bold", color="#ffffff", ha="center")
        fig.text(
            0.5, 0.88, 
            f"Текущая цена: {format_rubles(current_price)}   |   Динамика: {change_sign}{format_rubles(total_change)} ({change_sign}{pct_change:.1f}%)",
            fontsize=10, 
            color=change_color, 
            fontweight="bold",
            ha="center"
        )

        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: format_rubles(x)))
        ax.tick_params(colors="#94a3b8", labelsize=9)

        if len(df) > 1:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))
            fig.autofmt_xdate(rotation=30)
        else:
            ax.set_xticks([df['timestamp'].iloc[0]])
            ax.set_xticklabels([df['timestamp'].iloc[0].strftime("%d.%m.%Y %H:%M")])
            ax.text(
                0.5, 0.5, "В базе зафиксирована только 1 цена",
                transform=ax.transAxes, ha="center", va="center", color="#94a3b8", fontsize=11
            )

        ax.grid(True, linestyle="--", alpha=0.45, color=grid_color)
        for spine in ax.spines.values():
            spine.set_color(grid_color)

        plt.subplots_adjust(top=0.81, bottom=0.15, left=0.13, right=0.93)

        safe_filename = sanitize_filename(f'история_цены_{selected_name}.png')
        file_path = os.path.join(CHARTS_DIR, safe_filename)
        fig.savefig(file_path, facecolor=fig.get_facecolor(), dpi=150)
        logging.info(f"💾 График сохранён в файл: {file_path}")
        result_label.config(text=f"✅ Сохранено в charts/{safe_filename}", fg=neon_green)

        chart_window = tk.Toplevel(root)
        chart_window.title(f"График — {selected_name[:50]}")
        chart_window.geometry("960x620")
        chart_window.configure(bg=bg_color)

        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, chart_window)
        toolbar.configure(background="#0f172a")
        toolbar.update()

        def on_close():
            plt.close(fig)
            chart_window.destroy()

        chart_window.protocol("WM_DELETE_WINDOW", on_close)

    except Exception as e:
        logging.error(f"❌ Ошибка построения графика: {e}", exc_info=True)
        result_label.config(text="❌ Ошибка при построении графика", fg="#ff4d4d")


def update_suggestions(event=None):
    if event and event.keysym in ("Down", "Up"):
        return

    query = search_var.get().strip().lower()
    suggestions_list.delete(0, tk.END)
    display_to_item.clear()

    keywords = query.split()
    raw_matches = []

    for name, info in products_info.items():
        art = info["article"]
        in_stock = info["in_stock"]
        price = info["price"]
        search_haystack = f"{art} {name}".lower()

        if not query or all(k in search_haystack for k in keywords):
            raw_matches.append((name, art, in_stock, info["url"], price))

    sorted_matches = sorted(raw_matches, key=lambda x: (not x[2], x[0].lower()))

    for name, art, in_stock, url, price in sorted_matches[:120]:
        tag = "[В НАЛИЧИИ]" if in_stock else "[ОЖИДАЕМ]  "
        art_tag = f" [Арт: {art}]" if art else ""
        price_tag = f" [{format_rubles(price)}]" if price else ""
        display_text = f"{tag}{art_tag}{price_tag}  {name}"

        display_to_item[display_text] = (name, art, url, price)
        suggestions_list.insert(tk.END, display_text)

        idx = suggestions_list.size() - 1
        item_color = "#00ff88" if in_stock else "#f87171"
        suggestions_list.itemconfig(idx, fg=item_color)


def on_select_item(event=None):
    global current_selected_name, current_selected_article, current_selected_url, current_selected_price
    selected_indices = suggestions_list.curselection()
    if selected_indices:
        display_text = suggestions_list.get(selected_indices[0])
        if display_text in display_to_item:
            current_selected_name, current_selected_article, current_selected_url, current_selected_price = display_to_item[display_text]
            art_str = f"Арт: {current_selected_article} | " if current_selected_article else ""
            price_str = f"Цена: {format_rubles(current_selected_price)} | " if current_selected_price else ""
            selected_info_label.config(
                text=f"Выбрано: {art_str}{price_str}{current_selected_name[:60]}...",
                fg="#ffffff"
            )
            logging.debug(f"Выбран товар в списке: {current_selected_name} ({current_selected_price} руб.)")


def on_double_click(event=None):
    on_select_item()
    plot_price_history()


def show_context_menu(event):
    idx = suggestions_list.nearest(event.y)
    if idx >= 0:
        suggestions_list.selection_clear(0, tk.END)
        suggestions_list.selection_set(idx)
        on_select_item()
        context_menu.tk_popup(event.x_root, event.y_root)


def handle_paste(event=None):
    try:
        text = root.clipboard_get()
        if search_entry.selection_present():
            search_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
        search_entry.insert(tk.INSERT, text)
        update_suggestions()
        logging.info(f"Вставка из буфера в поиск: '{text}'")
        return "break"
    except tk.TclError:
        pass


def handle_select_all(event=None):
    search_entry.select_range(0, tk.END)
    search_entry.icursor(tk.END)
    return "break"


def clear_search():
    search_var.set("")
    update_suggestions()
    search_entry.focus_set()
    logging.info("Поле поиска очищено")


# --- ЗАГРУЗКА БАЗЫ ---
try:
    logging.info(f"Подключение к БД: {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(products)")
    cols = [c[1] for c in cursor.fetchall()]
    has_article = "article" in cols
    has_url = "url" in cols

    select_article = "article" if has_article else "''"
    select_url = "url" if has_url else "''"

    cursor.execute(f"""
        SELECT name, {select_article}, stock_status, {select_url}, price_int
        FROM products 
        WHERE id IN (SELECT MAX(id) FROM products GROUP BY name)
        ORDER BY name ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    products_info = {}
    for row in rows:
        name = row[0]
        art = str(row[1]).strip() if row[1] else ""
        st = (row[2] or "").lower()
        in_stock = ("ожидаем" not in st) and ("нет" not in st)
        url = str(row[3]).strip() if row[3] else ""
        price = row[4] if row[4] else 0
        products_info[name] = {"article": art, "in_stock": in_stock, "url": url, "price": price}

    logging.info(f"✅ Успешно загружено уникальных товаров: {len(products_info)}")

except Exception as e:
    logging.error(f"❌ Критическая ошибка при чтении базы данных: {e}", exc_info=True)
    products_info = {}

display_to_item = {}

# --- ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ---
root = tk.Tk()
root.title("Wishmaster Analytics — Графики цен")
root.geometry("900x540")
root.configure(bg="#131b2e")

tk.Label(
    root, text="🔍 Поиск модели или артикула (зелёные — В наличии | красные — Ожидаем):",
    font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#131b2e"
).pack(pady=(12, 4), anchor="w", padx=25)

search_var = tk.StringVar()
search_entry = tk.Entry(
    root, textvariable=search_var, font=("Segoe UI", 10),
    bg="#1e293b", fg="#ffffff", insertbackground="#00f0ff",
    relief="flat", bd=5
)
search_entry.pack(fill="x", padx=25, ipady=4)
search_entry.bind("<KeyRelease>", update_suggestions)
search_entry.bind("<Return>", lambda e: plot_price_history())

search_entry.bind("<Control-v>", handle_paste)
search_entry.bind("<Control-V>", handle_paste)
search_entry.bind("<Control-KeyPress-Cyrillic_em>", handle_paste)
search_entry.bind("<Control-KeyPress-Cyrillic_EM>", handle_paste)

search_entry.bind("<Control-a>", handle_select_all)
search_entry.bind("<Control-A>", handle_select_all)
search_entry.bind("<Control-KeyPress-Cyrillic_ef>", handle_select_all)
search_entry.bind("<Control-KeyPress-Cyrillic_EF>", handle_select_all)

entry_menu = tk.Menu(root, tearoff=0, bg="#1e293b", fg="#ffffff", activebackground="#00f0ff", activeforeground="#0b0f19")
entry_menu.add_command(label="📋 Вставить", command=handle_paste)
entry_menu.add_command(label="🔄 Выделить всё", command=handle_select_all)
entry_menu.add_separator()
entry_menu.add_command(label="❌ Очистить строку", command=clear_search)
search_entry.bind("<Button-3>", lambda e: entry_menu.tk_popup(e.x_root, e.y_root))

list_frame = tk.Frame(root, bg="#131b2e")
list_frame.pack(fill="both", expand=True, padx=25, pady=(5, 6))

scrollbar = tk.Scrollbar(list_frame, orient="vertical")
suggestions_list = tk.Listbox(
    list_frame, font=("Segoe UI", 9),
    bg="#1e293b", fg="#cbd5e1",
    selectbackground="#00f0ff", selectforeground="#0b0f19",
    activestyle="none", relief="flat", bd=3,
    yscrollcommand=scrollbar.set
)
scrollbar.config(command=suggestions_list.yview)
scrollbar.pack(side="right", fill="y")
suggestions_list.pack(side="left", fill="both", expand=True)

suggestions_list.bind("<<ListboxSelect>>", on_select_item)
suggestions_list.bind("<Double-Button-1>", on_double_click)
suggestions_list.bind("<Return>", lambda e: plot_price_history())
suggestions_list.bind("<Button-3>", show_context_menu)

selected_info_label = tk.Label(
    root, text="Кликните по товару из списка для выбора",
    font=("Segoe UI", 9, "italic"), fg="#94a3b8", bg="#131b2e"
)
selected_info_label.pack(anchor="w", padx=25, pady=(0, 6))

btn_frame = tk.Frame(root, bg="#131b2e")
btn_frame.pack(fill="x", padx=25, pady=(0, 6))

plot_button = tk.Button(
    btn_frame, text="📊 График", font=("Segoe UI", 10, "bold"),
    bg="#00f0ff", fg="#0b0f19", activebackground="#00c8d7", activeforeground="#0b0f19",
    relief="flat", cursor="hand2", padx=14, pady=5, command=plot_price_history
)
plot_button.pack(side="left", padx=(0, 6))

open_site_btn = tk.Button(
    btn_frame, text="🌐 На сайт", font=("Segoe UI", 9, "bold"),
    bg="#3b82f6", fg="#ffffff", activebackground="#2563eb", activeforeground="#ffffff",
    relief="flat", cursor="hand2", padx=14, pady=6, command=open_on_website
)
open_site_btn.pack(side="left", padx=(0, 6))

copy_art_btn = tk.Button(
    btn_frame, text="📋 Скопировать арт.", font=("Segoe UI", 9),
    bg="#1e293b", fg="#00ff88", activebackground="#334155", activeforeground="#00ff88",
    relief="flat", cursor="hand2", padx=10, pady=6, command=copy_article
)
copy_art_btn.pack(side="left", padx=(0, 6))

copy_name_btn = tk.Button(
    btn_frame, text="📋 Название", font=("Segoe UI", 9),
    bg="#1e293b", fg="#cbd5e1", activebackground="#334155", activeforeground="#ffffff",
    relief="flat", cursor="hand2", padx=10, pady=6, command=copy_name
)
copy_name_btn.pack(side="left", padx=(0, 6))

open_folder_btn = tk.Button(
    btn_frame, text="📁 Графики", font=("Segoe UI", 9),
    bg="#1e293b", fg="#94a3b8", activebackground="#334155", activeforeground="#ffffff",
    relief="flat", cursor="hand2", padx=10, pady=6, command=open_charts_folder
)
open_folder_btn.pack(side="right")

result_label = tk.Label(root, text="", font=("Segoe UI", 9), bg="#131b2e")
result_label.pack(pady=(0, 6))

context_menu = tk.Menu(root, tearoff=0, bg="#1e293b", fg="#ffffff", activebackground="#00f0ff", activeforeground="#0b0f19")
context_menu.add_command(label="🌐 Открыть на сайте", command=open_on_website)
context_menu.add_command(label="📋 Скопировать артикул", command=copy_article)
context_menu.add_command(label="📋 Скопировать название", command=copy_name)
context_menu.add_separator()
context_menu.add_command(label="📊 Построить график", command=plot_price_history)

update_suggestions()

root.mainloop()