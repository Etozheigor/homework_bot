from msilib.schema import Error
import time
import logging
import os
import requests
from telegram import ReplyKeyboardMarkup, Bot
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 6
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    

def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    return response.json()


def check_response(response):

    try:
        return response.get('homeworks')
    except len(response.get('homeworks')) < 1: 
        raise TypeError
    except type(response) != dict:
        raise TypeError
    except type(response.get('homeworks')) != list:
        raise TypeError
    
        
    


def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    print(homework_status)

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    if (os.getenv(PRACTICUM_TOKEN) and os.getenv(TELEGRAM_TOKEN) and os.getenv(TELEGRAM_CHAT_ID)) is not None:
        return True
    return False

def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if check_response(response) is not None:
                message = parse_status(check_response(response)[0])
                send_message(bot, message)
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
