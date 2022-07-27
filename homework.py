import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import DontSendException, StatusNot200Exception

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
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(filename='homework_bot.log',
                            encoding='utf-8'),
        logging.StreamHandler()],
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение с заданным текстом в чат Телеграм."""
    try:
        logging.info(f'Начата отправка сообщения "{message}"')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError:
        raise telegram.error.TelegramError


def get_api_answer(current_timestamp: int) -> dict:
    """Возвращает ответ от сервера в виде словаря."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logging.info('Начало запроса к API')
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise StatusNot200Exception('Статус ответа сервера не 200')
    except StatusNot200Exception:
        raise StatusNot200Exception('Статус ответа сервера не 200')
    except Exception:
        raise Exception('Cбой при запросе к эндпоинту')
    else:
        return response.json()


def check_response(response: dict) -> list:
    """Проверяет полученный ответ от сервера на корректность."""
    if response['current_date'] is None:
        raise Exception('отсутствует ключ current_date')
    if not isinstance(response, dict):
        raise DontSendException('Ответ не в формате словаря')
    else:
        if response.get('homeworks') is None:
            raise Exception('отсутствует ключ homeworks')
    if len(response.keys()) == 0:
        raise DontSendException('Сервер венул пустой ответ')
    if not isinstance(response['homeworks'], list):
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
    tokens_list = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,)
    return all(tokens_list)


def main() -> None:
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        no_tokens_message = 'Отсутствует нужный токен в переменных окружения'
        logging.critical(no_tokens_message)
        sys.exit(no_tokens_message)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            logging.debug('Параметры запроса к API:'
                          f'url={ENDPOINT}, headers={HEADERS},'
                          f'params={get_api_answer.params}')
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                logging.info(f'Успешно отправлено сообщение: "{message}"')
                current_timestamp = response.get('current_date')
            else:
                logging.debug('Нет новых статусов работы')
        except DontSendException as error:
            logging.exception(f'Сбой в работе программы: {error}')
        except (StatusNot200Exception, Exception) as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(f'Сбой в работе программы: {error}')
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
