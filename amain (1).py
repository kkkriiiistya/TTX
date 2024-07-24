import telebot
from telebot import types
import json
import time
import threading

# Замените этот токен на ваш токен бота
TOKEN = "7387730083:AAE3ESmkr_ldxqjEA0JNPYKnakXkyt-IWE0"

bot = telebot.TeleBot(TOKEN)

try:
    with open('dvig.json', 'r', encoding='utf-8') as f:
        dvig_data = json.load(f)
        print("Данные о двигателях из файла dvig.json загружены!")
except FileNotFoundError:
    print("Ошибка: файл dvig.json не найден!")
    bot.send_message(chat_id="@your_chat_id",
                     text="Ошибка: файл dvig.json не найден! Пожалуйста, создайте файл с данными о двигателях.")
    dvig_data = []  # Создаем пустой список, чтобы бот мог продолжить работу

try:
    with open('akkum.json', 'r', encoding='utf-8') as f:
        akum_data = json.load(f)
        print("Данные об аккумуляторах из файла akkum.json загружены!")
except FileNotFoundError:
    print("Ошибка: файл akkum.json не найден!")
    bot.send_message(chat_id="@your_chat_id",
                     text="Ошибка: файл akkum.json не найден! Пожалуйста, создайте файл с данными об аккумуляторах.")
    akum_data = []  # Создаем пустой список, чтобы бот мог продолжить работу

try:
    with open('combination.json', 'r', encoding='utf-8') as f:
        combination_data = json.load(f)
        print("Данные о комбинациях из файла combination.json загружены!")
except FileNotFoundError:
    print("Ошибка: файл combination.json не найден!")
    bot.send_message(chat_id="@your_chat_id",
                     text="Ошибка: файл combination.json не найден! Пожалуйста, создайте файл с данными о комбинациях.")
    combination_data = {}  # Создаем пустой словарь, чтобы бот мог продолжить работу

# --- Ограничение запросов ---
user_requests = {}
REQUEST_LIMIT = 25  # Максимальное количество запросов в секунду
REQUEST_TIMEOUT = 0.5  # Таймаут для ограничения запросов (в секундах)

# --- Таймер ---
last_click_time = {}
CLICK_TIMEOUT = 0.5  # Таймаут для предотвращения спама (в секундах)

# --- Флаг для отслеживания состояния "заморозки" ---
frozen_users = {}

# --- Время последней заморозки ---
last_freeze_time = {}


# --- Обработчики команд бота ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    # Проверяем, заморожен ли пользователь
    if user_id in frozen_users and frozen_users[user_id]:
        bot.reply_to(message, "Большое количество запросов! Подождите немного.")
        return

    # Ограничение запросов
    if user_id not in user_requests:
        user_requests[user_id] = []
    user_requests[user_id].append(time.time())
    if len(user_requests[user_id]) > REQUEST_LIMIT:
        # Замораживаем пользователя, если прошло 30 секунд с последней заморозки
        if user_id not in last_freeze_time or time.time() - last_freeze_time[user_id] >= 10:
            # Замораживаем пользователя
            freeze_message = bot.send_message(chat_id=message.chat.id, text="Пожалуйста, подождите...")
            threading.Thread(target=freeze_user, args=(message.chat.id, 10, freeze_message.message_id)).start()
            last_freeze_time[user_id] = time.time()
            return

    # Таймер для предотвращения спама
    if user_id in last_click_time:
        time_diff = time.time() - last_click_time[user_id]
        if time_diff < CLICK_TIMEOUT:
            # Если пользователь кликнул слишком быстро, выводим предупреждение
            bot.reply_to(message, "Слишком быстро! Подождите немного...")
            # Запускаем отдельный поток для удаления сообщения
            threading.Thread(target=freeze_user, args=(message.chat.id, 1, None)).start()
            return
    last_click_time[user_id] = time.time()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Выбрать двигатель", callback_data='choose_engine'))
    bot.reply_to(message, "Привет. Я могу рассчитать ТТХ БПЛА для твоей конфигурации квадракоптера. Выберите действие:",
                 reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'reset')
