class SendMessageExeption(Exception):
    """Класс ошибки отправки сообщения."""

    pass


class InvalidStatusError(Exception):
    """Класс ошибки статуса ответа отличного от 200."""

    pass


class GetResposneError(Exception):
    """Класс ошибки при получении ответа."""

    pass
