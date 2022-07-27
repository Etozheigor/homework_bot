class DontSendException(Exception):
    """Класс для ошибок, о которых не нужно отправлять сообщение в телеграм."""


class StatusNot200Exception(Exception):
    """Класс для ошибоки, если статус ответа сервера не 200."""