def handle_reset(call):
    bot.answer_callback_query(call.id, "Возврат в главное меню")
    send_welcome(call.message)


# --------------------- Меню выбора двигателя ---------------------
@bot.callback_query_handler(func=lambda call: call.data == 'choose_engine')
def show_engines(call, page=1):
    user_id = call.from_user.id
    # Проверяем, заморожен ли пользователь
    if user_id in frozen_users and frozen_users[user_id]:
        bot.answer_callback_query(call.id, "Слишком много запросов! Подождите немного.")
        return

    # Ограничение запросов
    if user_id not in user_requests:
        user_requests[user_id] = []
    user_requests[user_id].append(time.time())
    if len(user_requests[user_id]) > REQUEST_LIMIT:
        # Замораживаем пользователя, если прошло 30 секунд с последней заморозки
        if user_id not in last_freeze_time or time.time() - last_freeze_time[user_id] >= 10:
            # Замораживаем пользователя
            freeze_message = bot.send_message(chat_id=call.message.chat.id, text="Пожалуйста, подождите...")
            threading.Thread(target=freeze_user, args=(call.message.chat.id, 10, freeze_message.message_id)).start()
            last_freeze_time[user_id] = time.time()
            return

    # Таймер для предотвращения спама
    if user_id in last_click_time:
        time_diff = time.time() - last_click_time[user_id]
        if time_diff < CLICK_TIMEOUT:
            # Если пользователь кликнул слишком быстро, выводим предупреждение
            bot.answer_callback_query(call.id, "Слишком много запросов! Подождите немного...")
            # Запускаем отдельный поток для удаления сообщения
            threading.Thread(target=freeze_user, args=(call.message.chat.id, 1, None)).start()
            return
    last_click_time[user_id] = time.time()
    if dvig_data:
        data_text = "Список двигателей:\n"
        start_index = (page - 1) * 7
        end_index = min(page * 7, len(dvig_data))

        markup = types.InlineKeyboardMarkup()
        for i, engine in enumerate(dvig_data[start_index:end_index]):
            markup.add(types.InlineKeyboardButton(f"{i + start_index + 1}. {engine}",
                                                  callback_data=f'engine_{i + start_index}'))

        if page > 1:
            markup.add(types.InlineKeyboardButton("Назад", callback_data=f'next_{page - 1}'))
        if end_index < len(dvig_data):
            markup.add(types.InlineKeyboardButton("Следующие", callback_data=f'next_{page + 1}'))
        markup.add(types.InlineKeyboardButton("Сброс", callback_data='reset'))

        bot.answer_callback_query(call.id, "Выбрано: Выбрать двигатель")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=data_text,
                              reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "Ошибка: список двигателей не загружен.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('next_'))
def handle_next_page(call):
    page = int(call.data.split('_')[1])
    show_engines(call, page)


# --------------------- Обработка выбора двигателя ---------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith('engine_'))
def handle_engine_selection(call):
    user_id = call.from_user.id
    # Проверяем, заморожен ли пользователь
    if user_id in frozen_users and frozen_users[user_id]:
        bot.answer_callback_query(call.id, "Большое количество запросов! Подождите немного.")
        return

    # Ограничение запросов
    if user_id not in user_requests:
        user_requests[user_id] = []
    user_requests[user_id].append(time.time())
    if len(user_requests[user_id]) > REQUEST_LIMIT:
        # Замораживаем пользователя, если прошло 30 секунд с последней заморозки
        if user_id not in last_freeze_time or time.time() - last_freeze_time[user_id] >= 10:
            # Замораживаем пользователя
            freeze_message = bot.send_message(chat_id=call.message.chat.id, text="Пожалуйста, подождите...")
            threading.Thread(target=freeze_user, args=(call.message.chat.id, 10, freeze_message.message_id)).start()
            last_freeze_time[user_id] = time.time()
            return

    # Таймер для предотвращения спама
    if user_id in last_click_time:
        time_diff = time.time() - last_click_time[user_id]
        if time_diff < CLICK_TIMEOUT:
            # Если пользователь кликнул слишком быстро, выводим предупреждение
            bot.answer_callback_query(call.id, "Слишком быстро! Подождите немного...")
            # Запускаем отдельный поток для удаления сообщения
            threading.Thread(target=freeze_user, args=(call.message.chat.id, 1, None)).start()
            return
    last_click_time[user_id] = time.time()

    engine_index = int(call.data.split('_')[1])
    if 0 <= engine_index < len(dvig_data):
        selected_engine = dvig_data[engine_index]
        show_engine_characteristics(call, engine_index, selected_engine)  # Вызываем новый обработчик
    else:
        bot.answer_callback_query(call.id, "Ошибка: неверный номер двигателя.")


