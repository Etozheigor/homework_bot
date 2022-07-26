from http import HTTPStatus
import time
import logging
import os
import requests
from telegram import Bot
from dotenv import load_dotenv
load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class ColorFilter(logging.Filter):
    """Кастомыный класс для выделения сообщений разным цветом."""

    COLOR = {
        "DEBUG": "GREEN",
        "INFO": "BLUE",
        "WARNING": "YELLOW",
        "ERROR": "ORANGE",
        "CRITICAL": "RED",
    }

    def filter(self, record):
        """Устанавливает цвет сообщения."""
        record.color = ColorFilter.COLOR[record.levelname]
        return True


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename='homework_bot.log',
    encoding='utf-8'
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addFilter(ColorFilter())

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[handler],
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def send_message(bot, message):
    """Отправляет сообщение с заданным текстом в чат Телеграм."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.info(f'Сообщение "{message}" успешно отправлено')


def get_api_answer(current_timestamp):
    """Возвращает ответ от сервера в виде словаря."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        logging.exception('Ошибка ответа сервера')
        raise Exception('Ошибка ответа сервера')
    return response.json()


def check_response(response):
    """Проверяет полученный ответ от сервера на корректность."""
    if response['homeworks'] is None:
        logging.exception('отсутствует ключ homeworks')
        raise Exception('отсутствует ключ homeworks')
    if type(response) != dict:
        raise Exception('Ответ не в формате словаря')
    elif len(response.keys()) == 0:
        raise Exception('Сервер венул пустой ответ')
    elif type(response['homeworks']) != list:
        raise Exception('Работы приходят не в виде списка')
    return response.get('homeworks')


def parse_status(homework):
    """Определяет статус домашней работы, возвращает сообщение об этом."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        logging.exception('отсутствует ключ homework_name')
    elif 'status' not in homework.keys():
        logging.exception('Отсутстует ключ status')
    elif homework_status not in HOMEWORK_STATUSES.keys():
        logging.exception('Недокументированный статус домашней работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие необходимых токенов в переменных окружения."""
    if PRACTICUM_TOKEN is None:
        logging.critical('Отсутствует токен Практикума в переменных окружения')
        return False
    elif TELEGRAM_TOKEN is None:
        logging.critical('Отсутствует токен Телеграма в переменных окружения')
        return False
    elif TELEGRAM_CHAT_ID is None:
        logging.critical('Отсутствует ID чата в переменных окружения')
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if check_tokens():
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if homeworks:
                    message = parse_status(homeworks[0])
                    send_message(bot, message)
                    current_timestamp = response.get('current_date')
                else:
                    logging.debug('Нет новых статусов работы')
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.exception(f'Сбой в работе программы: {error}')
                send_message(bot, message)
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
