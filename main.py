
import telebot
import configparser
import random
from telebot import types, custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from db_conn import get_db_connection
from db_interaction import (
    initialize_db, ensure_user_exists, fill_common_words_table,
    get_random_words, check_word_existence, add_word_to_user,
    delete_user_word, update_word_to_user_dict
)

# Подключение к базе данных
get_db_connection()

# Инициализация базы данных
initialize_db()

print('Telegram bot is OK!...')

config = configparser.ConfigParser()
config.read('settings.ini')
token_bot = config['Tokens']['tg_bot']

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(token_bot, state_storage=state_storage)

# Проверка существования пользователя
ensure_user_exists(user_id=bot.get_me().id, username=bot.get_me().username)


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово 🔙'
    NEXT = 'Следующее слово ➡️'


# Состояния
class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    other_words = State()
    adding_new_word = State()
    saving_new_word = State()
    deleting_word = State()


# Общие слова для обучения
common_words = [
    ('Peace', 'Мир'), ('Green', 'Зелёный'), ('White', 'Белый'),
    ('Hello', 'Привет'), ('Car', 'Машина'), ('Sky', 'Небо'),
    ('Tree', 'Дерево'), ('Book', 'Книга'), ('Love', 'Любовь'),
    ('Friend', 'Друг'),('Plane', 'Самолет'),('Ball','Мяч'),('Game','Игра')
]

# Заполнение общего словаря
fill_common_words_table(common_words)


# Обработчики
@bot.message_handler(commands=['start', 'cards'])
def send_welcome(message):
    cid = message.chat.id
    username = message.chat.username or "Unknown"
    ensure_user_exists(cid, username)

    print("Starting bot for the first time...")

    # Отправка стикера и приветствие
    sti = open('welcome_benny.png', 'rb')
    bot.send_sticker(cid, sti)
    bot.send_message(cid, f"Приветствую, {message.from_user.first_name}!\nЯ {bot.get_me().first_name}! "
                          f"Приступаем к изучению английского языка 🇬🇧\nТакже можно использовать тренажёр,\nкак конструктор, "
                          f"и собирать свой собственный словарь для обучения.\nДля этого воспрользуйся инструментами:\n"
                          f"- добавить слово ➕\n"
                          f"- удалить слово 🔙\n"
                          f"Приступим ⬇️", parse_mode='html'
                     )

    create_cards(message)


