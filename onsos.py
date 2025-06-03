import telebot
import random
import time
import json
import os

# Ваш токен бота
TOKEN = '7880474922:AAH8vQtpPvruTqltYQANnC54ZG6JxmBY_vM'
bot = telebot.TeleBot(TOKEN)

# Файл для сохранения данных
DATA_FILE = 'bot_data.json'

# Время ожидания между подоями в секундах (5 минут)
COOLDOWN_SECONDS = 5 * 60

# --- Настройки Казино ---
CASINO_SYMBOLS = ['🍒', '🍋', '🍇', '🔔', '💎', '7️⃣']
# Время ожидания между играми в казино (30 секунд)
CASINO_COOLDOWN_SECONDS = 30 

# Коэффициенты выигрыша
CASINO_PAYOUTS = {
    ('7️⃣', '7️⃣', '7️⃣'): 10,  # Джекпот
    ('💎', '💎', '💎'): 5,   # Высокий выигрыш
    ('🔔', '🔔', '🔔'): 3,   # Средний выигрыш
    ('🍒', '🍒', '🍒'): 2,   # Выигрыш по фруктам
    ('🍋', '🍋', '🍋'): 2,
    ('🍇', '🍇', '🍇'): 2,
    # Выигрыши за две одинаковые (более сложная логика, но можно упростить)
    # Здесь упрощено: две одинаковые будут обрабатываться после трех
}

# --- Функции для сохранения и загрузки данных ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # Инициализация всех необходимых полей, если они отсутствуют
                if 'last_milk_time_cow' not in data:
                    data['last_milk_time_cow'] = {}
                if 'last_milk_time_bull' not in data:
                    data['last_milk_time_bull'] = {}
                if 'last_casino_time' not in data: # Новое поле для казино
                    data['last_casino_time'] = {}
                if 'user_inventories' not in data:
                    data['user_inventories'] = {}
                if 'user_display_names' not in data:
                    data['user_display_names'] = {}

                # Убедимся, что новые поля инвентаря присутствуют и обновим старые
                for user_id in data['user_inventories']:
                    inventory = data['user_inventories'][user_id]
                    # Обновляем старые поля на новые, если они существуют
                    if 'won_deposits' in inventory: # Это старые литры выигрыша
                        inventory['casino_wins'] = 0 # Обнуляем или пробуем конвертировать
                        del inventory['won_deposits']
                    if 'lost_deposits' in inventory: # Это старые литры проигрыша
                        inventory['casino_losses'] = 0 # Обнуляем или пробуем конвертировать
                        del inventory['lost_deposits']
                    
                    # Проверяем и инициализируем новые поля
                    if 'casino_deposits' not in inventory:
                        inventory['casino_deposits'] = 0 
                    if 'casino_wins' not in inventory:
                        inventory['casino_wins'] = 0
                    if 'casino_losses' not in inventory:
                        inventory['casino_losses'] = 0
                    if 'casino_games_played' not in inventory:
                        inventory['casino_games_played'] = 0 
                return data
            except json.JSONDecodeError:
                print(f"Внимание: Ошибка чтения JSON файла '{DATA_FILE}'. Возможно, файл поврежден. Создаю новый пустой файл данных.")
                return {
                    'last_milk_time_cow': {},
                    'last_milk_time_bull': {},
                    'last_casino_time': {}, # Инициализируем при ошибке
                    'user_inventories': {},
                    'user_display_names': {}
                }
    print(f"Информация: Файл данных '{DATA_FILE}' не найден. Создаю новый.")
    return {
        'last_milk_time_cow': {},
        'last_milk_time_bull': {},
        'last_casino_time': {}, # Инициализируем здесь
        'user_inventories': {},
        'user_display_names': {}
    }

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Ошибка сохранения данных: {e}")

# Загружаем данные при старте бота
bot_data = load_data()

# --- Вспомогательная функция для обновления имени пользователя для отображения ---
def update_user_display_name(user_id, user_obj):
    current_display_name = bot_data['user_display_names'].get(user_id)
    new_display_name = ""

    if user_obj.username:
        new_display_name = "@" + user_obj.username
    elif user_obj.first_name:
        new_display_name = user_obj.first_name
        if user_obj.last_name:
            new_display_name += " " + user_obj.last_name
    else:
        new_display_name = "[Скрытый пользователь]"

    if current_display_name != new_display_name:
        bot_data['user_display_names'][user_id] = new_display_name
        save_data(bot_data) # Сохраняем только при изменении
        print(f"Обновлено имя для пользователя {user_id}: {new_display_name}") # Для отладки

