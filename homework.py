import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot

from exceptions import DontSendException

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
handler = logging.FileHandler(
    filename='homework_bot.log',
    encoding='utf-8')
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s')
logger.addFilter(ColorFilter())
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[handler],
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def send_message(bot: Bot, message: str) -> None:
    """Отправляет сообщение с заданным текстом в чат Телеграм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Начата отправка сообщения "{message}"')
    except Exception:
        new_message = 'Сбой при отправке сообщения'
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=new_message)
        logging.info(f'Начата отправка сообщения "{new_message}"')
    else:
        logging.info(f'Успешно отправлено сообщение: "{new_message}"')


def get_api_answer(current_timestamp: int) -> dict:
    """Возвращает ответ от сервера в виде словаря."""
    # timestamp = current_timestamp or int(time.time())
    # params = {'from_date': timestamp}
    # try:
    #     response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    #     logging.info('Начало запроса к API')
    #     logging.debug('Параметры запроса к API:'
    #                   f'url={ENDPOINT}, headers={HEADERS}, params={params}')
    #     if response.status_code != HTTPStatus.OK:
    #         raise Exception('Ошибка ответа сервера')
    # except Exception:
    #     return None
    # else:
    #     return response.json()

    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        logging.exception('Ошибка ответа сервера')
        logging.debug('Параметры запроса к API:'
                      f'url={ENDPOINT}, headers={HEADERS}, params={params}')
        raise Exception('Ошибка ответа сервера')
    return response.json()


def check_response(response: dict) -> list:
    """Проверяет полученный ответ от сервера на корректность."""
    if response['homeworks'] is None:
        logging.exception('отсутствует ключ homeworks')
        raise Exception('отсутствует ключ homeworks')
    if not isinstance(response, dict):
        raise DontSendException('Ответ не в формате словаря')
    elif len(response.keys()) == 0:
        raise DontSendException('Сервер венул пустой ответ')
    elif not isinstance(response['homeworks'], list):
        raise DontSendException('Работы приходят не в виде списка')
    return response.get('homeworks')


def parse_status(homework: list) -> dict:
    """Определяет статус домашней работы, возвращает сообщение об этом."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('В словаре отсутствует ключ homeworl_name')
    elif 'status' not in homework.keys():
        raise KeyError('В словаре отсутствует ключ status')
    elif homework_status not in HOMEWORK_STATUSES.keys():
        raise ValueError('Недокументированный статус домашней работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет наличие необходимых токенов в переменных окружения."""
    tokens_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if all([x is not None for x in tokens_list]):
        return True
    else:
        return False


def main() -> None:
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logging.critical('Отсутствует нужный токен в переменных окружения')
        sys.exit('Отсутствует нужный токен в переменных окружения')
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
        except DontSendException as error:
            logging.exception(f'Сбой в работе программы: {error}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(f'Сбой в работе программы: {error}')
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