def create_cards(message):
    cid = message.chat.id

    # Получаем случайные слова
    words = get_random_words(cid, limit=4)
    print(f"Случайные слова: {words}")

    if not words or len(words) < 4:
        bot.send_message(cid, "Нет доступных слов!\nДобавьте новые через 'Добавить слово ➕'.")
        print("Слов недостаточно для создания карточек.")
        return

    # Извлекаем целевое слово и другие варианты
    target_word, translate_word = words[0]
    other_words = [w[0] for w in words[1:]]

    # Перемешиваем варианты
    options = other_words + [target_word]
    random.shuffle(options)

    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(row_width=4)
    buttons = [types.KeyboardButton(option) for option in options]
    buttons.append(types.KeyboardButton(Command.NEXT))
    buttons.append(types.KeyboardButton(Command.ADD_WORD))
    buttons.append(types.KeyboardButton(Command.DELETE_WORD))
    markup.add(*buttons)

    main_menu_markup = types.ReplyKeyboardMarkup(row_width=2)
    main_menu_buttons = [
        types.KeyboardButton(Command.ADD_WORD),
        types.KeyboardButton(Command.DELETE_WORD),
        types.KeyboardButton(Command.NEXT)
    ]
    main_menu_markup.add(*main_menu_buttons)

    # Установка состояния для пользователя
    bot.set_state(user_id=message.from_user.id, chat_id=message.chat.id, state=MyStates.target_word)
    with bot.retrieve_data(user_id=message.from_user.id, chat_id=message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate_word

    # Отправляем сообщение
    greeting = f"Выбери перевод слова:\n🇷🇺 {translate_word}"
    bot.send_message(cid, greeting, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_word(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word_start(message):
    cid = message.chat.id
    bot.set_state(user_id=message.from_user.id, chat_id=cid, state=MyStates.adding_new_word)
    bot.send_message(cid, "Введите слово, которое вы хотите добавить, на английском:")


@bot.message_handler(state=MyStates.adding_new_word)
def add_translate_word(message):
    cid = message.chat.id
    word = message.text.strip().capitalize()

    # Проверяем, что слова нет в общем словаре
    if check_word_existence(word):
        bot.send_message(cid, "Это слово уже есть в общем словаре. Пожалуйста, введите другое слово.")
        return

    # Сохраняем слово в состоянии
    with bot.retrieve_data(user_id=message.from_user.id, chat_id=cid) as data:
        data['target_word'] = word

    bot.set_state(user_id=message.from_user.id, chat_id=cid, state=MyStates.saving_new_word)
    bot.send_message(cid, f"Теперь введите перевод для слова '{word}':")


@bot.message_handler(state=MyStates.saving_new_word)
def save_new_word(message):
    cid = message.chat.id
    translation = message.text.strip().capitalize()

    # Проверяем, что перевод не пустой
    if not translation:
        bot.send_message(cid, "Перевод не может быть пустым. Пожалуйста, введите перевод.")
        return

    try:
        # Извлекаем данные из состояния
        with bot.retrieve_data(user_id=message.from_user.id, chat_id=cid) as data:
            target_word = data.get('target_word').capitalize()

        if not target_word:
            bot.send_message(cid, "Ошибка! Попробуй снова начать с /start.")
            bot.delete_state(user_id=message.from_user.id, chat_id=cid)
            return

        # Сохраняем новое слово в персональный словарь пользователя
        add_word_to_user(message.from_user.id, target_word, translation)

        bot.send_message(cid, f"Слово '{target_word}' и его перевод '{translation}' успешно добавлены!")
    except Exception as e:
        print(f"Произошла ошибка при сохранении слова: {e}")
        bot.send_message(cid, f"Произошла ошибка при сохранении слова: {e}")
    finally:
        bot.delete_state(user_id=message.from_user.id, chat_id=cid)

    send_main_menu(cid)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word_start(message):
    cid = message.chat.id

    bot.set_state(user_id=message.from_user.id, chat_id=message.chat.id, state=MyStates.deleting_word)
    bot.send_message(cid, "Введите слово, которое хотите удалить, на английском:")


@bot.message_handler(state=MyStates.deleting_word)
def delete_word(message):
    cid = message.chat.id
    word_to_delete = message.text.strip().capitalize()

    # Удаляем слово и проверяем состояние
    word_to_delete = delete_user_word(message.from_user.id, word_to_delete)

    if word_to_delete:
        bot.send_message(cid, f"Слово '{word_to_delete[0]}' успешно удалено из вашего словаря!")
        print(f"Удалено слово: {word_to_delete[0]}")
    else:
        bot.send_message(cid, "Слово не найдено в вашем персональном словаре.")
        print("Слово не удалено.")
    bot.delete_state(user_id=message.from_user.id, chat_id=message.chat.id)
    send_main_menu(cid)


# Функция для отправки основного меню
def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = [
        types.KeyboardButton(Command.ADD_WORD),
        types.KeyboardButton(Command.DELETE_WORD),
        types.KeyboardButton(Command.NEXT)
    ]
    markup.add(*buttons)
    bot.send_message(chat_id, "Выберите дальнейшее действие:", reply_markup=markup)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    user_response = message.text.strip()
    print(f"Ответ пользователя: {user_response}")

    # Проверяем текущее состояние
    state = bot.get_state(user_id=message.from_user.id, chat_id=message.chat.id)
    print(f"Полученное состояние для пользователя {message.from_user.id}, чат {message.chat.id}: {state}")

    if state != MyStates.target_word.name:
        bot.send_message(message.chat.id, "Ошибка! Начните заново с /start.")
        return

    # Извлекаем данные из состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data.get('target_word')
        translate_word = data.get('translate_word')
        attempts = data.get('attempts', 0)
        print(f"Данные из состояний: target_word={target_word}, translate_word={translate_word}")

    if not target_word or not translate_word:
        bot.send_message(message.chat.id, "Ошибка! Попробуй снова начать с /start.")
        return

    # Если пользователь ответил правильно
    if user_response.strip().lower() == target_word.strip().lower():
        try:
            update_word_to_user_dict(message.from_user.id, target_word, translate_word)
            bot.send_message(message.chat.id, f"✅ Правильно!\n{target_word} => {translate_word}!")
        except ValueError as e:
            print(f"Ошибка при обновлении слова: {e}")
        data.clear()
        return

    # Если пользователь ответил неправильно
    attempts += 1
    data['attempts'] = attempts
    if attempts < 3:
        bot.send_message(
            message.chat.id, f"❌ Неправильно! Попробуй снова.\nПеревод слова: {translate_word}\n"
                             f"Попытка {attempts} из 3."
        )
    else:
        bot.send_message(
            message.chat.id, f"К сожалению, вы исчерпали попытки.\n"f"Правильный перевод: {target_word}"
        )
        data.clear()


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)