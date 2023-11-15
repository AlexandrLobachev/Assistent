import os
import requests
import time
import logging
import sys
from http import HTTPStatus
from dotenv import load_dotenv

import telegram


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    format=(
        '%(asctime)s, %(levelname)s, Функция - %(funcName)s, %(message)s'
    ),
    handlers=[logging.StreamHandler(sys.stdout), ])


def check_tokens():
    """Проверяет наличие токенов и номера чата."""
    tokens_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens_list:
        try:
            if len(token) == 0:
                logging.critical('Поле с токеном или чатом пусто')
                return False
        except TypeError:
            logging.critical('Токен или чат не обнаружен')
            return False
    return True


def send_message(bot, message):
    """Отправлет сообщение в TG."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение со статусом успешно отправлено')
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Получить статус домашней работы."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logging.error('Сбой в работе программы: '
                          f'Эндпоинт {ENDPOINT} недоступен. '
                          f'Код ответа API: {response.status_code}')
            raise Exception
        return response.json()
    except Exception:
        raise Exception


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError
    return homeworks


def parse_status(homework):
    """Извлекает статус работы и возращает строку для отправки в TG."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError
    if homework.get('status') not in HOMEWORK_VERDICTS:
        raise KeyError
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Переменные окружения не найдены')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    status = 'Работа еще не взята на проверку.'
    prev_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0 and prev_status != status:
                message = status
                send_message(bot, message)
                prev_status = status
            if len(homeworks) != 0:
                homework = homeworks[0]
                status = homework.get('status')
                if status != prev_status:
                    message = parse_status(homework)
                    send_message(bot, message)
                    prev_status = status
            else:
                continue
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
