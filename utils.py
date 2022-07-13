from datetime import datetime

from pytz import timezone
from tinkoff.invest import MoneyValue

from exceptions import InvalidNumber


def handler(func):
    """Хендлеры имеют право не пробрасывать исключение вверх по иерархии, а осуществлять их обработку внутри себя"""

    def wrapper(msg):
        return func(msg)

    return wrapper


def localize(d: datetime) \
        -> datetime:
    return timezone('Europe/Moscow').localize(d)


def get_now() \
        -> datetime:
    return localize(datetime.now())


def parse_int(n: str) \
        -> int:
    try:
        return int(n)
    except ValueError:
        raise InvalidNumber()


def get_canonical_price(price: MoneyValue) -> float:
    return float(str(abs(price.units)) + "." + str(abs(price.nano)))


def int_to_rub(a: int) \
        -> str:
    return str(a) + " руб"
