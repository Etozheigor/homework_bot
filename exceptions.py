class DontSendException(Exception):
    """Класс для ошибок, о которых не нужно отправлять сообщение в телеграм."""

    pass


class StatusNot200Exception(Exception):
    """Класс для ошибоки, если статус ответа сервера не 200."""

    pass
