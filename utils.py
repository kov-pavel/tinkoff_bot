from datetime import datetime
from decimal import Decimal

from pytz import timezone

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


def price_to_decimal(price) -> Decimal:
    return Decimal(str(price.units) + "." + str(price.nano))