# --------------------- Вывод характеристик двигателя ---------------------
def show_engine_characteristics(call, engine_index, selected_engine):
    # Извлекаем характеристики двигателя из строки
    parts = selected_engine.split('(')
    name = parts[0].strip()
    characteristics = parts[1].strip(')')

    # Поиск комбинации
    for i in range(1, len(akum_data) + 1):
        combination_key = f"combination{engine_index + 1}{i}"
        if combination_key in combination_data:
            combination = combination_data[combination_key]
            motor_characteristics = combination.get('Мотор', {})
            data_text = f"{engine_index + 1}. {name}\n{characteristics}\n\n(Характеристики выбранного двигателя):\n"
            for param, values in motor_characteristics.items():
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, dict):
                            data_text += f"  {param}: {value['Значение']} {value['Единица измерения']}\n"
                        else:
                            data_text += f"  {param}: {value}\n"
                else:
                    if isinstance(values, dict):
                        data_text += f"  {param}: {values['Значение']} {values['Единица измерения']}\n"
                    else:
                        data_text += f"  {param}: {values}\n"

            # Вывод меню выбора аккумулятора
            data_text += "\n\n⚫Выберите аккумулятор:⚫\n\n"  # Добавляем текст "Выберите аккумулятор" в конец
            markup = types.InlineKeyboardMarkup()
            for i, battery in enumerate(akum_data):
                markup.add(
                    types.InlineKeyboardButton(f"{i + 1}. {battery}", callback_data=f'battery_{engine_index}_{i}'))
            markup.add(types.InlineKeyboardButton("Сброс", callback_data='reset'))

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=data_text,
                                  reply_markup=markup)
            return  # Выходим из функции после нахождения комбинации

    # Если комбинация не найдена
    bot.send_message(chat_id=call.message.chat.id, text=f"Нет совместимых комбинаций для двигателя {engine_index + 1}")



# --------------------- Меню выбора аккумулятора ---------------------
def show_batteries(call, engine_index, selected_engine):
    if akum_data:
        data_text = f"Двигатель: {selected_engine}\n\nСписок аккумуляторов:\n"

        markup = types.InlineKeyboardMarkup()
        for i, battery in enumerate(akum_data):
            markup.add(types.InlineKeyboardButton(f"{i + 1}. {battery}", callback_data=f'battery_{engine_index}_{i}'))
        markup.add(types.InlineKeyboardButton("Сброс", callback_data='reset'))

        # Добавьте пробел в конец сообщения, чтобы избежать ошибки
        data_text += " "

        bot.answer_callback_query(call.id, "Выбрано: Выбрать аккумулятор")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=data_text,
                              reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "Ошибка: список аккумуляторов не загружен.")

    # --------------------- Обработка выбора комбинации ---------------------


