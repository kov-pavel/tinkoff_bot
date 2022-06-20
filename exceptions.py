class NotEnoughArguments(Exception):
    def __init__(self):
        self.message = "Неполное число входных аргументов!"


class InvalidNumber(Exception):
    def __init__(self):
        self.message = "Указано число неверного формата!"


class InvalidDate(Exception):
    def __init__(self):
        self.message = "Указана некорректная дата!"


class InvalidTinkoffToken(Exception):
    def __init__(self):
        self.message = "Нет пользователя с таким Tinkoff API token!"


class InvalidPortfolioID(Exception):
    def __init__(self):
        self.message = "Нет портфеля с таким ID!"