# --- Обработчик команды /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    update_user_display_name(user_id, message.from_user)

    welcome_text = (
        "Привет, фермер! 🤠 Готов начать свой день на ферме?\n\n"
        "🐄 Используй команду /milk_cow, чтобы подоить свою милую корову и получить свежее молоко.\n"
        "🐂 А для тех, кто посмелее – /milk_bull, чтобы 'подоить' быка и получить ценную сперму!\n"
        "🎰 Попробуй удачу в казино! Ставь молоко с помощью /casino <сумма>.\n"
        "📦 А чтобы узнать, сколько у тебя добра, используй /inventory.\n"
        "🏆 Посмотри, кто круче всех – /leaders!"
    )
    bot.reply_to(message, welcome_text)

# --- Обработчик команды /milk_cow ---
@bot.message_handler(commands=['milk_cow'])
def milk_cow(message):
    user_id = str(message.from_user.id)
    update_user_display_name(user_id, message.from_user)

    current_time = time.time()

    if user_id in bot_data['last_milk_time_cow']:
        time_since_last_milk = current_time - bot_data['last_milk_time_cow'][user_id]
        if time_since_last_milk < COOLDOWN_SECONDS:
            remaining_time = int(COOLDOWN_SECONDS - time_since_last_milk)
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            bot.reply_to(message, f"Ой-ой! 😅 Ваша корова еще не готова к следующему подою. Ей нужно отдохнуть еще {minutes} мин {seconds} сек.")
            return

    bot_data['last_milk_time_cow'][user_id] = current_time

    milk_amount = random.randint(0, 15)

    if user_id not in bot_data['user_inventories']:
        # Инициализируем все новые поля
        bot_data['user_inventories'][user_id] = {'milk': 0, 'sperm': 0, 'casino_deposits': 0, 'casino_wins': 0, 'casino_losses': 0, 'casino_games_played': 0}
    bot_data['user_inventories'][user_id]['milk'] += milk_amount

    save_data(bot_data)

    if milk_amount > 10:
        bot.reply_to(message, f"Ура! 🎉 Вы подоили корову и получили целых {milk_amount} литров свежайшего молока! Отличная работа, фермер!")
    elif milk_amount > 0:
        bot.reply_to(message, f"Вы подоили корову и получили {milk_amount} литров молока. Неплохо! 🥛")
    else:
        bot.reply_to(message, f"Хм... 🤨 Вы подоили корову, но она дала всего {milk_amount} литров молока. Может, повезет в следующий раз!")

# --- Обработчик команды /milk_bull ---
@bot.message_handler(commands=['milk_bull'])
def milk_bull(message):
    user_id = str(message.from_user.id)
    update_user_display_name(user_id, message.from_user)

    current_time = time.time()

    if user_id in bot_data['last_milk_time_bull']:
        time_since_last_milk = current_time - bot_data['last_milk_time_bull'][user_id]
        if time_since_last_milk < COOLDOWN_SECONDS:
            remaining_time = int(COOLDOWN_SECONDS - time_since_last_milk)
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            bot.reply_to(message, f"Ух ты! 🐂 Бычок еще не восстановился после прошлого раза. Ему нужно еще {minutes} мин {seconds} сек.")
            return

    bot_data['last_milk_time_bull'][user_id] = current_time

    sperm_amount = random.randint(0, 15)

    if user_id not in bot_data['user_inventories']:
        # Инициализируем все новые поля
        bot_data['user_inventories'][user_id] = {'milk': 0, 'sperm': 0, 'casino_deposits': 0, 'casino_wins': 0, 'casino_losses': 0, 'casino_games_played': 0}
    bot_data['user_inventories'][user_id]['sperm'] += sperm_amount

    save_data(bot_data)

    if sperm_amount > 10:
        bot.reply_to(message, f"Впечатляюще! 💪 Вы 'подоили' быка и получили целых {sperm_amount} литров элитной спермы! Да это же сокровище фермы!")
    elif sperm_amount > 0:
        bot.reply_to(message, f"Вы 'подоили' быка и получили {sperm_amount} литров спермы. Достойно! 💦")
    else:
        bot.reply_to(message, f"Упс... 😬 Вы попытались 'подоить' быка, но он оказался не в настроении и дал всего {sperm_amount} литров. Не расстраивайся, такое бывает!")