@bot.callback_query_handler(func=lambda call: call.data.startswith('battery_'))
def handle_battery_selection(call):
    user_id = call.from_user.id
    # Проверяем, заморожен ли пользователь
    if user_id in frozen_users and frozen_users[user_id]:
        bot.answer_callback_query(call.id, "Много запросов! Подождите немного.")
        return

    # Ограничение запросов
    if user_id not in user_requests:
        user_requests[user_id] = []
    user_requests[user_id].append(time.time())
    if len(user_requests[user_id]) > REQUEST_LIMIT:
        # Замораживаем пользователя, если прошло 30 секунд с последней заморозки
        if user_id not in last_freeze_time or time.time() - last_freeze_time[user_id] >= 10:
            # Замораживаем пользователя
            freeze_message = bot.send_message(chat_id=call.message.chat.id, text="Пожалуйста, подождите...")
            threading.Thread(target=freeze_user, args=(call.message.chat.id, 10, freeze_message.message_id)).start()
            last_freeze_time[user_id] = time.time()
            return

    # Таймер для предотвращения спама
    if user_id in last_click_time:
        time_diff = time.time() - last_click_time[user_id]
        if time_diff < CLICK_TIMEOUT:
            # Если пользователь кликнул слишком быстро, выводим предупреждение
            bot.answer_callback_query(call.id, "Слишком много запросов! Подождите немного...")
            # Запускаем отдельный поток для удаления сообщения
            threading.Thread(target=freeze_user, args=(call.message.chat.id, 1, None)).start()
            return
    last_click_time[user_id] = time.time()

    engine_index, battery_index = map(int, call.data.split('_')[1:])
    if 0 <= engine_index < len(dvig_data) and 0 <= battery_index < len(akum_data):
        combination_key = f"combination{engine_index + 1}{battery_index + 1}"
        if combination_key in combination_data:
            combination = combination_data[combination_key]

            # Извлекаем числовые значения
            try:
                akkum_capacity = combination['Аккумулятор.']['Емкость банки']['Значение']
                hang_time_current = combination['Параметры ВМГ']['Ток  (Висение)']['Значение']

                # Рассчитываем время зависания
                hang_time = (akkum_capacity / 1000) / hang_time_current * 60
            except KeyError:
                data_text = "Ошибка: Не удалось получить данные о комбинации."
                bot.answer_callback_query(call.id, f"Выбран аккумулятор: {akum_data[battery_index]}")
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("В главное меню", callback_data='reset'))
                # Изменение отправки сообщения
                bot.send_message(chat_id=call.message.chat.id, text=data_text, reply_markup=markup)
                return

            # Формируем текст с основными характеристиками
            data_text = "Характеристики:\n"
            # Вывод только основных категорий
            for category in ["Основное", "Аккумулятор", "Мотор", "Пропеллер", "Коптер"]:
                if category in combination:
                    data_text += f"⚫{category}⚫\n"
                    for param, values in combination[category].items():
                        if isinstance(values, list):
                            for value in values:
                                if isinstance(value, dict):
                                    data_text += f"  {param}: {value['Значение']} {value['Единица измерения']}\n"
                                else:
                                    data_text += f"  {param}: {value}\n"
                        else:
                            if isinstance(values, dict):
                                data_text += f"  {param}: {values['Значение']} {values['Единица измерения']}\n"
                            else:
                                data_text += f"  {param}: {values}\n"

            # Добавляем время зависания (с форматированием)
            data_text += f"⚫Время зависания⚫: {hang_time:.2f} мин.\n"

            bot.answer_callback_query(call.id, f"Выбран аккумулятор: {akum_data[battery_index]}")
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("Показать все",
                                           callback_data=f'full_characteristics_{combination_key}'))  # Кнопка "Показать все"
            markup.add(types.InlineKeyboardButton("В главное меню", callback_data='reset'))
            # Изменение отправки сообщения
            bot.send_message(chat_id=call.message.chat.id, text=data_text, reply_markup=markup)
        else:
            bot.send_message(chat_id=call.message.chat.id, text="Ошибка: двигатель не совместим с этим аккумулятором.")
    else:
        bot.send_message(chat_id=call.message.chat.id, text="Ошибка: неверный номер аккумулятора.")


# ... (остальные обработчики)


