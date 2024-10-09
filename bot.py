import requests
from bs4 import BeautifulSoup
import telebot
import schedule
import time
import threading

# Укажите токен вашего бота
TELEGRAM_BOT_TOKEN = '----------------------------------------------'

# Создаем объект бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

CHANNELS = ['-1002058890432']

# Список банков, которые нужно оставить
TARGET_BANKS = {
    'СберБанк': None,
    'Банк ВТБ': None,
    'Банк «Открытие»': None,
    'Приморье': None,
    'ББР Банк': None,
    'Совкомбанк': None,
    'Россельхозбанк': None,
    'Альфа-Банк': None
}

def get_currency_rates():
    url = 'https://ru.myfin.by/currency/cny/moskva'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверка успешности запроса
        soup = BeautifulSoup(response.text, 'html.parser')

        rates = {}
        # Ищем все строки с курсами валют
        rows = soup.find_all('tr', class_=lambda x: x and 'row body' in x)
        if not rows:
            print("Не удалось найти строки с курсами валют.")
            return rates

        for row in rows:
            bank_name_tag = row.find('a', class_='bank_link')
            if bank_name_tag:
                bank_name = bank_name_tag.text.strip()
                if bank_name in TARGET_BANKS:
                    # Ищем значения продажи юаня
                    rate_tags = row.find_all('td', class_='CNY')
                    if len(rate_tags) >= 2:
                        selling_rate = rate_tags[1].text.strip()
                        rates[bank_name] = selling_rate

        return rates

    except requests.exceptions.RequestException as e:
        print(f"Произошла ошибка при запросе к сайту: {e}")
        return {}

def send_rates_to_channels():
    rates = get_currency_rates()
    if rates:
        message_lines = ["Текущие курсы юаня к рублю:", ""]
        for bank_name in TARGET_BANKS.keys():
            if rates.get(bank_name):
                message_lines.append(f"{bank_name}: {rates[bank_name]} руб.")
        message_text = "\n".join(message_lines)
    else:
        message_text = "Не удалось получить курсы. Попробуйте позже."

    for channel_id in CHANNELS:
        try:
            bot.send_message(channel_id, message_text)
        except Exception as e:
            print(f"Ошибка отправки сообщения в канал {channel_id}: {e}")
            time.sleep(5)
            bot.send_message(channel_id, message_text)  # Повторная попытка

def schedule_tasks():
    # Настраиваем расписание для отправки сообщений с учетом разницы во времени (сервер на 3 часа меньше Москвы)
    schedule.every().day.at("07:00").do(send_rates_to_channels)  # 10:00 по Москве
    schedule.every().day.at("09:00").do(send_rates_to_channels)  # 12:00 по Москве
    schedule.every().day.at("12:00").do(send_rates_to_channels)  # 15:00 по Москве

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    # Запуск задач по расписанию
    schedule_tasks()

    # Запуск планировщика в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    # Запуск бота с обработкой ошибок
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=20)
        except Exception as e:
            print(f"Ошибка в polling: {e}")
            time.sleep(15)  # Задержка перед перезапуском

@bot.message_handler(commands=['start'])
def send_welcome(message):
    print("Команда /start получена")
    bot.reply_to(message, 'Привет! Используйте команду /get_rates, чтобы получить текущие курсы продажи юаня.')

@bot.message_handler(commands=['get_rates'])
def send_manual_rates(message):
    print("Команда /get_rates получена")
    send_rates_to_channels()
    bot.reply_to(message, "Курсы отправлены в каналы.")

if __name__ == '__main__':
    main()
