let chartInstance = null;  // Для хранения экземпляра графика

// Функция для поиска товаров
function searchProducts() {
    const query = document.getElementById('search-input').value;
    fetch(`/search?query=${query}`)
        .then(response => response.json())
        .then(data => {
            const productList = document.getElementById('product-list');
            productList.innerHTML = '';
            data.forEach(product => {
                const li = document.createElement('li');
                li.textContent = product;
                li.onclick = () => fetchChart(product);
                productList.appendChild(li);
            });
        })
        .catch(error => console.log('Ошибка:', error));
}

// Функция для получения данных и отрисовки графика
function fetchChart(productName) {
    fetch(`/chart?product_name=${productName}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }

            // Уничтожаем предыдущий график, если он существует
            if (chartInstance) {
                chartInstance.destroy();
            }

            // Создаём новый график
            const ctx = document.getElementById('price-chart').getContext('2d');
            chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,  // Даты
                    datasets: [{
                        label: `Цена товара: ${productName}`,
                        data: data.prices,  // Цены
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderWidth: 2,
                        fill: true,
                        pointBackgroundColor: data.stock_status.map(status =>
                            status === 'in_stock' ? 'green' : 'red'  // Цвет точек в зависимости от статуса
                        ),
                        pointRadius: 5,  // Размер точек
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: `Изменение цены товара: ${productName}`
                        },
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    const label = context.dataset.label || '';
                                    const value = context.raw || 0;
                                    const status = data.stock_status[context.dataIndex];
                                    return `${label}: ${value} (${status === 'in_stock' ? 'В наличии' : 'Нет в наличии'})`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Дата'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Цена'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => console.log('Ошибка:', error));
}