# --- Обработчик команды /inventory ---
@bot.message_handler(commands=['inventory'])
def show_inventory(message):
    user_id = str(message.from_user.id)
    update_user_display_name(user_id, message.from_user)

    if user_id in bot_data['user_inventories']:
        inventory = bot_data['user_inventories'][user_id]
        milk = inventory.get('milk', 0)
        sperm = inventory.get('sperm', 0)
        casino_games_played = inventory.get('casino_games_played', 0) 
        casino_wins = inventory.get('casino_wins', 0)
        casino_losses = inventory.get('casino_losses', 0)

        bot.reply_to(message, f"Ваша стата, фермер:\n"
                                f"Молоко 🥛 - {milk} л\n"
                                f"Сперма 💦 - {sperm} л\n"
                                f"Сыграно в казик 🎰 - {casino_games_played} раз\n" 
                                f"Выигранных игр 👍 - {casino_wins} раз\n"
                                f"Проигранных игр 👎 - {casino_losses} раз")
    else:
        bot.reply_to(message, "Ваша стата пока пуста! 😔 Начните 'доить' корову или быка.")

# --- Обработчик команды /casino ---
@bot.message_handler(commands=['casino'])
def play_casino(message):
    user_id = str(message.from_user.id)
    update_user_display_name(user_id, message.from_user)

    current_time = time.time()

    # Проверка таймера для казино
    if user_id in bot_data['last_casino_time']:
        time_since_last_casino = current_time - bot_data['last_casino_time'][user_id]
        if time_since_last_casino < CASINO_COOLDOWN_SECONDS:
            remaining_time = int(CASINO_COOLDOWN_SECONDS - time_since_last_casino)
            bot.reply_to(message, f"Погодите! ⏳ Казино ещё не открылось для вас. Подождите ещё {remaining_time} секунд.")
            return

    # Обновляем время последней игры в казино
    bot_data['last_casino_time'][user_id] = current_time

    if user_id not in bot_data['user_inventories']:
        # Инициализируем все новые поля
        bot_data['user_inventories'][user_id] = {'milk': 0, 'sperm': 0, 'casino_deposits': 0, 'casino_wins': 0, 'casino_losses': 0, 'casino_games_played': 0}

    # Проверяем, есть ли ставка
    try:
        bet_amount = int(message.text.split()[1])
        if bet_amount <= 0:
            bot.reply_to(message, "Ставка должна быть положительным числом! 🤷‍♂️")
            return
    except (IndexError, ValueError):
        bot.reply_to(message, "Пожалуйста, укажите сумму ставки молоком, например: `/casino 10`")
        return

    user_milk = bot_data['user_inventories'][user_id]['milk']

    if user_milk < bet_amount:
        bot.reply_to(message, f"У вас недостаточно молока для такой ставки! У вас есть только {user_milk} л. 🥛")
        return

    # Списываем ставку
    bot_data['user_inventories'][user_id]['milk'] -= bet_amount
    bot_data['user_inventories'][user_id]['casino_deposits'] += bet_amount # Это поле все еще отслеживает общую сумму в литрах
    bot_data['user_inventories'][user_id]['casino_games_played'] += 1 # Увеличиваем счетчик игр

    # --- ИГРА В КАЗИНО (ЭМОДЗИ СЛОТ) ---
    reels = [random.choice(CASINO_SYMBOLS) for _ in range(3)]
    result_str = " ".join(reels)
    winnings = 0
    message_text = f"🎰 Крутим барабаны...\n\n{result_str}\n\n"

    # Проверка выигрышных комбинаций
    # Сначала проверяем три одинаковых
    if reels[0] == reels[1] == reels[2]:
        payout_multiplier = CASINO_PAYOUTS.get(tuple(reels), 0)
        if payout_multiplier > 0:
            winnings = bet_amount * payout_multiplier
            message_text += f"🎉 **ТРИ ОДИНАКОВЫХ!** Вы выиграли {winnings} литров молока!\n"
        else: # На случай, если символ не прописан в CASINO_PAYOUTS для трех
            winnings = int(bet_amount * 1.5) # Дефолтный выигрыш за 3 одинаковых, если не указан
            message_text += f"🥳 **ТРИ ОДИНАКОВЫХ!** Вы выиграли {winnings} литров молока!\n"
    # Затем проверяем две одинаковые
    elif (reels[0] == reels[1] or
          reels[0] == reels[2] or
          reels[1] == reels[2]):
        winnings = int(bet_amount * 1.5) # Выигрыш в 1.5 раза от ставки
        message_text += f"👍 **ДВЕ ОДИНАКОВЫХ!** Вы выиграли {winnings} литров молока!\n"
    else:
        message_text += "💔 Увы, ничего не совпало. Вы проиграли.\n"

    if winnings > 0:
        bot_data['user_inventories'][user_id]['milk'] += winnings
        bot_data['user_inventories'][user_id]['casino_wins'] += 1 # Увеличиваем счетчик выигрышей
    else:
        bot_data['user_inventories'][user_id]['casino_losses'] += 1 # Увеличиваем счетчик проигрышей


    message_text += f"Ваш текущий баланс: {bot_data['user_inventories'][user_id]['milk']} л. 🥛"
    bot.reply_to(message, message_text, parse_mode='Markdown')

    save_data(bot_data)


