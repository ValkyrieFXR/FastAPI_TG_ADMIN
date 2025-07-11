#!/usr/bin/python

import psycopg2
from psycopg2 import OperationalError

try:
    # Подключение к базе данных
    conn = psycopg2.connect(
        host="192.168.0.4",  # IP-адрес сервера
        database="tg_bot",    # Имя базы данных
        user="valkyriefx",    # Имя пользователя
        password="Q123456789" # Пароль
    )
    
    # Создание курсора для выполнения запросов
    cursor = conn.cursor()
    
    # Выполнение простого запроса для проверки подключения
    cursor.execute("SELECT version();")
    
    # Получение результата
    db_version = cursor.fetchone()
    print(f"Подключение к базе данных успешно! Версия: {db_version}")
    
    # Закрытие курсора и соединения
    cursor.close()
    conn.close()

except OperationalError as e:
    print(f"Ошибка при подключении к базе данных: {e}")
