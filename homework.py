import os
import requests
import time
import logging
import sys
from http import HTTPStatus
from dotenv import load_dotenv

import telegram
from telegram.error import TelegramError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
STATUS_POLLING_PERIOD_IN_SECONDS = RETRY_PERIOD
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

log_format = '%(asctime)s, %(levelname)s, Функция - %(funcName)s, %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(handler)


def check_tokens():
    """Проверяет наличие токенов и номера чата."""
    tokens_dict = {'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
                   'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
                   'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID}
    sucsess = True
    for item in tokens_dict.items():
        token_name, token_value = item
        if not token_value:
            logger.critical(f'Переменная окружения {token_name} не найдена.')
            sucsess = False
    return sucsess


def send_message(bot, message):
    """Отправлет сообщение в TG."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение: {message}')
    except TelegramError as error:
        raise TelegramError(
            f'Ошибка при отправке сообщения: {error}'
        )


def get_api_answer(timestamp):
    """Получить статус домашней работы."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        raise Exception(f'Ошибка при получении ответа от API: {error}'
                        f'Параметры запроса: {HEADERS}, {payload}')
    if response.status_code != HTTPStatus.OK:
        raise Exception('Ошибка статуса ответа от API: '
                        f'Эндпоинт {ENDPOINT}, '
                        f'Код ответа API: {response.status_code}, '
                        f'Параметры запроса: {HEADERS}, {payload}, '
                        f'Ответ: {response}.')
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не является словарем.')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Список с домашними работами не обнаружен.')
    return homeworks


def parse_status(homework):
    """Извлекает статус работы и возращает строку для отправки в TG."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('В словаре "homework" не найден ключ "homework_name"')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('В словаре "homework" не найден ключ "status"')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Переменные окружения не найдены')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    list_sent_errors = []
    while True:
        try:
            api_answer = get_api_answer(timestamp)
            logger.debug('Ответ от API получен')
            timestamp = int(time.time())
            homeworks = check_response(api_answer)
            if len(homeworks) != 0:
                for homework in homeworks:
                    logger.debug(
                        f'Проверка {homeworks.index(homework) + 1} домашки'
                    )
                    message = parse_status(homework)
                    send_message(bot, message)
            logger.debug('Домашек нет, жду 10 минут')
            continue
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if str(error) not in list_sent_errors:
                list_sent_errors.append(str(error))
                send_message(bot, message)
        finally:
            time.sleep(STATUS_POLLING_PERIOD_IN_SECONDS)


if __name__ == '__main__':
    main()