# --- Обработчик команды /leaders ---
@bot.message_handler(commands=['leaders'])
def show_leaders(message):
    leaderboard_milk = []
    leaderboard_sperm = []
    leaderboard_most_wins = [] # Для топ игроков по количеству побед

    # Собираем данные для таблицы лидеров
    for user_id, inventory in bot_data['user_inventories'].items():
        display_name = bot_data['user_display_names'].get(user_id, f"Пользователь_{user_id}")
        milk = inventory.get('milk', 0)
        sperm = inventory.get('sperm', 0)
        
        casino_wins_count = inventory.get('casino_wins', 0) # Количество побед
        
        leaderboard_milk.append({'display_name': display_name, 'amount': milk})
        leaderboard_sperm.append({'display_name': display_name, 'amount': sperm})
        leaderboard_most_wins.append({'display_name': display_name, 'amount': casino_wins_count}) # Добавляем для казино по количеству побед

    # Сортируем по убыванию количества
    leaderboard_milk.sort(key=lambda x: x['amount'], reverse=True)
    leaderboard_sperm.sort(key=lambda x: x['amount'], reverse=True)
    leaderboard_most_wins.sort(key=lambda x: x['amount'], reverse=True) # Сортируем по количеству выигрышей

    # Формируем сообщение для молока
    milk_leaders_text = "🏆 **ТОП-10 Фермеров по Молоку** 🥛\n"
    if not leaderboard_milk or leaderboard_milk[0]['amount'] == 0:
        milk_leaders_text += "Пока никто не подоил ни капли молока. Будь первым! 🌟"
    else:
        for i, entry in enumerate(leaderboard_milk[:10]):
            rank = i + 1
            milk_leaders_text += f"{rank}. {entry['display_name']}: {entry['amount']} л\n"

    # Формируем сообщение для спермы
    sperm_leaders_text = "\n\n💦 **ТОП-10 Асов по Сперме** 🐂\n"
    if not leaderboard_sperm or leaderboard_sperm[0]['amount'] == 0:
        sperm_leaders_text += "Здесь пока пусто. Стань легендой! 🔥"
    else:
        for i, entry in enumerate(leaderboard_sperm[:10]):
            rank = i + 1
            sperm_leaders_text += f"{rank}. {entry['display_name']}: {entry['amount']} л\n"

    # Формируем сообщение для казино (по количеству побед)
    casino_leaders_text = "\n\n🎰 **ТОП-10 Удачливых Игроков Казино** 🍀\n"
    if not leaderboard_most_wins or leaderboard_most_wins[0]['amount'] == 0:
        casino_leaders_text += "Никто еще не сорвал куш в казино. Может, ты первый? ✨"
    else:
        for i, entry in enumerate(leaderboard_most_wins[:10]):
            rank = i + 1
            casino_leaders_text += f"{rank}. {entry['display_name']}: {entry['amount']} побед\n"

    bot.reply_to(message, milk_leaders_text + sperm_leaders_text + casino_leaders_text, parse_mode='Markdown')


# Запуск бота
print("Бот запущен...")
bot.polling(none_stop=True)