# --------------------- Показать все характеристики ---------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith('full_characteristics_'))
def handle_full_characteristics(call):
    user_id = call.from_user.id
    # Проверяем, заморожен ли пользователь
    if user_id in frozen_users and frozen_users[user_id]:
        bot.answer_callback_query(call.id, "Много запросов! Подождите немного.")
        return

    # Ограничение запросов
    if user_id not in user_requests:
        user_requests[user_id] = []
    user_requests[user_id].append(time.time())
    if len(user_requests[user_id]) > REQUEST_LIMIT:
        # Замораживаем пользователя, если прошло 30 секунд с последней заморозки
        if user_id not in last_freeze_time or time.time() - last_freeze_time[user_id] >= 10:
            # Замораживаем пользователя
            freeze_message = bot.send_message(chat_id=call.message.chat.id, text="Пожалуйста, подождите...")
            threading.Thread(target=freeze_user, args=(call.message.chat.id, 10, freeze_message.message_id)).start()
            last_freeze_time[user_id] = time.time()
            return

    # Таймер для предотвращения спама
    if user_id in last_click_time:
        time_diff = time.time() - last_click_time[user_id]
        if time_diff < CLICK_TIMEOUT:
            # Если пользователь кликнул слишком быстро, выводим предупреждение
            bot.answer_callback_query(call.id, "Слишком много запросов! Подождите немного...")
            # Запускаем отдельный поток для удаления сообщения
            threading.Thread(target=freeze_user, args=(call.message.chat.id, 1, None)).start()
            return
    last_click_time[user_id] = time.time()

    combination_number = call.data.split('combination')[1]  # Извлекаем номер комбинации
    combination_key = f"combination{combination_number}"  # Формируем ключ
    if combination_key in combination_data:
        combination = combination_data[combination_key]

        # Извлекаем числовые значения
        try:
            akkum_capacity = combination['Аккумулятор.']['Емкость банки']['Значение']
            hang_time_current = combination['Параметры ВМГ']['Ток  (Висение)']['Значение']

            # Рассчитываем время зависания
            hang_time = (akkum_capacity / 1000) / hang_time_current * 60
        except KeyError:
            data_text = "Ошибка: Не удалось получить данные о комбинации."
            bot.answer_callback_query(call.id, f"Выбран аккумулятор: {akum_data[battery_index]}")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("В главное меню", callback_data='reset'))
            # Изменение отправки сообщения
            bot.send_message(chat_id=call.message.chat.id, text=data_text, reply_markup=markup)
            return

        data_text = "Полные характеристики:\n"
        for category, params in combination.items():
            data_text += f"⚫{category}⚫\n"
            for param, values in params.items():
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, dict):
                            data_text += f"  {param}: {value['Значение']} {value['Единица измерения']}\n"
                        else:
                            data_text += f"  {param}: {value}\n"
                else:
                    if isinstance(values, dict):
                        data_text += f"  {param}: {values['Значение']} {values['Единица измерения']}\n"
                    else:
                        data_text += f"  {param}: {values}\n"

        # Добавляем время зависания
        data_text += f"⚫Время зависания⚫: {hang_time:.2f} мин.\n"

        # Создаем клавиатуру с кнопкой "Сброс"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Сброс", callback_data='reset'))

        # Редактируем предыдущее сообщение вместо отправки нового
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=data_text,
                              reply_markup=markup)
    else:
        bot.send_message(chat_id=call.message.chat.id, text="Ошибка: комбинация не найдена.")


# --- Функция для "замораживания" пользователя ---
def freeze_user(chat_id, seconds, message_id=None):
    user_id = chat_id  # Предполагается, что chat_id совпадает с user_id
    frozen_users[user_id] = True
    if seconds >= 9:
        # Отправляем сообщение с таймером, если заморозка больше 10 секунд
        if message_id is not None:
            timer_message = bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                  text=f"Слишком много запросов, подождите: {seconds} секунд")
        else:
            timer_message = bot.send_message(chat_id=chat_id,
                                             text=f"Слишком много запросов, подождите: {seconds} секунд")
        for i in range(seconds - 1, 0, -1):
            time.sleep(1)
            if message_id is not None:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                      text=f"Слишком много запросов, подождите: {i - 1} секунд")
            else:
                bot.send_message(chat_id=chat_id, text=f"Слишком много запросов, подождите: {i - 1} секунд")

        # Удаляем таймер после завершения
        bot.delete_message(chat_id=chat_id, message_id=timer_message.message_id)
    else:
        # Не отправляем таймер, если заморозка меньше 10 секунд
        time.sleep(seconds)
    frozen_users[user_id] = False
    # Сбрасываем список запросов пользователя
    user_requests[user_id] = []


# --- Запуск бота ---

bot.polling(timeout=15)
